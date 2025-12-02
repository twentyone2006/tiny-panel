#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
用户表单定义
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_login import current_user
from app.models import User


class RegistrationForm(FlaskForm):
    """用户注册表单"""
    username = StringField('用户名', 
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('邮箱', 
                        validators=[DataRequired(), Email()])
    password = PasswordField('密码', 
                             validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('确认密码', 
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('注册')
    
    def validate_username(self, username):
        """验证用户名是否已存在"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被使用，请选择其他用户名')
    
    def validate_email(self, email):
        """验证邮箱是否已存在"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册，请使用其他邮箱')


class LoginForm(FlaskForm):
    """用户登录表单"""
    email = StringField('邮箱', 
                        validators=[DataRequired(), Email()])
    password = PasswordField('密码', 
                             validators=[DataRequired()])
    remember = BooleanField('记住我')
    submit = SubmitField('登录')


class UpdateAccountForm(FlaskForm):
    """用户账户更新表单"""
    username = StringField('用户名', 
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('邮箱', 
                        validators=[DataRequired(), Email()])
    picture = FileField('更新头像', 
                        validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('更新')
    
    def validate_username(self, username):
        """验证用户名是否已存在（排除当前用户）"""
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('该用户名已被使用，请选择其他用户名')
    
    def validate_email(self, email):
        """验证邮箱是否已存在（排除当前用户）"""
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('该邮箱已被注册，请使用其他邮箱')