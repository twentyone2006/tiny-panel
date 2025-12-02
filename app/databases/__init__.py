#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
数据库管理模块初始化文件
"""

from flask import Blueprint

# 创建蓝图实例
databases = Blueprint('databases', __name__, template_folder='templates')

# 导入路由
from app.databases import routes