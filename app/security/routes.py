#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
安全管理模块路由

本模块提供安全管理相关的路由和视图函数，包括防火墙管理、密码策略、安全审计等。
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app import db
from app.models import Server, FirewallRule
from app.security.forms import FirewallRuleForm, SecurityAuditForm
from app.security.utils import (
    get_firewall_status,
    add_firewall_rule,
    delete_firewall_rule,
    list_firewall_rules,
    get_security_audit_logs,
    check_ssh_status,
    update_ssh_config
)

# 导入蓝图
from app.security import security


@security.route('/')
def index():
    """
    安全管理首页
    """
    servers = Server.query.all()
    security_status = {
        'firewall_enabled': False,
        'ssh_secure': False,
        'recent_login_failures': 0
    }
    
    # 获取第一个服务器的安全状态（实际项目中应该检查所有服务器）
    if servers:
        server = servers[0]
        security_status['firewall_enabled'] = get_firewall_status(server)
        security_status['ssh_secure'] = check_ssh_status(server)
        security_status['recent_login_failures'] = 5  # 模拟数据
    
    return render_template('security/index.html', 
                           title='安全管理',
                           security_status=security_status,
                           servers=servers)


@security.route('/firewall')
def firewall():
    """
    防火墙管理页面
    """
    form = FirewallRuleForm()
    servers = Server.query.all()
    
    # 获取第一个服务器的防火墙规则（实际项目中应该让用户选择服务器）
    firewall_rules = []
    firewall_enabled = False
    
    if servers:
        server = servers[0]
        firewall_rules = list_firewall_rules(server)
        firewall_enabled = get_firewall_status(server)
    
    return render_template('security/firewall.html', 
                           title='防火墙管理',
                           form=form,
                           servers=servers,
                           firewall_rules=firewall_rules,
                           firewall_enabled=firewall_enabled)


@security.route('/add-firewall-rule', methods=['POST'])
def add_firewall_rule_view():
    """
    添加防火墙规则
    """
    form = FirewallRuleForm()
    if form.validate_on_submit():
        server_id = form.server.data
        port = form.port.data
        protocol = form.protocol.data
        source = form.source.data
        action = form.action.data
        
        server = Server.query.get(server_id)
        if not server:
            flash('服务器不存在', 'danger')
            return redirect(url_for('security.firewall'))
        
        # 添加防火墙规则
        result = add_firewall_rule(server, port, protocol, source, action)
        
        if result['success']:
            flash('防火墙规则添加成功', 'success')
        else:
            flash(f'防火墙规则添加失败: {result["message"]}', 'danger')
        
        return redirect(url_for('security.firewall'))
    
    return redirect(url_for('security.firewall'))


@security.route('/delete-firewall-rule/<int:rule_id>')
def delete_firewall_rule_view(rule_id):
    """
    删除防火墙规则
    """
    # 从数据库中获取规则
    rule = FirewallRule.query.get(rule_id)
    if not rule:
        flash('防火墙规则不存在', 'danger')
        return redirect(url_for('security.firewall'))
    
    server = rule.server
    
    # 删除防火墙规则
    result = delete_firewall_rule(server, rule_id)
    
    if result['success']:
        db.session.delete(rule)
        db.session.commit()
        flash('防火墙规则删除成功', 'success')
    else:
        flash(f'防火墙规则删除失败: {result["message"]}', 'danger')
    
    return redirect(url_for('security.firewall'))


@security.route('/audit')
def audit():
    """
    安全审计页面
    """
    form = SecurityAuditForm()
    servers = Server.query.all()
    
    # 获取安全审计日志
    audit_logs = []
    if servers:
        server = servers[0]
        audit_logs = get_security_audit_logs(server)
    
    return render_template('security/audit.html', 
                           title='安全审计',
                           form=form,
                           servers=servers,
                           audit_logs=audit_logs)


@security.route('/ssh')
def ssh_config():
    """
    SSH配置页面
    """
    servers = Server.query.all()
    ssh_status = {}
    
    if servers:
        server = servers[0]
        ssh_status = check_ssh_status(server)
    
    return render_template('security/ssh.html', 
                           title='SSH配置',
                           servers=servers,
                           ssh_status=ssh_status)


@security.route('/update-ssh-config', methods=['POST'])
def update_ssh_config_view():
    """
    更新SSH配置
    """
    server_id = request.form.get('server_id')
    disable_root_login = request.form.get('disable_root_login') == 'on'
    use_key_auth = request.form.get('use_key_auth') == 'on'
    
    server = Server.query.get(server_id)
    if not server:
        flash('服务器不存在', 'danger')
        return redirect(url_for('security.ssh_config'))
    
    # 更新SSH配置
    result = update_ssh_config(server, disable_root_login, use_key_auth)
    
    if result['success']:
        flash('SSH配置更新成功', 'success')
    else:
        flash(f'SSH配置更新失败: {result["message"]}', 'danger')
    
    return redirect(url_for('security.ssh_config'))