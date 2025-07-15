require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const path = require('path');
const authRoutes = require('./routes/auth');
const monitorRoutes = require('./routes/monitor');
const fileRoutes = require('./routes/file');
const backupRoutes = require('./routes/backup');
const cronRoutes = require('./routes/cron');
const serviceRoutes = require('./routes/service');
const siteRoutes = require('./routes/site');
const databaseRoutes = require('./routes/database');

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// API路由
app.use('/api/auth', authRoutes);
app.use('/api/monitor', monitorRoutes);
app.use('/api/files', fileRoutes);
app.use('/api/database/backup', backupRoutes);
app.use('/api/cron', cronRoutes);
app.use('/api/service', serviceRoutes);
app.use('/api/site', siteRoutes);
app.use('/api/database', databaseRoutes);

// 提供前端应用
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'spa.html'));
});

// 错误处理中间件
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    message: '服务器内部错误',
    error: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
});

module.exports = app;