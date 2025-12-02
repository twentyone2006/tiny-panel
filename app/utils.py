#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
通用工具函数和装饰器
"""

from flask import flash, redirect, url_for
from flask_login import current_user
from functools import wraps


def admin_required(f):
    """检查用户是否为管理员的装饰器
    
    用法：
    @admin_required
    def some_admin_function():
        pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('请先登录', 'danger')
            return redirect(url_for('users.login'))
        if current_user.role != 'admin':
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('dashboard.home'))
        return f(*args, **kwargs)
    return decorated_function
