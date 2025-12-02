#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
数据库管理模块路由

本模块提供数据库的创建、管理、备份、还原等功能。
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import os
import subprocess
import time
import datetime
import json
import psycopg2
import mysql.connector
from werkzeug.utils import secure_filename

from app import db, bcrypt
from app.models import Database, User
from app.databases.forms import DatabaseForm, DatabaseBackupForm
from app.databases.utils import (
    get_database_types, get_database_info, create_mysql_database, create_postgresql_database,
    backup_database, restore_database, delete_database, change_database_password
)

# 创建蓝图
databases = Blueprint('databases', __name__, template_folder='templates')


@databases.route('/databases')
@login_required
def database_management():
    """数据库管理页面"""
    # 获取所有数据库信息
    databases = Database.query.all()
    
    # 获取数据库类型列表
    db_types = get_database_types()
    
    return render_template('databases/databases.html', databases=databases, db_types=db_types)


@databases.route('/databases/create', methods=['GET', 'POST'])
@login_required
def create_database():
    """创建新数据库"""
    form = DatabaseForm()
    
    # 获取数据库类型列表
    db_types = get_database_types()
    form.db_type.choices = [(db_type, db_type) for db_type in db_types]
    
    if form.validate_on_submit():
        try:
            # 根据数据库类型创建数据库
            if form.db_type.data == 'MySQL':
                success, message = create_mysql_database(
                    db_name=form.db_name.data,
                    db_user=form.db_user.data,
                    db_password=form.db_password.data
                )
            elif form.db_type.data == 'PostgreSQL':
                success, message = create_postgresql_database(
                    db_name=form.db_name.data,
                    db_user=form.db_user.data,
                    db_password=form.db_password.data
                )
            else:
                flash('不支持的数据库类型', 'danger')
                return redirect(url_for('databases.database_management'))
            
            if success:
                # 保存数据库信息到本地数据库
                db_instance = Database(
                    name=form.db_name.data,
                    user=form.db_user.data,
                    password=bcrypt.generate_password_hash(form.db_password.data).decode('utf-8'),
                    db_type=form.db_type.data,
                    created_at=datetime.datetime.utcnow(),
                    created_by=current_user.username
                )
                db.session.add(db_instance)
                db.session.commit()
                
                flash(f'数据库 {form.db_name.data} 创建成功', 'success')
                return redirect(url_for('databases.database_management'))
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'创建数据库时发生错误: {str(e)}', 'danger')
    
    return render_template('databases/create_database.html', form=form)


