#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
监控管理模块路由

本模块提供监控相关的路由和视图函数，包括服务器状态监控、资源使用情况等功能。
"""

from flask import render_template, jsonify, request, current_app
from flask_login import login_required
from datetime import datetime, timedelta
import time

from app import db
from app.models import Server, MonitoringData
from app.monitoring import monitoring_bp
from app.monitoring.utils import (
    get_server_status, 
    get_cpu_usage, 
    get_memory_usage, 
    get_disk_usage, 
    get_network_usage,
    get_process_list,
    collect_monitoring_data
)


@monitoring_bp.route('/')
@login_required
def index():
    """
    监控管理首页
    """
    # 获取所有服务器
    servers = Server.query.all()
    
    # 获取监控数据（最近1小时）
    one_hour_ago = datetime.now() - timedelta(hours=1)
    
    # 为每个服务器获取最新的监控数据
    servers_with_status = []
    for server in servers:
        # 获取服务器状态
        status = get_server_status(server)
        
        # 获取最新的监控数据
        latest_data = MonitoringData.query.filter_by(
            server_id=server.id
        ).order_by(MonitoringData.timestamp.desc()).first()
        
        # 如果没有监控数据，使用模拟数据
        if not latest_data:
            cpu_usage = 0
            memory_usage = 0
            disk_usage = 0
            network_rx = 0
            network_tx = 0
        else:
            cpu_usage = latest_data.cpu_usage
            memory_usage = latest_data.memory_usage
            disk_usage = latest_data.disk_usage
            network_rx = latest_data.network_rx
            network_tx = latest_data.network_tx
        
        servers_with_status.append({
            'server': server,
            'status': status,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage,
            'network_rx': network_rx,
            'network_tx': network_tx,
            'latest_data': latest_data
        })
    
    return render_template('monitoring/index.html', servers=servers_with_status)


@monitoring_bp.route('/server/<int:server_id>')
def server_monitoring(server_id):
    """
    单个服务器监控页面
    """
    # 获取服务器信息
    server = Server.query.get_or_404(server_id)
    
    # 获取服务器状态
    status = get_server_status(server)
    
    # 获取最近24小时的监控数据
    twenty_four_hours_ago = datetime.now() - timedelta(days=1)
    monitoring_data = MonitoringData.query.filter_by(
        server_id=server_id
    ).filter(
        MonitoringData.timestamp >= twenty_four_hours_ago
    ).order_by(MonitoringData.timestamp).all()
    
    # 准备图表数据
    timestamps = []
    cpu_data = []
    memory_data = []
    disk_data = []
    network_rx_data = []
    network_tx_data = []
    
    for data in monitoring_data:
        timestamps.append(data.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        cpu_data.append(data.cpu_usage)
        memory_data.append(data.memory_usage)
        disk_data.append(data.disk_usage)
        network_rx_data.append(data.network_rx)
        network_tx_data.append(data.network_tx)
    
    # 获取进程列表（仅当服务器在线时）
    processes = []
    if status['online']:
        processes = get_process_list(server)
    
    return render_template(
        'monitoring/server.html',
        server=server,
        status=status,
        timestamps=timestamps,
        cpu_data=cpu_data,
        memory_data=memory_data,
        disk_data=disk_data,
        network_rx_data=network_rx_data,
        network_tx_data=network_tx_data,
        processes=processes
    )


@monitoring_bp.route('/api/server_status/<int:server_id>')
def api_server_status(server_id):
    """
    获取服务器实时状态的API
    """
    # 获取服务器信息
    server = Server.query.get_or_404(server_id)
    
    # 获取服务器状态
    status = get_server_status(server)
    
    # 获取最新的监控数据
    latest_data = MonitoringData.query.filter_by(
        server_id=server_id
    ).order_by(MonitoringData.timestamp.desc()).first()
    
    # 收集最新的监控数据
    collect_monitoring_data(server)
    
    # 获取更新后的监控数据
    updated_data = MonitoringData.query.filter_by(
        server_id=server_id
    ).order_by(MonitoringData.timestamp.desc()).first()
    
    # 准备响应数据
    response_data = {
        'status': status,
        'cpu_usage': updated_data.cpu_usage if updated_data else 0,
        'memory_usage': updated_data.memory_usage if updated_data else 0,
        'disk_usage': updated_data.disk_usage if updated_data else 0,
        'network_rx': updated_data.network_rx if updated_data else 0,
        'network_tx': updated_data.network_tx if updated_data else 0,
        'timestamp': updated_data.timestamp.strftime('%Y-%m-%d %H:%M:%S') if updated_data else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify(response_data)


@monitoring_bp.route('/api/monitoring_data/<int:server_id>')
def api_monitoring_data(server_id):
    """
    获取服务器监控数据的API
    """
    # 获取查询参数
    hours = request.args.get('hours', default=24, type=int)
    interval = request.args.get('interval', default=60, type=int)  # 分钟
    
    # 计算时间范围
    start_time = datetime.now() - timedelta(hours=hours)
    
    # 获取监控数据
    monitoring_data = MonitoringData.query.filter_by(
        server_id=server_id
    ).filter(
        MonitoringData.timestamp >= start_time
    ).order_by(MonitoringData.timestamp).all()
    
    # 准备图表数据
    timestamps = []
    cpu_data = []
    memory_data = []
    disk_data = []
    network_rx_data = []
    network_tx_data = []
    
    for data in monitoring_data:
        timestamps.append(data.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        cpu_data.append(data.cpu_usage)
        memory_data.append(data.memory_usage)
        disk_data.append(data.disk_usage)
        network_rx_data.append(data.network_rx)
        network_tx_data.append(data.network_tx)
    
    return jsonify({
        'timestamps': timestamps,
        'cpu_data': cpu_data,
        'memory_data': memory_data,
        'disk_data': disk_data,
        'network_rx_data': network_rx_data,
        'network_tx_data': network_tx_data
    })


@monitoring_bp.route('/api/process_list/<int:server_id>')
def api_process_list(server_id):
    """
    获取服务器进程列表的API
    """
    # 获取服务器信息
    server = Server.query.get_or_404(server_id)
    
    # 获取进程列表
    processes = get_process_list(server)
    
    return jsonify(processes)


@monitoring_bp.route('/collect_data/<int:server_id>')
def collect_data(server_id):
    """
    手动触发数据收集
    """
    # 获取服务器信息
    server = Server.query.get_or_404(server_id)
    
    # 收集监控数据
    success = collect_monitoring_data(server)
    
    if success:
        return jsonify({'success': True, 'message': '监控数据收集成功'})
    else:
        return jsonify({'success': False, 'message': '监控数据收集失败'})
