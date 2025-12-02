#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tiny Panel - Linux服务器管理面板
数据库管理模块工具函数

本模块提供数据库管理相关的工具函数，包括数据库创建、备份、还原等操作。
"""

import os
import subprocess
import time
import datetime
import json
import re
import psycopg2
import mysql.connector
from mysql.connector import Error as MySQLError
from psycopg2 import OperationalError as PostgreSQLError


def get_database_types():
    """
    获取系统中可用的数据库类型列表
    
    Returns:
        list: 可用的数据库类型列表
    """
    db_types = []
    
    # 检查MySQL
    try:
        result = subprocess.run(['mysql', '--version'], capture_output=True, text=True)
        if result.returncode == 0 and 'mysql' in result.stdout.lower():
            db_types.append('MySQL')
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # 检查PostgreSQL
    try:
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode == 0 and 'psql' in result.stdout.lower():
            db_types.append('PostgreSQL')
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    
    return db_types


def get_database_info(db_type, db_name, db_user, db_password):
    """
    获取数据库详细信息
    
    Args:
        db_type (str): 数据库类型 (MySQL/PostgreSQL)
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        db_password (str): 数据库密码
    
    Returns:
        dict: 数据库详细信息
    """
    if db_type == 'MySQL':
        return _get_mysql_info(db_name, db_user, db_password)
    elif db_type == 'PostgreSQL':
        return _get_postgresql_info(db_name, db_user, db_password)
    else:
        raise ValueError(f'不支持的数据库类型: {db_type}')


def _get_mysql_info(db_name, db_user, db_password):
    """
    获取MySQL数据库详细信息
    
    Args:
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        db_password (str): 数据库密码
    
    Returns:
        dict: MySQL数据库详细信息
    """
    try:
        # 连接到MySQL
        connection = mysql.connector.connect(
            host='localhost',
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # 获取表列表
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            
            # 获取数据库大小
            cursor.execute(f"""SELECT table_schema AS 'Database', 
                          SUM(data_length + index_length) / 1024 / 1024 AS 'Size (MB)'
                          FROM information_schema.TABLES 
                          WHERE table_schema = '{db_name}'
                          GROUP BY table_schema""")
            size = cursor.fetchone()
            size_mb = size[1] if size else 0
            
            # 获取表信息
            tables_info = []
            for table in tables:
                cursor.execute(f"SHOW TABLE STATUS LIKE '{table}'")
                table_status = cursor.fetchone()
                
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                
                tables_info.append({
                    'name': table,
                    'engine': table_status[1],
                    'rows': row_count,
                    'size_mb': round((table_status[6] + table_status[8]) / 1024 / 1024, 2),
                    'create_time': table_status[10].strftime('%Y-%m-%d %H:%M:%S') if table_status[10] else None
                })
            
            cursor.close()
            connection.close()
            
            return {
                'type': 'MySQL',
                'name': db_name,
                'tables': tables,
                'table_count': len(tables),
                'size_mb': round(size_mb, 2),
                'tables_info': tables_info
            }
    
    except MySQLError as e:
        raise Exception(f'MySQL连接错误: {str(e)}')


def _get_postgresql_info(db_name, db_user, db_password):
    """
    获取PostgreSQL数据库详细信息
    
    Args:
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        db_password (str): 数据库密码
    
    Returns:
        dict: PostgreSQL数据库详细信息
    """
    try:
        # 连接到PostgreSQL
        connection = psycopg2.connect(
            host='localhost',
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        cursor = connection.cursor()
        
        # 获取表列表
        cursor.execute("\dt")
        tables = [table[2] for table in cursor.fetchall()]
        
        # 获取数据库大小
        cursor.execute(f"SELECT pg_database_size('{db_name}') / 1024 / 1024 AS size_mb")
        size_mb = cursor.fetchone()[0]
        
        # 获取表信息
        tables_info = []
        for table in tables:
            # 获取表行数
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            
            # 获取表大小
            cursor.execute(f"SELECT pg_total_relation_size('{table}') / 1024 / 1024 AS size_mb")
            table_size = cursor.fetchone()[0]
            
            # 获取创建时间
            cursor.execute(f"SELECT to_char(created, 'YYYY-MM-DD HH24:MI:SS') FROM pg_stat_user_tables WHERE relname = '{table}'")
            create_time = cursor.fetchone()[0]
            
            tables_info.append({
                'name': table,
                'rows': row_count,
                'size_mb': round(table_size, 2),
                'create_time': create_time
            })
        
        cursor.close()
        connection.close()
        
        return {
            'type': 'PostgreSQL',
            'name': db_name,
            'tables': tables,
            'table_count': len(tables),
            'size_mb': round(size_mb, 2),
            'tables_info': tables_info
        }
    
    except PostgreSQLError as e:
        raise Exception(f'PostgreSQL连接错误: {str(e)}')


def create_mysql_database(db_name, db_user, db_password):
    """
    创建MySQL数据库和用户
    
    Args:
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        db_password (str): 数据库密码
    
    Returns:
        tuple: (success, message)
    """
    try:
        # 检查MySQL是否安装
        result = subprocess.run(['mysql', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            return False, 'MySQL未安装或不可用'
        
        # 检查数据库是否已存在
        check_db_cmd = f"mysql -e \"SHOW DATABASES LIKE '{db_name}';\""
        check_db = subprocess.run(check_db_cmd, shell=True, capture_output=True, text=True)
        if check_db.stdout.strip():
            return False, f'数据库 {db_name} 已存在'
        
        # 检查用户是否已存在
        check_user_cmd = f"mysql -e \"SELECT User FROM mysql.user WHERE User='{db_user}';\""
        check_user = subprocess.run(check_user_cmd, shell=True, capture_output=True, text=True)
        
        # 创建数据库
        create_db_cmd = f"mysql -e \"CREATE DATABASE {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\""
        subprocess.run(create_db_cmd, shell=True, check=True)
        
        if not check_user.stdout.strip():
            # 创建用户
            create_user_cmd = f"mysql -e \"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';\""
            subprocess.run(create_user_cmd, shell=True, check=True)
        else:
            # 更新用户密码
            update_user_cmd = f"mysql -e \"ALTER USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';\""
            subprocess.run(update_user_cmd, shell=True, check=True)
        
        # 授予用户权限
        grant_cmd = f"mysql -e \"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';\""
        subprocess.run(grant_cmd, shell=True, check=True)
        
        # 刷新权限
        flush_cmd = "mysql -e \"FLUSH PRIVILEGES;\""
        subprocess.run(flush_cmd, shell=True, check=True)
        
        return True, f'MySQL数据库 {db_name} 创建成功'
    
    except subprocess.SubprocessError as e:
        return False, f'创建MySQL数据库失败: {str(e)}'
    except Exception as e:
        return False, f'发生错误: {str(e)}'


def create_postgresql_database(db_name, db_user, db_password):
    """
    创建PostgreSQL数据库和用户
    
    Args:
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        db_password (str): 数据库密码
    
    Returns:
        tuple: (success, message)
    """
    try:
        # 检查PostgreSQL是否安装
        result = subprocess.run(['psql', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            return False, 'PostgreSQL未安装或不可用'
        
        # 检查数据库是否已存在
        check_db_cmd = f"psql -U postgres -c \"SELECT datname FROM pg_database WHERE datname = '{db_name}';\""
        check_db = subprocess.run(check_db_cmd, shell=True, capture_output=True, text=True)
        if check_db.stdout.strip():
            return False, f'数据库 {db_name} 已存在'
        
        # 检查用户是否已存在
        check_user_cmd = f"psql -U postgres -c \"SELECT usename FROM pg_user WHERE usename = '{db_user}';\""
        check_user = subprocess.run(check_user_cmd, shell=True, capture_output=True, text=True)
        
        if not check_user.stdout.strip():
            # 创建用户
            create_user_cmd = f"psql -U postgres -c \"CREATE USER {db_user} WITH PASSWORD '{db_password}';\""
            subprocess.run(create_user_cmd, shell=True, check=True)
        else:
            # 更新用户密码
            update_user_cmd = f"psql -U postgres -c \"ALTER USER {db_user} WITH PASSWORD '{db_password}';\""
            subprocess.run(update_user_cmd, shell=True, check=True)
        
        # 创建数据库
        create_db_cmd = f"psql -U postgres -c \"CREATE DATABASE {db_name} OWNER {db_user} ENCODING 'UTF8';\""
        subprocess.run(create_db_cmd, shell=True, check=True)
        
        # 授予用户权限
        grant_cmd = f"psql -U postgres -c \"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};\""
        subprocess.run(grant_cmd, shell=True, check=True)
        
        return True, f'PostgreSQL数据库 {db_name} 创建成功'
    
    except subprocess.SubprocessError as e:
        return False, f'创建PostgreSQL数据库失败: {str(e)}'
    except Exception as e:
        return False, f'发生错误: {str(e)}'


def delete_database(db_type, db_name):
    """
    删除数据库
    
    Args:
        db_type (str): 数据库类型 (MySQL/PostgreSQL)
        db_name (str): 数据库名称
    
    Returns:
        tuple: (success, message)
    """
    try:
        if db_type == 'MySQL':
            # 检查数据库是否存在
            check_cmd = f"mysql -e \"SHOW DATABASES LIKE '{db_name}';\""
            check = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if not check.stdout.strip():
                return False, f'MySQL数据库 {db_name} 不存在'
            
            # 删除数据库
            delete_cmd = f"mysql -e \"DROP DATABASE {db_name};\""
            subprocess.run(delete_cmd, shell=True, check=True)
            
            return True, f'MySQL数据库 {db_name} 删除成功'
            
        elif db_type == 'PostgreSQL':
            # 检查数据库是否存在
            check_cmd = f"psql -U postgres -c \"SELECT datname FROM pg_database WHERE datname = '{db_name}';\""
            check = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if not check.stdout.strip():
                return False, f'PostgreSQL数据库 {db_name} 不存在'
            
            # 确保没有活动连接
            disconnect_cmd = f"psql -U postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_name}';\""
            subprocess.run(disconnect_cmd, shell=True, check=True)
            
            # 删除数据库
            delete_cmd = f"psql -U postgres -c \"DROP DATABASE {db_name};\""
            subprocess.run(delete_cmd, shell=True, check=True)
            
            return True, f'PostgreSQL数据库 {db_name} 删除成功'
        
        else:
            return False, f'不支持的数据库类型: {db_type}'
    
    except subprocess.SubprocessError as e:
        return False, f'删除数据库失败: {str(e)}'
    except Exception as e:
        return False, f'发生错误: {str(e)}'


def change_database_password(db_type, db_name, db_user, new_password):
    """
    修改数据库用户密码
    
    Args:
        db_type (str): 数据库类型 (MySQL/PostgreSQL)
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        new_password (str): 新密码
    
    Returns:
        tuple: (success, message)
    """
    try:
        if db_type == 'MySQL':
            # 检查用户是否存在
            check_cmd = f"mysql -e \"SELECT User FROM mysql.user WHERE User='{db_user}';\""
            check = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if not check.stdout.strip():
                return False, f'MySQL用户 {db_user} 不存在'
            
            # 修改密码
            update_cmd = f"mysql -e \"ALTER USER '{db_user}'@'localhost' IDENTIFIED BY '{new_password}';\""
            subprocess.run(update_cmd, shell=True, check=True)
            
            # 刷新权限
            flush_cmd = "mysql -e \"FLUSH PRIVILEGES;\""
            subprocess.run(flush_cmd, shell=True, check=True)
            
            return True, f'MySQL用户 {db_user} 密码修改成功'
            
        elif db_type == 'PostgreSQL':
            # 检查用户是否存在
            check_cmd = f"psql -U postgres -c \"SELECT usename FROM pg_user WHERE usename = '{db_user}';\""
            check = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if not check.stdout.strip():
                return False, f'PostgreSQL用户 {db_user} 不存在'
            
            # 修改密码
            update_cmd = f"psql -U postgres -c \"ALTER USER {db_user} WITH PASSWORD '{new_password}';\""
            subprocess.run(update_cmd, shell=True, check=True)
            
            return True, f'PostgreSQL用户 {db_user} 密码修改成功'
        
        else:
            return False, f'不支持的数据库类型: {db_type}'
    
    except subprocess.SubprocessError as e:
        return False, f'修改密码失败: {str(e)}'
    except Exception as e:
        return False, f'发生错误: {str(e)}'


def backup_database(db_type, db_name, db_user, db_password, backup_name=None):
    """
    备份数据库
    
    Args:
        db_type (str): 数据库类型 (MySQL/PostgreSQL)
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        db_password (str): 数据库密码
        backup_name (str): 备份文件名（可选）
    
    Returns:
        tuple: (success, message)
    """
    try:
        # 创建备份目录
        backup_dir = os.path.join('app', 'static', 'backups', db_name)
        os.makedirs(backup_dir, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        if backup_name:
            filename = f'{backup_name}_{timestamp}'
        else:
            filename = f'{db_name}_{timestamp}'
        
        if db_type == 'MySQL':
            # MySQL备份
            backup_file = os.path.join(backup_dir, f'{filename}.sql')
            cmd = f"mysqldump -u {db_user} -p{db_password} --databases {db_name} > {backup_file}"
            subprocess.run(cmd, shell=True, check=True)
            
            # 压缩备份文件
            zip_cmd = f"zip -q {backup_file}.zip {backup_file}"
            subprocess.run(zip_cmd, shell=True, check=True)
            
            # 删除未压缩的文件
            os.remove(backup_file)
            
            return True, f'MySQL数据库备份成功: {filename}.sql.zip'
            
        elif db_type == 'PostgreSQL':
            # PostgreSQL备份
            backup_file = os.path.join(backup_dir, f'{filename}.sql')
            cmd = f"PGPASSWORD={db_password} pg_dump -U {db_user} -d {db_name} > {backup_file}"
            subprocess.run(cmd, shell=True, check=True)
            
            # 压缩备份文件
            zip_cmd = f"zip -q {backup_file}.zip {backup_file}"
            subprocess.run(zip_cmd, shell=True, check=True)
            
            # 删除未压缩的文件
            os.remove(backup_file)
            
            return True, f'PostgreSQL数据库备份成功: {filename}.sql.zip'
        
        else:
            return False, f'不支持的数据库类型: {db_type}'
    
    except subprocess.SubprocessError as e:
        return False, f'数据库备份失败: {str(e)}'
    except Exception as e:
        return False, f'发生错误: {str(e)}'


def restore_database(db_type, db_name, db_user, db_password, backup_file):
    """
    从备份还原数据库
    
    Args:
        db_type (str): 数据库类型 (MySQL/PostgreSQL)
        db_name (str): 数据库名称
        db_user (str): 数据库用户名
        db_password (str): 数据库密码
        backup_file (str): 备份文件名
    
    Returns:
        tuple: (success, message)
    """
    try:
        # 构建备份文件路径
        backup_dir = os.path.join('app', 'static', 'backups', db_name)
        backup_path = os.path.join(backup_dir, backup_file)
        
        # 检查备份文件是否存在
        if not os.path.exists(backup_path):
            return False, f'备份文件 {backup_file} 不存在'
        
        temp_file = None
        try:
            # 如果是压缩文件，先解压
            if backup_file.endswith('.zip'):
                temp_file = backup_path[:-4]  # 去掉.zip扩展名
                unzip_cmd = f"unzip -q {backup_path} -d {backup_dir}"
                subprocess.run(unzip_cmd, shell=True, check=True)
                sql_file = temp_file
            else:
                sql_file = backup_path
            
            if db_type == 'MySQL':
                # MySQL还原
                cmd = f"mysql -u {db_user} -p{db_password} {db_name} < {sql_file}"
                subprocess.run(cmd, shell=True, check=True)
                
                return True, f'MySQL数据库还原成功: {db_name}'
                
            elif db_type == 'PostgreSQL':
                # PostgreSQL还原
                # 先清空数据库
                truncate_cmd = f"PGPASSWORD={db_password} psql -U {db_user} -d {db_name} -c \"DO $$ DECLARE r record; BEGIN FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE'; END LOOP; END $$;\""
                subprocess.run(truncate_cmd, shell=True, check=True)
                
                # 执行还原
                cmd = f"PGPASSWORD={db_password} psql -U {db_user} -d {db_name} < {sql_file}"
                subprocess.run(cmd, shell=True, check=True)
                
                return True, f'PostgreSQL数据库还原成功: {db_name}'
            
            else:
                return False, f'不支持的数据库类型: {db_type}'
                
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
    
    except subprocess.SubprocessError as e:
        return False, f'数据库还原失败: {str(e)}'
    except Exception as e:
        return False, f'发生错误: {str(e)}'