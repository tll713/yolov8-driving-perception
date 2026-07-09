(() => {
const { ref, watch, nextTick, onBeforeUnmount } = Vue

const RISK_STYLE_MAP = {
    high: { label: '高风险', cls: 'risk-high' },
    medium: { label: '中风险', cls: 'risk-medium' },
    info: { label: '交通提示', cls: 'risk-info' },
    low: { label: '低风险', cls: 'risk-low' },
}

const AppHeader = {
    props: {
        healthStatus: Object,
        modelInfo: Object,
        currentUser: String
    },
    computed: {
        statusText() {
            return this.healthStatus?.status === 'ok' ? '系统就绪' : '连接中...'
        }
    },
    methods: {
        handleLogout() {
            localStorage.removeItem('currentUser')
            window.location.href = '/login'
        }
    },
    template: `
    <header class="header">
        <div class="header-inner">
            <div class="logo">
                <div class="logo-icon">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                </div>
                <div class="logo-text">
                    <h1>自动驾驶场景风险感知系统</h1>
                    <span class="logo-sub" v-if="modelInfo">{{ modelInfo.name }} · {{ modelInfo.inference_mode }} · {{ modelInfo.device }}</span>
                    <span class="logo-sub" v-else>YOLOv8 Detection & Driving Risk Assessment</span>
                </div>
            </div>
            <div class="header-right">
                <div class="header-status">
                    <span class="status-dot"></span>
                    <span class="status-text">{{ statusText }}</span>
                </div>
                <div class="header-auth" v-if="currentUser">
                    <span class="user-badge">{{ currentUser }}</span>
                    <button class="btn btn-ghost btn-sm" @click="handleLogout">退出</button>
                </div>
                <div class="header-auth" v-else>
                    <a href="/login" class="btn btn-ghost btn-sm">登录</a>
                    <a href="/register" class="btn btn-primary btn-sm">注册</a>
                    <a href="/admin/login" class="btn btn-ghost btn-sm">管理</a>
                </div>
            </div>
        </div>
    </header>
    `
}

const ControlPanel = {
    props: {
        hasFile: Boolean,
        isDetecting: Boolean
    },
    emits: ['fileSelected', 'detect', 'clear'],
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
        function onDragOver(e) { e.preventDefault(); isDragOver.value = true }
        function onDragLeave() { isDragOver.value = false }
        function onDrop(e) {
            e.preventDefault(); isDragOver.value = false
            const file = e.dataTransfer.files[0]
            if (file) handleFile(file)
        }
        function onClear() {
            fileName.value = '未选择文件'
            const input = document.getElementById('fileInput')
            if (input) input.value = ''
            emit('clear')
        }

        return { fileName, isDragOver, onFileChange, onDragOver, onDragLeave, onDrop, onClear }
    },
    template: `
    <section class="controls-panel">
        <div class="controls-row">
            <div class="upload-zone" :class="{ 'drag-over': isDragOver }"
                @dragover="onDragOver" @dragleave="onDragLeave" @drop="onDrop"
                @click="$el.querySelector('input[type=file]').click()">
                <div class="upload-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                </div>
                <div class="upload-info">
                    <span class="upload-title">拖放文件或点击上传</span>
                    <span class="upload-hint">支持 JPG / PNG / MP4 / AVI</span>
                </div>
                <input id="fileInput" type="file" accept=".jpg,.jpeg,.png,.bmp,.webp,.mp4,.avi,.mov,.mkv" @change="onFileChange" @click.stop>
                <span class="file-name">{{ fileName }}</span>
            </div>
            <div class="action-group">
                <button class="btn btn-primary" :disabled="!hasFile || isDetecting" @click="$emit('detect')">
                    {{ isDetecting ? '分析中...' : '开始检测' }}
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
        detections: Array,
        detectionTimeline: Array,
        isDetecting: Boolean,
        showBadge: Boolean,
        resultVideoUrl: String,
        resultImageUrl: String,
        maxRiskLevel: String
    },
    setup(props) {
        const videoRef = ref(null)
        const videoOverlayRef = ref(null)
        const videoOverlayFrameId = ref(null)

        const riskBorderClass = Vue.computed(() => {
            const level = props.maxRiskLevel || ''
            if (level === 'high') return 'risk-border-high'
            if (level === 'medium') return 'risk-border-medium'
            if (level === 'info') return 'risk-border-info'
            if (level === 'low') return 'risk-border-low'
            return ''
        })

        watch(() => [props.detectionTimeline, props.resultVideoUrl, props.filePreviewUrl], () => {
            if (props.fileType && props.fileType.startsWith('video/')) {
                nextTick(() => drawVideoOverlay())
            }
        }, { deep: true })

        onBeforeUnmount(() => stopVideoOverlayLoop())

        function drawVideoOverlay() {
            const video = videoRef.value
            const canvas = videoOverlayRef.value
            if (!video || !canvas) return
            const rect = video.getBoundingClientRect()
            if (!rect.width || !rect.height) return

            canvas.width = Math.round(rect.width)
            canvas.height = Math.round(rect.height)
            const ctx = canvas.getContext('2d')
            ctx.clearRect(0, 0, canvas.width, canvas.height)

            const timeline = props.detectionTimeline || []
            if (!timeline.length) return
            const current = video.currentTime || 0
            let frame = timeline[0]
            for (const item of timeline) {
                if (item.timestamp_sec <= current + 0.35) frame = item
                else break
            }

            const sourceWidth = frame.image_width || video.videoWidth || canvas.width
            const sourceHeight = frame.image_height || video.videoHeight || canvas.height
            const scale = Math.min(canvas.width / sourceWidth, canvas.height / sourceHeight)
            const drawWidth = sourceWidth * scale
            const drawHeight = sourceHeight * scale
            const offsetX = (canvas.width - drawWidth) / 2
            const offsetY = (canvas.height - drawHeight) / 2

            ;(frame.detections || []).forEach(d => {
                const [x1, y1, x2, y2] = d.bbox
                const risk = d.risk || {}
                const color = risk.level === 'high' ? '#ef4444' : risk.level === 'medium' ? '#f59e0b' : risk.level === 'info' ? '#3b82f6' : '#10b981'
                const left = offsetX + x1 * scale
                const top = offsetY + y1 * scale
                const width = (x2 - x1) * scale
                const height = (y2 - y1) * scale
                ctx.strokeStyle = color
                ctx.lineWidth = 2
                ctx.strokeRect(left, top, width, height)
                const label = `${d.class_name_cn || d.class_name} ${((d.confidence || 0) * 100).toFixed(0)}% ${risk.score || 0}`
                ctx.font = '13px JetBrains Mono, monospace'
                const labelWidth = ctx.measureText(label).width + 8
                ctx.fillStyle = color
                ctx.fillRect(left, Math.max(0, top - 21), labelWidth, 20)
                ctx.fillStyle = '#fff'
                ctx.fillText(label, left + 4, Math.max(13, top - 6))
            })
        }

        function drawVideoOverlayFrame() {
            drawVideoOverlay()
            const video = videoRef.value
            if (video && !video.paused && !video.ended) {
                videoOverlayFrameId.value = requestAnimationFrame(drawVideoOverlayFrame)
            }
        }

        function startVideoOverlayLoop() {
            stopVideoOverlayLoop()
            videoOverlayFrameId.value = requestAnimationFrame(drawVideoOverlayFrame)
        }

        function stopVideoOverlayLoop() {
            if (videoOverlayFrameId.value) {
                cancelAnimationFrame(videoOverlayFrameId.value)
                videoOverlayFrameId.value = null
            }
            drawVideoOverlay()
        }

        function downloadResult() {
            if (props.fileType && props.fileType.startsWith('video/') && props.resultVideoUrl) {
                const link = document.createElement('a')
                link.download = 'detection_result.mp4'
                link.href = props.resultVideoUrl
                link.click()
                return
            }
            if (props.resultImageUrl) {
                const link = document.createElement('a')
                link.download = 'detection_result.png'
                link.href = props.resultImageUrl
                link.click()
            }
        }

        return {
            videoRef,
            videoOverlayRef,
            drawVideoOverlay,
            startVideoOverlayLoop,
            stopVideoOverlayLoop,
            downloadResult,
            riskBorderClass
        }
    },
    template: `
    <section class="display-area">
        <div class="panel panel-highlight" :class="riskBorderClass">
            <div class="panel-header">
                <span class="panel-dot dot-accent"></span>
                <h3>检测结果</h3>
                <span v-if="isDetecting" class="panel-badge">检测中</span>
                <span v-else-if="showBadge" class="panel-badge">NEW</span>
                <button v-if="detections && detections.length" class="btn btn-ghost btn-sm" @click="downloadResult" style="margin-left:auto;">下载结果</button>
            </div>
            <div class="panel-body" :class="{ 'panel-body-auto': detections && detections.length }">
                <div v-if="isDetecting && !filePreviewUrl" class="placeholder"><p>正在分析场景风险...</p></div>
                <template v-else-if="detections && detections.length && fileType && fileType.startsWith('image/') && resultImageUrl">
                    <img :src="resultImageUrl" class="result-canvas animate-in" alt="检测结果" />
                </template>
                <div v-else-if="fileType && fileType.startsWith('video/') && (filePreviewUrl || resultVideoUrl)" class="video-result-wrap animate-in">
                    <div class="video-overlay-wrap">
                        <video
                            ref="videoRef"
                            :src="filePreviewUrl || resultVideoUrl"
                            controls
                            muted
                            class="result-video"
                            @loadedmetadata="drawVideoOverlay"
                            @loadeddata="drawVideoOverlay"
                            @play="startVideoOverlayLoop"
                            @pause="stopVideoOverlayLoop"
                            @ended="stopVideoOverlayLoop"
                            @seeked="drawVideoOverlay"
                        ></video>
                        <canvas ref="videoOverlayRef" class="video-overlay-canvas"></canvas>
                    </div>
                </div>
                <template v-else-if="filePreviewUrl">
                    <img v-if="fileType && fileType.startsWith('image/')" :src="filePreviewUrl" alt="检测预览" class="result-preview animate-in" />
                    <video v-else-if="fileType && fileType.startsWith('video/')" controls muted class="result-video animate-in">
                        <source :src="filePreviewUrl" :type="fileType" />
                    </video>
                </template>
                <div v-else class="placeholder"><p>选择文件后将在此实时显示</p></div>
            </div>
        </div>
    </section>
    `
}
const StatsGrid = {
    props: {
        confidence: Number,
        totalCount: Number,
        overallRisk: String,
        riskClass: String,
        inferenceTime: String,
        classCounts: Object,
        riskCounts: Object,
        maxRiskScore: Number,
        inferenceMode: String,
        inferenceSize: Number,
        refined: Boolean
    },
    template: `
    <section class="stats-grid">
        <div class="stat-card"><div class="stat-content"><span class="stat-label">置信度阈值</span><span class="stat-number">{{ confidence != null ? confidence.toFixed(2) : '-' }}</span></div></div>
        <div class="stat-card"><div class="stat-content"><span class="stat-label">检测目标数</span><span class="stat-number">{{ totalCount }}</span></div></div>
        <div class="stat-card"><div class="stat-content"><span class="stat-label">整体风险</span><span class="stat-number" :class="riskClass">{{ overallRisk }}</span></div></div>
        <div class="stat-card"><div class="stat-content"><span class="stat-label">推理耗时</span><span class="stat-number">{{ inferenceTime }}</span></div></div>
        <div class="stat-card"><div class="stat-content"><span class="stat-label">最高风险分</span><span class="stat-number">{{ maxRiskScore || 0 }}</span></div></div>
        <div class="stat-card"><div class="stat-content"><span class="stat-label">推理模式</span><span class="stat-number stat-text">{{ inferenceMode || '-' }}</span></div></div>
        <div class="stat-card"><div class="stat-content"><span class="stat-label">输入尺寸</span><span class="stat-number">{{ inferenceSize || '-' }}</span></div></div>
        <div class="stat-card"><div class="stat-content"><span class="stat-label">高精度补检</span><span class="stat-number stat-text">{{ refined ? '已触发' : '未触发' }}</span></div></div>
        <div class="stat-card stat-card-wide">
            <div class="stat-content">
                <span class="stat-label">风险统计</span>
                <div class="class-tags">
                    <span class="class-tag risk-high">高 {{ riskCounts?.high || 0 }}</span>
                    <span class="class-tag risk-medium">中 {{ riskCounts?.medium || 0 }}</span>
                    <span class="class-tag risk-low">低 {{ riskCounts?.low || 0 }}</span>
                    <span class="class-tag risk-info">提示 {{ riskCounts?.info || 0 }}</span>
                </div>
            </div>
        </div>
        <div class="stat-card stat-card-wide">
            <div class="stat-content">
                <span class="stat-label">各类别计数</span>
                <div class="class-tags" v-if="Object.keys(classCounts).length">
                    <span class="class-tag" v-for="(count, cls) in classCounts" :key="cls">{{ cls }} <span class="class-tag-count">{{ count }}</span></span>
                </div>
                <span v-else class="stat-number stat-text">暂无目标</span>
            </div>
        </div>
    </section>
    `
}

const RiskAnalysisPanel = {
    props: { detections: Array },
    data() {
        return { historyItems: [], expandedItems: {} }
    },
    async mounted() {
        await this.loadHistory()
    },
    watch: {
        detections: {
            handler() { this.loadHistory() },
            deep: true,
        },
    },
    methods: {
        riskClass(level) { return RISK_STYLE_MAP[level]?.cls || 'risk-low' },
        riskLabel(level) { return RISK_STYLE_MAP[level]?.label || level || '低风险' },
        async loadHistory() {
            try {
                const res = await fetch('/api/detections/history')
                const json = await res.json()
                if (json.code === 0 && json.data.items?.length) {
                    this.historyItems = json.data.items
                }
            } catch { this.historyItems = [] }
        },
        formatTime(iso) {
            if (!iso) return ''
            const d = new Date(iso)
            const pad = n => String(n).padStart(2, '0')
            return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
        },
        toggleItem(idx) {
            this.expandedItems[idx] = !this.expandedItems[idx]
        },
        isItemExpanded(idx) {
            return !!this.expandedItems[idx]
        },
    },
    template: `
    <section class="analysis-panel">
        <div class="section-header"><h3>目标风险明细</h3><span>{{ historyItems.length }} 条记录</span></div>
        <div v-if="historyItems.length">
            <div v-for="(item, idx) in historyItems" :key="idx" class="risk-time-group">
                <div class="risk-time-header" @click="toggleItem(idx)" style="cursor:pointer;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    {{ formatTime(item.created_at) }}
                    <span class="risk-time-count">{{ item.count || item.total_objects || 0 }} 个目标</span>
                    <span class="risk-time-badges">
                        <span v-if="(item.max_risk_level || 'low') === 'high'" class="risk-badge risk-high">高风险</span>
                        <span v-else-if="(item.max_risk_level || 'low') === 'medium'" class="risk-badge risk-medium">中风险</span>
                        <span v-else-if="(item.max_risk_level || 'low') === 'info'" class="risk-badge risk-info">交通提示</span>
                        <span v-else class="risk-badge risk-low">低风险</span>
                    </span>
                    <span class="risk-toggle-icon">{{ isItemExpanded(idx) ? '▾' : '▸' }}</span>
                </div>
                <div v-show="isItemExpanded(idx)" class="risk-time-body">
                    <div class="analysis-list">
                        <article class="analysis-item">
                            <div class="analysis-main">
                                <strong>{{ item.original_filename || item.filename || '-' }}</strong>
                                <span>{{ item.count || item.total_objects || 0 }} 个目标</span>
                                <span :class="riskClass(item.max_risk_level || 'low')">{{ riskLabel(item.max_risk_level || 'low') }}</span>
                            </div>
                            <div class="metric-row">
                                <span>置信度 {{ item.confidence != null ? item.confidence.toFixed(2) : '-' }}</span>
                                <span>耗时 {{ item.inference_time_ms || '-' }} ms</span>
                            </div>
                            <div v-if="item.detections?.length" class="risk-det-sub">
                                <div class="risk-det-item" v-for="(d, di) in item.detections" :key="di">
                                    <strong>{{ d.class_name_cn || d.class_name }}</strong>
                                    <span>{{ ((d.confidence || 0) * 100).toFixed(1) }}%</span>
                                    <span :class="riskClass(d.risk?.level || d.risk_level)">{{ riskLabel(d.risk?.level || d.risk_level) }}</span>
                                    <span class="risk-det-reason">{{ d.risk?.reason || d.risk_reason || '' }}</span>
                                </div>
                            </div>
                        </article>
                    </div>
                </div>
            </div>
        </div>
        <div v-else class="empty-block">完成检测后显示每个目标的风险依据。</div>
    </section>
    `
}

const SafetyAdvicePanel = {
    props: { advice: Array },
    methods: {
        riskClass(level) { return RISK_STYLE_MAP[level]?.cls || 'risk-low' },
    },
    template: `
    <section class="analysis-panel">
        <div class="section-header"><h3>驾驶安全建议</h3><span>decision support</span></div>
        <div v-if="advice && advice.length" class="advice-list">
            <div class="advice-item" v-for="(item, i) in advice" :key="i">
                <span :class="riskClass(item.level)">{{ item.level }}</span>
                <p>{{ item.message }}</p>
            </div>
        </div>
        <div v-else class="empty-block">完成检测后自动生成驾驶建议。</div>
    </section>
    `
}

const SceneInsightPanel = {
    props: {
        summary: Object,
        trace: Array,
    },
    methods: {
        riskClass(level) { return RISK_STYLE_MAP[level]?.cls || 'risk-low' },
        riskLabel(level) { return RISK_STYLE_MAP[level]?.label || level || '低风险' },
    },
    template: `
    <section class="insight-panel">
        <div class="section-header"><h3>场景理解与决策链</h3><span>explainable risk</span></div>
        <div v-if="summary" class="insight-layout">
            <div class="scene-summary">
                <div>
                    <span>场景类型</span>
                    <strong>{{ summary.scene_type }}</strong>
                </div>
                <div>
                    <span>目标密度</span>
                    <strong>{{ summary.density_level }}</strong>
                </div>
                <div>
                    <span>路径占用</span>
                    <strong>{{ summary.lane_target_count || 0 }}</strong>
                </div>
                <div>
                    <span>近距离目标</span>
                    <strong>{{ summary.close_target_count || 0 }}</strong>
                </div>
                <div v-if="summary.primary_target" class="scene-primary">
                    <span>主风险目标</span>
                    <strong>{{ summary.primary_target.class_name }} · {{ summary.primary_target.risk_score }}</strong>
                    <small :class="riskClass(summary.primary_target.risk_level)">{{ riskLabel(summary.primary_target.risk_level) }}</small>
                </div>
                <div class="class-tags scene-tags">
                    <span class="class-tag" v-for="tag in summary.tags" :key="tag">{{ tag }}</span>
                </div>
            </div>
            <div class="decision-trace">
                <article v-for="(item, i) in trace" :key="i">
                    <span>{{ i + 1 }}</span>
                    <div>
                        <strong>{{ item.step }}</strong>
                        <p>{{ item.result }}</p>
                        <small>{{ item.evidence }}</small>
                    </div>
                </article>
            </div>
        </div>
        <div v-else class="empty-block">完成检测后展示场景标签、主风险目标和逐步决策依据。</div>
    </section>
    `
}


const SimulationPanel = {
    props: {
        presets: Array,
        scenario: String,
        speed: Number,
        duration: Number,
        result: Object,
        isSimulating: Boolean,
    },
    emits: ['scenarioChange', 'speedChange', 'durationChange', 'run'],
    methods: {
        riskClass(level) { return RISK_STYLE_MAP[level]?.cls || 'risk-low' },
        currentFrame() {
            const timeline = this.result?.timeline || []
            if (!timeline.length) return null
            return timeline.reduce((best, item) => item.max_risk_score > best.max_risk_score ? item : best, timeline[0])
        },
        targetStyle(target) {
            const x = Math.max(8, Math.min(92, 50 + (target.lateral_m || 0) * 13))
            const y = Math.max(8, Math.min(92, 88 - (target.distance_m || 0) * 1.35))
            return { left: x + '%', top: y + '%' }
        },
    },
    computed: {
        frame() {
            return this.currentFrame()
        },
        peakRisk() {
            return this.result?.peak_risk || { level: 'low', score: 0, time_sec: 0 }
        },
    },
    template: `
    <section class="simulation-panel">
        <div class="section-header"><h3>风险仿真</h3><span>2D driving simulation</span></div>
        <div class="simulation-layout">
            <div class="simulation-controls">
                <label>
                    <span>场景预设</span>
                    <select :value="scenario" @change="$emit('scenarioChange', $event.target.value)">
                        <option v-for="item in presets" :key="item.key" :value="item.key">{{ item.name }}</option>
                    </select>
                </label>
                <label>
                    <span>自车速度 {{ speed }} km/h</span>
                    <input type="range" min="0" max="100" step="5" :value="speed" @input="$emit('speedChange', Number($event.target.value))">
                </label>
                <label>
                    <span>仿真时长 {{ duration }} s</span>
                    <input type="range" min="2" max="10" step="1" :value="duration" @input="$emit('durationChange', Number($event.target.value))">
                </label>
                <button class="btn btn-primary" :disabled="isSimulating" @click="$emit('run')">
                    {{ isSimulating ? '仿真中...' : '运行仿真' }}
                </button>
                <div v-if="result" class="simulation-summary">
                    <strong :class="riskClass(peakRisk.level)">最高风险 {{ peakRisk.score }}</strong>
                    <span>{{ peakRisk.time_sec }}s · {{ result.scenario_name }}</span>
                    <p v-for="line in result.summary" :key="line">{{ line }}</p>
                </div>
            </div>
            <div class="simulation-road">
                <div class="road-lane lane-left"></div>
                <div class="road-lane lane-right"></div>
                <div class="ego-car">自车</div>
                <template v-if="frame">
                    <div
                        v-for="target in frame.targets"
                        :key="target.id"
                        class="sim-target"
                        :class="'risk-bg-' + target.risk.level"
                        :style="targetStyle(target)"
                    >
                        <strong>{{ target.class_name_cn }}</strong>
                        <span>{{ target.risk.score }}</span>
                    </div>
                </template>
            </div>
        </div>
        <div v-if="result" class="sim-timeline">
            <div v-for="item in result.timeline" :key="item.frame_index" class="sim-tick">
                <span>{{ item.time_sec }}s</span>
                <strong :class="riskClass(item.max_risk_level)">{{ item.max_risk_score }}</strong>
            </div>
        </div>
    </section>
    `
}

const DashboardPanel = {
    props: { dashboard: Object },
    template: `
    <section class="system-panel">
        <div class="section-header"><h3>数据统计看板</h3><span>recent history</span></div>
        <div class="system-grid">
            <div><span>检测次数</span><strong>{{ dashboard?.total_records || 0 }}</strong></div>
            <div><span>累计目标</span><strong>{{ dashboard?.total_objects || 0 }}</strong></div>
            <div><span>高风险记录</span><strong>{{ dashboard?.high_risk_records || 0 }}</strong></div>
            <div><span>高风险占比</span><strong>{{ Math.round((dashboard?.high_risk_ratio || 0) * 100) }}%</strong></div>
            <div><span>平均耗时</span><strong>{{ dashboard?.average_inference_time_ms || 0 }} ms</strong></div>
            <div><span>常见目标</span><strong>{{ dashboard?.top_classes?.[0]?.class_name || '-' }}</strong></div>
        </div>
        <div class="class-tags dashboard-tags" v-if="dashboard?.top_classes?.length">
            <span class="class-tag" v-for="item in dashboard.top_classes" :key="item.class_name">
                {{ item.class_name }} <span class="class-tag-count">{{ item.count }}</span>
            </span>
        </div>
    </section>
    `
}

const ReportPanel = {
    props: {
        currentFile: Object,
        stats: Object,
        detections: Array,
        advice: Array,
        modelInfo: Object,
    },
    emits: ['exportReport'],
    template: `
    <section class="flow-panel">
        <div class="section-header"><h3>检测报告</h3><span>HTML / printable</span></div>
        <div class="report-row">
            <div>
                <strong>{{ currentFile?.name || '暂无检测文件' }}</strong>
                <p>报告包含模型信息、风险统计、目标明细、驾驶建议和算法流程，可直接打印或另存为 PDF。</p>
            </div>
            <button class="btn btn-primary" :disabled="!detections.length" @click="$emit('exportReport')">生成报告</button>
        </div>
    </section>
    `
}

const SystemInfoPanel = {
    props: { modelInfo: Object, healthStatus: Object },
    template: `
    <section class="system-panel">
        <div class="section-header"><h3>系统运行状态</h3><span>{{ healthStatus?.status === 'ok' ? 'online' : 'checking' }}</span></div>
        <div class="system-grid">
            <div><span>模型</span><strong>{{ modelInfo?.name || '-' }}</strong></div>
            <div><span>模型文件</span><strong>{{ modelInfo?.exists ? '已就绪' : '缺失' }}</strong></div>
            <div><span>推理模式</span><strong>{{ modelInfo?.inference_mode || '-' }}</strong></div>
            <div><span>输入尺寸</span><strong>{{ modelInfo?.image_size || '-' }} / {{ modelInfo?.refine_image_size || '-' }}</strong></div>
            <div><span>补检阈值</span><strong>{{ modelInfo?.refine_confidence || '-' }}</strong></div>
            <div><span>运行设备</span><strong>{{ modelInfo?.device || 'cpu' }}</strong></div>
        </div>
    </section>
    `
}


const HistoryPanel = {
    props: { history: Array },
    emits: ['downloadLog', 'clearHistory'],
    data() {
        return { allItems: [], viewItem: null }
    },
    async mounted() {
        await this.loadFullHistory()
    },
    methods: {
        riskClass(level) { return RISK_STYLE_MAP[level]?.cls || 'risk-low' },
        riskLabel(level) { return RISK_STYLE_MAP[level]?.label || level || '低风险' },
        async loadFullHistory() {
            try {
                const res = await fetch('/api/detections/history')
                const json = await res.json()
                if (json.code === 0 && json.data.items?.length) {
                    this.allItems = json.data.items
                }
            } catch { this.allItems = [] }
        },
        formatTime(iso) {
            if (!iso) return ''
            const d = new Date(iso)
            const pad = n => String(n).padStart(2, '0')
            return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
        },
        overallRisk(item) {
            return item.max_risk_level || 'low'
        },
        isImage(item) {
            return item.type === 'image' || (item.filename || '').match(/\.(jpg|jpeg|png|bmp|webp)$/i)
        },
        isVideo(item) {
            return item.type === 'video' || (item.filename || '').match(/\.(mp4|avi|mov|mkv)$/i)
        },
        mediaUrl(item) {
            if (this.isImage(item) && item.result_filename) return '/results/' + item.result_filename
            if (this.isVideo(item) && item.result_video) return item.result_video
            return ''
        },
        viewMedia(item) {
            if (this.mediaUrl(item)) this.viewItem = item
        },
        closeView() {
            this.viewItem = null
        },
        downloadMedia(item) {
            const url = this.mediaUrl(item)
            if (!url) return
            const link = document.createElement('a')
            link.download = this.isImage(item) ? 'detection_result.png' : 'detection_result.mp4'
            link.href = url
            link.click()
        },
    },
    template: `
    <section class="ph-wrap">
        <div class="ph-header">
            <h3>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                检测记录
                <span v-if="allItems.length" class="history-badge">{{ allItems.length }}</span>
            </h3>

        </div>
        <div v-if="allItems.length" class="ph-timeline">
            <div v-for="(item, i) in allItems" :key="i" class="ph-row">
                <div class="ph-left">
                    <div class="ph-dot" :class="riskClass(overallRisk(item))"></div>
                    <div v-if="i < allItems.length - 1" class="ph-line"></div>
                </div>
                <div class="ph-right">
                    <div class="ph-time">{{ formatTime(item.created_at) }}</div>
                    <div class="ph-card">
                        <div class="ph-thumb ph-thumb-clickable" v-if="isImage(item) && item.result_filename" @click="viewMedia(item)">
                            <img :src="'/results/' + item.result_filename" alt="">
                            <div class="ph-thumb-overlay">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                            </div>
                        </div>
                        <div class="ph-thumb ph-thumb-clickable ph-thumb-video" v-else-if="isVideo(item) && item.result_video" @click="viewMedia(item)">
                            <video :src="item.result_video" muted preload="metadata"></video>
                            <div class="ph-play-icon">▶</div>
                            <div class="ph-thumb-overlay">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                            </div>
                        </div>
                        <div class="ph-thumb ph-thumb-empty" v-else>
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                        </div>
                        <div class="ph-meta">
                            <span class="ph-filename">{{ item.original_filename || item.filename || '-' }}</span>
                            <span class="ph-counts">{{ item.count || item.total_objects || 0 }} 个目标</span>
                            <span :class="riskClass(overallRisk(item))">{{ riskLabel(overallRisk(item)) }}</span>
                            <div class="ph-actions" v-if="mediaUrl(item)">
                                <button class="btn btn-ghost btn-sm" @click="viewMedia(item)">查看</button>
                                <button class="btn btn-ghost btn-sm" @click="downloadMedia(item)">下载</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div v-else class="empty-block">暂无记录</div>

        <div v-if="viewItem" class="ph-modal" @click.self="closeView">
            <div class="ph-modal-content">
                <div class="ph-modal-header">
                    <span>{{ viewItem.original_filename || viewItem.filename || '检测结果' }}</span>
                    <div style="display:flex;gap:8px;">
                        <button class="btn btn-ghost btn-sm" @click="downloadMedia(viewItem)">下载</button>
                        <button class="btn btn-ghost btn-sm" @click="closeView">关闭</button>
                    </div>
                </div>
                <div class="ph-modal-body">
                    <img v-if="isImage(viewItem) && viewItem.result_filename" :src="'/results/' + viewItem.result_filename" class="ph-modal-media" alt="">
                    <video v-else-if="isVideo(viewItem) && viewItem.result_video" :src="viewItem.result_video" controls class="ph-modal-media"></video>
                </div>
            </div>
        </div>
    </section>
    `
}

window.AppComponents = {
    AppHeader,
    ControlPanel,
    DisplayArea,
    StatsGrid,
    RiskAnalysisPanel,
    SafetyAdvicePanel,
    SceneInsightPanel,

    SimulationPanel,
    DashboardPanel,
    ReportPanel,
    SystemInfoPanel,

    HistoryPanel,
}
window.RISK_STYLE_MAP = RISK_STYLE_MAP
})()
