#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
数据库管理模块表单类

本模块定义了数据库管理相关的表单类，包括数据库创建、编辑和备份表单。
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError
import re


class DatabaseForm(FlaskForm):
    """数据库创建/编辑表单"""
    db_name = StringField(
        '数据库名称',
        validators=[
            DataRequired(message='请输入数据库名称'),
            Length(min=2, max=64, message='数据库名称长度应在2-64个字符之间'),
            Regexp(r'^[a-zA-Z0-9_]+$', message='数据库名称只能包含字母、数字和下划线')
        ]
    )
    
    db_user = StringField(
        '数据库用户名',
        validators=[
            DataRequired(message='请输入数据库用户名'),
            Length(min=2, max=32, message='用户名长度应在2-32个字符之间'),
            Regexp(r'^[a-zA-Z0-9_]+$', message='用户名只能包含字母、数字和下划线')
        ]
    )
    
    db_password = PasswordField(
        '数据库密码',
        validators=[
            DataRequired(message='请输入数据库密码'),
            Length(min=8, message='密码长度至少为8个字符'),
            Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', 
                  message='密码必须包含大小写字母和数字')
        ]
    )
    
    confirm_password = PasswordField(
        '确认密码',
        validators=[
            DataRequired(message='请确认密码'),
            EqualTo('db_password', message='两次输入的密码不一致')
        ]
    )
    
    db_type = SelectField(
        '数据库类型',
        validators=[
            DataRequired(message='请选择数据库类型')
        ]
    )
    
    submit = SubmitField('提交')
    
    def validate_db_name(self, db_name):
        """验证数据库名称"""
        # 不允许使用特殊数据库名称
        reserved_names = ['mysql', 'information_schema', 'performance_schema', 'sys', 'postgres', 'template0', 'template1']
        if db_name.data.lower() in reserved_names:
            raise ValidationError('不能使用保留的数据库名称')
    
    def validate_db_user(self, db_user):
        """验证数据库用户名"""
        # 不允许使用特殊用户名
        reserved_users = ['root', 'admin', 'postgres', 'mysql', 'system']
        if db_user.data.lower() in reserved_users:
            raise ValidationError('不能使用保留的用户名')


class DatabaseBackupForm(FlaskForm):
    """数据库备份表单"""
    backup_name = StringField(
        '备份名称',
        validators=[
            DataRequired(message='请输入备份名称'),
            Length(min=1, max=64, message='备份名称长度应在1-64个字符之间'),
            Regexp(r'^[a-zA-Z0-9_.-]+$', message='备份名称只能包含字母、数字、下划线、点和减号')
        ]
    )
    
    password = PasswordField(
        '数据库密码',
        validators=[
            DataRequired(message='请输入数据库密码')
        ]
    )
    
    compress = BooleanField(
        '压缩备份文件',
        default=True
    )
    
    submit = SubmitField('创建备份')


class DatabaseRestoreForm(FlaskForm):
    """数据库还原表单"""
    backup_file = SelectField(
        '备份文件',
        validators=[
            DataRequired(message='请选择备份文件')
        ]
    )
    
    password = PasswordField(
        '数据库密码',
        validators=[
            DataRequired(message='请输入数据库密码')
        ]
    )
    
    drop_existing = BooleanField(
        '删除现有数据库（谨慎操作）',
        default=False
    )
    
    submit = SubmitField('还原数据库')


class DatabaseUserForm(FlaskForm):
    """数据库用户管理表单"""
    username = StringField(
        '用户名',
        validators=[
            DataRequired(message='请输入用户名'),
            Length(min=2, max=32, message='用户名长度应在2-32个字符之间'),
            Regexp(r'^[a-zA-Z0-9_]+$', message='用户名只能包含字母、数字和下划线')
        ]
    )
    
    password = PasswordField(
        '密码',
        validators=[
            DataRequired(message='请输入密码'),
            Length(min=8, message='密码长度至少为8个字符'),
            Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', 
                  message='密码必须包含大小写字母和数字')
        ]
    )
    
    confirm_password = PasswordField(
        '确认密码',
        validators=[
            DataRequired(message='请确认密码'),
            EqualTo('password', message='两次输入的密码不一致')
        ]
    )
    
    db_type = SelectField(
        '数据库类型',
        validators=[
            DataRequired(message='请选择数据库类型')
        ]
    )
    
    submit = SubmitField('提交')
    
    def validate_username(self, username):
        """验证用户名"""
        # 不允许使用特殊用户名
        reserved_users = ['root', 'admin', 'postgres', 'mysql', 'system']
        if username.data.lower() in reserved_users:
            raise ValidationError('不能使用保留的用户名')