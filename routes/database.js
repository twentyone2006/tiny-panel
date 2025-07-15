const express = require('express');
const router = express.Router();
const { execAsync } = require('../utils/exec');
const db = require('../models/db');
const fs = require('fs').promises;
const path = require('path');
const fsExtra = require('fs-extra');

// 数据库备份目录
const DB_BACKUP_DIR = path.join(__dirname, '../backups/databases');
fsExtra.ensureDirSync(DB_BACKUP_DIR);

// 获取数据库列表
router.get('/list', async (req, res) => {
  try {
    // 对于MySQL
    const mysqlDatabases = await getMySQLDatabases();
    
    // 对于SQLite
    const sqliteDatabases = await getSQLiteDatabases();
    
    res.json({
      mysql: mysqlDatabases,
      sqlite: sqliteDatabases
    });
  } catch (err) {
    res.status(500).json({ message: '获取数据库列表失败', error: err.message });
  }
});

// 创建MySQL数据库
router.post('/mysql/create', async (req, res) => {
  try {
    const { dbName, username, password, host = 'localhost' } = req.body;
    
    if (!dbName || !username || !password) {
      return res.status(400).json({ message: '数据库名称、用户名和密码不能为空' });
    }

    // 创建数据库
    await execAsync(`mysql -h ${host} -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "CREATE DATABASE IF NOT EXISTS ${dbName};"`);
    
    // 创建用户并授权
    await execAsync(`mysql -h ${host} -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "CREATE USER IF NOT EXISTS '${username}'@'localhost' IDENTIFIED BY '${password}';"`);
    await execAsync(`mysql -h ${host} -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "GRANT ALL PRIVILEGES ON ${dbName}.* TO '${username}'@'localhost';"`);
    await execAsync(`mysql -h ${host} -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "FLUSH PRIVILEGES;"`);

    // 记录到面板数据库
    await db.run(
      'INSERT INTO databases (name, type, username, host, created_at) VALUES (?, ?, ?, ?, ?)',
      [dbName, 'mysql', username, host, new Date().toISOString()]
    );

    res.json({ message: 'MySQL数据库创建成功' });
  } catch (err) {
    res.status(500).json({ message: '创建MySQL数据库失败', error: err.message });
  }
});

// 删除MySQL数据库
router.delete('/mysql/:dbName', async (req, res) => {
  try {
    const { dbName } = req.params;
    const { dropUser = false } = req.query;
    
    if (!dbName) {
      return res.status(400).json({ message: '数据库名称不能为空' });
    }

    // 获取数据库信息
    const dbInfo = await db.get('SELECT * FROM databases WHERE name = ? AND type = ?', [dbName, 'mysql']);
    if (!dbInfo) {
      return res.status(404).json({ message: '数据库不存在' });
    }

    // 删除数据库
    await execAsync(`mysql -h ${dbInfo.host} -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "DROP DATABASE IF EXISTS ${dbName};"`);
    
    // 如果需要同时删除用户
    if (dropUser) {
      await execAsync(`mysql -h ${dbInfo.host} -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "DROP USER IF EXISTS '${dbInfo.username}'@'localhost';"`);
      await execAsync(`mysql -h ${dbInfo.host} -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "FLUSH PRIVILEGES;"`);
    }

    // 从面板数据库删除记录
    await db.run('DELETE FROM databases WHERE id = ?', [dbInfo.id]);

    res.json({ message: 'MySQL数据库删除成功' });
  } catch (err) {
    res.status(500).json({ message: '删除MySQL数据库失败', error: err.message });
  }
});

// 导出数据库
router.post('/export', async (req, res) => {
  try {
    const { dbName, dbType, host = 'localhost' } = req.body;
    
    if (!dbName || !dbType) {
      return res.status(400).json({ message: '数据库名称和类型不能为空' });
    }

    const timestamp = new Date().toISOString().replace(/:/g, '-');
    const backupFileName = `${dbType}_${dbName}_${timestamp}.sql`;
    const backupFilePath = path.join(DB_BACKUP_DIR, backupFileName);

    if (dbType === 'mysql') {
      // 导出MySQL数据库
      await execAsync(`mysqldump -h ${host} -u root -p'${process.env.DB_ROOT_PASSWORD}' ${dbName} > ${backupFilePath}`);
    } else if (dbType === 'sqlite') {
      // 导出SQLite数据库
      const dbPath = path.join(__dirname, `../data/${dbName}.db`);
      await execAsync(`sqlite3 ${dbPath} .dump > ${backupFilePath}`);
    } else {
      return res.status(400).json({ message: '不支持的数据库类型' });
    }

    // 记录备份信息
    const stats = await fs.stat(backupFilePath);
    await db.run(
      'INSERT INTO database_backups (db_name, db_type, file_name, file_path, size, created_at) VALUES (?, ?, ?, ?, ?, ?)',
      [dbName, dbType, backupFileName, backupFilePath, stats.size, new Date().toISOString()]
    );

    res.json({
      message: '数据库导出成功',
      backupFile: backupFileName,
      size: stats.size
    });
  } catch (err) {
    res.status(500).json({ message: '数据库导出失败', error: err.message });
  }
});

