#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
网站管理模块路由

本模块提供网站管理相关的路由和视图函数，包括网站的创建、编辑、删除、虚拟主机配置等功能。
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
import os
import subprocess
import json
import time
import datetime
import re
from app.utils import admin_required
from app.models import Website, User, db
from app.databases.utils import get_database_types
from app.websites.forms import WebsiteForm, SSLForm
from app.websites.utils import (
    create_website_directory, create_apache_vhost, create_nginx_vhost,
    delete_website_directory, delete_apache_vhost, delete_nginx_vhost,
    reload_web_server, get_web_servers, check_domain_availability,
    install_ssl_cert, get_ssl_info, delete_ssl_cert,
    get_website_stats, restart_website_service, get_website_logs
)

# 从__init__.py导入蓝图
from app.websites import websites


@websites.route('/websites')
def index():
    """
    网站管理主页面
    """
    websites = Website.query.all()
    web_servers = get_web_servers()
    
    return render_template('websites/websites.html', 
                          websites=websites, 
                          web_servers=web_servers)


@websites.route('/websites/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_website():
    """
    创建新网站
    """
    form = WebsiteForm()
    
    # 获取可用的Web服务器
    web_servers = get_web_servers()
    form.web_server.choices = [(server, server) for server in web_servers]
    
    # 获取可用的数据库类型
    db_types = get_database_types()
    form.db_type.choices = [('', '无数据库')] + [(db, db) for db in db_types]
    
    if form.validate_on_submit():
        # 检查域名是否可注册
        domain_available = check_domain_availability(form.domain.data)
        if not domain_available:
            flash('域名已被使用或无效，请选择其他域名', 'danger')
            return redirect(url_for('websites.create_website'))
        
        try:
            # 创建网站目录
            doc_root = create_website_directory(form.domain.data)
            if not doc_root:
                flash('创建网站目录失败', 'danger')
                return redirect(url_for('websites.create_website'))
            
            # 创建网站记录
            website = Website(
                name=form.name.data,
                domain=form.domain.data,
                web_server=form.web_server.data,
                php_version=form.php_version.data,
                document_root=doc_root,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            )
            
            db.session.add(website)
            db.session.commit()
            
            # 创建虚拟主机配置
            if form.web_server.data == 'Apache':
                success = create_apache_vhost(website)
            elif form.web_server.data == 'Nginx':
                success = create_nginx_vhost(website)
            else:
                success = False
            
            if not success:
                # 回滚操作
                delete_website_directory(doc_root)
                db.session.delete(website)
                db.session.commit()
                flash('创建虚拟主机配置失败', 'danger')
                return redirect(url_for('websites.create_website'))
            
            # 重新加载Web服务器
            reload_success = reload_web_server(form.web_server.data)
            if not reload_success:
                flash('网站创建成功，但Web服务器重载失败，请手动重启Web服务器', 'warning')
            else:
                flash(f'网站 {form.name.data} 创建成功', 'success')
            
            return redirect(url_for('websites.index'))
            
        except Exception as e:
            # 发生错误时回滚
            if 'website' in locals():
                delete_website_directory(doc_root)
                db.session.delete(website)
                db.session.commit()
            flash(f'创建网站失败: {str(e)}', 'danger')
            return redirect(url_for('websites.create_website'))
    
    return render_template('websites/create_website.html', form=form)


@websites.route('/websites/<int:website_id>')
@login_required
def view_website(website_id):
    """
    查看网站详情
    """
    website = Website.query.get_or_404(website_id)
    stats = get_website_stats(website)
    
    return render_template('websites/view_website.html', 
                          website=website, 
                          stats=stats)


@websites.route('/websites/<int:website_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_website(website_id):
    """
    编辑网站信息
    """
    website = Website.query.get_or_404(website_id)
    form = WebsiteForm(obj=website)
    
    # 获取可用的Web服务器
    web_servers = get_web_servers()
    form.web_server.choices = [(server, server) for server in web_servers]
    
    # 获取可用的数据库类型
    db_types = get_database_types()
    form.db_type.choices = [('', '无数据库')] + [(db, db) for db in db_types]
    
    if form.validate_on_submit():
        try:
            # 更新网站信息
            website.name = form.name.data
            website.php_version = form.php_version.data
            website.updated_at = datetime.datetime.now()
            
            # 如果修改了Web服务器，需要重新创建虚拟主机配置
            if form.web_server.data != website.web_server:
                # 删除旧的虚拟主机配置
                if website.web_server == 'Apache':
                    delete_apache_vhost(website)
                elif website.web_server == 'Nginx':
                    delete_nginx_vhost(website)
                
                # 更新Web服务器
                website.web_server = form.web_server.data
                
                # 创建新的虚拟主机配置
                if form.web_server.data == 'Apache':
                    create_apache_vhost(website)
                elif form.web_server.data == 'Nginx':
                    create_nginx_vhost(website)
                
                # 重新加载Web服务器
                reload_web_server(form.web_server.data)
            
            db.session.commit()
            flash(f'网站 {website.name} 更新成功', 'success')
            return redirect(url_for('websites.view_website', website_id=website.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'更新网站失败: {str(e)}', 'danger')
            return redirect(url_for('websites.edit_website', website_id=website.id))
    
    return render_template('websites/edit_website.html', 
                          form=form, 
                          website=website)


@websites.route('/websites/<int:website_id>/delete', methods=['POST'])
def delete_website(website_id):
    """
    删除网站
    """
    website = Website.query.get_or_404(website_id)
    
    try:
        # 删除虚拟主机配置
        if website.web_server == 'Apache':
            delete_apache_vhost(website)
        elif website.web_server == 'Nginx':
            delete_nginx_vhost(website)
        
        # 删除SSL证书（如果有）
        if website.ssl_enabled:
            delete_ssl_cert(website.domain)
        
        # 删除网站目录
        delete_website_directory(website.document_root)
        
        # 删除网站记录
        db.session.delete(website)
        db.session.commit()
        
        # 重新加载Web服务器
        reload_web_server(website.web_server)
        
        flash(f'网站 {website.name} 删除成功', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除网站失败: {str(e)}', 'danger')
    
    return redirect(url_for('websites.index'))


@websites.route('/websites/<int:website_id>/restart')
@login_required
def restart_website(website_id):
    """
    重启网站服务
    """
    website = Website.query.get_or_404(website_id)
    
    try:
        success = restart_website_service(website)
        if success:
            flash(f'网站 {website.name} 重启成功', 'success')
        else:
            flash(f'网站 {website.name} 重启失败', 'danger')
    except Exception as e:
        flash(f'重启网站服务失败: {str(e)}', 'danger')
    
    return redirect(url_for('websites.view_website', website_id=website.id))


@websites.route('/websites/<int:website_id>/ssl', methods=['GET', 'POST'])
@login_required
def manage_ssl(website_id):
    """
    管理网站SSL证书
    """
    website = Website.query.get_or_404(website_id)
    form = SSLForm()
    
    # 获取当前SSL信息
    ssl_info = None
    if website.ssl_enabled:
        ssl_info = get_ssl_info(website.domain)
    
    if form.validate_on_submit():
        try:
            if form.action.data == 'install':
                # 安装SSL证书
                success = install_ssl_cert(website.domain)
                if success:
                    website.ssl_enabled = True
                    website.updated_at = datetime.datetime.now()
                    db.session.commit()
                    
                    # 更新虚拟主机配置以支持SSL
                    if website.web_server == 'Apache':
                        delete_apache_vhost(website)
                        create_apache_vhost(website)
                    elif website.web_server == 'Nginx':
                        delete_nginx_vhost(website)
                        create_nginx_vhost(website)
                    
                    # 重新加载Web服务器
                    reload_web_server(website.web_server)
                    
                    flash(f'SSL证书安装成功', 'success')
                else:
                    flash('SSL证书安装失败', 'danger')
                    
            elif form.action.data == 'remove':
                # 移除SSL证书
                delete_ssl_cert(website.domain)
                
                website.ssl_enabled = False
                website.updated_at = datetime.datetime.now()
                db.session.commit()
                
                # 更新虚拟主机配置以移除SSL
                if website.web_server == 'Apache':
                    delete_apache_vhost(website)
                    create_apache_vhost(website)
                elif website.web_server == 'Nginx':
                    delete_nginx_vhost(website)
                    create_nginx_vhost(website)
                
                # 重新加载Web服务器
                reload_web_server(website.web_server)
                
                flash(f'SSL证书移除成功', 'success')
                
        except Exception as e:
            db.session.rollback()
            flash(f'SSL管理操作失败: {str(e)}', 'danger')
        
        return redirect(url_for('websites.manage_ssl', website_id=website.id))
    
    return render_template('websites/manage_ssl.html', 
                          form=form, 
                          website=website, 
                          ssl_info=ssl_info)


@websites.route('/websites/<int:website_id>/logs')
@login_required
def view_logs(website_id):
    """
    查看网站访问日志
    """
    website = Website.query.get_or_404(website_id)
    log_type = request.args.get('type', 'access')  # access 或 error
    lines = int(request.args.get('lines', 100))
    
    try:
        logs = get_website_logs(website, log_type, lines)
    except Exception as e:
        flash(f'获取日志失败: {str(e)}', 'danger')
        logs = []
    
    return render_template('websites/view_logs.html', 
                          website=website, 
                          logs=logs, 
                          log_type=log_type, 
                          lines=lines)


@websites.route('/websites/check_domain', methods=['POST'])
def check_domain():
    """
    检查域名是否可用
    """
    domain = request.json.get('domain')
    if not domain:
        return jsonify({'available': False, 'message': '请输入域名'})
    
    try:
        available = check_domain_availability(domain)
        return jsonify({'available': available, 'message': '域名可用' if available else '域名已被使用'})
    except Exception as e:
        return jsonify({'available': False, 'message': str(e)})


@websites.route('/websites/get_website_stats/<int:website_id>')
def get_website_stats_api(website_id):
    """
    获取网站统计数据（API）
    """
    website = Website.query.get_or_404(website_id)
    
    try:
        stats = get_website_stats(website)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500