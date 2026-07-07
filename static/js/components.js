const { createApp, ref, reactive, computed } = Vue

const AppHeader = {
    props: {
        isAdmin: Boolean
    },
    emits: ['toggleAdmin'],
    template: `
    <header class="header">
        <div class="header-inner">
            <div class="logo">
                <div class="logo-icon">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                </div>
                <div class="logo-text">
                    <h1>自动驾驶感知系统</h1>
                    <span class="logo-sub">YOLOv8 Object Detection & Risk Assessment</span>
                </div>
            </div>
            <div class="header-status">
                <span class="status-dot"></span>
                <span class="status-text">系统就绪</span>
            </div>
        </div>
    </header>
    `
}

const ControlPanel = {
    props: {
        hasFile: Boolean,
        isDetecting: Boolean,
        threshold: Number
    },
    emits: ['update:threshold', 'fileSelected', 'detect', 'clear'],
    setup(props, { emit }) {
        const fileName = ref('未选择文件')
        const isDragOver = ref(false)

        function handleFile(file) {
            fileName.value = file.name
            emit('fileSelected', file)
        }

        function onFileChange(e) {
            const file = e.target.files[0]
            if (file) handleFile(file)
        }

        function onDragOver(e) {
            e.preventDefault()
            isDragOver.value = true
        }

        function onDragLeave() {
            isDragOver.value = false
        }

        function onDrop(e) {
            e.preventDefault()
            isDragOver.value = false
            const file = e.dataTransfer.files[0]
            if (file) handleFile(file)
        }

        function onThresholdChange(e) {
            emit('update:threshold', parseFloat(e.target.value))
        }

        function onClear() {
            fileName.value = '未选择文件'
            const input = document.getElementById('fileInput')
            if (input) input.value = ''
            emit('clear')
        }

        return { fileName, isDragOver, onFileChange, onDragOver, onDragLeave, onDrop, onThresholdChange, onClear }
    },
    template: `
    <section class="controls-panel">
        <div class="controls-row">
            <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver }"
                @dragover="onDragOver"
                @dragleave="onDragLeave"
                @drop="onDrop"
                @click="$el.querySelector('input[type=file]').click()"
            >
                <div class="upload-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="17 8 12 3 7 8"/>
                        <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                </div>
                <div class="upload-info">
                    <span class="upload-title">拖放文件或点击上传</span>
                    <span class="upload-hint">支持 JPG / PNG / MP4 / AVI</span>
                </div>
                <input id="fileInput" type="file" accept=".jpg,.jpeg,.png,.mp4,.avi" @change="onFileChange" @click.stop>
                <span class="file-name">{{ fileName }}</span>
            </div>

            <div class="param-group">
                <label class="param-label">
                    置信度阈值
                    <span class="param-value">{{ threshold.toFixed(2) }}</span>
                </label>
                <input type="range" min="0.1" max="0.9" step="0.05" :value="threshold" class="slider" @input="onThresholdChange">
            </div>

            <div class="action-group">
                <button class="btn btn-primary" :disabled="!hasFile || isDetecting" @click="$emit('detect')">
                    <svg v-if="!isDetecting" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    <svg v-else class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                    </svg>
                    {{ isDetecting ? '检测中...' : '开始检测' }}
                </button>
                <button class="btn btn-ghost" @click="onClear">清空结果</button>
            </div>
        </div>
    </section>
    `
}

const DisplayArea = {
    props: {
        filePreviewUrl: String,
        fileType: String,
        resultImageUrl: String,
        isDetecting: Boolean,
        showBadge: Boolean
    },
    template: `
    <section class="display-area">
        <div class="panel">
            <div class="panel-header">
                <span class="panel-dot"></span>
                <h3>原始画面</h3>
            </div>
            <div class="panel-body">
                <template v-if="filePreviewUrl">
                    <img v-if="fileType.startsWith('image/')" :src="filePreviewUrl" alt="原始图片" class="animate-in" />
                    <video v-else-if="fileType.startsWith('video/')" controls autoplay muted class="animate-in">
                        <source :src="filePreviewUrl" :type="fileType" />
                    </video>
                </template>
                <div v-else class="placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" opacity="0.3">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21 15 16 10 5 21"/>
                    </svg>
                    <p>请上传图片或视频</p>
                </div>
            </div>
        </div>
        <div class="panel panel-highlight">
            <div class="panel-header">
                <span class="panel-dot dot-accent"></span>
                <h3>检测结果</h3>
                <span v-if="showBadge" class="panel-badge">NEW</span>
            </div>
            <div class="panel-body">
                <div v-if="isDetecting" class="placeholder">
                    <svg class="spin" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.5">
                        <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                    </svg>
                    <p>正在分析...</p>
                </div>
                <img v-else-if="resultImageUrl" :src="resultImageUrl" alt="检测结果" class="animate-in" />
                <div v-else class="placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" opacity="0.3">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                    <p>检测后将在此显示</p>
                </div>
            </div>
        </div>
    </section>
    `
}

