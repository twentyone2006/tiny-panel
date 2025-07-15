const express = require('express');
const router = express.Router();
const si = require('systeminformation');
const db = require('../models/db');

// 获取当前系统状态
router.get('/current', async (req, res) => {
  try {
    // 获取系统信息
    const [cpu, memory, disk, network] = await Promise.all([
      si.currentLoad(),
      si.mem(),
      si.fsSize(),
      si.networkStats()
    ]);

    // 格式化磁盘信息（取第一个磁盘分区）
    const diskUsage = disk.length > 0 ? {
      total: disk[0].size,
      used: disk[0].used,
      free: disk[0].available,
      usage: disk[0].use
    } : {};

    // 格式化网络信息
    const networkUsage = network.reduce((acc, iface) => {
      acc[iface.iface] = {
        rx: iface.rx_sec,
        tx: iface.tx_sec
      };
      return acc;
    }, {});

    const stats = {
      cpu: { usage: cpu.currentLoad },
      memory: {
        total: memory.total,
        used: memory.used,
        free: memory.free,
        usage: memory.used / memory.total * 100
      },
      disk: diskUsage,
      network: networkUsage,
      timestamp: new Date().toISOString()
    };

    // 保存到数据库
    await db.run(
      'INSERT INTO system_stats (cpu_usage, memory_usage, disk_usage, network_io, recorded_at) VALUES (?, ?, ?, ?, ?)',
      [stats.cpu.usage, stats.memory.usage, stats.disk.usage, JSON.stringify(stats.network), stats.timestamp]
    );

    res.json(stats);
  } catch (err) {
    res.status(500).json({ message: '获取系统状态失败', error: err.message });
  }
});

// 获取历史系统状态
router.get('/history', async (req, res) => {
  try {
    const { limit = 100, offset = 0 } = req.query;
    const stats = await db.all(
      'SELECT * FROM system_stats ORDER BY recorded_at DESC LIMIT ? OFFSET ?',
      [parseInt(limit), parseInt(offset)]
    );
    res.json(stats);
  } catch (err) {
    res.status(500).json({ message: '获取历史状态失败', error: err.message });
  }
});

module.exports = router;