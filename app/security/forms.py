#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
安全管理模块表单

本模块提供安全管理相关的表单类，包括防火墙规则表单、安全审计表单等。
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DateTimeField, BooleanField
from wtforms.validators import DataRequired, IPAddress, NumberRange, Length
from app.models import Server


class FirewallRuleForm(FlaskForm):
    """
    防火墙规则表单
    """
    server = SelectField('服务器', validators=[DataRequired()])
    port = StringField('端口', validators=[DataRequired(), Length(max=20)])
    protocol = SelectField('协议', choices=[
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
        ('icmp', 'ICMP'),
        ('all', '全部')
    ], validators=[DataRequired()])
    source = StringField('源地址', validators=[IPAddress(ipv4=True, ipv6=True, message='请输入有效的IP地址')], render_kw={'placeholder': '0.0.0.0/0 表示全部'})
    action = SelectField('操作', choices=[
        ('allow', '允许'),
        ('deny', '拒绝')
    ], validators=[DataRequired()])
    submit = SubmitField('保存')
    
    def __init__(self, *args, **kwargs):
        super(FirewallRuleForm, self).__init__(*args, **kwargs)
        # 动态加载服务器列表
        self.server.choices = [(s.id, f'{s.hostname} ({s.ip_address})') for s in Server.query.all()]


class SecurityAuditForm(FlaskForm):
    """
    安全审计表单
    """
    server = SelectField('服务器', validators=[DataRequired()])
    start_time = DateTimeField('开始时间', format='%Y-%m-%d %H:%M:%S')
    end_time = DateTimeField('结束时间', format='%Y-%m-%d %H:%M:%S')
    event_type = SelectField('事件类型', choices=[
        ('', '全部'),
        ('login', '登录事件'),
        ('firewall', '防火墙事件'),
        ('system', '系统事件'),
        ('security', '安全事件')
    ])
    submit = SubmitField('查询')
    
    def __init__(self, *args, **kwargs):
        super(SecurityAuditForm, self).__init__(*args, **kwargs)
        # 动态加载服务器列表
        self.server.choices = [(s.id, f'{s.hostname} ({s.ip_address})') for s in Server.query.all()]