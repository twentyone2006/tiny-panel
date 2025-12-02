#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
应用程序配置文件
"""

import os

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///tiny_panel.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件上传设置
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 服务器设置
    SERVER_PORT = 8888
    
    # 日志设置
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    # 安全设置
    PASSWORD_COMPLEXITY = {
        'min_length': 8,
        'require_upper': True,
        'require_lower': True,
        'require_digit': True,
        'require_special': True
    }

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境下应该使用更安全的设置
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = 'https'

# 根据环境变量选择配置
config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig,
    'default': DevelopmentConfig
}