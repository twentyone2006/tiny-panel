#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
仪表盘路由
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
import psutil
import platform
import socket
import os
from datetime import datetime, timedelta
from app.models import Server, Website, Database, MonitoringData
from app import db

# 创建蓝图
dashboard = Blueprint('dashboard', __name__)


@dashboard.route('/')
@dashboard.route('/home')
@login_required
def home():
    """仪表盘主页"""
    # 获取系统信息
    system_info = get_system_info()
    
    # 获取用户数据统计
    user_stats = get_user_stats()
    
    # 获取最近的监控数据
    recent_monitoring = get_recent_monitoring()
    
    return render_template('dashboard/home.html', 
                          title='仪表盘',
                          system_info=system_info,
                          user_stats=user_stats,
                          recent_monitoring=recent_monitoring)


def get_system_info():
    """获取系统基本信息"""
    return {
        'os': platform.system(),
        'os_version': platform.version(),
        'architecture': platform.architecture()[0],
        'hostname': socket.gethostname(),
        'ip_address': socket.gethostbyname(socket.gethostname()),
        'cpu_count': psutil.cpu_count(),
        'cpu_usage': psutil.cpu_percent(interval=1),
        'memory_total': round(psutil.virtual_memory().total / (1024**3), 2),
        'memory_used': round(psutil.virtual_memory().used / (1024**3), 2),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_total': round(psutil.disk_usage('/').total / (1024**3), 2),
        'disk_used': round(psutil.disk_usage('/').used / (1024**3), 2),
        'disk_percent': psutil.disk_usage('/').percent,
        'uptime': str(timedelta(seconds=psutil.boot_time()))
    }


def get_user_stats():
    """获取用户相关统计信息"""
    return {
        'servers': Server.query.filter_by(user_id=current_user.id).count(),
        'websites': Website.query.filter_by(user_id=current_user.id).count(),
        'databases': Database.query.filter_by(user_id=current_user.id).count(),
        'active_websites': Website.query.filter_by(user_id=current_user.id, status='active').count()
    }


def get_recent_monitoring():
    """获取最近的监控数据"""
    # 获取最近24小时的监控数据
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    
    # 获取用户所有服务器的监控数据
    servers = Server.query.filter_by(user_id=current_user.id).all()
    server_monitoring = {}
    
    for server in servers:
        # 获取最近的监控数据点（每小时一个）
        monitoring_data = MonitoringData.query\
            .filter_by(server_id=server.id)\
            .filter(MonitoringData.timestamp >= twenty_four_hours_ago)\
            .order_by(MonitoringData.timestamp)\
            .all()
        
        server_monitoring[server.name] = monitoring_data
    
    return server_monitoring