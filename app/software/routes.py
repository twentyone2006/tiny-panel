#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
软件管理模块路由

本模块提供软件管理相关的路由和视图函数。
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app import db
from app.models import Server, Software
from app.software.forms import SoftwareInstallForm, SoftwareSearchForm, SoftwareUninstallForm
from app.software.utils import (
    execute_remote_command,
    check_software_installed,
    get_software_version,
    load_software_config,
    save_software_config,
    get_software_category_display,
    get_installation_status_display
)
import time
import threading
from datetime import datetime

software = Blueprint('software', __name__, template_folder='templates')

# 全局变量用于存储安装状态
installation_status = {}


@software.route('/')
def list():
    """
    软件列表页面
    """
    search_form = SoftwareSearchForm()
    install_form = SoftwareInstallForm()
    uninstall_form = SoftwareUninstallForm()
    
    # 加载软件配置
    software_list = load_software_config()
    
    # 检查软件安装状态
    for software in software_list:
        software['installed'] = check_software_installed(software['name'])
    
    # 统计信息
    software_count = len(software_list)
    installed_count = sum(1 for s in software_list if s['installed'])
    web_count = sum(1 for s in software_list if s['category'] == 'web')
    database_count = sum(1 for s in software_list if s['category'] == 'database')
    
    return render_template('software/list.html', 
                           software_list=software_list,
                           search_form=search_form,
                           install_form=install_form,
                           uninstall_form=uninstall_form,
                           software_count=software_count,
                           installed_count=installed_count,
                           web_count=web_count,
                           database_count=database_count,
                           get_software_category_display=get_software_category_display)


@software.route('/install', methods=['POST'])
@login_required
def install():
    """
    安装软件
    """
    form = SoftwareInstallForm()
    if form.validate_on_submit():
        software_name = request.form.get('software_name')
        server_id = form.server.data
        
        # 获取服务器信息
        server = Server.query.get(server_id)
        if not server:
            flash('服务器不存在', 'danger')
            return redirect(url_for('software.list'))
        
        # 加载软件配置
        software_list = load_software_config()
        software_info = next((s for s in software_list if s['name'] == software_name), None)
        
        if not software_info:
            flash('软件不存在', 'danger')
            return redirect(url_for('software.list'))
        
        # 设置安装状态
        installation_status[software_name] = {
            'status': 'installing',
            'progress': 0,
            'message': '开始安装...',
            'log': '',
            'start_time': datetime.now().isoformat()
        }
        
        # 执行安装命令（模拟）
        # 实际项目中应该在后台线程中执行安装
        result = execute_remote_command(server, software_info['install_command'])
        
        if result['returncode'] == 0:
            flash(f'软件 {software_name} 安装成功', 'success')
            return jsonify({
                'success': True,
                'message': f'软件 {software_name} 安装成功'
            })
        else:
            error_message = f'软件 {software_name} 安装失败'
            flash(error_message, 'danger')
            return jsonify({
                'success': False,
                'message': error_message,
                'log': f"标准输出: {result['stdout']}\n错误输出: {result['stderr']}"
            })
    
    return jsonify({
        'success': False,
        'message': '表单验证失败',
        'errors': form.errors
    })


@software.route('/uninstall', methods=['POST'])
@login_required
def uninstall():
    """
    卸载软件
    """
    form = SoftwareUninstallForm()
    if form.validate_on_submit():
        software_name = request.form.get('software_name')
        
        # 加载软件配置
        software_list = load_software_config()
        software_info = next((s for s in software_list if s['name'] == software_name), None)
        
        if not software_info:
            flash('软件不存在', 'danger')
            return redirect(url_for('software.list'))
        
        # 检查软件是否已安装
        if not check_software_installed(software_name):
            flash('软件未安装', 'warning')
            return redirect(url_for('software.list'))
        
        # 执行卸载命令
        result = execute_remote_command(Server.query.first(), software_info['uninstall_command'])
        
        if result['returncode'] == 0:
            flash(f'软件 {software_name} 卸载成功', 'success')
        else:
            flash(f'软件 {software_name} 卸载失败: {result["stderr"]}', 'danger')
        
        return redirect(url_for('software.list'))
    
    return redirect(url_for('software.list'))


@software.route('/get-installation-status/<software_name>')
def get_installation_status(software_name):
    """
    获取软件安装状态
    """
    status = installation_status.get(software_name, {
        'status': 'not_started',
        'progress': 0,
        'message': '安装未开始',
        'log': ''
    })
    
    return jsonify(status)


@software.route('/search')
def search():
    """
    搜索软件
    """
    category = request.args.get('category', '')
    
    # 加载软件配置
    software_list = load_software_config()
    
    # 筛选软件
    if category:
        software_list = [s for s in software_list if s['category'] == category]
    
    # 检查软件安装状态
    for software in software_list:
        software['installed'] = check_software_installed(software['name'])
    
    return jsonify({
        'success': True,
        'software_list': software_list
    })


@software.route('/refresh')
def refresh():
    """
    刷新软件列表
    """
    # 重新加载软件配置
    software_list = load_software_config()
    
    # 检查软件安装状态
    for software in software_list:
        software['installed'] = check_software_installed(software['name'])
    
    return jsonify({
        'success': True,
        'software_list': software_list
    })


@software.route('/get-software-detail')
def get_software_detail():
    """
    获取软件详情
    """
    software_id = request.args.get('software_id')
    
    # 加载软件配置
    software_list = load_software_config()
    software = next((s for s in software_list if s['name'] == software_id), None)
    
    if not software:
        return jsonify({
            'success': False,
            'message': '软件不存在'
        })
    
    # 检查软件安装状态
    software['installed'] = check_software_installed(software['name'])
    software['category_display'] = get_software_category_display(software['category'])
    
    return jsonify({
        'success': True,
        'software': software
    })
