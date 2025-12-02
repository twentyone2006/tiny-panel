#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
网站管理模块表单

本模块提供网站管理相关的表单类，用于网站创建、编辑和SSL管理等操作。
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, URL, Regexp, Length, Optional
import re


class WebsiteForm(FlaskForm):
    """
    网站创建和编辑表单
    """
    name = StringField('网站名称', 
                      validators=[
                          DataRequired('请输入网站名称'),
                          Length(min=2, max=100, message='网站名称长度应在2-100个字符之间')
                      ])
    
    domain = StringField('域名', 
                        validators=[
                            DataRequired('请输入域名'),
                            Regexp(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?(\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?)*$', 
                                  message='域名格式不正确')
                        ])
    
    web_server = SelectField('Web服务器', 
                            validators=[
                                DataRequired('请选择Web服务器')
                            ])
    
    php_version = SelectField('PHP版本', 
                             choices=[
                                 ('', '无PHP'),
                                 ('5.6', 'PHP 5.6'),
                                 ('7.0', 'PHP 7.0'),
                                 ('7.1', 'PHP 7.1'),
                                 ('7.2', 'PHP 7.2'),
                                 ('7.3', 'PHP 7.3'),
                                 ('7.4', 'PHP 7.4'),
                                 ('8.0', 'PHP 8.0'),
                                 ('8.1', 'PHP 8.1'),
                                 ('8.2', 'PHP 8.2')
                             ],
                             validators=[
                                 Optional()
                             ])
    
    db_type = SelectField('数据库类型', 
                         validators=[
                             Optional()
                         ])
    
    description = TextAreaField('网站描述', 
                               validators=[
                                   Length(max=500, message='网站描述不能超过500个字符')
                               ])
    
    submit = SubmitField('保存')
    
    def validate_domain(self, field):
        """
        验证域名格式是否正确
        """
        domain = field.data.lower()
        
        # 检查域名长度
        if len(domain) > 253:
            raise ValueError('域名长度不能超过253个字符')
        
        # 检查域名标签
        labels = domain.split('.')
        if len(labels) < 2:
            raise ValueError('域名至少需要包含一个点（如 example.com）')
        
        # 检查每个标签
        for label in labels:
            if len(label) > 63:
                raise ValueError('域名中的每个标签长度不能超过63个字符')
            
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?$', label):
                raise ValueError('域名标签只能包含字母、数字和连字符，且不能以连字符开头或结尾')
        
        # 检查顶级域名
        tld = labels[-1]
        if not re.match(r'^[a-zA-Z]{2,}$', tld):
            raise ValueError('顶级域名只能包含字母，且长度至少为2个字符')


class SSLForm(FlaskForm):
    """
    SSL证书管理表单
    """
    action = HiddenField('操作', 
                        validators=[
                            DataRequired()
                        ])
    
    submit = SubmitField('执行操作')