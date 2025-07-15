#!/bin/bash
#
# 轻巧面板安装脚本
# 功能: 自动化安装面板服务
# 作者: 合肥轻巧智联信息科技公司
# 版本: 1.2.0

# 错误代码定义
declare -r ERR_DEPENDENCY=10
declare -r ERR_INSTALL=11
declare -r ERR_SERVICE=12
declare -r ERR_CONFIG=13
declare -r ERR_LOG=14

# 初始化全局变量
declare PANEL_DIR
declare PANEL_PORT
declare LOG_FILE

# 变量类型检查函数
check_var_type() {
    local var_name=$1
    local var_value=$2
    local expected_type=$3

    case $expected_type in
        "int")
            if ! [[ "$var_value" =~ ^[0-9]+$ ]]; then
                log "错误: ${var_name}应为整数类型"
                return 1
            fi
            ;;
        "path")
            if [[ "$var_value" != /* ]]; then
                log "错误: ${var_name}应为绝对路径"
                return 1
            fi
            ;;
    esac
    return 0
}

# 加载配置文件
load_config() {
    # 默认配置
    PANEL_DIR="/opt/panel"
    PANEL_PORT=3000
    LOG_FILE="$(pwd)/install_$(date +%Y%m%d).log"

    # 确保变量不为空
    PANEL_DIR=${PANEL_DIR:-/opt/panel}
    PANEL_PORT=${PANEL_PORT:-5000}
    LOG_FILE=${LOG_FILE:-install_$(date +%Y%m%d).log}

    # 变量类型检查
    check_var_type "PANEL_PORT" "$PANEL_PORT" "int" || exit $ERR_CONFIG
    check_var_type "PANEL_DIR" "$PANEL_DIR" "path" || exit $ERR_CONFIG
}

# 服务启动函数
start_service() {
    local retries=3
    while ((retries-- > 0)); do
        if gunicorn -b 0.0.0.0:${PANEL_PORT} server_manager:app; then
            return 0
        fi
        sleep 5
    done
    log "服务启动失败"
    return $ERR_SERVICE
}

# 端口检查函数
check_port() {
    local port=$1
    local attempts=3
    
    while ((attempts-- > 0)); do
        if (ss -tuln | grep -q ":${port}") || \
           (netstat -tuln 2>/dev/null | grep -q ":${port}"); then
            return 0
        fi
        sleep 2
    done
    return 1
}



# 模块化函数定义
function init_logging() {
    # 日志初始化
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始安装" > "$LOG_FILE"
    log "日志系统初始化完成"
    
    # 添加安全相关日志记录
    log "安全配置: 启用CSRF保护"
    log "安全配置: 文件上传限制为10MB"
}

# 日志记录函数(同时输出到控制台和文件)
log() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_entry="${timestamp} - ${message}"
    
    # 输出到控制台(带颜色)
    if [[ "${message}" == *"失败"* || "${message}" == *"错误"* ]]; then
        echo -e "\033[31m${log_entry}\033[0m"  # 红色显示错误
    elif [[ "${message}" == *"成功"* || "${message}" == *"完成"* ]]; then
        echo -e "\033[32m${log_entry}\033[0m"  # 绿色显示成功
    else
        echo -e "\033[33m${log_entry}\033[0m"  # 黄色显示普通信息
    fi
    
    # 同时写入日志文件(不带颜色)
    # 确保日志文件目录存在
    # 确保日志文件路径是绝对路径
    if [[ "$LOG_FILE" != /* ]]; then
        LOG_FILE="$(pwd)/$LOG_FILE"
    fi
    
    LOG_DIR="$(dirname "$LOG_FILE")"
    mkdir -p "$LOG_DIR" || {
        echo "无法创建日志目录: $LOG_DIR" >&2
        exit $ERR_LOG
    }
    
    # 尝试写入日志文件
    if ! echo "${log_entry}" >> "$LOG_FILE" 2>/dev/null; then
        # 如果写入失败，尝试使用sudo
        if ! sudo sh -c "echo '${log_entry}' >> '$LOG_FILE'" 2>/dev/null; then
            echo "严重错误: 无法写入日志文件: $LOG_FILE" >&2
            exit $ERR_LOG
        fi
    fi
}



# 安装前检查函数
pre_install_check() {
    # 检查root权限
    if [ "$(id -u)" != "0" ]; then
        echo "错误: 必须使用root用户运行此脚本"
        exit 1
    fi
    
    # 检查系统类型
    if [ ! -f /etc/os-release ]; then
        echo "错误: 不支持的操作系统"
        exit 1
    fi
    
    # 检查磁盘空间(至少需要500MB)
    local free_space=$(df -k / | tail -1 | awk '{print $4}')
    if [ $free_space -lt 512000 ]; then
        echo "错误: 磁盘空间不足，至少需要500MB可用空间"
        exit 1
    fi
    
    echo "[✓] 系统环境检查通过"
}

# 安装后验证函数
post_install_verify() {
    # 检查服务是否运行
    if ! systemctl is-active --quiet panel.service; then
        log "错误: 面板服务未运行"
        return 1
    fi

    # 检查端口是否监听
    if ! check_port ${PANEL_PORT}; then
        log "错误: ${PANEL_PORT}端口未监听"
        return 1
    fi

    log "服务验证通过"
    return 0
}





# 交互式配置函数
interactive_config() {
    # 显示欢迎信息
    echo "=== 轻巧面板安装向导 ==="
    echo "1. 标准安装(使用默认配置)"
    echo "2. 自定义安装"
    read -p "请选择安装模式[1/2]: " install_mode

    if [ "$install_mode" = "2" ]; then
        # 自定义安装选项
        read -p "输入安装目录[默认:/opt/panel]: " custom_dir
        PANEL_DIR=${custom_dir:-/opt/panel}

        while true; do
            read -p "输入服务端口[默认:3000]: " custom_port
            if [[ "$custom_port" =~ ^[0-9]+$ ]] && [ "$custom_port" -gt 1024 ] && [ "$custom_port" -lt 65535 ]; then
                PANEL_PORT=${custom_port:-3000}
                break
            else
                echo "错误: 端口必须是1025-65534之间的数字"
            fi
        done

        read -p "是否启用HTTPS? [y/N]: " enable_https
        if [[ "$enable_https" =~ ^[Yy]$ ]]; then
            SSL_CERT="$(readlink -f "$(read -p "SSL证书路径: " ssl_cert)")"
            SSL_KEY="$(readlink -f "$(read -p "SSL私钥路径: " ssl_key)")"
        fi
    fi

    # 确认配置
    echo "安装配置摘要:"
    echo "- 安装目录: $PANEL_DIR"
    echo "- 服务端口: $PANEL_PORT"
    [ -n "$SSL_CERT" ] && echo "- HTTPS: 启用" || echo "- HTTPS: 禁用"
    read -p "确认开始安装? [Y/n]: " confirm
    [[ "$confirm" =~ ^[Nn]$ ]] && exit 0
}

# 检查是否已安装
check_installed() {
    if [ -f "/etc/systemd/system/panel.service" ] || [ -d "$PANEL_DIR" ]; then
        echo "检测到面板已安装"
        read -p "是否要卸载现有面板并重新安装? [y/N] " uninstall_choice
        if [[ "$uninstall_choice" =~ [yY] ]]; then
            # 停止服务
            systemctl stop panel.service 2>/dev/null
            # 删除服务文件
            rm -f /etc/systemd/system/panel.service
            # 删除安装目录
            rm -rf "$PANEL_DIR"
            echo "旧版面板已卸载"
        else
            echo "安装已取消"
            exit 0
        fi
    fi
}

# 执行安装前检查
pre_install_check

# 检查是否已安装
check_installed

# 交互式配置
interactive_config

# 定义国内镜像源列表
declare -A MIRRORS=( 
    ["aliyun"]="http://mirrors.aliyun.com/ubuntu/" 
    ["tsinghua"]="https://mirrors.tuna.tsinghua.edu.cn/ubuntu/" 
    ["ustc"]="https://mirrors.ustc.edu.cn/ubuntu/" 
    ["163"]="http://mirrors.163.com/ubuntu/" 
    ["default"]="http://archive.ubuntu.com/ubuntu/" 
)

# 测试镜像源速度
test_mirror_speed() {
    local mirror_url=\$1
    local start_time=$(date +%s%N)
    if curl -s --connect-timeout 2 --max-time 5 "\${mirror_url}dists/\$(lsb_release -cs)/Release" > /dev/null; then
        local end_time=$(date +%s%N)
        echo $(( (end_time - start_time) / 1000000 ))
    else
        echo 9999
    fi
}

# 选择最优镜像源
select_best_mirror() {
    log "正在测试镜像源速度..."
    local best_mirror="default"
    local min_time=9999
    local codename=\$(lsb_release -cs)
    local current_mirror=\$(grep -oP 'http://[^/]+' /etc/apt/sources.list | head -1)

    # 备份原始源
    if [ ! -f /etc/apt/sources.list.bak ]; then
        cp /etc/apt/sources.list /etc/apt/sources.list.bak
    fi

    # 测试所有镜像源
    for mirror in "\${!MIRRORS[@]}"; do
        log "测试\${mirror}源..."
        time=\$(test_mirror_speed \${MIRRORS[\$mirror]})
        log "\${mirror}源响应时间: \${time}ms"
        if [ \$time -lt \$min_time ]; then
            min_time=\$time
            best_mirror=\$mirror
        fi
    done

    # 更新为最优源
    if [ \${best_mirror} != "default" ] && [ \${MIRRORS[\$best_mirror]} != \${current_mirror} ]; then
        log "选择最优镜像源: \${best_mirror}"
        sed -i "s|http://[^/]*|${MIRRORS[\$best_mirror]}|g" /etc/apt/sources.list
    fi
}

# 配置npm镜像源
configure_package_mirrors() {
    # 配置npm镜像
    npm config set registry https://registry.npm.taobao.org > /dev/null 2>&1
    log "已配置npm国内镜像源"
}

# 安装依赖
select_best_mirror
configure_package_mirrors

log "正在更新软件包列表..."
apt-get update -y > /dev/null 2>&1 || { log "更新软件包列表失败"; exit 1; }

log "正在安装依赖包..."
# 并行安装以加快速度
apt-get install -y -qq nginx curl build-essential > /dev/null 2>&1

# 安装Node.js和npm
log "正在安装Node.js和npm..."
curl -sL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y -qq nodejs > /dev/null 2>&1
# 验证Node.js和npm安装
node -v > /dev/null 2>&1 || { log "Node.js安装失败"; exit $ERR_DEPENDENCY; }
npm -v > /dev/null 2>&1 || { log "npm安装失败"; exit $ERR_DEPENDENCY; }

log "正在安装Node.js依赖..."
cd "${PANEL_DIR}" && npm install -q > /dev/null 2>&1
if [ ! -d "${PANEL_DIR}/node_modules" ]; then
    log "错误: npm依赖安装失败"
    exit $ERR_DEPENDENCY
fi

log "依赖安装完成"

# 配置Nginx反向代理
log "配置Nginx反向代理..."
cat > /etc/nginx/sites-available/panel <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:${PANEL_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# 禁用默认站点
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi

# 启用站点配置
ln -s /etc/nginx/sites-available/panel /etc/nginx/sites-enabled/
# 测试Nginx配置
nginx -t > /dev/null 2>&1 || { log "Nginx配置错误"; exit $ERR_CONFIG; }
systemctl restart nginx
log "Nginx反向代理配置完成"

# 配置系统服务
cat > /etc/systemd/system/panel.service <<EOF
[Unit]
Description=Server Management Panel
After=network.target

[Service]
User=root
WorkingDirectory=/opt/panel
Environment="NODE_ENV=production"
ExecStart=/usr/bin/npm start
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 创建安装目录
if [ -z "${PANEL_DIR}" ]; then
    PANEL_DIR="/opt/panel"
    log "警告: 使用默认安装目录 ${PANEL_DIR}"
fi

mkdir -p "${PANEL_DIR}" || {
    log "错误: 无法创建安装目录 ${PANEL_DIR}"
    exit $ERR_INSTALL
}

if ! cp -r . "${PANEL_DIR}" --exclude=node_modules; then
    log "错误: 无法复制文件到安装目录 ${PANEL_DIR}"
    exit $ERR_INSTALL
fi
log "安装目录已创建: ${PANEL_DIR}"

# 设置登录凭证
while true; do
    read -p "请设置管理员用户名(至少4字符): " username
    [ "${#username}" -ge 4 ] && break
    echo "错误: 用户名太短"
done

while true; do
    read -s -p "请设置管理员密码(至少8字符): " password
    echo
    [ "${#password}" -ge 8 ] && break
    echo "错误: 密码太短"
done

# 更新.env文件
if [ -f "/opt/panel/.env" ]; then
    # 添加或更新管理员凭证
    sed -i "s/^ADMIN_USER=.*/ADMIN_USER=${username}/" /opt/panel/.env
    sed -i "s/^ADMIN_PASS=.*/ADMIN_PASS=${password}/" /opt/panel/.env
else
    # 创建.env文件
    cat > /opt/panel/.env <<EOF
PORT=${PANEL_PORT}
NODE_ENV=production
JWT_SECRET=$(openssl rand -hex 32)
ADMIN_USER=${username}
ADMIN_PASS=${password}
EOF
fi

# 初始化数据库
log "初始化数据库..."
cd "${PANEL_DIR}" && node -e "
const db = require('./models/db.js');
(async () => {
  try {
    await db.initialize();
    console.log('数据库初始化成功');
  } catch (err) {
    console.error('数据库初始化失败:', err);
    process.exit(1);
  }
})();
" > db_init.log 2>&1

if [ $? -ne 0 ]; then
    log "错误: 数据库初始化失败，请查看日志: ${PANEL_DIR}/db_init.log"
    exit $ERR_INSTALL
fi
log "数据库初始化成功"

# 检查端口是否被占用
if ss -tuln | grep -q ":${PANEL_PORT}"; then
    log "错误: 端口 ${PANEL_PORT} 已被占用"
    exit $ERR_SERVICE
fi

# 启动服务
systemctl daemon-reload
systemctl enable panel.service
if ! systemctl start panel.service; then
    log "服务启动失败，详细信息:"
    journalctl -u panel.service --no-pager -n 10 >> "$LOG_FILE"
    journalctl -u panel.service --no-pager -n 10
    exit 1
fi

# 输出安装信息
log "安装完成！"

# 执行安装后验证
echo "正在验证服务状态..."
if post_install_verify; then
    log "验证完成，安装成功！"
else
    echo "验证失败，请检查日志文件: $(pwd)/$(basename "$LOG_FILE")"
    exit 1
fi
echo "========================================"
echo "！！！合肥轻巧智联信息科技公司 - 轻巧面板安装完成！！！"
echo "========================================"
# 获取可用IP地址
IP=\$(hostname -I | awk '{print $1}' || curl -s ifconfig.me)
echo "面板访问地址: http://\${IP}:${PANEL_PORT}"
echo "用户名: ${username}"
echo "密码: ${password}"
echo "========================================"