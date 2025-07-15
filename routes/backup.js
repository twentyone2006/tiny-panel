const express = require('express');
const router = express.Router();
const fs = require('fs').promises;
const fsExtra = require('fs-extra');
const path = require('path');
const { exec } = require('child_process');
const db = require('../models/db');

// 确保备份目录存在
const backupDir = process.env.BACKUP_DIR || path.join(__dirname, '../backups');
fsExtra.ensureDirSync(backupDir);

// 创建数据库备份
router.post('/create', async (req, res) => {
  try {
    const dbPath = process.env.DB_PATH || path.join(__dirname, '../data/server_manager.db');
    const timestamp = new Date().toISOString().replace(/:/g, '-');
    const backupFilename = `backup-${timestamp}.db`;
    const backupPath = path.join(backupDir, backupFilename);

    // 复制数据库文件创建备份
    await fs.copyFile(dbPath, backupPath);

    // 获取备份文件大小
    const stats = await fs.stat(backupPath);

    // 记录备份信息到数据库
    await db.run(
      'INSERT INTO backups (filename, path, size, created_at, status) VALUES (?, ?, ?, ?, ?)',
      [backupFilename, backupPath, stats.size, new Date().toISOString(), 'success']
    );

    res.json({
      message: '数据库备份成功',
      backup: {
        filename: backupFilename,
        path: backupPath,
        size: stats.size,
        createdAt: new Date().toISOString()
      }
    });
  } catch (err) {
    // 记录失败状态
    await db.run(
      'INSERT INTO backups (filename, path, size, created_at, status) VALUES (?, ?, ?, ?, ?)',
      [`failed-backup-${Date.now()}`, '', 0, new Date().toISOString(), 'failed']
    );
    res.status(500).json({ message: '数据库备份失败', error: err.message });
  }
});

// 获取备份列表
router.get('/list', async (req, res) => {
  try {
    const backups = await db.all('SELECT * FROM backups ORDER BY created_at DESC');
    res.json(backups);
  } catch (err) {
    res.status(500).json({ message: '获取备份列表失败', error: err.message });
  }
});

// 恢复数据库
router.post('/restore/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const backup = await db.get('SELECT * FROM backups WHERE id = ?', [id]);

    if (!backup) {
      return res.status(404).json({ message: '备份不存在' });
    }

    const dbPath = process.env.DB_PATH || path.join(__dirname, '../data/server_manager.db');
    const tempPath = `${dbPath}.bak`;

    // 先备份当前数据库
    await fs.copyFile(dbPath, tempPath);

    try {
      // 恢复选中的备份
      await fs.copyFile(backup.path, dbPath);
      res.json({ message: '数据库恢复成功' });
    } catch (restoreErr) {
      // 恢复失败，回滚到临时备份
      await fs.copyFile(tempPath, dbPath);
      res.status(500).json({ message: '数据库恢复失败', error: restoreErr.message });
    } finally {
      // 删除临时备份
      await fs.unlink(tempPath);
    }
  } catch (err) {
    res.status(500).json({ message: '恢复操作失败', error: err.message });
  }
});

// 删除备份
router.delete('/delete/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const backup = await db.get('SELECT * FROM backups WHERE id = ?', [id]);

    if (!backup) {
      return res.status(404).json({ message: '备份不存在' });
    }

    // 删除备份文件
    await fs.unlink(backup.path);

    // 从数据库中删除记录
    await db.run('DELETE FROM backups WHERE id = ?', [id]);

    res.json({ message: '备份删除成功' });
  } catch (err) {
    res.status(500).json({ message: '备份删除失败', error: err.message });
  }
});

module.exports = router;