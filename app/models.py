#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
数据库模型定义
"""

from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import relationship


@login_manager.user_loader
def load_user(user_id):
    """加载用户对象"""
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    avatar = db.Column(db.String(20), nullable=False, default='default.jpg')
    role = db.Column(db.String(20), nullable=False, default='user')  # admin, user
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # 关系
    servers = relationship('Server', backref='admin', lazy=True)
    websites = relationship('Website', backref='owner', lazy=True)
    databases = relationship('Database', backref='owner', lazy=True)


class Server(db.Model):
    """服务器模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    port = db.Column(db.Integer, default=22)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255))
    private_key = db.Column(Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # 关系
    websites = relationship('Website', backref='server', lazy=True)
    databases = relationship('Database', backref='server', lazy=True)
    monitoring_data = relationship('MonitoringData', backref='server', lazy=True)


class Website(db.Model):
    """网站模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='inactive')  # active, inactive, error
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    webserver_id = db.Column(db.Integer, db.ForeignKey('webserver.id'))
    
    # 关系
    ssl_certificates = relationship('SSLCertificate', backref='website', lazy=True)
    redirects = relationship('Redirect', backref='website', lazy=True)


class Database(db.Model):
    """数据库模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # mysql, postgresql, mongodb
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    size = db.Column(db.BigInteger, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)


class Webserver(db.Model):
    """Web服务器模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # nginx, apache
    version = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='inactive')  # active, inactive
    install_path = db.Column(db.String(255), nullable=False)
    config_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    websites = relationship('Website', backref='webserver', lazy=True)


class SSLCertificate(db.Model):
    """SSL证书模型"""
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), nullable=False)
    issuer = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # valid, expired, expiring_soon
    certificate_path = db.Column(db.String(255), nullable=False)
    private_key_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'), nullable=False)


class Redirect(db.Model):
    """重定向模型"""
    id = db.Column(db.Integer, primary_key=True)
    from_url = db.Column(db.String(255), nullable=False)
    to_url = db.Column(db.String(255), nullable=False)
    type = db.Column(db.Integer, nullable=False)  # 301, 302
    status = db.Column(db.String(20), nullable=False, default='active')  # active, inactive
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    website_id = db.Column(db.Integer, db.ForeignKey('website.id'), nullable=False)


class MonitoringData(db.Model):
    """服务器监控数据模型"""
    id = db.Column(db.Integer, primary_key=True)
    cpu_usage = db.Column(db.Float, nullable=False)
    memory_usage = db.Column(db.Float, nullable=False)
    disk_usage = db.Column(db.Float, nullable=False)
    network_in = db.Column(db.BigInteger, nullable=False)
    network_out = db.Column(db.BigInteger, nullable=False)
    uptime = db.Column(db.Integer, nullable=False)  # 秒
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 外键
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)


class Software(db.Model):
    """软件模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(Text)
    install_command = db.Column(Text, nullable=False)
    uninstall_command = db.Column(Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')  # available, installed, updating
    
    # 关系
    installations = relationship('SoftwareInstallation', backref='software', lazy=True)


class SoftwareInstallation(db.Model):
    """软件安装记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)  # installing, installed, failed
    installed_at = db.Column(db.DateTime)
    failed_reason = db.Column(Text)
    
    # 外键
    software_id = db.Column(db.Integer, db.ForeignKey('software.id'), nullable=False)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)


class FirewallRule(db.Model):
    """防火墙规则模型"""
    id = db.Column(db.Integer, primary_key=True)
    port = db.Column(db.Integer, nullable=False)
    protocol = db.Column(db.String(10), nullable=False)  # tcp, udp
    source = db.Column(db.String(45), nullable=False)  # IP地址或网段
    action = db.Column(db.String(10), nullable=False)  # allow, deny
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 外键
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    
    # 关系
    server = relationship('Server', backref='firewall_rules', lazy=True)