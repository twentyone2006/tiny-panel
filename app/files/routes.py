#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tiny Panel - Linux服务器管理面板
文件管理模块路由
"""

import os
import shutil
from flask import render_template, redirect, url_for, request, flash, send_file, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import Server
from app.files import files

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'zip', 'rar', 'tar', 'gz'}

# 检查文件类型是否允许
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 获取文件大小的友好显示
def get_human_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

# 获取文件或目录的权限模式
def get_permissions(path):
    st_mode = os.stat(path).st_mode
    return oct(st_mode)[-3:]

# 格式化文件修改时间
def get_modified_time(path):
    return os.path.getmtime(path)

# 根目录文件浏览页面
@files.route('/files')
@login_required
def file_manager():
    # 默认从根目录开始浏览
    return redirect(url_for('files.browse', path=''))

# 文件浏览功能
@files.route('/files/browse/<path:path>')
@login_required
def browse(path):
    # 获取服务器的根目录，这里使用当前用户的主目录作为示例
    # 实际应用中应该根据服务器配置获取根目录
    root_dir = os.path.abspath('/')
    
    # 构建完整路径
    current_path = os.path.join(root_dir, path)
    
    # 安全检查：确保用户不会访问根目录以外的文件
    if not os.path.abspath(current_path).startswith(root_dir):
        flash('无权访问该目录！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    # 检查路径是否存在
    if not os.path.exists(current_path):
        flash('目录不存在！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    # 获取当前路径的上一级目录
    parent_path = os.path.dirname(path)
    
    # 获取当前目录下的所有文件和文件夹
    try:
        items = os.listdir(current_path)
    except PermissionError:
        flash('没有权限访问该目录！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    # 准备文件和文件夹列表
    directories = []
    files_list = []
    
    for item in items:
        item_path = os.path.join(current_path, item)
        item_relative_path = os.path.join(path, item)
        
        try:
            if os.path.isdir(item_path):
                # 文件夹信息
                directories.append({
                    'name': item,
                    'path': item_relative_path,
                    'permissions': get_permissions(item_path),
                    'modified_time': get_modified_time(item_path),
                    'size': '-',
                    'type': 'directory'
                })
            else:
                # 文件信息
                files_list.append({
                    'name': item,
                    'path': item_relative_path,
                    'permissions': get_permissions(item_path),
                    'modified_time': get_modified_time(item_path),
                    'size': get_human_size(os.path.getsize(item_path)),
                    'type': item.rsplit('.', 1)[1].lower() if '.' in item else 'file'
                })
        except PermissionError:
            # 跳过没有权限的文件或文件夹
            continue
    
    # 按名称排序：文件夹在前，文件在后
    directories.sort(key=lambda x: x['name'].lower())
    files_list.sort(key=lambda x: x['name'].lower())
    
    return render_template('files/browse.html', 
                          parent_path=parent_path,
                          current_path=path,
                          directories=directories,
                          files=files_list)

# 创建文件夹
@files.route('/files/create_directory/<path:path>', methods=['POST'])
def create_directory(path):
    root_dir = os.path.abspath('/')
    current_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(current_path).startswith(root_dir):
        flash('无权访问该目录！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    dir_name = request.form.get('dir_name')
    if not dir_name:
        flash('文件夹名称不能为空！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    # 检查文件夹名称是否合法
    if any(c in dir_name for c in '/\:*?"<>|'):
        flash('文件夹名称包含非法字符！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    new_dir_path = os.path.join(current_path, dir_name)
    
    try:
        os.makedirs(new_dir_path, exist_ok=False)
        flash(f'文件夹 "{dir_name}" 创建成功！', 'success')
    except Exception as e:
        flash(f'创建文件夹失败：{str(e)}', 'danger')
    
    return redirect(url_for('files.browse', path=path))

# 删除文件或文件夹
@files.route('/files/delete/<path:path>', methods=['POST'])
def delete(path):
    root_dir = os.path.abspath('/')
    item_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(item_path).startswith(root_dir):
        flash('无权访问该文件！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    try:
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
            flash(f'文件夹 "{os.path.basename(item_path)}" 删除成功！', 'success')
        else:
            os.remove(item_path)
            flash(f'文件 "{os.path.basename(item_path)}" 删除成功！', 'success')
    except Exception as e:
        flash(f'删除失败：{str(e)}', 'danger')
    
    # 返回上一级目录
    parent_path = os.path.dirname(path)
    return redirect(url_for('files.browse', path=parent_path))

# 重命名文件或文件夹
@files.route('/files/rename/<path:path>', methods=['POST'])
def rename(path):
    root_dir = os.path.abspath('/')
    item_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(item_path).startswith(root_dir):
        flash('无权访问该文件！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    new_name = request.form.get('new_name')
    if not new_name:
        flash('新名称不能为空！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    # 检查新名称是否合法
    if any(c in new_name for c in '/\:*?"<>|'):
        flash('名称包含非法字符！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    # 构建新路径
    parent_path = os.path.dirname(item_path)
    new_path = os.path.join(parent_path, new_name)
    
    try:
        os.rename(item_path, new_path)
        flash(f'重命名成功！', 'success')
    except Exception as e:
        flash(f'重命名失败：{str(e)}', 'danger')
    
    # 返回上一级目录
    return redirect(url_for('files.browse', path=os.path.dirname(path)))

# 上传文件
@files.route('/files/upload/<path:path>', methods=['POST'])
def upload_file(path):
    root_dir = os.path.abspath('/')
    current_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(current_path).startswith(root_dir):
        flash('无权访问该目录！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    # 检查是否有文件上传
    if 'file' not in request.files:
        flash('请选择要上传的文件！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    file = request.files['file']
    
    # 如果用户没有选择文件，浏览器会发送一个空文件
    if file.filename == '':
        flash('请选择要上传的文件！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    # 检查文件类型
    if not allowed_file(file.filename):
        flash('不允许上传该类型的文件！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    # 保存文件
    try:
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_path, filename))
        flash(f'文件 "{filename}" 上传成功！', 'success')
    except Exception as e:
        flash(f'文件上传失败：{str(e)}', 'danger')
    
    return redirect(url_for('files.browse', path=path))

# 下载文件
@files.route('/files/download/<path:path>')
@login_required
def download_file(path):
    root_dir = os.path.abspath('/')
    file_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(file_path).startswith(root_dir):
        flash('无权访问该文件！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        flash('文件不存在！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    try:
        return send_file(file_path, as_attachment=True, attachment_filename=os.path.basename(file_path))
    except Exception as e:
        flash(f'文件下载失败：{str(e)}', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))

# 编辑文件
@files.route('/files/edit/<path:path>', methods=['GET', 'POST'])
@login_required
def edit_file(path):
    root_dir = os.path.abspath('/')
    file_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(file_path).startswith(root_dir):
        flash('无权访问该文件！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    if not os.path.exists(file_path) or os.path.isdir(file_path):
        flash('文件不存在！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    # 检查文件大小，限制大文件的编辑
    file_size = os.path.getsize(file_path)
    if file_size > 1024 * 1024:  # 限制1MB以内的文件可以编辑
        flash('文件过大，不建议在线编辑！', 'warning')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    # 检查文件类型，只允许文本文件编辑
    file_ext = os.path.splitext(file_path)[1].lower()
    text_extensions = ['.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.ini', '.conf', '.log', '.md']
    if file_ext not in text_extensions:
        flash('该类型文件不支持在线编辑！', 'warning')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    # 读取文件内容
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        flash(f'读取文件失败：{str(e)}', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    if request.method == 'POST':
        # 获取新的文件内容
        new_content = request.form.get('content')
        
        # 保存文件内容
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            flash(f'文件 "{os.path.basename(file_path)}" 保存成功！', 'success')
            return redirect(url_for('files.browse', path=os.path.dirname(path)))
        except Exception as e:
            flash(f'保存文件失败：{str(e)}', 'danger')
    
    return render_template('files/edit.html', 
                          file_path=path,
                          file_name=os.path.basename(file_path),
                          content=content)

# 创建新文件
@files.route('/files/create/<path:path>', methods=['POST'])
def create_file(path):
    root_dir = os.path.abspath('/')
    current_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(current_path).startswith(root_dir):
        flash('无权访问该目录！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    file_name = request.form.get('file_name')
    if not file_name:
        flash('文件名不能为空！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    # 检查文件名是否合法
    if any(c in file_name for c in '/\:*?"<>|'):
        flash('文件名包含非法字符！', 'danger')
        return redirect(url_for('files.browse', path=path))
    
    # 构建新文件路径
    new_file_path = os.path.join(current_path, file_name)
    
    try:
        with open(new_file_path, 'w', encoding='utf-8') as f:
            f.write('')
        flash(f'文件 "{file_name}" 创建成功！', 'success')
    except Exception as e:
        flash(f'创建文件失败：{str(e)}', 'danger')
    
    return redirect(url_for('files.browse', path=path))

# 复制文件或文件夹
@files.route('/files/copy/<path:path>', methods=['POST'])
def copy_file(path):
    root_dir = os.path.abspath('/')
    source_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(source_path).startswith(root_dir):
        flash('无权访问该文件！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    if not os.path.exists(source_path):
        flash('源文件或目录不存在！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    # 获取目标路径
    target_path = request.form.get('target_path')
    if not target_path:
        flash('目标路径不能为空！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    target_full_path = os.path.join(root_dir, target_path)
    
    # 安全检查
    if not os.path.abspath(target_full_path).startswith(root_dir) or not os.path.exists(target_full_path):
        flash('目标路径无效！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    try:
        source_name = os.path.basename(source_path)
        destination_path = os.path.join(target_full_path, source_name)
        
        # 如果目标已存在，添加数字后缀
        counter = 1
        while os.path.exists(destination_path):
            base_name, ext = os.path.splitext(source_name)
            destination_path = os.path.join(target_full_path, f"{base_name}_{counter}{ext}")
            counter += 1
        
        if os.path.isdir(source_path):
            shutil.copytree(source_path, destination_path)
            flash(f'文件夹 "{source_name}" 复制成功！', 'success')
        else:
            shutil.copy2(source_path, destination_path)
            flash(f'文件 "{source_name}" 复制成功！', 'success')
    except Exception as e:
        flash(f'复制失败：{str(e)}', 'danger')
    
    return redirect(url_for('files.browse', path=os.path.dirname(path)))

# 移动文件或文件夹
@files.route('/files/move/<path:path>', methods=['POST'])
def move_file(path):
    root_dir = os.path.abspath('/')
    source_path = os.path.join(root_dir, path)
    
    if not os.path.abspath(source_path).startswith(root_dir):
        flash('无权访问该文件！', 'danger')
        return redirect(url_for('files.file_manager'))
    
    if not os.path.exists(source_path):
        flash('源文件或目录不存在！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    # 获取目标路径
    target_path = request.form.get('target_path')
    if not target_path:
        flash('目标路径不能为空！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    target_full_path = os.path.join(root_dir, target_path)
    
    # 安全检查
    if not os.path.abspath(target_full_path).startswith(root_dir) or not os.path.exists(target_full_path):
        flash('目标路径无效！', 'danger')
        return redirect(url_for('files.browse', path=os.path.dirname(path)))
    
    try:
        source_name = os.path.basename(source_path)
        destination_path = os.path.join(target_full_path, source_name)
        
        # 如果目标已存在，添加数字后缀
        counter = 1
        while os.path.exists(destination_path):
            base_name, ext = os.path.splitext(source_name)
            destination_path = os.path.join(target_full_path, f"{base_name}_{counter}{ext}")
            counter += 1
        
        os.rename(source_path, destination_path)
        flash(f'移动成功！', 'success')
    except Exception as e:
        flash(f'移动失败：{str(e)}', 'danger')
    
    return redirect(url_for('files.browse', path=os.path.dirname(path)))
