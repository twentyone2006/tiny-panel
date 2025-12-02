#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
网站管理模块

本模块提供网站管理相关功能，包括网站的创建、编辑、删除，SSL证书管理等。
"""

from flask import Blueprint

# 创建蓝图
websites = Blueprint('websites', __name__, url_prefix='/websites')

# 导入路由
from app.websites import routes