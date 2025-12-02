#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
应用程序入口文件
"""

import os
from app import create_app

# 创建应用实例，使用环境变量指定配置
app = create_app(os.environ.get('FLASK_ENV', 'dev'))

if __name__ == '__main__':
    # 根据配置决定是否启用调试模式，但始终禁用自动重载功能以提高稳定性
    app.run(host='0.0.0.0', port=8888, debug=app.config['DEBUG'], use_reloader=False)