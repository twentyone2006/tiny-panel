#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
用户认证和权限管理路由
"""

from flask import Blueprint, render_template, url_for, flash, redirect, request, current_app
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models import User
from app.users.forms import RegistrationForm, LoginForm, UpdateAccountForm
import secrets
import os
from datetime import datetime
from PIL import Image

users = Blueprint('users', __name__)


@users.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('您的账号已创建成功！现在可以登录了', 'success')
        return redirect(url_for('users.login'))
    return render_template('users/register.html', title='注册', form=form)


@users.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.home'))
        else:
            flash('登录失败，请检查邮箱和密码', 'danger')
    return render_template('users/login.html', title='登录', form=form)


@users.route('/logout')
def logout():
    """用户登出"""
    logout_user()
    return redirect(url_for('users.login'))


@users.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """用户账户管理"""
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.avatar = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('您的账号信息已更新', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.avatar)
    return render_template('users/account.html', title='账户', image_file=image_file, form=form)


def save_picture(form_picture):
    """保存用户头像图片"""
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)
    
    # 调整图片大小
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    # 删除旧头像（如果不是默认头像）
    if current_user.avatar != 'default.jpg':
        old_picture_path = os.path.join(current_app.root_path, 'static/profile_pics', current_user.avatar)
        if os.path.exists(old_picture_path):
            os.remove(old_picture_path)
    
    return picture_fn


@users.route('/admin/users')
@login_required
def admin_users():
    """管理员查看所有用户（仅管理员可用）"""
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('dashboard.home'))
    users = User.query.all()
    return render_template('users/admin_users.html', title='用户管理', users=users)