#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
网站管理模块工具函数

本模块提供网站管理相关的工具函数，包括网站目录创建、虚拟主机配置、SSL证书管理等功能。
"""

import os
import subprocess
import time
import datetime
import json
import re
import ssl
import socket
from cryptography import x509
from cryptography.hazmat.backends import default_backend


# 默认网站目录
DEFAULT_WEBSITE_DIR = '/var/www'

# Apache 配置目录
APACHE_VHOST_DIR = '/etc/apache2/sites-available'
APACHE_ENABLED_DIR = '/etc/apache2/sites-enabled'

# Nginx 配置目录
NGINX_VHOST_DIR = '/etc/nginx/sites-available'
NGINX_ENABLED_DIR = '/etc/nginx/sites-enabled'

# SSL 证书目录
SSL_CERT_DIR = '/etc/ssl/certs'
SSL_KEY_DIR = '/etc/ssl/private'


# 检查目录是否存在，如果不存在则创建
def ensure_directory(path):
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path (str): 目录路径
    
    Returns:
        bool: 是否成功创建或目录已存在
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            # 设置权限
            subprocess.run(['chmod', '755', path], check=True)
        return True
    except (OSError, subprocess.SubprocessError) as e:
        print(f'创建目录失败: {e}')
        return False


# 获取系统中可用的Web服务器
def get_web_servers():
    """
    获取系统中可用的Web服务器
    
    Returns:
        list: 可用的Web服务器列表
    """
    web_servers = []
    
    # 检查Apache
    try:
        result = subprocess.run(['apache2', '-v'], capture_output=True, text=True)
        if result.returncode == 0 and 'Apache' in result.stdout:
            web_servers.append('Apache')
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # 检查Nginx
    try:
        result = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        if result.returncode == 0 and 'nginx' in result.stdout:
            web_servers.append('Nginx')
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    
    return web_servers


# 检查域名是否可用
def check_domain_availability(domain):
    """
    检查域名是否可用（未被其他网站使用）
    
    Args:
        domain (str): 域名
    
    Returns:
        bool: 域名是否可用
    """
    try:
        # 检查域名格式
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?(\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?)*$', domain):
            return False
        
        # 检查是否已存在同名网站目录
        website_dir = os.path.join(DEFAULT_WEBSITE_DIR, domain)
        if os.path.exists(website_dir):
            return False
        
        # 检查是否已存在虚拟主机配置
        if os.path.exists(os.path.join(APACHE_VHOST_DIR, f'{domain}.conf')):
            return False
        if os.path.exists(os.path.join(NGINX_VHOST_DIR, f'{domain}.conf')):
            return False
        
        return True
    except Exception as e:
        print(f'检查域名可用性失败: {e}')
        return False


# 创建网站目录
def create_website_directory(domain):
    """
    创建网站目录结构
    
    Args:
        domain (str): 域名
    
    Returns:
        str: 网站文档根目录路径，如果失败则返回None
    """
    try:
        # 创建网站主目录
        website_dir = os.path.join(DEFAULT_WEBSITE_DIR, domain)
        if not ensure_directory(website_dir):
            return None
        
        # 创建文档根目录
        doc_root = os.path.join(website_dir, 'public_html')
        if not ensure_directory(doc_root):
            return None
        
        # 创建日志目录
        logs_dir = os.path.join(website_dir, 'logs')
        if not ensure_directory(logs_dir):
            return None
        
        # 创建配置目录
        conf_dir = os.path.join(website_dir, 'conf')
        if not ensure_directory(conf_dir):
            return None
        
        # 创建临时目录
        tmp_dir = os.path.join(website_dir, 'tmp')
        if not ensure_directory(tmp_dir):
            return None
        
        # 创建index.html文件
        index_file = os.path.join(doc_root, 'index.html')
        with open(index_file, 'w') as f:
            f.write(f'''
<!DOCTYPE html>
<html>
<head>
    <title>Welcome to {domain}!</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 800px;
            margin: 100px auto;
            padding: 40px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        p {{
            color: #666;
            margin-bottom: 30px;
        }}
        .info {{
            background-color: #e7f3ff;
            padding: 20px;
            border-radius: 5px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {domain}!</h1>
        <p>您的网站已经成功创建。</p>
        <div class="info">
            <p>域名: {domain}</p>
            <p>日期: {datetime.datetime.now().strftime('%Y-%m-%d')}</p>
        </div>
    </div>
</body>
</html>
''')
        
        # 设置正确的权限
        subprocess.run(['chown', '-R', 'www-data:www-data', website_dir], check=True)
        subprocess.run(['chmod', '755', doc_root], check=True)
        
        return doc_root
    except Exception as e:
        print(f'创建网站目录失败: {e}')
        return None


# 删除网站目录
def delete_website_directory(doc_root):
    """
    删除网站目录结构
    
    Args:
        doc_root (str): 网站文档根目录路径
    
    Returns:
        bool: 是否成功删除
    """
    try:
        # 获取网站主目录（假设doc_root是.../domain/public_html）
        website_dir = os.path.dirname(doc_root)
        
        if os.path.exists(website_dir):
            # 删除整个网站目录
            subprocess.run(['rm', '-rf', website_dir], check=True)
        
        return True
    except Exception as e:
        print(f'删除网站目录失败: {e}')
        return False


# 创建Apache虚拟主机配置
def create_apache_vhost(website):
    """
    创建Apache虚拟主机配置文件
    
    Args:
        website (Website): 网站对象
    
    Returns:
        bool: 是否成功创建
    """
    try:
        # 获取域名和文档根目录
        domain = website.domain
        doc_root = website.document_root
        logs_dir = os.path.join(os.path.dirname(doc_root), 'logs')
        
        # 检查Apache是否安装
        result = subprocess.run(['apache2', '-v'], capture_output=True, text=True)
        if result.returncode != 0:
            return False
        
        # 确保日志目录存在
        ensure_directory(logs_dir)
        
        # 准备配置内容
        config_content = f'''
<VirtualHost *:80>
    ServerName {domain}
    ServerAlias www.{domain}
    DocumentRoot {doc_root}
    
    ErrorLog {os.path.join(logs_dir, 'error.log')}
    CustomLog {os.path.join(logs_dir, 'access.log')} combined
    
    <Directory {doc_root}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
'''
        
        # 如果需要PHP支持
        if website.php_version:
            php_module = f'php{website.php_version.replace('.', '')}'
            config_content += f'''
    <FilesMatch \.php$>
        SetHandler "proxy:unix:/run/php/{php_module}-fpm.sock|fcgi://localhost/"
    </FilesMatch>
'''
        
        # 如果启用了SSL
        if website.ssl_enabled:
            config_content += f'''
    RewriteEngine on
    RewriteCond %{{SERVER_NAME}} ={domain} [OR]
    RewriteCond %{{SERVER_NAME}} =www.{domain}
    RewriteRule ^ https://%{{SERVER_NAME}}%{{REQUEST_URI}} [END,NE,R=permanent]
'''
        
        config_content += '''
</VirtualHost>
'''
        
        # 如果启用了SSL，添加SSL配置
        if website.ssl_enabled:
            ssl_cert = os.path.join(SSL_CERT_DIR, f'{domain}.pem')
            ssl_key = os.path.join(SSL_KEY_DIR, f'{domain}.key')
            
            config_content += f'''
<VirtualHost *:443>
    ServerName {domain}
    ServerAlias www.{domain}
    DocumentRoot {doc_root}
    
    ErrorLog {os.path.join(logs_dir, 'error.log')}
    CustomLog {os.path.join(logs_dir, 'access.log')} combined
    
    SSLEngine on
    SSLCertificateFile {ssl_cert}
    SSLCertificateKeyFile {ssl_key}
    
    <Directory {doc_root}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
'''
            
            # 如果需要PHP支持
            if website.php_version:
                config_content += f'''
    <FilesMatch \.php$>
        SetHandler "proxy:unix:/run/php/{php_module}-fpm.sock|fcgi://localhost/"
    </FilesMatch>
'''
            
            config_content += '''
</VirtualHost>
'''
        
        # 写入配置文件
        config_path = os.path.join(APACHE_VHOST_DIR, f'{domain}.conf')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # 启用虚拟主机
        subprocess.run(['a2ensite', f'{domain}.conf'], check=True)
        
        return True
    except Exception as e:
        print(f'创建Apache虚拟主机配置失败: {e}')
        return False


# 删除Apache虚拟主机配置
def delete_apache_vhost(website):
    """
    删除Apache虚拟主机配置文件
    
    Args:
        website (Website): 网站对象
    
    Returns:
        bool: 是否成功删除
    """
    try:
        domain = website.domain
        config_path = os.path.join(APACHE_VHOST_DIR, f'{domain}.conf')
        
        # 禁用虚拟主机
        subprocess.run(['a2dissite', f'{domain}.conf'], check=True)
        
        # 删除配置文件
        if os.path.exists(config_path):
            os.remove(config_path)
        
        return True
    except Exception as e:
        print(f'删除Apache虚拟主机配置失败: {e}')
        return False


# 创建Nginx虚拟主机配置
def create_nginx_vhost(website):
    """
    创建Nginx虚拟主机配置文件
    
    Args:
        website (Website): 网站对象
    
    Returns:
        bool: 是否成功创建
    """
    try:
        # 获取域名和文档根目录
        domain = website.domain
        doc_root = website.document_root
        logs_dir = os.path.join(os.path.dirname(doc_root), 'logs')
        
        # 检查Nginx是否安装
        result = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        if result.returncode != 0:
            return False
        
        # 确保日志目录存在
        ensure_directory(logs_dir)
        
        # 准备配置内容
        config_content = f'''
server {{
    listen 80;
    server_name {domain} www.{domain};
    
    root {doc_root};
    index index.html index.htm index.php;
    
    access_log {os.path.join(logs_dir, 'access.log')};
    error_log {os.path.join(logs_dir, 'error.log')};
    
    location / {{
        try_files $uri $uri/ =404;
    }}
'''
        
        # 如果需要PHP支持
        if website.php_version:
            php_module = f'php{website.php_version.replace('.', '')}'
            config_content += f'''
    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/{php_module}-fpm.sock;
    }}
'''
        
        # 如果启用了SSL
        if website.ssl_enabled:
            config_content += f'''
    return 301 https://$server_name$request_uri;
'''
        
        config_content += '''
}
'''
        
        # 如果启用了SSL，添加SSL配置
        if website.ssl_enabled:
            ssl_cert = os.path.join(SSL_CERT_DIR, f'{domain}.pem')
            ssl_key = os.path.join(SSL_KEY_DIR, f'{domain}.key')
            
            config_content += f'''
server {{
    listen 443 ssl;
    server_name {domain} www.{domain};
    
    root {doc_root};
    index index.html index.htm index.php;
    
    access_log {os.path.join(logs_dir, 'access.log')};
    error_log {os.path.join(logs_dir, 'error.log')};
    
    ssl_certificate {ssl_cert};
    ssl_certificate_key {ssl_key};
    
    location / {{
        try_files $uri $uri/ =404;
    }}
'''
            
            # 如果需要PHP支持
            if website.php_version:
                config_content += f'''
    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/{php_module}-fpm.sock;
    }}
'''
            
            config_content += '''
}
'''
        
        # 写入配置文件
        config_path = os.path.join(NGINX_VHOST_DIR, f'{domain}.conf')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # 创建符号链接启用虚拟主机
        enabled_path = os.path.join(NGINX_ENABLED_DIR, f'{domain}.conf')
        if os.path.exists(enabled_path):
            os.remove(enabled_path)
        os.symlink(config_path, enabled_path)
        
        return True
    except Exception as e:
        print(f'创建Nginx虚拟主机配置失败: {e}')
        return False


# 删除Nginx虚拟主机配置
def delete_nginx_vhost(website):
    """
    删除Nginx虚拟主机配置文件
    
    Args:
        website (Website): 网站对象
    
    Returns:
        bool: 是否成功删除
    """
    try:
        domain = website.domain
        config_path = os.path.join(NGINX_VHOST_DIR, f'{domain}.conf')
        enabled_path = os.path.join(NGINX_ENABLED_DIR, f'{domain}.conf')
        
        # 删除符号链接
        if os.path.exists(enabled_path):
            os.remove(enabled_path)
        
        # 删除配置文件
        if os.path.exists(config_path):
            os.remove(config_path)
        
        return True
    except Exception as e:
        print(f'删除Nginx虚拟主机配置失败: {e}')
        return False


# 重新加载Web服务器
def reload_web_server(web_server):
    """
    重新加载Web服务器配置
    
    Args:
        web_server (str): Web服务器类型（Apache/Nginx）
    
    Returns:
        bool: 是否成功重新加载
    """
    try:
        if web_server == 'Apache':
            subprocess.run(['systemctl', 'reload', 'apache2'], check=True)
        elif web_server == 'Nginx':
            subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
        else:
            return False
        
        return True
    except Exception as e:
        print(f'重新加载{web_server}失败: {e}')
        return False


# 安装SSL证书
def install_ssl_cert(domain):
    """
    安装SSL证书（使用Let's Encrypt）
    
    Args:
        domain (str): 域名
    
    Returns:
        bool: 是否成功安装
    """
    try:
        # 检查certbot是否安装
        result = subprocess.run(['certbot', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            # 尝试安装certbot
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'certbot'], check=True)
        
        # 获取SSL证书
        # 注意：这里使用--standalone模式，需要确保80端口未被占用
        # 在实际生产环境中，可能需要使用webroot模式
        cmd = ['certbot', 'certonly', '--standalone', '--agree-tos', '--email', 'admin@example.com', '-d', domain, '-d', f'www.{domain}']
        subprocess.run(cmd, check=True)
        
        # 复制证书到指定位置
        cert_path = f'/etc/letsencrypt/live/{domain}/fullchain.pem'
        key_path = f'/etc/letsencrypt/live/{domain}/privkey.pem'
        
        # 确保SSL目录存在
        ensure_directory(SSL_CERT_DIR)
        ensure_directory(SSL_KEY_DIR)
        
        # 复制证书
        subprocess.run(['cp', cert_path, os.path.join(SSL_CERT_DIR, f'{domain}.pem')], check=True)
        subprocess.run(['cp', key_path, os.path.join(SSL_KEY_DIR, f'{domain}.key')], check=True)
        
        # 设置权限
        subprocess.run(['chmod', '644', os.path.join(SSL_CERT_DIR, f'{domain}.pem')], check=True)
        subprocess.run(['chmod', '600', os.path.join(SSL_KEY_DIR, f'{domain}.key')], check=True)
        
        return True
    except Exception as e:
        print(f'安装SSL证书失败: {e}')
        return False


# 获取SSL证书信息
def get_ssl_info(domain):
    """
    获取SSL证书信息
    
    Args:
        domain (str): 域名
    
    Returns:
        dict: SSL证书信息，如果不存在则返回None
    """
    try:
        # 尝试从文件读取证书
        cert_path = os.path.join(SSL_CERT_DIR, f'{domain}.pem')
        if not os.path.exists(cert_path):
            return None
        
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        
        # 解析证书
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        
        # 获取证书信息
        ssl_info = {
            'subject': dict(x[0] for x in cert.subject.rdns),
            'issuer': dict(x[0] for x in cert.issuer.rdns),
            'not_before': cert.not_valid_before,
            'not_after': cert.not_valid_after,
            'serial_number': cert.serial_number,
            'version': cert.version
        }
        
        # 计算剩余天数
        remaining_days = (cert.not_valid_after - datetime.datetime.now()).days
        ssl_info['remaining_days'] = remaining_days
        
        return ssl_info
    except Exception as e:
        print(f'获取SSL证书信息失败: {e}')
        return None


# 删除SSL证书
def delete_ssl_cert(domain):
    """
    删除SSL证书
    
    Args:
        domain (str): 域名
    
    Returns:
        bool: 是否成功删除
    """
    try:
        # 删除证书文件
        cert_path = os.path.join(SSL_CERT_DIR, f'{domain}.pem')
        key_path = os.path.join(SSL_KEY_DIR, f'{domain}.key')
        
        if os.path.exists(cert_path):
            os.remove(cert_path)
        
        if os.path.exists(key_path):
            os.remove(key_path)
        
        return True
    except Exception as e:
        print(f'删除SSL证书失败: {e}')
        return False


# 获取网站统计信息
def get_website_stats(website):
    """
    获取网站统计信息
    
    Args:
        website (Website): 网站对象
    
    Returns:
        dict: 网站统计信息
    """
    try:
        stats = {
            'domain': website.domain,
            'status': 'unknown',
            'uptime': 0,
            'disk_usage': 0,
            'file_count': 0,
            'ssl_info': None
        }
        
        # 检查网站状态
        try:
            result = subprocess.run(['curl', '-I', '-m', '5', f'http://{website.domain}'], capture_output=True, text=True)
            if result.returncode == 0 and '200 OK' in result.stdout:
                stats['status'] = 'up'
            else:
                stats['status'] = 'down'
        except Exception:
            stats['status'] = 'down'
        
        # 获取磁盘使用情况
        try:
            doc_root = website.document_root
            result = subprocess.run(['du', '-sh', doc_root], capture_output=True, text=True)
            if result.returncode == 0:
                stats['disk_usage'] = result.stdout.split()[0]
        except Exception:
            pass
        
        # 获取文件数量
        try:
            result = subprocess.run(['find', website.document_root, '-type', 'f', '|', 'wc', '-l'], shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                stats['file_count'] = int(result.stdout.strip())
        except Exception:
            pass
        
        # 获取SSL信息
        if website.ssl_enabled:
            ssl_info = get_ssl_info(website.domain)
            if ssl_info:
                stats['ssl_info'] = ssl_info
        
        return stats
    except Exception as e:
        print(f'获取网站统计信息失败: {e}')
        return {
            'domain': website.domain,
            'status': 'unknown',
            'uptime': 0,
            'disk_usage': 0,
            'file_count': 0,
            'ssl_info': None
        }


# 重启网站服务
def restart_website_service(website):
    """
    重启网站相关服务
    
    Args:
        website (Website): 网站对象
    
    Returns:
        bool: 是否成功重启
    """
    try:
        # 重启Web服务器
        if not reload_web_server(website.web_server):
            return False
        
        # 如果使用PHP，重启PHP-FPM
        if website.php_version:
            php_module = f'php{website.php_version.replace('.', '')}-fpm'
            subprocess.run(['systemctl', 'restart', php_module], check=True)
        
        return True
    except Exception as e:
        print(f'重启网站服务失败: {e}')
        return False


# 获取网站日志
def get_website_logs(website, log_type='access', lines=100):
    """
    获取网站日志
    
    Args:
        website (Website): 网站对象
        log_type (str): 日志类型（access/error）
        lines (int): 获取的行数
    
    Returns:
        list: 日志行列表
    """
    try:
        logs_dir = os.path.join(os.path.dirname(website.document_root), 'logs')
        log_file = os.path.join(logs_dir, f'{log_type}.log')
        
        if not os.path.exists(log_file):
            return []
        
        # 获取日志内容
        result = subprocess.run(['tail', '-n', str(lines), log_file], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')
        else:
            return []
    except Exception as e:
        print(f'获取网站日志失败: {e}')
        return []