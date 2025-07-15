# Server Manager

## 项目简介
Ubuntu服务器管理系统(Node.js版)，提供服务器监控、文件管理、数据库备份、定时任务等功能的Web管理界面。

## 功能特点
- 服务器状态监控
- 文件上传与管理
- 数据库备份与恢复
- 定时任务管理
- 服务管理
- 网站管理

## 环境要求
- Node.js v14+ 
- npm v6+
- SQLite3

## 安装步骤
1. 克隆仓库
```bash
git clone <repository-url>
cd server-manager
```

2. 安装依赖
```bash
npm install
```

3. 配置环境变量
创建并编辑.env文件：
```
PORT=3000
NODE_ENV=production
# 其他配置变量...
```

4. 启动服务
开发环境：
```bash
npm run dev
```

生产环境：
```bash
npm start
```

## 使用方法
启动服务后，访问 http://localhost:3000 即可打开管理界面

## 目录结构
- /routes: API路由定义
- /models: 数据模型
- /utils: 工具函数
- /public: 前端静态文件
- /data: 数据库文件
- /backups: 备份文件

## 技术栈
- Express.js
- SQLite3
- Node-cron
- Systeminformation
