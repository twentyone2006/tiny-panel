#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
软件管理模块表单

本模块提供软件管理相关的表单类，用于软件安装等操作的表单验证。
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, ValidationError


class SoftwareInstallForm(FlaskForm):
    """软件安装表单"""
    # 服务器选择
    server_id = SelectField('服务器', validators=[DataRequired()], coerce=int)
    
    # 提交按钮
    submit = SubmitField('安装')
    
    def __init__(self, *args, **kwargs):
        super(SoftwareInstallForm, self).__init__(*args, **kwargs)
        # 这里会在路由中动态设置choices
        self.server_id.choices = []


class SoftwareSearchForm(FlaskForm):
    """软件搜索表单"""
    # 搜索类别
    category = SelectField('类别', choices=[
        ('', '所有类别'),
        ('web', 'Web服务器'),
        ('database', '数据库'),
        ('language', '编程语言'),
        ('cache', '缓存'),
        ('monitoring', '监控工具'),
        ('security', '安全工具'),
        ('other', '其他')
    ])
    
    # 提交按钮
    submit = SubmitField('筛选')


class SoftwareUninstallForm(FlaskForm):
    """软件卸载表单"""
    # 确认卸载
    confirm = HiddenField('确认', default='false')
    
    # 提交按钮
    submit = SubmitField('确认卸载')