// 导入数据库
router.post('/import', async (req, res) => {
  try {
    const { dbName, dbType, backupFile, host = 'localhost' } = req.body;
    
    if (!dbName || !dbType || !backupFile) {
      return res.status(400).json({ message: '数据库名称、类型和备份文件不能为空' });
    }

    const backupFilePath = path.join(DB_BACKUP_DIR, backupFile);

    // 检查备份文件是否存在
    try {
      await fs.access(backupFilePath);
    } catch {
      return res.status(404).json({ message: '备份文件不存在' });
    }

    if (dbType === 'mysql') {
      // 导入MySQL数据库
      await execAsync(`mysql -h ${host} -u root -p'${process.env.DB_ROOT_PASSWORD}' ${dbName} < ${backupFilePath}`);
    } else if (dbType === 'sqlite') {
      // 导入SQLite数据库
      const dbPath = path.join(__dirname, `../data/${dbName}.db`);
      // 确保目录存在
      await fsExtra.ensureDir(path.dirname(dbPath));
      await execAsync(`sqlite3 ${dbPath} < ${backupFilePath}`);
    } else {
      return res.status(400).json({ message: '不支持的数据库类型' });
    }

    res.json({ message: '数据库导入成功' });
  } catch (err) {
    res.status(500).json({ message: '数据库导入失败', error: err.message });
  }
});

// 获取数据库备份列表
router.get('/backups', async (req, res) => {
  try {
    const { dbName, dbType } = req.query;
    let query = 'SELECT * FROM database_backups WHERE 1=1';
    const params = [];

    if (dbName) {
      query += ' AND db_name = ?';
      params.push(dbName);
    }

    if (dbType) {
      query += ' AND db_type = ?';
      params.push(dbType);
    }

    query += ' ORDER BY created_at DESC';
    const backups = await db.all(query, params);
    res.json(backups);
  } catch (err) {
    res.status(500).json({ message: '获取备份列表失败', error: err.message });
  }
});

// 删除数据库备份
router.delete('/backups/:id', async (req, res) => {
  try {
    const { id } = req.params;

    // 获取备份信息
    const backup = await db.get('SELECT * FROM database_backups WHERE id = ?', [id]);
    if (!backup) {
      return res.status(404).json({ message: '备份不存在' });
    }

    // 删除备份文件
    await fs.unlink(backup.file_path);

    // 从数据库删除记录
    await db.run('DELETE FROM database_backups WHERE id = ?', [id]);

    res.json({ message: '备份删除成功' });
  } catch (err) {
    res.status(500).json({ message: '删除备份失败', error: err.message });
  }
});

// 辅助函数：获取MySQL数据库列表
async function getMySQLDatabases() {
  try {
    // 获取所有数据库
    const result = await execAsync(`mysql -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "SHOW DATABASES;"`);
    const databases = result.split('\n')
      .slice(1) // 跳过表头
      .filter(db => db && !['information_schema', 'mysql', 'performance_schema', 'sys'].includes(db))
      .map(db => db.trim());

    // 获取每个数据库的大小和用户
    const dbDetails = await Promise.all(databases.map(async (dbName) => {
      // 获取数据库大小
      const sizeResult = await execAsync(`mysql -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "SELECT SUM(data_length + index_length) AS size FROM information_schema.TABLES WHERE TABLE_SCHEMA = '${dbName}';"`);
      const size = sizeResult.split('\n')[1]?.trim() || 0;

      // 获取数据库用户
      const usersResult = await execAsync(`mysql -u root -p'${process.env.DB_ROOT_PASSWORD}' -e "SELECT DISTINCT USER FROM mysql.db WHERE db = '${dbName}';"`);
      const users = usersResult.split('\n')
        .slice(1)
        .filter(user => user)
        .map(user => user.trim());

      return {
        name: dbName,
        size: parseInt(size) || 0,
        users: users.length > 0 ? users : ['root'],
        type: 'mysql',
        status: 'active'
      };
    }));

    return dbDetails;
  } catch (err) {
    console.error('获取MySQL数据库列表失败:', err);
    return [];
  }
}

// 辅助函数：获取SQLite数据库列表
async function getSQLiteDatabases() {
  try {
    const dataDir = path.join(__dirname, '../data');
    await fsExtra.ensureDir(dataDir);

    const files = await fs.readdir(dataDir);
    const dbFiles = files.filter(file => file.endsWith('.db'));

    const dbDetails = await Promise.all(dbFiles.map(async (file) => {
      const dbName = path.basename(file, '.db');
      const dbPath = path.join(dataDir, file);
      const stats = await fs.stat(dbPath);

      return {
        name: dbName,
        file: file,
        path: dbPath,
        size: stats.size,
        type: 'sqlite',
        status: 'active'
      };
    }));

    return dbDetails;
  } catch (err) {
    console.error('获取SQLite数据库列表失败:', err);
    return [];
  }
}

module.exports = router;