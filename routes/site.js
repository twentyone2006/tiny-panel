// 触发服务器重启以验证execAsync导入
const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const fsExtra = require('fs-extra');
const path = require('path');
const { execAsync } = require(path.join(__dirname, '../utils/exec'));
const db = require('../models/db');

// 网站根目录
const WEB_ROOT = process.env.WEB_ROOT || '/var/www';

// 确保网站根目录存在
fsExtra.ensureDirSync(WEB_ROOT);

// 获取网站列表
router.get('/list', async (req, res) => {
  try {
    // 从数据库获取网站配置
    const sites = await db.all('SELECT * FROM websites ORDER BY id DESC');
    
    // 获取每个网站的基本信息
    const siteList = await Promise.all(sites.map(async (site) => {
      const sitePath = path.join(WEB_ROOT, site.domain);
      let size = 0;
      let isExist = false;
      
      try {
        // 检查目录是否存在
        await fs.access(sitePath);
        isExist = true;
        
        // 计算目录大小
        const stats = await fsExtra.stat(sitePath);
        if (stats.isDirectory()) {
          const files = await fsExtra.readdir(sitePath, { withFileTypes: true, recursive: true });
          for (const file of files) {
            if (file.isFile()) {
              const fileStats = await fsExtra.stat(file.fullPath());
              size += fileStats.size;
            }
          }
        }
      } catch {}
      
      return {
        ...site,
        path: sitePath,
        size,
        isExist,
        status: isExist ? '正常' : '目录不存在'
      };
    }));
    
    res.json(siteList);
  } catch (err) {
    res.status(500).json({ message: '获取网站列表失败', error: err.message });
  }
});

// 创建网站
router.post('/create', async (req, res) => {
  try {
    const { domain, port = 80, phpVersion = 'none', ssl = false } = req.body;
    
    if (!domain) {
      return res.status(400).json({ message: '域名不能为空' });
    }

    // 检查域名是否已存在
    const existing = await db.get('SELECT * FROM websites WHERE domain = ?', [domain]);
    if (existing) {
      return res.status(400).json({ message: '该域名已存在' });
    }

    // 创建网站目录
    const sitePath = path.join(WEB_ROOT, domain);
    await fsExtra.ensureDir(sitePath);
    
    // 创建默认首页
    const indexPath = path.join(sitePath, 'index.html');
    await fs.writeFile(indexPath, `<!DOCTYPE html>\n<html>\n<head>\n    <title>${domain}</title>\n</head>\n<body>\n    <h1>Welcome to ${domain}</h1>\n</body>\n</html>`);

    // 保存到数据库
    const result = await db.run(
      'INSERT INTO websites (domain, port, php_version, ssl, path, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
      [domain, port, phpVersion, ssl ? 1 : 0, sitePath, new Date().toISOString(), 'active']
    );

    // 配置Nginx
    if (phpVersion === 'none') {
      await configureNginxStaticSite(domain, port, sitePath);
    } else {
      await configureNginxPhpSite(domain, port, sitePath, phpVersion);
    }

    res.json({
      message: '网站创建成功',
      site: {
        id: result.lastID,
        domain,
        port,
        phpVersion,
        ssl,
        path: sitePath,
        createdAt: new Date().toISOString(),
        status: 'active'
      }
    });
  } catch (err) {
    res.status(500).json({ message: '创建网站失败', error: err.message });
  }
});

// 删除网站
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    // 获取网站信息
    const site = await db.get('SELECT * FROM websites WHERE id = ?', [id]);
    if (!site) {
      return res.status(404).json({ message: '网站不存在' });
    }

    // 删除Nginx配置
    await removeNginxConfig(site.domain);

    // 删除网站目录（可选）
    if (req.query.deleteFiles === 'true') {
      await fsExtra.remove(site.path);
    }

    // 从数据库删除
    await db.run('DELETE FROM websites WHERE id = ?', [id]);

    res.json({ message: '网站删除成功' });
  } catch (err) {
    res.status(500).json({ message: '删除网站失败', error: err.message });
  }
});

// 配置SSL
router.post('/:id/ssl', async (req, res) => {
  try {
    const { id } = req.params;
    const { ssl = true, email, autoRenew = true } = req.body;
    
    // 获取网站信息
    const site = await db.get('SELECT * FROM websites WHERE id = ?', [id]);
    if (!site) {
      return res.status(404).json({ message: '网站不存在' });
    }

    if (ssl) {
      // 申请SSL证书
      await execAsync(`certbot --nginx -d ${site.domain} --email ${email} --agree-tos --non-interactive`);
      
      // 更新数据库
      await db.run(
        'UPDATE websites SET ssl = 1, ssl_email = ?, ssl_auto_renew = ?, ssl_expiry = DATE(\'now\', \'+90 days\') WHERE id = ?',
        [email, autoRenew ? 1 : 0, id]
      );

      res.json({ message: 'SSL证书配置成功' });
    } else {
      // 禁用SSL
      await execAsync(`certbot delete --cert-name ${site.domain} --non-interactive`);
      
      // 更新数据库
      await db.run('UPDATE websites SET ssl = 0 WHERE id = ?', [id]);

      res.json({ message: 'SSL证书已禁用' });
    }
  } catch (err) {
    res.status(500).json({ message: 'SSL配置失败', error: err.message });
  }
});

// Nginx配置相关函数
async function configureNginxStaticSite(domain, port, rootPath) {
  const config = `server {
    listen ${port};
    server_name ${domain};
    root ${rootPath};
    index index.html index.htm;

    location / {
      try_files $uri $uri/ =404;
    }
}`;

  const configPath = `/etc/nginx/sites-available/${domain}`;
  await fs.writeFile(configPath, config);
  await fs.symlink(configPath, `/etc/nginx/sites-enabled/${domain}`);
  await execAsync('nginx -t && systemctl reload nginx');
}

async function configureNginxPhpSite(domain, port, rootPath, phpVersion) {
  const phpSocket = phpVersion === '7.4' ? 'php7.4-fpm' : 
                   phpVersion === '8.0' ? 'php8.0-fpm' : 
                   phpVersion === '8.1' ? 'php8.1-fpm' : 'php-fpm';

  const config = `server {
    listen ${port};
    server_name ${domain};
    root ${rootPath};
    index index.php index.html index.htm;

    location / {
      try_files $uri $uri/ =404;
    }

    location ~ \.php$ {
      include snippets/fastcgi-php.conf;
      fastcgi_pass unix:/run/php/${phpSocket}.sock;
    }
}`;

  const configPath = `/etc/nginx/sites-available/${domain}`;
  await fs.writeFile(configPath, config);
  await fs.symlink(configPath, `/etc/nginx/sites-enabled/${domain}`);
  await execAsync('nginx -t && systemctl reload nginx');
}

async function removeNginxConfig(domain) {
  const enabledPath = `/etc/nginx/sites-enabled/${domain}`;
  const availablePath = `/etc/nginx/sites-available/${domain}`;

  // 移除符号链接
  if (await fsExtra.pathExists(enabledPath)) {
    await fs.unlink(enabledPath);
  }

  // 删除配置文件
  if (await fsExtra.pathExists(availablePath)) {
    await fs.unlink(availablePath);
  }

  await execAsync('nginx -t && systemctl reload nginx');
}

module.exports = router;