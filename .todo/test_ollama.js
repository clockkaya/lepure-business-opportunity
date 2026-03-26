const http = require('http');

// 配置信息
const config = {
    host: '192.168.10.43',
    port: 11434,
    path: '/api/generate',
    model: 'deepseek-r1:32b',
    prompt: '你好，请做一个简单的自我介绍。'
};

console.log(`正在连接 Ollama 服务: http://${config.host}:${config.port}...`);
console.log(`请求模型: ${config.model}`);
console.log(`发送问题: ${config.prompt}\n`);

const postData = JSON.stringify({
    model: config.model,
    prompt: config.prompt,
    stream: false
});

const options = {
    hostname: config.host,
    port: config.port,
    path: config.path,
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
    }
};

const req = http.request(options, (res) => {
    let responseData = '';

    res.on('data', (chunk) => {
        responseData += chunk;
    });

    res.on('end', () => {
        try {
            const json = JSON.parse(responseData);
            console.log('--- AI 响应内容 ---');
            console.log(json.response);
            console.log('------------------');
            console.log(`\n状态: 成功 | 耗时: ${(json.total_duration / 1e9).toFixed(2)}s`);
        } catch (e) {
            console.error('解析响应失败:', e.message);
            console.log('原始响应:', responseData);
        }
    });
});

req.on('error', (e) => {
    console.error(`请求出错: ${e.message}`);
    console.log('\n故障排查建议：');
    console.log(`1. 检查网络：ping ${config.host}`);
    console.log('2. 确认服务：确保 Ollama 在目标服务器上运行并监听 11434 端口');
});

req.write(postData);
req.end();
