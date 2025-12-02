#!/bin/bash

# Tiny Panel 一键安装脚本
# Version: 1.0.0

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}  Tiny Panel - Linux服务器管理面板${NC}"
echo -e "${GREEN}        一键安装脚本${NC}"
echo -e "${BLUE}=========================================${NC}"
echo

# 检查是否为root用户
if [ "$(id -u)" != "0" ]; then
    echo -e "${RED}错误: 请使用root用户运行此脚本${NC}"
    exit 1
fi

# 检查操作系统
echo -e "${BLUE}检查操作系统...${NC}"
if [ -f /etc/centos-release ]; then
    OS=centos
    VER=$(grep -oE '[0-9]+\.[0-9]+' /etc/centos-release | head -1)
elif [ -f /etc/redhat-release ]; then
    OS=redhat
    VER=$(grep -oE '[0-9]+\.[0-9]+' /etc/redhat-release | head -1)
elif [ -f /etc/ubuntu-release ] || grep -q 'Ubuntu' /etc/os-release; then
    OS=ubuntu
    VER=$(grep -oE '[0-9]+\.[0-9]+' /etc/os-release | head -1)
elif [ -f /etc/debian_version ]; then
    OS=debian
    VER=$(cat /etc/debian_version)
else
    echo -e "${RED}错误: 不支持的操作系统${NC}"
    exit 1
fi

echo -e "${GREEN}操作系统: $OS $VER${NC}"

# 检查Python版本
echo -e "\n${BLUE}检查Python版本...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}Python版本: $PYTHON_VERSION${NC}"
    if [[ "$PYTHON_VERSION" < "3.7" ]]; then
        echo -e "${RED}错误: Python版本必须大于等于3.7${NC}"
        exit 1
    fi
else
    echo -e "${RED}错误: 未找到Python3${NC}"
    exit 1
fi

# 安装系统依赖
echo -e "\n${BLUE}安装系统依赖...${NC}"
case "$OS" in
    centos|redhat)
        yum update -y
        yum install -y gcc python3-devel python3-pip mariadb-devel openssl-devel git
        ;;
    ubuntu|debian)
        apt-get update -y
        apt-get install -y gcc python3-dev python3-pip default-libmysqlclient-dev libssl-dev git
        ;;
esac

# 安装Python虚拟环境工具
pip3 install --upgrade pip virtualenv

# 创建安装目录
INSTALL_DIR="/opt/tiny-panel"
DATA_DIR="/var/lib/tiny-panel"
LOG_DIR="/var/log/tiny-panel"

echo -e "\n${BLUE}创建安装目录...${NC}"
mkdir -p $INSTALL_DIR $DATA_DIR $LOG_DIR

# 进入安装目录
cd $INSTALL_DIR

# 下载代码
echo -e "\n${BLUE}下载Tiny Panel代码...${NC}"
if command -v git &> /dev/null; then
    git clone https://github.com/tiny-panel/tiny-panel.git .
else
    # 如果没有git，使用wget下载
    wget -O tiny-panel.tar.gz http://www.tiny-lab.cn/dl/tiny-panel.tar.gz
    tar -xzf tiny-panel.tar.gz --strip-components=1
    rm tiny-panel.tar.gz
fi

# 创建虚拟环境
echo -e "\n${BLUE}创建Python虚拟环境...${NC}"
python3 -m virtualenv venv
source venv/bin/activate

# 安装Python依赖
echo -e "\n${BLUE}安装Python依赖...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量
echo -e "\n${BLUE}配置环境变量...${NC}"
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite:///$DATA_DIR/tiny_panel.db
LOG_TO_STDOUT=true
EOF

# 初始化数据库
echo -e "\n${BLUE}初始化数据库...${NC}"
python -c "from app import create_app, db; from app.models import User; app = create_app('prod'); with app.app_context(): db.create_all(); if not User.query.filter_by(username='admin').first(): admin = User(username='admin', email='admin@example.com'); admin.set_password('admin123'); db.session.add(admin); db.session.commit(); print('默认管理员账号已创建')"

# 创建系统服务
echo -e "\n${BLUE}创建系统服务...${NC}"
cat > /etc/systemd/system/tiny-panel.service << EOF
[Unit]
Description=Tiny Panel - Linux服务器管理面板
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=FLASK_ENV=prod
Environment=DATABASE_URL=sqlite:///$DATA_DIR/tiny_panel.db
Environment=SECRET_KEY=$(openssl rand -hex 32)
Environment=LOG_TO_STDOUT=true
ExecStart=$INSTALL_DIR/venv/bin/gunicorn -w 4 -b 0.0.0.0:8888 app:create_app('prod')
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
echo -e "\n${BLUE}启动Tiny Panel服务...${NC}"
systemctl daemon-reload
systemctl enable tiny-panel
systemctl start tiny-panel

# 检查服务状态
echo -e "\n${BLUE}检查服务状态...${NC}"
sleep 3
systemctl status tiny-panel --no-pager

# 获取服务器IP
IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}Tiny Panel安装成功！${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "${YELLOW}访问地址:${NC} http://$IP:8888"
echo -e "${YELLOW}默认账号:${NC} admin"
echo -e "${YELLOW}默认密码:${NC} admin123"
echo -e "${RED}注意: 请登录后立即修改默认密码！${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "\n${BLUE}使用以下命令管理服务:${NC}"
echo -e "  启动服务: systemctl start tiny-panel"
echo -e "  停止服务: systemctl stop tiny-panel"
echo -e "  重启服务: systemctl restart tiny-panel"
echo -e "  查看状态: systemctl status tiny-panel"
echo