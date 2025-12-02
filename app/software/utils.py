#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
软件管理模块工具函数

本模块提供软件管理相关的工具函数，用于软件安装、卸载等操作的辅助功能。
"""

import subprocess
import json
import os
import platform
import re
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


def check_software_installed(software_name):
    """
    检查软件是否已安装
    
    Args:
        software_name: 软件名称
    
    Returns:
        bool: 是否已安装
    """
    try:
        # 根据操作系统类型使用不同的命令
        if platform.system() == 'Linux':
            # 尝试使用which命令检查
            result = subprocess.run(
                f'which {software_name}', 
                shell=True, 
                capture_output=True, 
                text=True
            )
            return result.returncode == 0
        elif platform.system() == 'Windows':
            # Windows系统使用where命令
            result = subprocess.run(
                f'where {software_name}', 
                shell=True, 
                capture_output=True, 
                text=True
            )
            return result.returncode == 0
        else:
            return False
            
    except Exception:
        return False


def get_software_version(software_name):
    """
    获取软件版本信息
    
    Args:
        software_name: 软件名称
    
    Returns:
        str: 版本信息，如果未安装则返回空字符串
    """
    try:
        # 尝试使用常见的版本查询命令
        version_commands = [
            f'{software_name} --version',
            f'{software_name} -v',
            f'{software_name} version'
        ]
        
        for cmd in version_commands:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                # 尝试从输出中提取版本号
                version_match = re.search(r'\d+\.\d+(\.\d+)?', result.stdout)
                if version_match:
                    return version_match.group(0)
                return result.stdout.strip()[:50]  # 最多返回50个字符
        
        return ''
        
    except Exception:
        return ''


def load_software_config(config_path=None):
    """
    加载软件配置文件
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        list: 软件配置列表
    """
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), 'software_config.json')
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 返回默认软件配置
            default_config = [
                {
                    "name": "Nginx",
                    "version": "1.24.0",
                    "category": "web",
                    "description": "高性能的HTTP和反向代理服务器",
                    "install_command": "apt-get update && apt-get install -y nginx",
                    "uninstall_command": "apt-get purge -y nginx"
                },
                {
                    "name": "Apache2",
                    "version": "2.4.58",
                    "category": "web",
                    "description": "功能强大的开源Web服务器",
                    "install_command": "apt-get update && apt-get install -y apache2",
                    "uninstall_command": "apt-get purge -y apache2"
                },
                {
                    "name": "MySQL",
                    "version": "8.0",
                    "category": "database",
                    "description": "流行的关系型数据库管理系统",
                    "install_command": "apt-get update && apt-get install -y mysql-server",
                    "uninstall_command": "apt-get purge -y mysql-server"
                },
                {
                    "name": "PostgreSQL",
                    "version": "15.0",
                    "category": "database",
                    "description": "功能强大的开源对象关系数据库系统",
                    "install_command": "apt-get update && apt-get install -y postgresql postgresql-contrib",
                    "uninstall_command": "apt-get purge -y postgresql postgresql-contrib"
                },
                {
                    "name": "Redis",
                    "version": "7.0",
                    "category": "cache",
                    "description": "高性能的内存数据库",
                    "install_command": "apt-get update && apt-get install -y redis-server",
                    "uninstall_command": "apt-get purge -y redis-server"
                },
                {
                    "name": "Python3",
                    "version": "3.10",
                    "category": "language",
                    "description": "强大的编程语言",
                    "install_command": "apt-get update && apt-get install -y python3 python3-pip",
                    "uninstall_command": "apt-get purge -y python3 python3-pip"
                },
                {
                    "name": "Node.js",
                    "version": "20.0",
                    "category": "language",
                    "description": "基于Chrome V8引擎的JavaScript运行时",
                    "install_command": "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs",
                    "uninstall_command": "apt-get purge -y nodejs"
                },
                {
                    "name": "Docker",
                    "version": "24.0",
                    "category": "other",
                    "description": "开源的容器化平台",
                    "install_command": "curl -fsSL https://get.docker.com | sh",
                    "uninstall_command": "apt-get purge -y docker-ce docker-ce-cli containerd.io"
                }
            ]
            
            # 保存默认配置到文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
            
            return default_config
            
    except Exception as e:
        print(f'加载软件配置文件时出错: {e}')
        return []


def save_software_config(software_list, config_path=None):
    """
    保存软件配置到文件
    
    Args:
        software_list: 软件配置列表
        config_path: 配置文件路径
    
    Returns:
        bool: 是否保存成功
    """
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), 'software_config.json')
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(software_list, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False


def get_software_category_display(category):
    """
    获取软件类别的中文显示名称
    
    Args:
        category: 类别代码
    
    Returns:
        str: 中文显示名称
    """
    category_map = {
        'web': 'Web服务器',
        'database': '数据库',
        'language': '编程语言',
        'cache': '缓存',
        'monitoring': '监控工具',
        'security': '安全工具',
        'other': '其他'
    }
    
    return category_map.get(category, category)


def get_installation_status_display(status):
    """
    获取安装状态的中文显示名称
    
    Args:
        status: 状态代码
    
    Returns:
        str: 中文显示名称
    """
    status_map = {
        'installing': '安装中',
        'installed': '已安装',
        'failed': '安装失败',
        'uninstalling': '卸载中',
        'uninstalled': '已卸载'
    }
    
    return status_map.get(status, status)


def parse_installation_log(log_content):
    """
    解析安装日志，提取关键信息
    
    Args:
        log_content: 日志内容
    
    Returns:
        dict: 提取的关键信息
    """
    info = {
        'steps': [],
        'errors': [],
        'warnings': [],
        'success': False
    }
    
    # 简单的日志解析逻辑
    lines = log_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if 'error' in line.lower() or 'failed' in line.lower() or 'exception' in line.lower():
            info['errors'].append(line)
        elif 'warning' in line.lower() or 'warn' in line.lower():
            info['warnings'].append(line)
        else:
            info['steps'].append(line)
    
    # 判断是否成功
    if not info['errors'] and 'success' in log_content.lower():
        info['success'] = True
    
    return info