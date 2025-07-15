const express = require('express');
const router = express.Router();
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

// 获取服务状态
router.get('/status/:service', async (req, res) => {
  try {
    const { service } = req.params;
    // 不同Linux发行版使用不同的服务管理命令
    let command;
    
    // 检查系统使用的服务管理器
    try {
      await execAsync('systemctl --version');
      command = `systemctl is-active ${service}`;
    } catch {
      try {
        await execAsync('service --version');
        command = `service ${service} status`;
      } catch {
        return res.status(500).json({ message: '不支持的服务管理系统' });
      }
    }

    const { stdout, stderr } = await execAsync(command);
    let status = 'unknown';
    
    if (command.includes('systemctl')) {
      status = stdout.trim() === 'active' ? 'running' : 'stopped';
    } else if (command.includes('service')) {
      status = stderr.includes('running') ? 'running' : 'stopped';
    }

    res.json({ service, status });
  } catch (err) {
    res.status(500).json({ message: '获取服务状态失败', error: err.message });
  }
});

// 启动服务
router.post('/start/:service', async (req, res) => {
  try {
    const { service } = req.params;
    let command;

    try {
      await execAsync('systemctl --version');
      command = `sudo systemctl start ${service}`;
    } catch {
      try {
        await execAsync('service --version');
        command = `sudo service ${service} start`;
      } catch {
        return res.status(500).json({ message: '不支持的服务管理系统' });
      }
    }

    await execAsync(command);
    res.json({ message: `服务 ${service} 已启动` });
  } catch (err) {
    res.status(500).json({ message: '启动服务失败', error: err.message });
  }
});

// 停止服务
router.post('/stop/:service', async (req, res) => {
  try {
    const { service } = req.params;
    let command;

    try {
      await execAsync('systemctl --version');
      command = `sudo systemctl stop ${service}`;
    } catch {
      try {
        await execAsync('service --version');
        command = `sudo service ${service} stop`;
      } catch {
        return res.status(500).json({ message: '不支持的服务管理系统' });
      }
    }

    await execAsync(command);
    res.json({ message: `服务 ${service} 已停止` });
  } catch (err) {
    res.status(500).json({ message: '停止服务失败', error: err.message });
  }
});

// 重启服务
router.post('/restart/:service', async (req, res) => {
  try {
    const { service } = req.params;
    let command;

    try {
      await execAsync('systemctl --version');
      command = `sudo systemctl restart ${service}`;
    } catch {
      try {
        await execAsync('service --version');
        command = `sudo service ${service} restart`;
      } catch {
        return res.status(500).json({ message: '不支持的服务管理系统' });
      }
    }

    await execAsync(command);
    res.json({ message: `服务 ${service} 已重启` });
  } catch (err) {
    res.status(500).json({ message: '重启服务失败', error: err.message });
  }
});

// 获取服务列表
router.get('/list', async (req, res) => {
  try {
    let command;

    try {
      await execAsync('systemctl --version');
      command = 'systemctl list-units --type=service --full --no-legend';
    } catch {
      try {
        await execAsync('service --version');
        command = 'ls /etc/init.d/';
      } catch {
        return res.status(500).json({ message: '不支持的服务管理系统' });
      }
    }

    const { stdout } = await execAsync(command);
    const services = [];

    if (command.includes('systemctl')) {
      stdout.split('\n').forEach(line => {
        if (line.trim()) {
          const parts = line.trim().split(/\s+/);
          services.push({
            name: parts[0],
            status: parts[2]
          });
        }
      });
    } else {
      stdout.split('\n').forEach(service => {
        if (service.trim() && !service.startsWith('.')) {
          services.push({
            name: service.trim(),
            status: 'unknown'
          });
        }
      });
    }

    res.json(services);
  } catch (err) {
    res.status(500).json({ message: '获取服务列表失败', error: err.message });
  }
});

module.exports = router;