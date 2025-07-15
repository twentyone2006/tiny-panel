const express = require('express');
const router = express.Router();
const multer = require('multer');
const fs = require('fs').promises;
const fsExtra = require('fs-extra');
const path = require('path');
const archiver = require('archiver');

// 配置文件上传存储
const uploadDir = path.join(__dirname, '../public/uploads');
fsExtra.ensureDirSync(uploadDir);

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9);
    const filename = `${file.fieldname}-${uniqueSuffix}-${file.originalname}`;
    cb(null, filename);
  }
});

const upload = multer({ storage: storage });

// 获取文件列表
router.get('/list', async (req, res) => {
  try {
    const { directory = '' } = req.query;
    const targetDir = path.join(uploadDir, directory);
    
    // 验证目录是否存在
    await fs.access(targetDir);
    
    // 读取目录内容
    const files = await fs.readdir(targetDir, { withFileTypes: true });
    
    const fileList = await Promise.all(files.map(async (file) => {
      const stats = await fs.stat(path.join(targetDir, file.name));
      return {
        name: file.name,
        isDirectory: file.isDirectory(),
        size: stats.size,
        modifiedAt: stats.mtime.toISOString(),
        path: directory ? path.join(directory, file.name) : file.name
      };
    }));
    
    res.json(fileList);
  } catch (err) {
    res.status(404).json({ message: '目录不存在或无法访问', error: err.message });
  }
});

// 上传文件
router.post('/upload', upload.array('files'), (req, res) => {
  try {
    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ message: '未选择文件' });
    }
    
    const uploadedFiles = req.files.map(file => ({
      name: file.originalname,
      filename: file.filename,
      path: file.path,
      size: file.size
    }));
    
    res.json({ message: '文件上传成功', files: uploadedFiles });
  } catch (err) {
    res.status(500).json({ message: '文件上传失败', error: err.message });
  }
});

// 下载文件
router.get('/download/:filename', async (req, res) => {
  try {
    const { filename } = req.params;
    const filePath = path.join(uploadDir, filename);
    
    // 验证文件是否存在
    await fs.access(filePath);
    
    res.download(filePath, (err) => {
      if (err) {
        res.status(404).json({ message: '文件不存在', error: err.message });
      }
    });
  } catch (err) {
    res.status(404).json({ message: '文件不存在', error: err.message });
  }
});

// 删除文件
router.delete('/delete/:filename', async (req, res) => {
  try {
    const { filename } = req.params;
    const filePath = path.join(uploadDir, filename);
    
    // 验证文件是否存在
    await fs.access(filePath);
    
    // 检查是否为目录
    const stats = await fs.stat(filePath);
    if (stats.isDirectory()) {
      await fsExtra.remove(filePath);
    } else {
      await fs.unlink(filePath);
    }
    
    res.json({ message: '文件删除成功' });
  } catch (err) {
    res.status(404).json({ message: '文件不存在或无法删除', error: err.message });
  }
});

// 压缩文件
router.post('/compress', async (req, res) => {
  try {
    const { files, archiveName } = req.body;
    if (!files || !archiveName) {
      return res.status(400).json({ message: '缺少文件列表或压缩包名称' });
    }
    
    const archivePath = path.join(uploadDir, `${archiveName}.zip`);
    const output = fs.createWriteStream(archivePath);
    const archive = archiver('zip', { zlib: { level: 9 } });
    
    output.on('close', () => {
      res.json({
        message: '文件压缩成功',
        archiveName: `${archiveName}.zip`,
        size: archive.pointer()
      });
    });
    
    archive.on('error', (err) => {
      throw err;
    });
    
    archive.pipe(output);
    
    // 添加文件到压缩包
    for (const file of files) {
      const filePath = path.join(uploadDir, file);
      const stats = await fs.stat(filePath);
      
      if (stats.isDirectory()) {
        archive.directory(filePath, file);
      } else {
        archive.file(filePath, { name: file });
      }
    }
    
    await archive.finalize();
  } catch (err) {
    res.status(500).json({ message: '文件压缩失败', error: err.message });
  }
});

module.exports = router;