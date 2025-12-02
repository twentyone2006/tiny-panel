#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
监控管理模块工具函数

本模块提供监控相关的工具函数，包括服务器状态检查、资源使用情况获取、监控数据收集等功能。
"""

import subprocess
import re
import psutil
import time
from datetime import datetime



def execute_remote_command(server, command, timeout=300):
    """
    在远程服务器上执行命令
    
    Args:
        server: 服务器对象
        command: 要执行的命令
        timeout: 超时时间（秒）
    
    Returns:
        dict: 包含返回码、标准输出和标准错误的字典
    """
    try:
        # 如果是本地服务器（用于开发测试）
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=timeout
            )
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        
        # 否则通过SSH连接到远程服务器
        # 这里应该使用paramiko或其他SSH库
        # 为了演示，我们返回模拟数据
        return {
            'returncode': 0,
            'stdout': f'[模拟] 在服务器 {server.hostname} 上执行命令: {command}',
            'stderr': ''
        }
        
    except Exception as e:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': str(e)
        }


def get_server_status(server):
    """
    获取服务器状态
    
    Args:
        server: 服务器对象
    
    Returns:
        dict: 包含服务器状态的字典
    """
    try:
        # 尝试ping服务器
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            # 本地服务器，直接返回在线
            return {'online': True, 'response_time': 0.5}
        
        # 远程服务器，尝试ping
        result = execute_remote_command(server, f'ping -c 1 -W 2 {server.hostname}')
        if result['returncode'] == 0:
            # 解析ping结果，获取响应时间
            match = re.search(r'time=(\d+\.\d+)\s+ms', result['stdout'])
            if match:
                response_time = float(match.group(1))
            else:
                response_time = 1.0  # 默认响应时间
            
            return {'online': True, 'response_time': response_time}
        else:
            return {'online': False, 'response_time': 0}
            
    except Exception:
        return {'online': False, 'response_time': 0}


def get_cpu_usage(server):
    """
    获取CPU使用率
    
    Args:
        server: 服务器对象
    
    Returns:
        float: CPU使用率（百分比）
    """
    try:
        # 如果是本地服务器，使用psutil获取
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            return psutil.cpu_percent(interval=1)
        
        # 否则通过SSH获取
        result = execute_remote_command(server, 'top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/"')
        if result['returncode'] == 0 and result['stdout'].strip():
            idle = float(result['stdout'].strip())
            return 100 - idle
        
        # 模拟数据
        return 0
        
    except Exception:
        return 0


def get_memory_usage(server):
    """
    获取内存使用率
    
    Args:
        server: 服务器对象
    
    Returns:
        float: 内存使用率（百分比）
    """
    try:
        # 如果是本地服务器，使用psutil获取
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            memory = psutil.virtual_memory()
            return memory.percent
        
        # 否则通过SSH获取
        result = execute_remote_command(server, 'free | grep Mem | awk "{print $3/$2 * 100.0}"')
        if result['returncode'] == 0 and result['stdout'].strip():
            return float(result['stdout'].strip())
        
        # 模拟数据
        return 0
        
    except Exception:
        return 0


def get_disk_usage(server, path='/'):
    """
    获取磁盘使用率
    
    Args:
        server: 服务器对象
        path: 要检查的磁盘路径
    
    Returns:
        float: 磁盘使用率（百分比）
    """
    try:
        # 如果是本地服务器，使用psutil获取
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            disk = psutil.disk_usage(path)
            return disk.percent
        
        # 否则通过SSH获取
        command = "df -h | grep {} | awk '{print $5}' | sed 's/%//'"
        command = command.format(path)
        result = execute_remote_command(server, command)
        if result['returncode'] == 0 and result['stdout'].strip():
            return float(result['stdout'].strip())
        
        # 模拟数据
        return 0
        
    except Exception:
        return 0


def get_network_usage(server, interval=1):
    """
    获取网络使用率
    
    Args:
        server: 服务器对象
        interval: 采样间隔（秒）
    
    Returns:
        tuple: (接收字节数, 发送字节数)
    """
    try:
        # 如果是本地服务器，使用psutil获取
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            net_io_start = psutil.net_io_counters()
            time.sleep(interval)
            net_io_end = psutil.net_io_counters()
            
            # 计算每秒钟的网络流量
            bytes_recv = (net_io_end.bytes_recv - net_io_start.bytes_recv) / interval
            bytes_sent = (net_io_end.bytes_sent - net_io_start.bytes_sent) / interval
            
            return (bytes_recv, bytes_sent)
        
        # 否则通过SSH获取
        # 简化处理，返回模拟数据
        return (1024 * 1024, 512 * 1024)  # 1MB/s 接收，512KB/s 发送
        
    except Exception:
        return (0, 0)


def get_process_list(server, limit=20):
    """
    获取进程列表
    
    Args:
        server: 服务器对象
        limit: 限制返回的进程数
    
    Returns:
        list: 进程列表
    """
    try:
        processes = []
        
        # 如果是本地服务器，使用psutil获取
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            # 获取所有进程
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time', 'username']):
                try:
                    process_info = proc.info
                    processes.append({
                        'pid': process_info['pid'],
                        'name': process_info['name'],
                        'cpu_percent': process_info['cpu_percent'],
                        'memory_percent': process_info['memory_percent'],
                        'create_time': datetime.fromtimestamp(process_info['create_time']).strftime('%Y-%m-%d %H:%M:%S'),
                        'username': process_info['username']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # 按CPU使用率排序，取前limit个
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            return processes[:limit]
        
        # 否则通过SSH获取
        result = execute_remote_command(server, f'ps aux --sort=-%cpu | head -n {limit + 1}')
        if result['returncode'] == 0:
            lines = result['stdout'].split('\n')[1:limit + 1]  # 跳过表头，取前limit行
            for line in lines:
                if line.strip():
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        processes.append({
                            'pid': parts[1],
                            'name': parts[10],
                            'cpu_percent': float(parts[2]),
                            'memory_percent': float(parts[3]),
                            'create_time': parts[8] + ' ' + parts[9],
                            'username': parts[0]
                        })
            
            return processes
        
        # 返回模拟数据
        return [
            {'pid': '1', 'name': 'systemd', 'cpu_percent': 0.1, 'memory_percent': 0.5, 'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'username': 'root'},
            {'pid': '2', 'name': 'sshd', 'cpu_percent': 0.0, 'memory_percent': 0.2, 'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'username': 'root'},
            {'pid': '3', 'name': 'nginx', 'cpu_percent': 2.3, 'memory_percent': 1.2, 'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'username': 'www-data'},
            {'pid': '4', 'name': 'python3', 'cpu_percent': 1.8, 'memory_percent': 3.5, 'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'username': 'root'}
        ]
        
    except Exception:
        # 返回模拟数据
        return [
            {'pid': '1', 'name': 'systemd', 'cpu_percent': 0.1, 'memory_percent': 0.5, 'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'username': 'root'},
            {'pid': '2', 'name': 'sshd', 'cpu_percent': 0.0, 'memory_percent': 0.2, 'create_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'username': 'root'}
        ]


def collect_monitoring_data(server):
    """
    收集服务器监控数据并保存到数据库
    
    Args:
        server: 服务器对象
    
    Returns:
        bool: 是否成功收集数据
    """
    try:
        from app import db
        from app.models import MonitoringData
        
        # 检查服务器是否在线
        status = get_server_status(server)
        if not status['online']:
            return False
        
        # 获取各项监控数据
        cpu_usage = get_cpu_usage(server)
        memory_usage = get_memory_usage(server)
        disk_usage = get_disk_usage(server)
        network_rx, network_tx = get_network_usage(server)
        
        # 创建监控数据记录
        monitoring_data = MonitoringData(
            server_id=server.id,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            network_rx=network_rx,
            network_tx=network_tx,
            timestamp=datetime.now()
        )
        
        # 保存到数据库
        db.session.add(monitoring_data)
        db.session.commit()
        
        return True
        
    except Exception:
        return False


def get_disk_partitions(server):
    """
    获取磁盘分区信息
    
    Args:
        server: 服务器对象
    
    Returns:
        list: 磁盘分区列表
    """
    try:
        partitions = []
        
        # 如果是本地服务器，使用psutil获取
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    })
                except (PermissionError, FileNotFoundError):
                    pass
            
            return partitions
        
        # 否则通过SSH获取
        result = execute_remote_command(server, 'df -h')
        if result['returncode'] == 0:
            lines = result['stdout'].split('\n')[1:-1]  # 跳过表头和最后一行
            for line in lines:
                if line.strip():
                    parts = line.split(None, 5)
                    if len(parts) >= 6:
                        partitions.append({
                            'device': parts[0],
                            'total': parts[1],
                            'used': parts[2],
                            'free': parts[3],
                            'percent': float(parts[4].rstrip('%')),
                            'mountpoint': parts[5]
                        })
            
            return partitions
        
        # 返回模拟数据
        return [
            {'device': '/dev/sda1', 'mountpoint': '/', 'fstype': 'ext4', 'total': 100 * 1024 * 1024 * 1024, 'used': 30 * 1024 * 1024 * 1024, 'free': 70 * 1024 * 1024 * 1024, 'percent': 30},
            {'device': '/dev/sda2', 'mountpoint': '/home', 'fstype': 'ext4', 'total': 500 * 1024 * 1024 * 1024, 'used': 200 * 1024 * 1024 * 1024, 'free': 300 * 1024 * 1024 * 1024, 'percent': 40}
        ]
        
    except Exception:
        # 返回模拟数据
        return [
            {'device': '/dev/sda1', 'mountpoint': '/', 'fstype': 'ext4', 'total': 100 * 1024 * 1024 * 1024, 'used': 30 * 1024 * 1024 * 1024, 'free': 70 * 1024 * 1024 * 1024, 'percent': 30}
        ]


def get_network_interfaces(server):
    """
    获取网络接口信息
    
    Args:
        server: 服务器对象
    
    Returns:
        list: 网络接口列表
    """
    try:
        interfaces = []
        
        # 如果是本地服务器，使用psutil获取
        if server.hostname == 'localhost' or server.hostname == '127.0.0.1':
            net_io = psutil.net_io_counters(pernic=True)
            net_if_addrs = psutil.net_if_addrs()
            
            for interface_name, io in net_io.items():
                if interface_name != 'lo':  # 跳过回环接口
                    # 获取IP地址
                    ip_address = ''
                    for addr in net_if_addrs.get(interface_name, []):
                        if addr.family.name == 'AF_INET':
                            ip_address = addr.address
                            break
                    
                    interfaces.append({
                        'name': interface_name,
                        'ip_address': ip_address,
                        'bytes_sent': io.bytes_sent,
                        'bytes_recv': io.bytes_recv,
                        'packets_sent': io.packets_sent,
                        'packets_recv': io.packets_recv,
                        'errin': io.errin,
                        'errout': io.errout
                    })
            
            return interfaces
        
        # 否则通过SSH获取
        # 简化处理，返回模拟数据
        return [
            {'name': 'eth0', 'ip_address': '192.168.1.100', 'bytes_sent': 1024 * 1024 * 1024, 'bytes_recv': 2048 * 1024 * 1024, 'packets_sent': 1000000, 'packets_recv': 2000000, 'errin': 0, 'errout': 0},
            {'name': 'eth1', 'ip_address': '10.0.0.100', 'bytes_sent': 512 * 1024 * 1024, 'bytes_recv': 1024 * 1024 * 1024, 'packets_sent': 500000, 'packets_recv': 1000000, 'errin': 0, 'errout': 0}
        ]
        
    except Exception:
        # 返回模拟数据
        return [
            {'name': 'eth0', 'ip_address': '192.168.1.100', 'bytes_sent': 1024 * 1024 * 1024, 'bytes_recv': 2048 * 1024 * 1024, 'packets_sent': 1000000, 'packets_recv': 2000000, 'errin': 0, 'errout': 0}
        ]