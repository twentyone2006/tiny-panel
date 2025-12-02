#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全管理模块"""

from flask import Blueprint

# 创建蓝图实例
security = Blueprint('security', __name__, template_folder='templates')

# 导入路由
from app.security import routes