@databases.route('/databases/<int:db_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_database(db_id):
    """编辑数据库信息"""
    db_instance = Database.query.get_or_404(db_id)
    form = DatabaseForm(obj=db_instance)
    
    # 获取数据库类型列表
    db_types = get_database_types()
    form.db_type.choices = [(db_type, db_type) for db_type in db_types]
    
    if form.validate_on_submit():
        try:
            # 更新数据库信息
            db_instance.name = form.db_name.data
            db_instance.user = form.db_user.data
            
            # 如果密码有修改，则更新密码
            if form.db_password.data:
                # 更新数据库实际密码
                success, message = change_database_password(
                    db_type=db_instance.db_type,
                    db_name=db_instance.name,
                    db_user=db_instance.user,
                    new_password=form.db_password.data
                )
                
                if success:
                    # 更新本地数据库中的密码
                    db_instance.password = bcrypt.generate_password_hash(form.db_password.data).decode('utf-8')
                else:
                    flash(message, 'danger')
                    return redirect(url_for('databases.edit_database', db_id=db_id))
            
            db.session.commit()
            flash(f'数据库 {db_instance.name} 信息更新成功', 'success')
            return redirect(url_for('databases.database_management'))
        except Exception as e:
            flash(f'更新数据库信息时发生错误: {str(e)}', 'danger')
    
    return render_template('databases/edit_database.html', form=form, db_instance=db_instance)


@databases.route('/databases/<int:db_id>/delete', methods=['POST'])
@login_required
def delete_database_route(db_id):
    """删除数据库"""
    db_instance = Database.query.get_or_404(db_id)
    
    try:
        # 删除实际的数据库
        success, message = delete_database(
            db_type=db_instance.db_type,
            db_name=db_instance.name
        )
        
        if success:
            # 从本地数据库中删除记录
            db.session.delete(db_instance)
            db.session.commit()
            flash(f'数据库 {db_instance.name} 删除成功', 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        flash(f'删除数据库时发生错误: {str(e)}', 'danger')
    
    return redirect(url_for('databases.database_management'))


@databases.route('/databases/<int:db_id>/info')
@login_required
def database_info(db_id):
    """查看数据库详细信息"""
    db_instance = Database.query.get_or_404(db_id)
    
    # 获取数据库详细信息
    try:
        db_info = get_database_info(
            db_type=db_instance.db_type,
            db_name=db_instance.name,
            db_user=db_instance.user,
            db_password=bcrypt.check_password_hash(db_instance.password, request.args.get('password'))
        )
    except Exception as e:
        flash(f'获取数据库信息失败: {str(e)}', 'danger')
        db_info = None
    
    return render_template('databases/database_info.html', db_instance=db_instance, db_info=db_info)


@databases.route('/databases/<int:db_id>/backups')
@login_required
def database_backups(db_id):
    """数据库备份管理页面"""
    db_instance = Database.query.get_or_404(db_id)
    
    # 这里应该从数据库或文件系统获取备份列表
    # 暂时返回空列表
    backups = []
    
    return render_template('databases/database_backups.html', db_instance=db_instance, backups=backups)


@databases.route('/databases/<int:db_id>/backup', methods=['GET', 'POST'])
@login_required
def create_backup(db_id):
    """创建数据库备份"""
    db_instance = Database.query.get_or_404(db_id)
    form = DatabaseBackupForm()
    
    if form.validate_on_submit():
        try:
            # 解密数据库密码
            if form.password.data:
                if bcrypt.check_password_hash(db_instance.password, form.password.data):
                    db_password = form.password.data
                else:
                    flash('密码错误', 'danger')
                    return redirect(url_for('databases.create_backup', db_id=db_id))
            else:
                flash('请输入数据库密码', 'danger')
                return redirect(url_for('databases.create_backup', db_id=db_id))
            
            # 创建备份
            success, message = backup_database(
                db_type=db_instance.db_type,
                db_name=db_instance.name,
                db_user=db_instance.user,
                db_password=db_password,
                backup_name=form.backup_name.data
            )
            
            if success:
                flash(f'数据库备份成功: {message}', 'success')
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'创建备份时发生错误: {str(e)}', 'danger')
    
    return render_template('databases/create_backup.html', form=form, db_instance=db_instance)


@databases.route('/databases/<int:db_id>/restore', methods=['GET', 'POST'])
@login_required
def restore_backup(db_id):
    """从备份还原数据库"""
    db_instance = Database.query.get_or_404(db_id)
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            backup_file = request.form.get('backup_file')
            db_password = request.form.get('password')
            
            if not backup_file:
                flash('请选择备份文件', 'danger')
                return redirect(url_for('databases.restore_backup', db_id=db_id))
            
            if not db_password:
                flash('请输入数据库密码', 'danger')
                return redirect(url_for('databases.restore_backup', db_id=db_id))
            
            # 验证密码
            if not bcrypt.check_password_hash(db_instance.password, db_password):
                flash('密码错误', 'danger')
                return redirect(url_for('databases.restore_backup', db_id=db_id))
            
            # 还原数据库
            success, message = restore_database(
                db_type=db_instance.db_type,
                db_name=db_instance.name,
                db_user=db_instance.user,
                db_password=db_password,
                backup_file=backup_file
            )
            
            if success:
                flash(f'数据库还原成功: {message}', 'success')
            else:
                flash(message, 'danger')
        except Exception as e:
            flash(f'还原数据库时发生错误: {str(e)}', 'danger')
    
    # 获取备份文件列表
    backups_dir = os.path.join('app', 'static', 'backups', db_instance.name)
    if os.path.exists(backups_dir):
        backups = [f for f in os.listdir(backups_dir) if os.path.isfile(os.path.join(backups_dir, f))]
    else:
        backups = []
    
    return render_template('databases/restore_backup.html', db_instance=db_instance, backups=backups)


@databases.route('/databases/<int:db_id>/download/<backup_file>')
@login_required
def download_backup(db_id, backup_file):
    """下载数据库备份文件"""
    db_instance = Database.query.get_or_404(db_id)
    
    # 安全检查
    backup_file = secure_filename(backup_file)
    backup_path = os.path.join('app', 'static', 'backups', db_instance.name, backup_file)
    
    if not os.path.exists(backup_path):
        flash('备份文件不存在', 'danger')
        return redirect(url_for('databases.database_backups', db_id=db_id))
    
    # 返回文件下载
    return send_file(backup_path, as_attachment=True, download_name=backup_file)


@databases.route('/databases/<int:db_id>/delete_backup/<backup_file>', methods=['POST'])
@login_required
def delete_backup_file(db_id, backup_file):
    """删除备份文件"""
    db_instance = Database.query.get_or_404(db_id)
    
    # 安全检查
    backup_file = secure_filename(backup_file)
    backup_path = os.path.join('app', 'static', 'backups', db_instance.name, backup_file)
    
    if not os.path.exists(backup_path):
        flash('备份文件不存在', 'danger')
        return redirect(url_for('databases.database_backups', db_id=db_id))
    
    try:
        os.remove(backup_path)
        flash('备份文件删除成功', 'success')
    except Exception as e:
        flash(f'删除备份文件时发生错误: {str(e)}', 'danger')
    
    return redirect(url_for('databases.database_backups', db_id=db_id))


@databases.route('/databases/check_name', methods=['POST'])
@login_required
def check_database_name():
    """检查数据库名称是否已存在"""
    db_name = request.json.get('db_name')
    
    # 检查本地数据库中是否存在同名数据库
    existing_db = Database.query.filter_by(name=db_name).first()
    
    # 检查实际数据库中是否存在同名数据库
    try:
        # 检查MySQL
        mysql_check = subprocess.run([
            'mysql', '-e', f'SHOW DATABASES LIKE "{db_name}";'
        ], capture_output=True, text=True)
        
        # 检查PostgreSQL
        pg_check = subprocess.run([
            'psql', '-U', 'postgres', '-c', f'SELECT datname FROM pg_database WHERE datname = \"{db_name}\";'
        ], capture_output=True, text=True)
        
        if existing_db or mysql_check.stdout.strip() or pg_check.stdout.strip():
            return jsonify({'exists': True})
        else:
            return jsonify({'exists': False})
    except Exception as e:
        # 如果命令执行失败，仅检查本地数据库
        return jsonify({'exists': existing_db is not None})


@databases.route('/databases/check_user', methods=['POST'])
@login_required
def check_database_user():
    """检查数据库用户是否已存在"""
    db_user = request.json.get('db_user')
    db_type = request.json.get('db_type')
    
    try:
        if db_type == 'MySQL':
            # 检查MySQL用户
            result = subprocess.run([
                'mysql', '-e', f'SELECT User FROM mysql.user WHERE User = "{db_user}";'
            ], capture_output=True, text=True)
            
            if result.stdout.strip():
                return jsonify({'exists': True})
        elif db_type == 'PostgreSQL':
            # 检查PostgreSQL用户
            result = subprocess.run([
                'psql', '-U', 'postgres', '-c', f'SELECT usename FROM pg_user WHERE usename = \"{db_user}\";'
            ], capture_output=True, text=True)
            
            if result.stdout.strip():
                return jsonify({'exists': True})
        
        return jsonify({'exists': False})
    except Exception as e:
        # 如果命令执行失败，返回默认值
        return jsonify({'exists': False})