const StatsGrid = {
    props: {
        totalCount: Number,
        overallRisk: String,
        riskClass: String,
        inferenceTime: String,
        classCounts: Object
    },
    emits: ['update:threshold'],
    template: `
    <section class="stats-grid">
        <div class="stat-card" :class="{ 'stat-card-admin': isAdmin }">
            <div class="stat-icon icon-threshold">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>
                    <line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>
                    <line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>
                    <line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>
                    <line x1="17" y1="16" x2="23" y2="16"/>
                </svg>
            </div>
            <div class="stat-content">
                <span class="stat-label">
                    置信度阈值
                    <span v-if="isAdmin" class="admin-badge">管理员</span>
                </span>
                <div v-if="isAdmin" class="threshold-control">
                    <input
                        type="range" min="0.1" max="0.9" step="0.05"
                        :value="threshold"
                        class="slider slider-inline"
                        @input="$emit('update:threshold', parseFloat($event.target.value))"
                    >
                    <span class="threshold-val">{{ threshold.toFixed(2) }}</span>
                </div>
                <span v-else class="stat-number">{{ threshold.toFixed(2) }}</span>
            </div>
        </div>
        inferenceTime: String,
        classCounts: Object
    },
    template: `
    <section class="stats-grid">
        <div class="stat-card">
            <div class="stat-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
            </div>
            <div class="stat-content">
                <span class="stat-label">检测目标数</span>
                <span class="stat-number">{{ totalCount }}</span>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon icon-risk">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
            </div>
            <div class="stat-content">
                <span class="stat-label">整体风险</span>
                <span class="stat-number" :class="riskClass">{{ overallRisk }}</span>
            </div>
        </div>
        <div class="stat-card">
            <div class="stat-icon icon-time">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
            </div>
            <div class="stat-content">
                <span class="stat-label">推理耗时</span>
                <span class="stat-number">{{ inferenceTime }}</span>
            </div>
        </div>
        <div class="stat-card stat-card-wide">
            <div class="stat-icon icon-class">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
                    <line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/>
                    <line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
                </svg>
            </div>
            <div class="stat-content">
                <span class="stat-label">各类别计数</span>
                <div class="class-tags" v-if="Object.keys(classCounts).length">
                    <span class="class-tag" v-for="(count, cls) in classCounts" :key="cls">
                        {{ cls }} <span class="class-tag-count">{{ count }}</span>
                    </span>
                </div>
                <span v-else class="stat-number">—</span>
            </div>
        </div>
    </section>
    `
}

const HistoryPanel = {
    props: {
        history: Array
    },
    emits: ['downloadLog'],
    setup(props, { emit }) {
        function riskClass(risk) {
            if (risk.includes('高')) return 'risk-high'
            if (risk.includes('中')) return 'risk-medium'
            return 'risk-low'
        }
        return { riskClass }
    },
    template: `
    <section class="history-panel">
        <div class="history-header">
            <h3>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
                检测历史
            </h3>
            <button class="btn btn-ghost btn-sm" @click="$emit('downloadLog')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                下载日志
            </button>
        </div>
        <ul v-if="history.length">
            <li v-for="(item, i) in history" :key="i" class="animate-in">
                <span class="history-time">{{ item.time }}</span>
                {{ item.filename }}
                <span class="history-arrow">→</span>
                <span :class="riskClass(item.risk)">{{ item.risk }}</span>
            </li>
        </ul>
        <ul v-else>
            <li class="history-empty">暂无记录</li>
        </ul>
    </section>
    `
}

window.AppComponents = { AppHeader, ControlPanel, DisplayArea, StatsGrid, HistoryPanel }