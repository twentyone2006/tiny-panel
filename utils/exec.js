const { exec } = require('child_process');
const { promisify } = require('util');

// 将exec转换为返回Promise的异步函数
const execAsync = promisify(exec);

module.exports = {
    execAsync
};