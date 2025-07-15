const express = require('express');
const router = express.Router();
const cron = require('node-cron');
const db = require('../models/db');
const { exec } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

// 存储当前运行的定时任务
const runningJobs = new Map();

// 从数据库加载并启动定时任务
async function loadJobs() {
  try {
    const jobs = await db.all('SELECT * FROM cron_jobs WHERE enabled = 1');
    jobs.forEach(job => {
      startJob(job);
    });
  } catch (err) {
    console.error('加载定时任务失败:', err.message);
  }
}

// 启动定时任务
function startJob(job) {
  // 停止已存在的同名任务
  if (runningJobs.has(job.id)) {
    runningJobs.get(job.id).stop();
  }

  // 创建新任务
  const task = cron.schedule(job.schedule, () => {
    executeJob(job);
  });

  runningJobs.set(job.id, task);
  console.log(`定时任务已启动: ${job.name} (ID: ${job.id})`);
}

// 执行定时任务
async function executeJob(job) {
  try {
    // 执行命令
    exec(job.command, (error, stdout, stderr) => {
      // 记录任务执行日志
      const logDir = path.join(__dirname, '../logs/cron');
      fs.mkdir(logDir, { recursive: true }).then(() => {
        const logPath = path.join(logDir, `${job.id}-${Date.now()}.log`);
        const logContent = `[${new Date().toISOString()}] 任务执行结果:\n命令: ${job.command}\n输出: ${stdout}\n错误: ${stderr || '无'}`;
        fs.writeFile(logPath, logContent);
      });

      // 更新最后执行时间
      db.run('UPDATE cron_jobs SET last_run = ? WHERE id = ?', [new Date().toISOString(), job.id]);
    });
  } catch (err) {
    console.error(`任务执行失败: ${job.name}`, err.message);
  }
}

// 获取所有定时任务
router.get('/jobs', async (req, res) => {
  try {
    const jobs = await db.all('SELECT * FROM cron_jobs ORDER BY created_at DESC');
    // 添加运行状态
    const jobsWithStatus = jobs.map(job => ({
      ...job,
      running: runningJobs.has(job.id) && !runningJobs.get(job.id).stop()
    }));
    res.json(jobsWithStatus);
  } catch (err) {
    res.status(500).json({ message: '获取定时任务失败', error: err.message });
  }
});

// 创建定时任务
router.post('/jobs', async (req, res) => {
  try {
    const { name, command, schedule, enabled = 1 } = req.body;

    if (!name || !command || !schedule) {
      return res.status(400).json({ message: '任务名称、命令和调度表达式为必填项' });
    }

    // 验证cron表达式
    if (!cron.validate(schedule)) {
      return res.status(400).json({ message: '无效的cron表达式' });
    }

    // 插入数据库
    const result = await db.run(
      'INSERT INTO cron_jobs (name, command, schedule, enabled, created_at) VALUES (?, ?, ?, ?, ?)',
      [name, command, schedule, enabled, new Date().toISOString()]
    );

    // 创建任务对象
    const newJob = {
      id: result.lastID,
      name,
      command,
      schedule,
      enabled,
      created_at: new Date().toISOString()
    };

    // 如果启用则立即启动
    if (enabled) {
      startJob(newJob);
    }

    res.json({ message: '定时任务创建成功', job: newJob });
  } catch (err) {
    res.status(500).json({ message: '创建定时任务失败', error: err.message });
  }
});

// 更新定时任务
router.put('/jobs/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { name, command, schedule, enabled } = req.body;

    // 查询任务是否存在
    const job = await db.get('SELECT * FROM cron_jobs WHERE id = ?', [id]);
    if (!job) {
      return res.status(404).json({ message: '定时任务不存在' });
    }

    // 构建更新数据
    const updates = [];
    const params = [];

    if (name !== undefined) { updates.push('name = ?'); params.push(name); }
    if (command !== undefined) { updates.push('command = ?'); params.push(command); }
    if (schedule !== undefined) { updates.push('schedule = ?'); params.push(schedule); }
    if (enabled !== undefined) { updates.push('enabled = ?'); params.push(enabled); }

    if (updates.length === 0) {
      return res.status(400).json({ message: '没有需要更新的字段' });
    }

    // 验证cron表达式（如果更新了）
    if (schedule && !cron.validate(schedule)) {
      return res.status(400).json({ message: '无效的cron表达式' });
    }

    // 执行更新
    params.push(id);
    await db.run(`UPDATE cron_jobs SET ${updates.join(', ')} WHERE id = ?`, params);

    // 获取更新后的任务
    const updatedJob = await db.get('SELECT * FROM cron_jobs WHERE id = ?', [id]);

    // 更新任务调度
    if (enabled || schedule || command) {
      if (enabled) {
        startJob(updatedJob);
      } else if (runningJobs.has(id)) {
        runningJobs.get(id).stop();
        runningJobs.delete(id);
      }
    }

    res.json({ message: '定时任务更新成功', job: updatedJob });
  } catch (err) {
    res.status(500).json({ message: '更新定时任务失败', error: err.message });
  }
});

// 删除定时任务
router.delete('/jobs/:id', async (req, res) => {
  try {
    const { id } = req.params;

    // 停止并移除任务
    if (runningJobs.has(id)) {
      runningJobs.get(id).stop();
      runningJobs.delete(id);
    }

    // 从数据库删除
    const result = await db.run('DELETE FROM cron_jobs WHERE id = ?', [id]);

    if (result.changes === 0) {
      return res.status(404).json({ message: '定时任务不存在' });
    }

    res.json({ message: '定时任务删除成功' });
  } catch (err) {
    res.status(500).json({ message: '删除定时任务失败', error: err.message });
  }
});

// 立即执行任务
router.post('/jobs/:id/execute', async (req, res) => {
  try {
    const { id } = req.params;
    const job = await db.get('SELECT * FROM cron_jobs WHERE id = ?', [id]);

    if (!job) {
      return res.status(404).json({ message: '定时任务不存在' });
    }

    // 立即执行任务
    executeJob(job);

    res.json({ message: '任务已开始执行' });
  } catch (err) {
    res.status(500).json({ message: '执行任务失败', error: err.message });
  }
});

// 初始化加载任务
loadJobs();

module.exports = router;