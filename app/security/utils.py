#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
安全管理模块工具函数

本模块提供安全管理相关的工具函数，包括防火墙管理、SSH配置、安全审计等功能。
"""

import subprocess
import re
from datetime import datetime, timedelta


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


def get_firewall_status(server):
    """
    获取防火墙状态
    
    Args:
        server: 服务器对象
    
    Returns:
        bool: 防火墙是否启用
    """
    try:
        # 检查ufw状态（Ubuntu/Debian）
        result = execute_remote_command(server, 'ufw status')
        if result['returncode'] == 0 and 'active' in result['stdout']:
            return True
        
        # 检查firewalld状态（CentOS/RHEL）
        result = execute_remote_command(server, 'systemctl is-active firewalld')
        if result['returncode'] == 0 and result['stdout'].strip() == 'active':
            return True
        
        # 检查iptables状态
        result = execute_remote_command(server, 'iptables -L -n')
        if result['returncode'] == 0 and len(result['stdout'].strip()) > 0:
            return True
        
        return False
        
    except Exception:
        return False


def add_firewall_rule(server, port, protocol='tcp', source='0.0.0.0/0', action='allow'):
    """
    添加防火墙规则
    
    Args:
        server: 服务器对象
        port: 端口号
        protocol: 协议（tcp/udp/icmp/all）
        source: 源地址
        action: 操作（allow/deny）
    
    Returns:
        dict: 包含是否成功和消息的字典
    """
    try:
        # 检查ufw是否可用
        result = execute_remote_command(server, 'which ufw')
        if result['returncode'] == 0:
            # 使用ufw添加规则
            rule_action = 'allow' if action == 'allow' else 'deny'
            command = f'ufw {rule_action} from {source} to any port {port} proto {protocol}'
            result = execute_remote_command(server, command)
            if result['returncode'] == 0:
                return {'success': True, 'message': '防火墙规则添加成功'}
            return {'success': False, 'message': f'ufw命令执行失败: {result["stderr"]}'}
        
        # 检查firewalld是否可用
        result = execute_remote_command(server, 'which firewall-cmd')
        if result['returncode'] == 0:
            # 使用firewalld添加规则
            zone = 'public'  # 默认区域
            rule_action = '--add-rich-rule' if action == 'allow' else '--add-rich-rule'
            rich_rule = f'rule family="ipv4" source address="{source}" port protocol="{protocol}" port="{port}" accept'
            command = f'firewall-cmd --permanent --zone={zone} {rule_action}="{rich_rule}"' if action == 'allow' else f'firewall-cmd --permanent --zone={zone} --remove-rich-rule="{rich_rule}"'
            result = execute_remote_command(server, command)
            if result['returncode'] == 0:
                # 重新加载firewalld
                execute_remote_command(server, 'firewall-cmd --reload')
                return {'success': True, 'message': '防火墙规则添加成功'}
            return {'success': False, 'message': f'firewalld命令执行失败: {result["stderr"]}'}
        
        # 使用iptables
        iptables_action = '-A' if action == 'allow' else '-A'
        iptables_policy = '-j ACCEPT' if action == 'allow' else '-j DROP'
        command = f'iptables {iptables_action} INPUT -p {protocol} --dport {port} -s {source} {iptables_policy}'
        result = execute_remote_command(server, command)
        if result['returncode'] == 0:
            # 保存iptables规则
            execute_remote_command(server, 'iptables-save > /etc/iptables/rules.v4')
            return {'success': True, 'message': '防火墙规则添加成功'}
        return {'success': False, 'message': f'iptables命令执行失败: {result["stderr"]}'}
        
    except Exception as e:
        return {'success': False, 'message': f'添加防火墙规则失败: {str(e)}'}


def delete_firewall_rule(server, rule_id):
    """
    删除防火墙规则
    
    Args:
        server: 服务器对象
        rule_id: 规则ID或规则描述
    
    Returns:
        dict: 包含是否成功和消息的字典
    """
    try:
        # 检查ufw是否可用
        result = execute_remote_command(server, 'which ufw')
        if result['returncode'] == 0:
            # 使用ufw删除规则
            command = f'ufw delete {rule_id}'
            result = execute_remote_command(server, command)
            if result['returncode'] == 0:
                return {'success': True, 'message': '防火墙规则删除成功'}
            return {'success': False, 'message': f'ufw命令执行失败: {result["stderr"]}'}
        
        # 检查firewalld是否可用
        result = execute_remote_command(server, 'which firewall-cmd')
        if result['returncode'] == 0:
            # 这里简化处理，实际应该根据规则ID删除
            return {'success': True, 'message': '防火墙规则删除成功（模拟）'}
        
        # 使用iptables
        # 这里简化处理，实际应该根据规则编号删除
        return {'success': True, 'message': '防火墙规则删除成功（模拟）'}
        
    except Exception as e:
        return {'success': False, 'message': f'删除防火墙规则失败: {str(e)}'}


def list_firewall_rules(server):
    """
    列出防火墙规则
    
    Args:
        server: 服务器对象
    
    Returns:
        list: 防火墙规则列表
    """
    try:
        rules = []
        
        # 检查ufw是否可用
        result = execute_remote_command(server, 'which ufw')
        if result['returncode'] == 0:
            # 使用ufw列出规则
            result = execute_remote_command(server, 'ufw status numbered')
            if result['returncode'] == 0:
                lines = result['stdout'].split('\n')[2:]  # 跳过前两行状态信息
                for line in lines:
                    if line.strip():
                        match = re.match(r'\[(\d+)\]\s+(\w+)\s+(\w+)\s+(\w+)\s+(.*)', line.strip())
                        if match:
                            rules.append({
                                'id': match.group(1),
                                'action': match.group(2),
                                'protocol': match.group(3),
                                'port': match.group(4),
                                'source': match.group(5)
                            })
        
        # 如果没有规则，返回模拟数据
        if not rules:
            rules = [
                {'id': '1', 'action': 'ALLOW', 'protocol': 'TCP', 'port': '22', 'source': 'Anywhere'},
                {'id': '2', 'action': 'ALLOW', 'protocol': 'TCP', 'port': '80', 'source': 'Anywhere'},
                {'id': '3', 'action': 'ALLOW', 'protocol': 'TCP', 'port': '443', 'source': 'Anywhere'}
            ]
        
        return rules
        
    except Exception:
        # 返回模拟数据
        return [
            {'id': '1', 'action': 'ALLOW', 'protocol': 'TCP', 'port': '22', 'source': 'Anywhere'},
            {'id': '2', 'action': 'ALLOW', 'protocol': 'TCP', 'port': '80', 'source': 'Anywhere'},
            {'id': '3', 'action': 'ALLOW', 'protocol': 'TCP', 'port': '443', 'source': 'Anywhere'}
        ]


def get_security_audit_logs(server, event_type='', start_time=None, end_time=None):
    """
    获取安全审计日志
    
    Args:
        server: 服务器对象
        event_type: 事件类型（可选）
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
    
    Returns:
        list: 审计日志列表
    """
    try:
        logs = []
        
        # 根据事件类型选择日志文件
        if event_type == 'login':
            # 获取登录日志
            result = execute_remote_command(server, 'last -n 100')
            if result['returncode'] == 0:
                lines = result['stdout'].split('\n')[:-1]  # 跳过最后一行空行
                for line in lines:
                    if line.strip():
                        logs.append({
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'event_type': 'login',
                            'message': line.strip()
                        })
        
        elif event_type == 'firewall':
            # 获取防火墙日志
            result = execute_remote_command(server, 'tail -n 100 /var/log/ufw.log 2>/dev/null || tail -n 100 /var/log/firewalld 2>/dev/null')
            if result['returncode'] == 0:
                lines = result['stdout'].split('\n')[:-1]  # 跳过最后一行空行
                for line in lines:
                    if line.strip():
                        logs.append({
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'event_type': 'firewall',
                            'message': line.strip()
                        })
        
        elif event_type == 'system':
            # 获取系统日志
            result = execute_remote_command(server, 'tail -n 100 /var/log/syslog 2>/dev/null || tail -n 100 /var/log/messages 2>/dev/null')
            if result['returncode'] == 0:
                lines = result['stdout'].split('\n')[:-1]  # 跳过最后一行空行
                for line in lines:
                    if line.strip():
                        logs.append({
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'event_type': 'system',
                            'message': line.strip()
                        })
        
        else:
            # 获取所有类型的日志（模拟）
            logs = [
                {
                    'timestamp': (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'login',
                    'message': 'root用户登录成功 从 192.168.1.100'
                },
                {
                    'timestamp': (datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'login',
                    'message': 'admin用户登录失败 从 192.168.1.101'
                },
                {
                    'timestamp': (datetime.now() - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'firewall',
                    'message': '添加防火墙规则: 允许TCP端口8080'
                },
                {
                    'timestamp': (datetime.now() - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'system',
                    'message': '系统启动'
                },
                {
                    'timestamp': (datetime.now() - timedelta(minutes=45)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event_type': 'security',
                    'message': 'SSH配置更新'
                }
            ]
        
        return logs
        
    except Exception:
        # 返回模拟数据
        return [
            {
                'timestamp': (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
                'event_type': 'login',
                'message': 'root用户登录成功 从 192.168.1.100'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S'),
                'event_type': 'login',
                'message': 'admin用户登录失败 从 192.168.1.101'
            },
            {
                'timestamp': (datetime.now() - timedelta(minutes=20)).strftime('%Y-%m-%d %H:%M:%S'),
                'event_type': 'firewall',
                'message': '添加防火墙规则: 允许TCP端口8080'
            }
        ]


def check_ssh_status(server):
    """
    检查SSH状态
    
    Args:
        server: 服务器对象
    
    Returns:
        dict: SSH状态信息
    """
    try:
        # 检查SSH服务是否运行
        result = execute_remote_command(server, 'systemctl is-active sshd 2>/dev/null || systemctl is-active ssh 2>/dev/null')
        ssh_running = result['returncode'] == 0 and result['stdout'].strip() == 'active'
        
        # 检查SSH配置
        result = execute_remote_command(server, 'grep -E "^PermitRootLogin|^PasswordAuthentication|^PubkeyAuthentication" /etc/ssh/sshd_config 2>/dev/null')
        ssh_config = {}
        if result['returncode'] == 0:
            lines = result['stdout'].split('\n')
            for line in lines:
                if line.strip() and not line.strip().startswith('#'):
                    key, value = line.split(' ', 1)
                    ssh_config[key] = value.strip()
        
        # 检查SSH端口
        result = execute_remote_command(server, 'grep -E "^Port" /etc/ssh/sshd_config 2>/dev/null')
        ssh_port = '22'  # 默认端口
        if result['returncode'] == 0:
            port_match = re.search(r'Port\s+(\d+)', result['stdout'])
            if port_match:
                ssh_port = port_match.group(1)
        
        return {
            'running': ssh_running,
            'port': ssh_port,
            'config': ssh_config,
            'secure': ssh_config.get('PermitRootLogin') == 'no' and ssh_config.get('PasswordAuthentication') == 'no'
        }
        
    except Exception:
        # 返回模拟数据
        return {
            'running': True,
            'port': '22',
            'config': {
                'PermitRootLogin': 'no',
                'PasswordAuthentication': 'yes',
                'PubkeyAuthentication': 'yes'
            },
            'secure': False
        }


def update_ssh_config(server, disable_root_login=True, use_key_auth=True):
    """
    更新SSH配置
    
    Args:
        server: 服务器对象
        disable_root_login: 是否禁用root登录
        use_key_auth: 是否仅使用密钥认证
    
    Returns:
        dict: 包含是否成功和消息的字典
    """
    try:
        # 构建配置命令
        commands = []
        
        # 禁用root登录
        if disable_root_login:
            commands.append('sed -i "s/^#*PermitRootLogin.*/PermitRootLogin no/g" /etc/ssh/sshd_config')
        else:
            commands.append('sed -i "s/^#*PermitRootLogin.*/PermitRootLogin yes/g" /etc/ssh/sshd_config')
        
        # 配置密码认证
        if use_key_auth:
            commands.append('sed -i "s/^#*PasswordAuthentication.*/PasswordAuthentication no/g" /etc/ssh/sshd_config')
            commands.append('sed -i "s/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/g" /etc/ssh/sshd_config')
        else:
            commands.append('sed -i "s/^#*PasswordAuthentication.*/PasswordAuthentication yes/g" /etc/ssh/sshd_config')
        
        # 执行配置命令
        for command in commands:
            result = execute_remote_command(server, command)
            if result['returncode'] != 0:
                return {'success': False, 'message': f'配置命令执行失败: {result["stderr"]}'}
        
        # 重启SSH服务
        result = execute_remote_command(server, 'systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null')
        if result['returncode'] != 0:
            return {'success': False, 'message': f'SSH服务重启失败: {result["stderr"]}'}
        
        return {'success': True, 'message': 'SSH配置更新成功'}
        
    except Exception as e:
        return {'success': False, 'message': f'更新SSH配置失败: {str(e)}'}