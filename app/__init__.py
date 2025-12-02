#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
应用程序初始化文件
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import os
from app.config import config_by_name

# 初始化扩展
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    """创建应用程序实例"""
    print(f"[DEBUG] Creating app with config: {config_name}")
    app = Flask(__name__)
    
    # 如果传入的是配置名称，则从config_by_name获取配置类
    if config_name in config_by_name:
        print(f"[DEBUG] Using config class: {config_by_name[config_name].__name__}")
        app.config.from_object(config_by_name[config_name])
    else:
        # 否则尝试将其作为导入路径处理
        print(f"[DEBUG] Using config path: {config_name}")
        app.config.from_object(config_name)
    
    print(f"[DEBUG] Debug mode: {app.config['DEBUG']}")
    print(f"[DEBUG] Secret key set: {app.config['SECRET_KEY'] is not None}")
    print(f"[DEBUG] Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # 注册扩展
    print("[DEBUG] Initializing extensions...")
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # 注册蓝图
    print("[DEBUG] Registering blueprints...")
    from app.users.routes import users
    from app.dashboard.routes import dashboard
    from app.files.routes import files
    from app.databases.routes import databases
    from app.websites.routes import websites
    from app.software.routes import software
    from app.security.routes import security
    from app.monitoring.routes import monitoring_bp as monitoring
    
    app.register_blueprint(users)
    app.register_blueprint(dashboard)
    app.register_blueprint(files)
    app.register_blueprint(databases)
    app.register_blueprint(websites)
    app.register_blueprint(software)
    app.register_blueprint(security)
    app.register_blueprint(monitoring)
    
    print("[DEBUG] App creation completed successfully!")
    return app