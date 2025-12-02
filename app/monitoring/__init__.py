#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
监控管理模块

本模块提供服务器状态监控功能，包括CPU、内存、磁盘、网络等资源的监控和图表展示。
"""

from flask import Blueprint

# 创建监控管理蓝图
monitoring_bp = Blueprint('monitoring', __name__, template_folder='templates')

# 导入路由
from app.monitoring import routes
