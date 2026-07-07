// 获取 DOM 元素
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const thresholdSlider = document.getElementById('threshold');
const thresholdValue = document.getElementById('thresholdValue');
const detectBtn = document.getElementById('detectBtn');
const clearBtn = document.getElementById('clearBtn');
const originalContainer = document.getElementById('originalContainer');
const resultContainer = document.getElementById('resultContainer');
const totalCountEl = document.getElementById('totalCount');
const overallRiskEl = document.getElementById('overallRisk');
const inferenceTimeEl = document.getElementById('inferenceTime');
const classCountsEl = document.getElementById('classCounts');
const historyList = document.getElementById('historyList');
const downloadLogBtn = document.getElementById('downloadLogBtn');

let currentFile = null;

// 更新滑块显示
thresholdSlider.addEventListener('input', () => {
    thresholdValue.textContent = thresholdSlider.value;
});

// 文件选择
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    currentFile = file;
    fileName.textContent = file.name;

    // 显示原始文件预览
    const reader = new FileReader();
    reader.onload = (ev) => {
        const fileType = file.type;
        let html = '';
        if (fileType.startsWith('image/')) {
            html = `<img src="${ev.target.result}" alt="原始图片">`;
        } else if (fileType.startsWith('video/')) {
            html = `<video controls autoplay muted><source src="${ev.target.result}" type="${fileType}"></video>`;
        } else {
            html = `<p class="placeholder">不支持的文件格式</p>`;
        }
        originalContainer.innerHTML = html;
        detectBtn.disabled = false;
    };
    reader.readAsDataURL(file);
});

// 开始检测（模拟，实际需调用后端API）
detectBtn.addEventListener('click', async () => {
    if (!currentFile) return;
    detectBtn.disabled = true;
    detectBtn.textContent = '检测中...';

    // 模拟检测过程（实际应使用 FormData 上传文件到 /detect）
    try {
        // 构造模拟结果（实际应从后端获取）
        const mockResult = {
            total_counts: { car: 3, person: 1, traffic_light: 1 },
            overall_risk: '中风险',
            inference_time: 256,
            class_counts: { car: 3, person: 1, traffic_light: 1 },
            result_image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==' // 占位
        };

        // 更新统计
        updateStats(mockResult);

        // 显示检测结果（模拟图片）
        resultContainer.innerHTML = `<img src="${mockResult.result_image}" alt="检测结果">`;

        // 添加历史
        addHistory(currentFile.name, mockResult.overall_risk);

        // 启用按钮
        detectBtn.disabled = false;
        detectBtn.textContent = '开始检测';

    } catch (error) {
        alert('检测失败，请检查网络或后端服务');
        console.error(error);
        detectBtn.disabled = false;
        detectBtn.textContent = '开始检测';
    }
});

// 清空结果
clearBtn.addEventListener('click', () => {
    resultContainer.innerHTML = `<p class="placeholder">检测后将在此显示</p>`;
    originalContainer.innerHTML = `<p class="placeholder">请上传图片或视频</p>`;
    fileInput.value = '';
    fileName.textContent = '未选择文件';
    currentFile = null;
    detectBtn.disabled = true;
    // 重置统计
    totalCountEl.textContent = '0';
    overallRiskEl.textContent = '—';
    overallRiskEl.className = 'risk-low';
    inferenceTimeEl.textContent = '— ms';
    classCountsEl.textContent = '—';
    // 历史不清除，保留
});

// 更新统计面板
function updateStats(data) {
    const total = Object.values(data.total_counts).reduce((a, b) => a + b, 0);
    totalCountEl.textContent = total;
    overallRiskEl.textContent = data.overall_risk;
    // 根据风险设置颜色
    overallRiskEl.className = data.overall_risk.includes('高') ? 'risk-high' :
                              data.overall_risk.includes('中') ? 'risk-medium' : 'risk-low';
    inferenceTimeEl.textContent = data.inference_time + ' ms';
    // 类别计数
    let countsHtml = '';
    for (const [cls, count] of Object.entries(data.class_counts)) {
        countsHtml += `<span style="margin-right:10px;">${cls}: ${count}</span>`;
    }
    classCountsEl.innerHTML = countsHtml || '—';
}

// 添加历史记录
function addHistory(filename, risk) {
    const now = new Date().toLocaleString();
    const li = document.createElement('li');
    li.textContent = `[${now}] ${filename} → ${risk}`;
    historyList.prepend(li);
    // 限制条目数量
    while (historyList.children.length > 10) {
        historyList.removeChild(historyList.lastChild);
    }
}

// 下载日志（模拟）
downloadLogBtn.addEventListener('click', () => {
    alert('实际项目中，此处会调用 /download_log 接口下载JSON日志文件。');
    // 实际可 window.open('/download_log') 或 fetch 下载
});