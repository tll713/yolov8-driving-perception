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
                    <h1>自动驾驶场景感知系统</h1>
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
                    <a href="/profile" class="user-badge user-badge-link">{{ currentUser }}</a>
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
        laneAnalysis: Object,
        maxRiskLevel: String
    },
    setup(props) {
        const videoRef = ref(null)
        const videoOverlayRef = ref(null)
        const videoOverlayFrameId = ref(null)
        const currentLane = ref(null)
        const currentFrameDetections = ref([])

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
            if (!timeline.length) {
                currentLane.value = props.laneAnalysis || null
                currentFrameDetections.value = props.detections || []
                return
            }
            const current = video.currentTime || 0
            let frame = timeline[0]
            for (const item of timeline) {
                if (item.timestamp_sec <= current + 0.35) frame = item
                else break
            }
            currentLane.value = frame.lane_analysis || props.laneAnalysis || null
            currentFrameDetections.value = frame.detections || []

            const sourceWidth = frame.image_width || video.videoWidth || canvas.width
            const sourceHeight = frame.image_height || video.videoHeight || canvas.height
            const scale = Math.min(canvas.width / sourceWidth, canvas.height / sourceHeight)
            const drawWidth = sourceWidth * scale
            const drawHeight = sourceHeight * scale
            const offsetX = (canvas.width - drawWidth) / 2
            const offsetY = (canvas.height - drawHeight) / 2

            drawLaneOverlay(ctx, frame.lane_analysis || props.laneAnalysis, scale, offsetX, offsetY)

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

        function drawLaneOverlay(ctx, lane, scale, offsetX, offsetY) {
            if (!lane || lane.status !== 'detected') return
            ctx.save()
            ctx.strokeStyle = '#38bdf8'
            ctx.lineWidth = 4
            ctx.shadowColor = 'rgba(56, 189, 248, 0.55)'
            ctx.shadowBlur = 10
            ;(lane.lines || []).forEach(line => {
                ctx.beginPath()
                ctx.moveTo(offsetX + line.x1 * scale, offsetY + line.y1 * scale)
                ctx.lineTo(offsetX + line.x2 * scale, offsetY + line.y2 * scale)
                ctx.stroke()
            })
            ctx.restore()
        }

        function hasHighRisk() {
            const activeDetections = props.fileType && props.fileType.startsWith('video/')
                ? currentFrameDetections.value
                : props.detections
            return (activeDetections || []).some(d => {
                const level = d.risk?.level || d.risk_level
                const score = d.risk?.score || d.risk_score || 0
                return level === 'high' && score >= 88
            })
        }

        function displayLane() {
            return currentLane.value || props.laneAnalysis || null
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
            hasHighRisk,
            displayLane,
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
            <div class="panel-body" :class="{ 'panel-body-auto': detections && detections.length, 'risk-alert-body': hasHighRisk() }">
                <div v-if="hasHighRisk()" class="risk-particle-alert">
                    <span v-for="i in 28" :key="i"></span>
                </div>
                <div v-if="displayLane()" class="lane-floating-banner" :class="'lane-floating-' + (displayLane().advice_direction || displayLane().direction || 'unknown')">
                    <span>{{ displayLane().advice_label || displayLane().direction_label || '保持车道观察' }}</span>
                    <strong>{{ displayLane().confidence || 0 }}%</strong>
                    <small>{{ displayLane().lane_count || 0 }} 条车道线</small>
                </div>
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

const LaneInsightPanel = {
    props: { laneAnalysis: Object },
    computed: {
        lane() {
            return this.laneAnalysis || {}
        },
        directionClass() {
            const direction = this.lane.direction || 'unknown'
            if (direction === 'left') return 'lane-left-turn'
            if (direction === 'right') return 'lane-right-turn'
            if (direction === 'straight') return 'lane-straight'
            return 'lane-unknown'
        },
        confidenceText() {
            return this.lane.confidence != null ? `${this.lane.confidence}%` : '-'
        },
    },
    template: `
    <section class="lane-panel" :class="directionClass">
        <div class="section-header">
            <h3>道路与车道感知</h3>
            <span>lane perception</span>
        </div>
        <div v-if="laneAnalysis" class="lane-grid">
            <div class="lane-primary">
                <span>行驶趋势</span>
                <strong>{{ lane.advice_label || lane.direction_label || '保持车道观察' }}</strong>
                <p>{{ lane.advice_message || lane.message || '等待道路检测结果。' }}</p>
            </div>
            <div>
                <span>检测状态</span>
                <strong>{{ lane.status_label || '-' }}</strong>
            </div>
            <div>
                <span>车道置信度</span>
                <strong>{{ confidenceText }}</strong>
            </div>
            <div>
                <span>车道线数量</span>
                <strong>{{ lane.lane_count || 0 }}</strong>
            </div>
            <div>
                <span>中心偏移</span>
                <strong>{{ lane.center_offset_ratio != null ? lane.center_offset_ratio : '-' }}</strong>
            </div>
        </div>
        <div v-else class="empty-block">完成图片或视频检测后，将显示直线行驶、左转或右转等道路感知结果。</div>
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
        exportItemReport(item) {
            const dets = item.detections || []
            const riskRows = dets.map((d, i) => `
                <tr>
                    <td>${i + 1}</td>
                    <td>${d.class_name_cn || d.class_name || '-'}</td>
                    <td>${((d.confidence || 0) * 100).toFixed(1)}%</td>
                    <td>${d.risk?.level || d.risk_level || '-'}</td>
                    <td>${d.risk?.score || d.risk_score || 0}</td>
                    <td>${d.risk?.reason || d.risk_reason || '-'}</td>
                </tr>
            `).join('')
            const riskMap = { high: '高风险', medium: '中风险', info: '交通提示', low: '低风险' }
            const overallRisk = riskMap[item.max_risk_level] || '低风险'
            const html = `
                <!doctype html>
                <html lang="zh-CN">
                <head>
                    <meta charset="utf-8">
                    <title>检测报告 - ${item.original_filename || item.filename || ''}</title>
                    <style>
                        body { font-family: Arial, "Microsoft YaHei", sans-serif; padding: 32px; color: #111827; }
                        h1 { margin-bottom: 4px; }
                        .meta, li { line-height: 1.7; }
                        .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }
                        .card { border: 1px solid #d1d5db; padding: 14px; border-radius: 8px; }
                        .card span { display: block; color: #6b7280; font-size: 12px; }
                        .card strong { font-size: 22px; }
                        table { width: 100%; border-collapse: collapse; margin-top: 16px; }
                        th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; font-size: 13px; }
                        th { background: #f3f4f6; }
                    </style>
                </head>
                <body>
                    <h1>自动驾驶场景风险检测报告</h1>
                    <div class="meta">文件：${item.original_filename || item.filename || '-'}</div>
                    <div class="meta">检测时间：${this.formatTime(item.created_at)}</div>
                    <div class="cards">
                        <div class="card"><span>检测目标</span><strong>${item.count || item.total_objects || 0}</strong></div>
                        <div class="card"><span>整体风险</span><strong>${overallRisk}</strong></div>
                        <div class="card"><span>置信度</span><strong>${item.confidence != null ? item.confidence.toFixed(2) : '-'}</strong></div>
                        <div class="card"><span>推理耗时</span><strong>${item.inference_time_ms || '-'} ms</strong></div>
                    </div>
                    <h2>目标明细</h2>
                    <table>
                        <thead><tr><th>#</th><th>类别</th><th>置信度</th><th>风险等级</th><th>风险分</th><th>原因</th></tr></thead>
                        <tbody>${riskRows || '<tr><td colspan="6">暂无目标</td></tr>'}</tbody>
                    </table>
                </body>
                </html>
            `
            const w = window.open('', '_blank')
            w.document.write(html)
            w.document.close()
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
                    <span class="risk-toggle-icon">{{ isItemExpanded(idx) ? '?' : '?' }}</span>
                    <button class="btn btn-ghost btn-sm" style="margin-left:auto;" @click.stop="exportItemReport(item)">生成报告</button>
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
        customScenarios: Array,
        weatherOptions: Array,
        scenario: String,
        weather: String,
        speed: Number,
        duration: Number,
        result: Object,
        comparisonResult: Object,
        isSimulating: Boolean,
        isComparing: Boolean,
    },
    emits: [
        'scenarioChange', 'weatherChange', 'speedChange', 'durationChange',
        'run', 'compare', 'saveScenario', 'deleteScenario',
    ],
    data() {
        return {
            frameIndex: 0,
            isPlaying: false,
            playbackTimer: null,
            playbackRate: 1,
            assetStatus: 'loading',
            showScenarioEditor: false,
            scenarioEditorError: '',
            scenarioDraft: {
                id: '',
                name: '',
                description: '',
                weather: 'clear',
                ego_speed_kmh: 35,
                duration_sec: 5,
                targetsJson: '[\n  {\n    "id": "car-1",\n    "class_name": "car",\n    "distance_m": 30,\n    "lateral_m": 0,\n    "longitudinal_speed_mps": 8\n  }\n]',
                eventsJson: '[]',
            },
        }
    },
    watch: {
        result(value) {
            this.stopPlayback()
            this.frameIndex = 0
            if (value?.timeline?.length) {
                this.$nextTick(() => {
                    if (!this.threeRenderer) this.initThreeScene()
                    this.configureThreeEnvironment()
                    this.configureThreeScenario()
                    this.resetThreeTargets()
                    this.syncThreeFrame()
                    this.startPlayback()
                })
            }
        },
        frameIndex() { this.syncThreeFrame() },
    },
    beforeUnmount() {
        this.stopPlayback()
        this.disposeThreeScene()
    },
    methods: {
        riskClass(level) { return RISK_STYLE_MAP[level]?.cls || 'risk-low' },
        riskLabel(level) { return RISK_STYLE_MAP[level]?.label || '低风险' },
        formatTtc(value) { return value == null ? '--' : Number(value).toFixed(1) + 's' },
        targetClass(target) { return 'target-' + String(target.class_name || 'car').replaceAll(' ', '_') },
        setPlaybackRate(rate) {
            const wasPlaying = this.isPlaying
            this.stopPlayback()
            this.playbackRate = rate
            if (wasPlaying) this.startPlayback()
        },
        openScenarioEditor() {
            const existing = (this.customScenarios || []).find(item => item.key === this.scenario)
            this.scenarioDraft = existing ? {
                id: existing.id,
                name: existing.name,
                description: existing.description || '',
                weather: existing.weather || 'clear',
                ego_speed_kmh: Number(existing.ego_speed_kmh || 35),
                duration_sec: Number(existing.duration_sec || 5),
                targetsJson: JSON.stringify(existing.targets || [], null, 2),
                eventsJson: JSON.stringify(existing.events || [], null, 2),
            } : {
                id: '',
                name: '',
                description: '',
                weather: this.weather || 'clear',
                ego_speed_kmh: Number(this.speed || 35),
                duration_sec: Number(this.duration || 5),
                targetsJson: '[\n  {\n    "id": "car-1",\n    "class_name": "car",\n    "distance_m": 30,\n    "lateral_m": 0,\n    "longitudinal_speed_mps": 8\n  }\n]',
                eventsJson: '[]',
            }
            this.scenarioEditorError = ''
            this.showScenarioEditor = true
        },
        submitScenario() {
            try {
                const targets = JSON.parse(this.scenarioDraft.targetsJson)
                const events = JSON.parse(this.scenarioDraft.eventsJson)
                if (!Array.isArray(targets) || !Array.isArray(events)) throw new Error('目标和事件必须是 JSON 数组')
                this.$emit('saveScenario', {
                    id: this.scenarioDraft.id || undefined,
                    name: this.scenarioDraft.name,
                    description: this.scenarioDraft.description,
                    weather: this.scenarioDraft.weather,
                    ego_speed_kmh: Number(this.scenarioDraft.ego_speed_kmh),
                    duration_sec: Number(this.scenarioDraft.duration_sec),
                    step_sec: 0.25,
                    targets,
                    events,
                })
                this.scenarioEditorError = ''
                this.showScenarioEditor = false
            } catch (error) {
                this.scenarioEditorError = error.message || '场景 JSON 格式错误'
            }
        },
        deleteDraftScenario() {
            if (!this.scenarioDraft.id) return
            this.$emit('deleteScenario', this.scenarioDraft.id)
            this.showScenarioEditor = false
        },
        comparisonChartPoints(result) {
            const timeline = result?.timeline || []
            if (!timeline.length) return ''
            const last = Math.max(1, timeline.length - 1)
            return timeline.map((item, index) => {
                const x = 8 + index / last * 284
                const y = 92 - item.max_risk_score * 0.78
                return `${x.toFixed(1)},${y.toFixed(1)}`
            }).join(' ')
        },
        startPlayback() {
            if (!this.timeline.length || this.isPlaying) return
            if (this.frameIndex >= this.timeline.length - 1) this.frameIndex = 0
            this.isPlaying = true
            const interval = Math.max(80, (this.result.step_sec * 1000) / this.playbackRate)
            this.playbackTimer = setInterval(() => {
                if (this.frameIndex >= this.timeline.length - 1) return this.stopPlayback()
                this.frameIndex += 1
            }, interval)
        },
        stopPlayback() {
            if (this.playbackTimer) clearInterval(this.playbackTimer)
            this.playbackTimer = null
            this.isPlaying = false
        },
        togglePlayback() { this.isPlaying ? this.stopPlayback() : this.startPlayback() },
        restartPlayback() {
            this.stopPlayback()
            this.frameIndex = 0
            this.startPlayback()
        },
        seekPlayback(value) {
            this.stopPlayback()
            this.frameIndex = Number(value)
        },
        initThreeScene() {
            const THREE = window.THREE
            const canvas = this.$refs.simCanvas
            if (!THREE || !canvas || this.threeRenderer) return

            const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false })
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
            renderer.outputEncoding = THREE.sRGBEncoding
            renderer.toneMapping = THREE.ACESFilmicToneMapping
            renderer.toneMappingExposure = 1.05
            renderer.shadowMap.enabled = true
            renderer.shadowMap.type = THREE.PCFSoftShadowMap

            const scene = new THREE.Scene()
            const camera = new THREE.PerspectiveCamera(62, 1, 0.1, 220)
            camera.position.set(0, 3.0, 6.6)
            camera.lookAt(0, 1.08, -36)

            const hemiLight = new THREE.HemisphereLight(0xc7e2ef, 0x35402d, 2.25)
            const sunLight = new THREE.DirectionalLight(0xfff3d6, 3.2)
            sunLight.position.set(-18, 28, 12)
            sunLight.castShadow = true
            sunLight.shadow.mapSize.set(2048, 2048)
            sunLight.shadow.camera.left = -36
            sunLight.shadow.camera.right = 36
            sunLight.shadow.camera.top = 42
            sunLight.shadow.camera.bottom = -18
            scene.add(hemiLight, sunLight)

            const headlightTarget = new THREE.Object3D()
            headlightTarget.position.set(0, 0.2, -42)
            scene.add(headlightTarget)
            const headlights = [-1.1, 1.1].map(x => {
                const light = new THREE.SpotLight(0xd9f3ff, 0.5, 95, 0.3, 0.58, 1.2)
                light.position.set(x, 2.1, 5.4)
                light.target = headlightTarget
                scene.add(light)
                return light
            })

            const skyMaterial = new THREE.ShaderMaterial({
                side: THREE.BackSide,
                depthWrite: false,
                uniforms: {
                    topColor: { value: new THREE.Color(0x4f8cb2) },
                    bottomColor: { value: new THREE.Color(0xd3e2e6) },
                },
                vertexShader: 'varying vec3 vPosition; void main(){ vPosition = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
                fragmentShader: 'varying vec3 vPosition; uniform vec3 topColor; uniform vec3 bottomColor; void main(){ float h = clamp(normalize(vPosition).y * 0.75 + 0.35, 0.0, 1.0); gl_FragColor = vec4(mix(bottomColor, topColor, h), 1.0); }',
            })
            const sky = new THREE.Mesh(new THREE.SphereGeometry(190, 32, 18), skyMaterial)
            scene.add(sky)

            const asphaltData = new Uint8Array(64 * 64 * 3)
            for (let index = 0; index < asphaltData.length; index += 3) {
                const shade = 35 + Math.floor(Math.random() * 22)
                asphaltData[index] = shade
                asphaltData[index + 1] = shade + 3
                asphaltData[index + 2] = shade + 4
            }
            const asphaltTexture = new THREE.DataTexture(asphaltData, 64, 64, THREE.RGBFormat)
            asphaltTexture.wrapS = asphaltTexture.wrapT = THREE.RepeatWrapping
            asphaltTexture.repeat.set(3, 42)
            asphaltTexture.needsUpdate = true

            const ground = new THREE.Mesh(
                new THREE.PlaneGeometry(140, 220),
                new THREE.MeshStandardMaterial({ color: 0x38513d, roughness: 1 })
            )
            ground.rotation.x = -Math.PI / 2
            ground.position.z = -88
            scene.add(ground)

            const road = new THREE.Mesh(
                new THREE.PlaneGeometry(18, 190),
                new THREE.MeshStandardMaterial({ color: 0x5d6263, map: asphaltTexture, roughness: 0.94, metalness: 0.02 })
            )
            road.rotation.x = -Math.PI / 2
            road.position.set(0, 0.012, -84)
            road.receiveShadow = true
            scene.add(road)
            this.threeRoadMaterial = road.material

            const roadMarkMaterial = new THREE.MeshStandardMaterial({ color: 0xe7e4d2, roughness: 0.9, metalness: 0.0 })
            const wornMarkMaterial = new THREE.MeshStandardMaterial({ color: 0xcac7b6, roughness: 1, transparent: true, opacity: 0.72 })
            const patchMaterial = new THREE.MeshStandardMaterial({ color: 0x272b2e, roughness: 0.96 })
            const createRoadArrow = (x, z, rotation = 0) => {
                const shape = new THREE.Shape()
                shape.moveTo(0, 1.62)
                shape.lineTo(0.48, 0.62)
                shape.lineTo(0.2, 0.62)
                shape.lineTo(0.2, -1.38)
                shape.lineTo(-0.2, -1.38)
                shape.lineTo(-0.2, 0.62)
                shape.lineTo(-0.48, 0.62)
                shape.closePath()
                const arrow = new THREE.Mesh(new THREE.ShapeGeometry(shape), roadMarkMaterial)
                arrow.rotation.set(-Math.PI / 2, 0, rotation)
                arrow.position.set(x, 0.071, z)
                arrow.receiveShadow = true
                return arrow
            }
            const trafficProps = []
            for (const z of [-20, -64, -108, -152]) {
                for (const x of [-5.2, 0, 5.2]) {
                    const arrow = createRoadArrow(x, z, 0)
                    trafficProps.push(arrow)
                    scene.add(arrow)
                }
            }
            for (let index = 0; index < 11; index += 1) {
                const patch = new THREE.Mesh(
                    new THREE.BoxGeometry(1.2 + (index % 3) * 0.5, 0.025, 2.6 + (index % 2) * 1.2),
                    patchMaterial
                )
                patch.position.set((index % 2 ? -1 : 1) * (1.1 + index % 4), 0.062, -12 - index * 14)
                patch.rotation.y = (index % 3 - 1) * 0.08
                trafficProps.push(patch)
                scene.add(patch)
            }
            for (const item of [
                { x: -0.75, z: -34, angle: -0.06 },
                { x: 0.86, z: -35, angle: 0.04 },
                { x: -0.55, z: -92, angle: -0.05 },
                { x: 0.62, z: -93, angle: 0.03 },
            ]) {
                const skid = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.022, 8.4), wornMarkMaterial)
                skid.position.set(item.x, 0.073, item.z)
                skid.rotation.y = item.angle
                trafficProps.push(skid)
                scene.add(skid)
            }

            const shoulderMaterial = new THREE.MeshStandardMaterial({ color: 0x2f3739, roughness: 0.98 })
            for (const x of [-11.3, 11.3]) {
                const shoulder = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 190), shoulderMaterial)
                shoulder.rotation.x = -Math.PI / 2
                shoulder.position.set(x, 0.018, -84)
                shoulder.receiveShadow = true
                scene.add(shoulder)
            }

            const markerGeometry = new THREE.BoxGeometry(0.13, 0.025, 3.4)
            const markerMaterial = new THREE.MeshStandardMaterial({ color: 0xf2edcf, emissive: 0x312e21 })
            const laneMarkers = []
            for (const x of [-3, 3]) {
                for (let index = 0; index < 24; index += 1) {
                    const marker = new THREE.Mesh(markerGeometry, markerMaterial)
                    marker.position.set(x, 0.04, 8 - index * 7.5)
                    laneMarkers.push(marker)
                    scene.add(marker)
                }
            }
            const edgeGeometry = new THREE.BoxGeometry(0.18, 0.035, 190)
            const edgeMaterial = new THREE.MeshStandardMaterial({ color: 0xe9d88c })
            for (const x of [-8.2, 8.2]) {
                const edge = new THREE.Mesh(edgeGeometry, edgeMaterial)
                edge.position.set(x, 0.045, -84)
                scene.add(edge)
            }

            const roadsideDetails = []
            const rumbleGeometry = new THREE.BoxGeometry(0.55, 0.035, 0.16)
            const rumbleMaterial = new THREE.MeshStandardMaterial({ color: 0xd9d0a0, roughness: 0.82 })
            for (const x of [-8.9, 8.9]) {
                for (let index = 0; index < 54; index += 1) {
                    const strip = new THREE.Mesh(rumbleGeometry, rumbleMaterial)
                    strip.position.set(x, 0.068, 9 - index * 3.3)
                    roadsideDetails.push(strip)
                    scene.add(strip)
                }
            }

            const railMaterial = new THREE.MeshStandardMaterial({ color: 0xaeb5b8, roughness: 0.48, metalness: 0.35 })
            const postMaterial = new THREE.MeshStandardMaterial({ color: 0x4b555a, roughness: 0.7 })
            const reflectorMaterial = new THREE.MeshStandardMaterial({ color: 0xffe29a, emissive: 0xffb02e, emissiveIntensity: 0.9, roughness: 0.45 })
            const sceneryDetails = []
            for (const side of [-1, 1]) {
                for (let index = 0; index < 13; index += 1) {
                    const rail = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.18, 9.2), railMaterial)
                    rail.position.set(side * 11.0, 0.88, 4 - index * 14)
                    rail.castShadow = true
                    roadsideDetails.push(rail)
                    scene.add(rail)
                    const post = new THREE.Mesh(new THREE.BoxGeometry(0.16, 1.1, 0.16), postMaterial)
                    post.position.set(side * 11.0, 0.54, 0.2 - index * 14)
                    post.castShadow = true
                    sceneryDetails.push(post)
                    scene.add(post)
                    const reflector = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.16, 0.28), reflectorMaterial)
                    reflector.position.set(side * 10.9, 0.92, 0.2 - index * 14)
                    reflector.rotation.y = side < 0 ? Math.PI / 2 : -Math.PI / 2
                    sceneryDetails.push(reflector)
                    scene.add(reflector)
                }
            }

            const buildingMaterial = new THREE.MeshStandardMaterial({ color: 0x56636a, roughness: 0.88 })
            const darkBuildingMaterial = new THREE.MeshStandardMaterial({ color: 0x38444b, roughness: 0.9 })
            const windowMaterial = new THREE.MeshStandardMaterial({ color: 0x7fb0c7, emissive: 0x123040, emissiveIntensity: 0.35, roughness: 0.35 })
            for (let index = 0; index < 15; index += 1) {
                const height = 5 + index % 4 * 2.2
                for (const side of [-1, 1]) {
                    const building = new THREE.Mesh(
                        new THREE.BoxGeometry(5 + index % 3, height, 7),
                        index % 2 ? buildingMaterial : darkBuildingMaterial
                    )
                    building.position.set(side * (13 + index % 3 * 2.5), height / 2, -10 - index * 11)
                    building.castShadow = true
                    sceneryDetails.push(building)
                    scene.add(building)
                    for (let floor = 1; floor < height - 1; floor += 1.8) {
                        const windowBand = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.38, 4.2), windowMaterial)
                        windowBand.position.set(building.position.x - side * ((5 + index % 3) / 2 + 0.025), floor, building.position.z)
                        sceneryDetails.push(windowBand)
                        scene.add(windowBand)
                    }
                }
            }

            const trunkMaterial = new THREE.MeshStandardMaterial({ color: 0x60412b, roughness: 0.9 })
            const crownMaterial = new THREE.MeshStandardMaterial({ color: 0x2f6b45, roughness: 0.96 })
            for (let index = 0; index < 18; index += 1) {
                for (const side of [-1, 1]) {
                    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.18, 1.8, 8), trunkMaterial)
                    trunk.position.set(side * (15.5 + index % 2 * 2.5), 0.9, -8 - index * 9.4)
                    trunk.castShadow = true
                    const crown = new THREE.Mesh(new THREE.ConeGeometry(1.25 + index % 3 * 0.18, 3.2, 10), crownMaterial)
                    crown.position.set(trunk.position.x, 2.85, trunk.position.z)
                    crown.castShadow = true
                    sceneryDetails.push(trunk, crown)
                    scene.add(trunk, crown)
                }
            }

            const signMaterial = new THREE.MeshStandardMaterial({ color: 0x1f7f63, roughness: 0.55, metalness: 0.05 })
            const signTextMaterial = new THREE.MeshStandardMaterial({ color: 0xdfeee8, emissive: 0x18342c, emissiveIntensity: 0.5 })
            const signFaceMaterial = new THREE.MeshStandardMaterial({ color: 0xf3f4ec, roughness: 0.55 })
            const signRedMaterial = new THREE.MeshStandardMaterial({ color: 0xd73535, emissive: 0x5b0b0b, emissiveIntensity: 0.35 })
            const warningMaterial = new THREE.MeshStandardMaterial({ color: 0xf6c84f, emissive: 0x4b3408, emissiveIntensity: 0.22, roughness: 0.52 })
            for (let index = 0; index < 4; index += 1) {
                const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 4.6, 10), postMaterial)
                pole.position.set(-10.3, 2.3, -22 - index * 38)
                const sign = new THREE.Mesh(new THREE.BoxGeometry(2.9, 1.15, 0.08), signMaterial)
                sign.position.set(-10.3, 4.25, pole.position.z)
                const mark = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.08, 0.095), signTextMaterial)
                mark.position.set(-10.3, 4.28, pole.position.z + 0.055)
                sceneryDetails.push(pole, sign, mark)
                scene.add(pole, sign, mark)
            }
            for (let index = 0; index < 5; index += 1) {
                const z = -16 - index * 34
                const side = index % 2 ? -1 : 1
                const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.07, 2.6, 10), postMaterial)
                pole.position.set(side * 9.8, 1.3, z)
                const face = new THREE.Mesh(new THREE.CylinderGeometry(0.52, 0.52, 0.045, 32), signFaceMaterial)
                face.rotation.x = Math.PI / 2
                face.position.set(side * 9.8, 2.7, z)
                const ring = new THREE.Mesh(new THREE.TorusGeometry(0.53, 0.055, 8, 32), signRedMaterial)
                ring.rotation.x = Math.PI / 2
                ring.position.copy(face.position)
                const markA = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.07, 0.05), signRedMaterial)
                markA.position.set(side * 9.8, 2.7, z + 0.035)
                const markB = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.34, 0.05), signRedMaterial)
                markB.position.set(side * 9.8, 2.7, z + 0.04)
                sceneryDetails.push(pole, face, ring, markA, markB)
                scene.add(pole, face, ring, markA, markB)
            }
            for (let index = 0; index < 4; index += 1) {
                const board = new THREE.Mesh(new THREE.ConeGeometry(0.68, 0.08, 3), warningMaterial)
                board.rotation.set(Math.PI / 2, 0, Math.PI / 3)
                board.position.set(-9.6, 2.55, -35 - index * 42)
                const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.065, 2.25, 8), postMaterial)
                pole.position.set(-9.6, 1.15, board.position.z)
                sceneryDetails.push(board, pole)
                scene.add(board, pole)
            }
            const busStopMaterial = new THREE.MeshStandardMaterial({ color: 0x2f78a6, emissive: 0x0d2636, emissiveIntensity: 0.28, roughness: 0.42 })
            const shelterGlassMaterial = new THREE.MeshStandardMaterial({ color: 0x9fc6d4, transparent: true, opacity: 0.34, roughness: 0.18, metalness: 0.1 })
            for (const z of [-58, -138]) {
                const signPole = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.07, 2.8, 8), postMaterial)
                signPole.position.set(12.7, 1.4, z)
                const stopBoard = new THREE.Mesh(new THREE.BoxGeometry(0.95, 1.05, 0.08), busStopMaterial)
                stopBoard.position.set(12.7, 2.85, z)
                const shelter = new THREE.Mesh(new THREE.BoxGeometry(2.7, 1.55, 0.08), shelterGlassMaterial)
                shelter.position.set(14.4, 1.15, z - 1.4)
                const roof = new THREE.Mesh(new THREE.BoxGeometry(3.1, 0.12, 1.35), railMaterial)
                roof.position.set(14.4, 2.04, z - 1.4)
                sceneryDetails.push(signPole, stopBoard, shelter, roof)
                scene.add(signPole, stopBoard, shelter, roof)
            }

            const streetLights = []
            const poleMaterial = new THREE.MeshStandardMaterial({ color: 0x2e363b, roughness: 0.75 })
            const lampMaterial = new THREE.MeshStandardMaterial({ color: 0xfff0ba, emissive: 0xffd66b, emissiveIntensity: 1.4 })
            for (let index = 0; index < 12; index += 1) {
                for (const side of [-1, 1]) {
                    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 5.6, 10), poleMaterial)
                    pole.position.set(side * 9.4, 2.8, -10 - index * 14)
                    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.08, 0.08), poleMaterial)
                    arm.position.set(side * 8.9, 5.55, pole.position.z)
                    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 8), lampMaterial)
                    bulb.position.set(side * 8.35, 5.48, pole.position.z)
                    sceneryDetails.push(pole, arm, bulb)
                    scene.add(pole, arm, bulb)
                    if (index % 3 === 0) {
                        const light = new THREE.PointLight(0xffdb91, 0, 18, 1.8)
                        light.position.copy(bulb.position)
                        streetLights.push(light)
                        sceneryDetails.push(light)
                        scene.add(light)
                    }
                }
            }

            this.threeRenderer = renderer
            this.threeScene = scene
            this.threeCamera = camera
            this.threeHemiLight = hemiLight
            this.threeSunLight = sunLight
            this.threeHeadlights = headlights
            this.threeSkyMaterial = skyMaterial
            this.threeStreetLights = streetLights
            this.threeLaneMarkers = laneMarkers
            this.threeRoadsideDetails = roadsideDetails
            this.threeSceneryDetails = sceneryDetails
            this.threeTrafficProps = trafficProps
            this.threeTargets = new Map()
            this.threeAmbientCars = []
            this.threeMixers = []
            this.threeLastTime = performance.now()

            const resize = () => {
                const width = Math.max(1, canvas.clientWidth)
                const height = Math.max(1, canvas.clientHeight)
                renderer.setSize(width, height, false)
                camera.aspect = width / height
                camera.updateProjectionMatrix()
            }
            this.threeResizeObserver = new ResizeObserver(resize)
            this.threeResizeObserver.observe(canvas)
            resize()

            const animate = now => {
                const delta = Math.min(0.05, (now - this.threeLastTime) / 1000)
                this.threeLastTime = now
                if (this.isPlaying) {
                    const roadSpeed = (this.frame?.ego_speed_kmh || 0) / 3.6
                    this.threeLaneMarkers.forEach(marker => {
                        marker.position.z += roadSpeed * delta
                        if (marker.position.z > 10) marker.position.z -= 180
                    })
                    this.threeRoadsideDetails.forEach(detail => {
                        detail.position.z += roadSpeed * delta
                        if (detail.position.z > 12) detail.position.z -= 178
                    })
                    this.threeSceneryDetails.forEach(detail => {
                        detail.position.z += roadSpeed * delta
                        if (detail.position.z > 14) detail.position.z -= 178
                    })
                    this.threeTrafficProps.forEach(detail => {
                        detail.position.z += roadSpeed * delta
                        if (detail.position.z > 14) detail.position.z -= 178
                    })
                }
                this.threeTargets.forEach(target => {
                    let visualY = target.userData.targetY || 0
                    if (target.userData.isProceduralPerson) {
                        visualY += Math.abs(Math.sin(now * 0.006)) * 0.012
                    }
                    target.position.x += (target.userData.targetX - target.position.x) * 0.12
                    target.position.y += (visualY - target.position.y) * 0.12
                    target.position.z += (target.userData.targetZ - target.position.z) * 0.12
                    if (target.userData.isProceduralPerson) {
                        const phase = now * 0.006
                        target.children.forEach(child => {
                            if (!child.userData.walkPhase) return
                            const swing = Math.sin(phase + child.userData.walkPhase * Math.PI) * target.userData.walkAmplitude
                            child.rotation.x = swing
                        })
                    }
                })
                this.threeMixers.forEach(mixer => mixer.update(delta))
                if (this.isPlaying) {
                    const trafficSpeed = ((this.frame?.ego_speed_kmh || 0) / 3.6) * delta * 0.42
                    this.threeAmbientCars.forEach(car => {
                        car.position.z += trafficSpeed
                        if (car.position.z > 8) car.position.z -= 150
                    })
                }
                if (this.threeRain) {
                    const positions = this.threeRain.geometry.attributes.position
                    for (let index = 1; index < positions.count * 3; index += 3) {
                        positions.array[index] -= delta * 18
                        if (positions.array[index] < 0.2) positions.array[index] = 12
                        positions.array[index + 1] += delta * 9
                        if (positions.array[index + 1] > 8) positions.array[index + 1] -= 112
                    }
                    positions.needsUpdate = true
                }
                camera.position.x = Math.sin(now * 0.0017) * 0.035
                camera.position.y = 3.0 + Math.sin(now * 0.0024) * 0.018
                renderer.render(scene, camera)
                this.threeAnimationFrame = requestAnimationFrame(animate)
            }
            this.threeAnimationFrame = requestAnimationFrame(animate)
            this.loadThreeAssets()
        },
        loadThreeAssets() {
            const THREE = window.THREE
            if (!THREE?.GLTFLoader) {
                this.assetStatus = 'fallback'
                return
            }
            const loader = new THREE.GLTFLoader()
            const dracoLoader = new THREE.DRACOLoader()
            dracoLoader.setDecoderPath('/static/js/draco/')
            dracoLoader.setDecoderConfig({ type: 'js' })
            loader.setDRACOLoader(dracoLoader)
            this.threeDracoLoader = dracoLoader
            const load = url => new Promise((resolve, reject) => loader.load(url, resolve, undefined, reject))
            Promise.all([
                load('/static/models/simulation/ferrari.glb'),
                load('/static/models/simulation/soldier.glb'),
            ]).then(([carGltf, personGltf]) => {
                const car = this.normalizeThreeAsset(carGltf.scene, { length: 4.5, rotateToRoad: true })
                const person = this.normalizeThreeAsset(personGltf.scene, { height: 1.82, rotateY: Math.PI })
                person.userData.animations = personGltf.animations || []
                this.threeAssetTemplates = { car, person }
                this.assetStatus = 'ready'
                this.buildAmbientTraffic()
                this.resetThreeTargets()
                this.syncThreeFrame()
            }).catch(error => {
                console.warn('3D assets unavailable, using procedural models.', error)
                this.assetStatus = 'fallback'
                this.buildAmbientTraffic()
            })
        },
        normalizeThreeAsset(source, options = {}) {
            const THREE = window.THREE
            const model = source
            if (options.rotateY) model.rotation.y = options.rotateY
            let box = new THREE.Box3().setFromObject(model)
            let size = box.getSize(new THREE.Vector3())
            if (options.rotateToRoad && size.x > size.z) {
                model.rotation.y += Math.PI / 2
                box = new THREE.Box3().setFromObject(model)
                size = box.getSize(new THREE.Vector3())
            }
            const scale = options.height ? options.height / size.y : options.length / Math.max(size.x, size.z)
            model.scale.multiplyScalar(scale)
            box = new THREE.Box3().setFromObject(model)
            const center = box.getCenter(new THREE.Vector3())
            model.position.set(-center.x, -box.min.y, -center.z)
            model.traverse(object => {
                if (!object.isMesh) return
                object.castShadow = true
                object.receiveShadow = true
            })
            const wrapper = new THREE.Group()
            wrapper.add(model)
            return wrapper
        },
        makeAssetCar(color = 0xb73038) {
            const THREE = window.THREE
            const car = this.threeAssetTemplates?.car?.clone(true)
            if (!car) return this.makeThreeVehicle(color)
            let tinted = false
            car.traverse(object => {
                if (!object.isMesh || tinted || !object.material) return
                object.material = object.material.clone()
                object.material.color = new THREE.Color(color)
                object.material.roughness = Math.min(object.material.roughness ?? 0.5, 0.42)
                tinted = true
            })
            return car
        },
        buildAmbientTraffic() {
            if (!this.threeScene) return
            this.threeAmbientCars.forEach(car => this.threeScene.remove(car))
            this.threeAmbientCars = []
            const traffic = [
                { x: -3.1, z: -42, color: 0x2d566f },
                { x: 3.15, z: -68, color: 0xd0d3d4 },
                { x: -3.05, z: -102, color: 0x5f666b },
                { x: 3.2, z: -132, color: 0xb58a32 },
            ]
            traffic.forEach(item => {
                const car = this.makeAssetCar(item.color)
                car.position.set(item.x, 0.02, item.z)
                car.rotation.y = Math.PI
                car.scale.multiplyScalar(0.92)
                this.threeAmbientCars.push(car)
                this.threeScene.add(car)
            })
        },
        makeThreeWheel(radius = 0.36) {
            const THREE = window.THREE
            const tireMaterial = new THREE.MeshStandardMaterial({ color: 0x111315, roughness: 0.95 })
            const rimMaterial = new THREE.MeshStandardMaterial({ color: 0xc8ced0, roughness: 0.35, metalness: 0.25 })
            const group = new THREE.Group()
            const tire = new THREE.Mesh(new THREE.TorusGeometry(radius, radius * 0.11, 12, 28), tireMaterial)
            tire.rotation.y = Math.PI / 2
            const rim = new THREE.Mesh(new THREE.CylinderGeometry(radius * 0.48, radius * 0.48, 0.04, 16), rimMaterial)
            rim.rotation.z = Math.PI / 2
            group.add(tire, rim)
            return group
        },
        makeThreeVehicle(color = 0xb6c0c8) {
            const THREE = window.THREE
            const group = new THREE.Group()
            const bodyMaterial = new THREE.MeshStandardMaterial({ color, roughness: 0.38, metalness: 0.42 })
            const glassMaterial = new THREE.MeshStandardMaterial({ color: 0x8fb8c8, roughness: 0.12, metalness: 0.25, transparent: true, opacity: 0.82 })
            const trimMaterial = new THREE.MeshStandardMaterial({ color: 0x12171b, roughness: 0.72, metalness: 0.2 })
            const lightMaterial = new THREE.MeshStandardMaterial({ color: 0xf7f0d5, emissive: 0xffe8a6, emissiveIntensity: 1.2 })
            const tailMaterial = new THREE.MeshStandardMaterial({ color: 0xb81f26, emissive: 0xff1f2d, emissiveIntensity: 0.9 })
            const body = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.72, 3.8), bodyMaterial)
            body.position.y = 0.62
            body.castShadow = true
            const hood = new THREE.Mesh(new THREE.BoxGeometry(1.68, 0.12, 1.05), bodyMaterial)
            hood.position.set(0, 1.03, -1.05)
            hood.castShadow = true
            const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.48, 0.7, 1.45), glassMaterial)
            cabin.position.set(0, 1.27, 0.35)
            cabin.castShadow = true
            const grille = new THREE.Mesh(new THREE.BoxGeometry(1.22, 0.18, 0.06), trimMaterial)
            grille.position.set(0, 0.69, -1.93)
            group.add(body, hood, cabin, grille)
            for (const x of [-0.55, 0.55]) {
                const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.13, 0.08), lightMaterial)
                lamp.position.set(x, 0.83, -1.94)
                const tail = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.13, 0.08), tailMaterial)
                tail.position.set(x, 0.82, 1.94)
                group.add(lamp, tail)
            }
            for (const x of [-0.98, 0.98]) {
                for (const z of [-1.15, 1.15]) {
                    const wheel = new THREE.Mesh(
                        new THREE.CylinderGeometry(0.33, 0.33, 0.22, 16),
                        new THREE.MeshStandardMaterial({ color: 0x101214, roughness: 1 })
                    )
                    wheel.rotation.z = Math.PI / 2
                    wheel.position.set(x, 0.36, z)
                    wheel.castShadow = true
                    group.add(wheel)
                }
            }
            return group
        },
        makeThreePerson(options = {}) {
            const THREE = window.THREE
            const group = new THREE.Group()
            const jacket = options.jacket ?? 0x2f80c2
            const pants = options.pants ?? 0x26313a
            const bodyMaterial = new THREE.MeshStandardMaterial({ color: jacket, roughness: 0.78 })
            const pantsMaterial = new THREE.MeshStandardMaterial({ color: pants, roughness: 0.86 })
            const skinMaterial = new THREE.MeshStandardMaterial({ color: 0xd8a47f, roughness: 0.82 })
            const shoeMaterial = new THREE.MeshStandardMaterial({ color: 0x181b1f, roughness: 0.9 })
            const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.27, 0.9, 6, 12), bodyMaterial)
            body.position.y = 1.18
            body.castShadow = true
            const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 18, 12), skinMaterial)
            head.position.y = 1.93
            head.castShadow = true
            const backpack = new THREE.Mesh(
                new THREE.BoxGeometry(0.34, 0.54, 0.16),
                new THREE.MeshStandardMaterial({ color: 0x39424b, roughness: 0.82 })
            )
            backpack.position.set(0, 1.25, -0.23)
            backpack.castShadow = true
            group.add(body, head, backpack)
            for (const side of [-1, 1]) {
                const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.065, 0.66, 5, 8), skinMaterial)
                arm.position.set(side * 0.34, 1.15, 0.04)
                arm.rotation.z = side * 0.18
                arm.userData.walkPhase = side
                arm.castShadow = true
                const leg = new THREE.Mesh(new THREE.CapsuleGeometry(0.08, 0.72, 5, 8), pantsMaterial)
                leg.position.set(side * 0.11, 0.48, 0)
                leg.userData.walkPhase = -side
                leg.castShadow = true
                const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.08, 0.28), shoeMaterial)
                shoe.position.set(side * 0.11, 0.08, 0.08)
                shoe.castShadow = true
                group.add(arm, leg, shoe)
            }
            group.userData.isProceduralPerson = true
            group.userData.walkAmplitude = options.walkAmplitude ?? 0.32
            return group
        },
        makeThreeCyclist() {
            const THREE = window.THREE
            const group = new THREE.Group()
            const frameMaterial = new THREE.MeshStandardMaterial({ color: 0xd8b24a, roughness: 0.46, metalness: 0.25 })
            for (const z of [-0.72, 0.72]) {
                const wheel = this.makeThreeWheel(0.34)
                wheel.position.set(0, 0.42, z)
                group.add(wheel)
            }
            const frame = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.12, 1.35), frameMaterial)
            frame.position.set(0, 0.74, 0)
            frame.rotation.x = -0.18
            const handle = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.06, 0.08), frameMaterial)
            handle.position.set(0, 1.06, -0.64)
            const rider = this.makeThreePerson({ jacket: 0x62a87c, pants: 0x20272d, walkAmplitude: 0.12 })
            rider.scale.setScalar(0.72)
            rider.position.set(0, 0.62, 0.06)
            rider.rotation.x = -0.18
            group.add(frame, handle, rider)
            return group
        },
        makeThreeMotorcycle() {
            const THREE = window.THREE
            const group = new THREE.Group()
            const tireMaterial = new THREE.MeshStandardMaterial({ color: 0x111315, roughness: 0.95 })
            const frameMaterial = new THREE.MeshStandardMaterial({ color: 0xe0a52b, roughness: 0.42, metalness: 0.35 })
            for (const z of [-1.15, 1.15]) {
                const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.47, 0.11, 12, 24), tireMaterial)
                wheel.rotation.y = Math.PI / 2
                wheel.position.set(0, 0.48, z)
                group.add(wheel)
            }
            const frame = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.32, 1.85), frameMaterial)
            frame.position.y = 0.77
            frame.rotation.x = -0.08
            const tank = new THREE.Mesh(new THREE.SphereGeometry(0.42, 18, 12), frameMaterial)
            tank.scale.set(0.8, 0.72, 1.15)
            tank.position.set(0, 1.05, 0.22)
            const rider = this.makeThreePerson()
            rider.scale.setScalar(0.78)
            rider.position.set(0, 0.72, 0.3)
            rider.rotation.x = -0.18
            group.add(frame, tank, rider)
            return group
        },
        makeThreeTrafficLight() {
            const THREE = window.THREE
            const group = new THREE.Group()
            const pole = new THREE.Mesh(
                new THREE.CylinderGeometry(0.09, 0.11, 4.8, 12),
                new THREE.MeshStandardMaterial({ color: 0x30383d, roughness: 0.8 })
            )
            pole.position.y = 2.4
            const housing = new THREE.Mesh(
                new THREE.BoxGeometry(0.8, 1.8, 0.55),
                new THREE.MeshStandardMaterial({ color: 0x171b1d })
            )
            housing.position.y = 4.65
            const red = new THREE.Mesh(
                new THREE.SphereGeometry(0.22, 16, 12),
                new THREE.MeshStandardMaterial({ color: 0xff2d2d, emissive: 0xff0000, emissiveIntensity: 3 })
            )
            red.position.set(0, 5.05, 0.3)
            group.add(pole, housing, red)
            return group
        },
        makeThreeTarget(target) {
            if (target.class_name === 'person') {
                return this.makeThreePerson()
            }
            if (['traffic light', 'traffic_light'].includes(target.class_name)) return this.makeThreeTrafficLight()
            if (target.class_name === 'motorcycle' || target.class_name === 'bicycle') return this.makeThreeMotorcycle()
            return this.makeAssetCar(0xb7c1c8)
        },
        resetThreeTargets() {
            if (!this.threeTargets || !this.threeScene) return
            this.threeTargets.forEach(target => this.threeScene.remove(target))
            this.threeTargets.clear()
            this.threeMixers = []
        },
        syncThreeFrame() {
            if (!this.threeScene || !this.frame) return
            if (this.threeScenarioProps) {
                this.threeScenarioProps.position.z = this.frame.ego_travel_distance_m || 0
            }
            const activeIds = new Set()
            this.frame.targets.forEach(target => {
                activeIds.add(target.id)
                let model = this.threeTargets.get(target.id)
                if (!model) {
                    model = this.makeThreeTarget(target)
                    const [x, y, z] = target.world_position || [target.lateral_m || 0, 0, -target.distance_m]
                    model.position.set(x, y, z)
                    model.userData.className = target.class_name
                    this.threeTargets.set(target.id, model)
                    this.threeScene.add(model)
                }
                model.visible = true
                const [x, y, z] = target.world_position || [target.lateral_m || 0, 0, -target.distance_m]
                model.userData.targetX = x
                model.userData.targetY = y
                model.userData.targetZ = z
                model.rotation.y = Number(target.heading_rad || 0)
            })
            this.threeTargets.forEach((target, id) => { target.visible = activeIds.has(id) })
        },
        configureThreeScenario() {
            const THREE = window.THREE
            if (!this.threeScene || !THREE || !this.result) return
            if (this.threeScenarioProps) this.threeScene.remove(this.threeScenarioProps)
            const group = new THREE.Group()
            const firstFrameTargets = this.result.timeline?.[0]?.targets || []
            const lightTarget = firstFrameTargets.find(target => ['traffic light', 'traffic_light'].includes(target.class_name))
            const personTarget = firstFrameTargets.find(target => target.class_name === 'person')
            const initialTarget = lightTarget || personTarget || firstFrameTargets[0]
            const conflictDistance = this.result.scenario === 'mixed_intersection'
                ? Math.min(lightTarget?.distance_m || 34, 42)
                : Math.min(initialTarget?.distance_m || 28, 38) * 1.18 + 4
            const conflictZ = -conflictDistance
            const whiteMaterial = new THREE.MeshStandardMaterial({ color: 0xe8e6d8, roughness: 0.88 })
            const curbMaterial = new THREE.MeshStandardMaterial({ color: 0xb6b8ad, roughness: 0.86 })
            const warningMaterial = new THREE.MeshStandardMaterial({ color: 0xf0782e, emissive: 0x361308 })
            const asphaltDarkMaterial = new THREE.MeshStandardMaterial({ color: 0x262b2f, roughness: 0.97 })
            const skidMaterial = new THREE.MeshStandardMaterial({ color: 0x111315, roughness: 1, transparent: true, opacity: 0.86 })

            if (['pedestrian_crossing', 'red_light', 'mixed_intersection'].includes(this.result.scenario)) {
                for (let index = 0; index < 9; index += 1) {
                    const stripe = new THREE.Mesh(new THREE.BoxGeometry(15.8, 0.035, 0.48), whiteMaterial)
                    stripe.position.set(0, 0.06, conflictZ + (index - 4) * 0.9)
                    group.add(stripe)
                }
                for (const x of [-9.2, 9.2]) {
                    const waitingCurb = new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.18, 5.8), curbMaterial)
                    waitingCurb.position.set(x, 0.14, conflictZ)
                    group.add(waitingCurb)
                    const tactile = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.025, 0.42), whiteMaterial)
                    tactile.position.set(x, 0.25, conflictZ - 2.2)
                    group.add(tactile)
                }
            }
            if (this.result.scenario === 'pedestrian_crossing') {
                const waitingA = this.makeThreePerson({ jacket: 0x6a9f5f, pants: 0x26313a, walkAmplitude: 0.08 })
                waitingA.position.set(-9.2, 0.18, conflictZ - 1.9)
                waitingA.rotation.y = Math.PI / 2
                const waitingB = this.makeThreePerson({ jacket: 0xd1a74b, pants: 0x2b3036, walkAmplitude: 0.08 })
                waitingB.position.set(9.15, 0.18, conflictZ + 1.8)
                waitingB.rotation.y = -Math.PI / 2
                const crossingSign = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.95, 0.08), new THREE.MeshStandardMaterial({ color: 0x2f78c2, emissive: 0x09243d, emissiveIntensity: 0.35 }))
                crossingSign.position.set(-10.2, 2.95, conflictZ + 3.4)
                const signPole = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.06, 2.65, 8), new THREE.MeshStandardMaterial({ color: 0x30383d, roughness: 0.8 }))
                signPole.position.set(-10.2, 1.33, conflictZ + 3.4)
                group.add(waitingA, waitingB, crossingSign, signPole)
            }
            if (this.result.scenario === 'red_light' || this.result.scenario === 'mixed_intersection') {
                const crossingRoad = new THREE.Mesh(
                    new THREE.PlaneGeometry(74, 17),
                    asphaltDarkMaterial
                )
                crossingRoad.rotation.x = -Math.PI / 2
                crossingRoad.position.set(0, 0.028, conflictZ - 9)
                group.add(crossingRoad)
                const stopLine = new THREE.Mesh(new THREE.BoxGeometry(16, 0.05, 0.65), whiteMaterial)
                stopLine.position.set(0, 0.07, conflictZ + 5.2)
                group.add(stopLine)
                for (const x of [-11.8, 11.8]) {
                    const pole = new THREE.Mesh(
                        new THREE.CylinderGeometry(0.09, 0.12, 5.4, 12),
                        new THREE.MeshStandardMaterial({ color: 0x30383d, roughness: 0.8 })
                    )
                    pole.position.set(x, 2.7, conflictZ + 3.2)
                    const arm = new THREE.Mesh(new THREE.BoxGeometry(4.7, 0.1, 0.1), pole.material)
                    arm.position.set(x > 0 ? x - 2.25 : x + 2.25, 5.32, conflictZ + 3.2)
                    const signal = this.makeThreeTrafficLight()
                    signal.scale.setScalar(0.58)
                    signal.position.set(x > 0 ? x - 4.2 : x + 4.2, 1.65, conflictZ + 3.3)
                    signal.rotation.y = x > 0 ? Math.PI / 2 : -Math.PI / 2
                    group.add(pole, arm, signal)
                }
                for (const x of [-3, 3]) {
                    const turnArrow = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.035, 5.2), whiteMaterial)
                    turnArrow.position.set(x, 0.075, conflictZ + 12.5)
                    group.add(turnArrow)
                }
                if (this.result.scenario === 'mixed_intersection') {
                    const queueCar = this.makeThreeVehicle(0xbfc7c9)
                    queueCar.scale.setScalar(0.86)
                    queueCar.position.set(-5.2, 0.03, conflictZ - 10)
                    queueCar.rotation.y = -Math.PI / 2
                    const cyclist = this.makeThreeCyclist()
                    cyclist.position.set(7.3, 0.02, conflictZ + 2.4)
                    cyclist.rotation.y = Math.PI / 2
                    const scooter = this.makeThreeMotorcycle()
                    scooter.scale.setScalar(0.72)
                    scooter.position.set(4.7, 0.03, conflictZ - 5.8)
                    scooter.rotation.y = -0.35
                    const waitingPerson = this.makeThreePerson({ jacket: 0x8a69c4, pants: 0x20272d, walkAmplitude: 0.08 })
                    waitingPerson.position.set(-9.3, 0.18, conflictZ + 2.2)
                    waitingPerson.rotation.y = Math.PI / 2
                    const busBay = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.03, 13), asphaltDarkMaterial)
                    busBay.position.set(8.2, 0.068, conflictZ - 16)
                    group.add(queueCar, cyclist, scooter, waitingPerson, busBay)
                }
            }
            if (this.result.scenario === 'front_car_brake') {
                for (const x of [-0.74, 0.74]) {
                    const mark = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.025, 13.2), skidMaterial)
                    mark.position.set(x, 0.058, conflictZ + 7)
                    mark.rotation.y = x > 0 ? 0.035 : -0.035
                    group.add(mark)
                }
                const warningTriangle = new THREE.Mesh(new THREE.ConeGeometry(0.72, 0.08, 3), warningMaterial)
                warningTriangle.rotation.set(Math.PI / 2, 0, Math.PI / 3)
                warningTriangle.position.set(5.8, 0.42, conflictZ + 11)
                const shoulderLine = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.035, 16), whiteMaterial)
                shoulderLine.position.set(7.25, 0.07, conflictZ + 7)
                group.add(warningTriangle, shoulderLine)
            }
            if (this.result.scenario === 'motorcycle_cut_in') {
                for (let index = 0; index < 7; index += 1) {
                    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.82, 14), warningMaterial)
                    cone.position.set(6.4 - index * 0.18, 0.42, conflictZ + 12 - index * 4.2)
                    group.add(cone)
                    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.34, 0.75, 14), warningMaterial)
                    barrel.position.set(8.05, 0.39, conflictZ + 9 - index * 5.4)
                    group.add(barrel)
                }
                const closedLane = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.03, 24), asphaltDarkMaterial)
                closedLane.position.set(7.1, 0.066, conflictZ - 3)
                group.add(closedLane)
            }
            this.threeScenarioProps = group
            this.threeScene.add(group)
        },
        configureThreeEnvironment() {
            const THREE = window.THREE
            if (!this.threeScene || !THREE) return
            const weather = this.result?.weather || 'clear'
            const config = {
                clear: { sky: 0x8fb4c7, skyTop: 0x4388b3, skyBottom: 0xdce6e5, fog: 0x8fb4c7, near: 45, far: 160, hemi: 2.25, sun: 3.2, headlight: 0.35, street: 0, exposure: 1.05, road: 0x5d6263, roughness: 0.94, metalness: 0.02 },
                rain: { sky: 0x586c78, skyTop: 0x354957, skyBottom: 0x9aa6a8, fog: 0x667984, near: 20, far: 92, hemi: 1.45, sun: 1.25, headlight: 2.2, street: 0.8, exposure: 0.92, road: 0x353d42, roughness: 0.48, metalness: 0.18 },
                fog: { sky: 0xaeb8b8, skyTop: 0x909d9e, skyBottom: 0xd4d7d2, fog: 0xb8c0bd, near: 8, far: 48, hemi: 1.7, sun: 1.1, headlight: 2.8, street: 1.2, exposure: 0.98, road: 0x596164, roughness: 0.82, metalness: 0.05 },
                night: { sky: 0x050d18, skyTop: 0x020611, skyBottom: 0x15283b, fog: 0x07101c, near: 24, far: 100, hemi: 0.55, sun: 0.25, headlight: 6.5, street: 3.4, exposure: 0.72, road: 0x232a30, roughness: 0.58, metalness: 0.15 },
            }[weather]
            this.threeScene.background = new THREE.Color(config.sky)
            this.threeScene.fog = new THREE.Fog(config.fog, config.near, config.far)
            this.threeRenderer.toneMappingExposure = config.exposure
            this.threeHemiLight.intensity = config.hemi
            this.threeSunLight.intensity = config.sun
            this.threeHeadlights.forEach(light => { light.intensity = config.headlight })
            this.threeStreetLights.forEach(light => { light.intensity = config.street })
            this.threeSkyMaterial.uniforms.topColor.value.setHex(config.skyTop)
            this.threeSkyMaterial.uniforms.bottomColor.value.setHex(config.skyBottom)
            if (this.threeRoadMaterial) {
                this.threeRoadMaterial.color.setHex(config.road)
                this.threeRoadMaterial.roughness = config.roughness
                this.threeRoadMaterial.metalness = config.metalness
                this.threeRoadMaterial.needsUpdate = true
            }

            if (this.threeRain) {
                this.threeScene.remove(this.threeRain)
                this.threeRain.geometry.dispose()
                this.threeRain.material.dispose()
                this.threeRain = null
            }
            if (weather === 'rain') {
                const positions = new Float32Array(950 * 3)
                for (let index = 0; index < 950; index += 1) {
                    positions[index * 3] = (Math.random() - 0.5) * 34
                    positions[index * 3 + 1] = Math.random() * 12
                    positions[index * 3 + 2] = 8 - Math.random() * 105
                }
                const geometry = new THREE.BufferGeometry()
                geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
                const material = new THREE.PointsMaterial({ color: 0xcbe7f2, size: 0.085, transparent: true, opacity: 0.68 })
                this.threeRain = new THREE.Points(geometry, material)
                this.threeScene.add(this.threeRain)
            }
        },
        disposeThreeScene() {
            if (this.threeAnimationFrame) cancelAnimationFrame(this.threeAnimationFrame)
            if (this.threeResizeObserver) this.threeResizeObserver.disconnect()
            if (this.threeRenderer) this.threeRenderer.dispose()
            if (this.threeDracoLoader) this.threeDracoLoader.dispose()
            this.threeAnimationFrame = null
            this.threeResizeObserver = null
            this.threeRenderer = null
        },
        targetStyle(target) {
            if (this.threeCamera && window.THREE) {
                const [x, , z] = target.world_position || [target.lateral_m || 0, 0, -target.distance_m]
                const point = new window.THREE.Vector3(
                    x,
                    ['traffic light', 'traffic_light'].includes(target.class_name) ? 3.1 : 1.25,
                    z
                ).project(this.threeCamera)
                const scale = Math.max(0.62, Math.min(1.45, 30 / (target.distance_m + 5)))
                return {
                    left: ((point.x + 1) / 2 * 100) + '%',
                    top: ((1 - point.y) / 2 * 100) + '%',
                    '--target-scale': scale,
                }
            }
            return { left: '50%', top: '50%', '--target-scale': 1 }
        },
    },
    computed: {
        timeline() { return this.result?.timeline || [] },
        frame() { return this.timeline[this.frameIndex] || null },
        peakRisk() {
            return this.result?.peak_risk || { level: 'low', score: 0, time_sec: 0 }
        },
        primaryTarget() { return this.frame?.primary_target || null },
        currentTtc() { return this.primaryTarget?.risk?.ttc_sec },
        chartPoints() {
            if (!this.timeline.length) return ''
            const last = Math.max(1, this.timeline.length - 1)
            return this.timeline.map((item, index) => {
                const x = 10 + index / last * 580
                const y = 142 - item.max_risk_score * 1.18
                return `${x.toFixed(1)},${y.toFixed(1)}`
            }).join(' ')
        },
        chartAreaPoints() { return this.chartPoints ? `10,142 ${this.chartPoints} 590,142` : '' },
        chartCursorX() {
            return 10 + this.frameIndex / Math.max(1, this.timeline.length - 1) * 580
        },
        eventLog() {
            const events = []
            let previousLevel = null
            this.timeline.slice(0, this.frameIndex + 1).forEach(item => {
                if (item.max_risk_level !== previousLevel) {
                    events.push({ time: item.time_sec, level: item.max_risk_level })
                    previousLevel = item.max_risk_level
                }
            })
            return events.slice(-4).reverse()
        },
    },
    template: `
    <section class="simulation-panel simulation-cockpit">
        <header class="sim-page-header">
            <div>
                <span class="sim-eyebrow">SCENARIO LAB / 01</span>
                <h2>自动驾驶风险仿真驾驶舱</h2>
            </div>
            <div class="sim-run-state" :class="{ active: isPlaying }">
                <span></span>{{ isPlaying ? '仿真运行中' : '仿真待机' }}
            </div>
        </header>

        <div class="sim-toolbar">
            <label class="sim-control sim-control-scene">
                <span>场景</span>
                <select :value="scenario" @change="$emit('scenarioChange', $event.target.value)">
                    <optgroup label="预设场景">
                        <option v-for="item in presets" :key="item.key" :value="item.key">{{ item.name }}</option>
                    </optgroup>
                    <optgroup v-if="customScenarios?.length" label="自定义场景">
                        <option v-for="item in customScenarios" :key="item.key" :value="item.key">{{ item.name }}</option>
                    </optgroup>
                </select>
            </label>
            <div class="sim-control sim-weather-control">
                <span>环境</span>
                <div class="sim-segmented">
                    <button v-for="item in weatherOptions" :key="item.key" :class="{ active: weather === item.key }" @click="$emit('weatherChange', item.key)">
                        {{ item.name }}
                    </button>
                </div>
            </div>
            <label class="sim-control sim-control-range">
                <span>自车速度 <strong>{{ speed }} km/h</strong></span>
                <input type="range" min="0" max="100" step="5" :value="speed" @input="$emit('speedChange', Number($event.target.value))">
            </label>
            <label class="sim-control sim-control-range">
                <span>时长 <strong>{{ duration }} s</strong></span>
                <input type="range" min="2" max="10" step="1" :value="duration" @input="$emit('durationChange', Number($event.target.value))">
            </label>
            <div class="sim-toolbar-actions">
                <button class="btn btn-primary sim-generate" :disabled="isSimulating" @click="$emit('run')">
                    <span v-if="!isSimulating">?</span>{{ isSimulating ? '计算中...' : '生成仿真' }}
                </button>
                <button class="btn btn-secondary" :disabled="isComparing" @click="$emit('compare')">
                    {{ isComparing ? '对比中...' : 'AEB 对比' }}
                </button>
                <button class="btn btn-secondary" @click="openScenarioEditor">场景编辑</button>
            </div>
        </div>

        <section v-if="showScenarioEditor" class="sim-scenario-editor">
            <div class="sim-editor-head">
                <div><span>自定义场景</span><strong>{{ scenarioDraft.id ? '编辑配置' : '新建配置' }}</strong></div>
                <button class="sim-icon-btn" title="关闭" @click="showScenarioEditor = false">×</button>
            </div>
            <div class="sim-editor-fields">
                <label><span>名称</span><input v-model.trim="scenarioDraft.name" maxlength="80"></label>
                <label><span>天气</span><select v-model="scenarioDraft.weather"><option v-for="item in weatherOptions" :key="item.key" :value="item.key">{{ item.name }}</option></select></label>
                <label><span>自车速度 km/h</span><input v-model.number="scenarioDraft.ego_speed_kmh" type="number" min="0" max="140"></label>
                <label><span>时长 s</span><input v-model.number="scenarioDraft.duration_sec" type="number" min="0.1" max="30" step="0.5"></label>
                <label class="sim-editor-description"><span>描述</span><input v-model.trim="scenarioDraft.description" maxlength="500"></label>
            </div>
            <div class="sim-editor-json">
                <label><span>目标 JSON</span><textarea v-model="scenarioDraft.targetsJson" spellcheck="false"></textarea></label>
                <label><span>事件 JSON</span><textarea v-model="scenarioDraft.eventsJson" spellcheck="false"></textarea></label>
            </div>
            <div class="sim-editor-footer">
                <span class="sim-editor-error">{{ scenarioEditorError }}</span>
                <button v-if="scenarioDraft.id" class="btn btn-danger" @click="deleteDraftScenario">删除</button>
                <button class="btn btn-primary" @click="submitScenario">保存场景</button>
            </div>
        </section>

        <div v-if="result" class="sim-workspace">
            <div class="sim-visual-column">
                <div class="simulation-road" :class="['weather-' + result.weather, 'risk-stage-' + (frame?.max_risk_level || 'low')]">
                    <canvas ref="simCanvas" class="sim-three-canvas"></canvas>
                    <div class="sim-windshield"><i></i><i></i></div>
                    <div v-if="result.weather === 'rain'" class="sim-wipers"><i></i><i></i></div>
                    <div class="sim-stage-top">
                        <div><span>场景</span><strong>{{ result.scenario_name }}</strong></div>
                        <div class="sim-live"><i></i> {{ assetStatus === 'ready' ? 'MODEL READY' : '3D LIVE' }} · {{ frame?.time_sec.toFixed(2) }}s</div>
                    </div>
                    <div class="sim-adas-bar">
                        <span><i></i> LKA 车道居中</span><span>ACC {{ Math.round(frame?.ego_speed_kmh || 0) }} km/h</span><span>FCW 已监测</span>
                    </div>
                    <div class="sim-weather-layer"></div>
                    <div class="sim-lane-assist"><span></span><span></span></div>
                    <template v-if="frame">
                        <div v-for="target in frame.targets" v-show="target.detected" :key="target.id" class="sim-target" :class="['risk-bg-' + target.risk.level, targetClass(target)]" :style="targetStyle(target)">
                            <i class="corner corner-tl"></i><i class="corner corner-tr"></i>
                            <i class="corner corner-bl"></i><i class="corner corner-br"></i>
                            <div class="sim-target-label">
                                <strong>{{ target.class_name_cn }}</strong>
                                <small>{{ target.distance_m.toFixed(1) }}m · {{ Math.round(target.confidence * 100) }}%</small>
                            </div>
                        </div>
                    </template>
                    <div class="sim-drive-data">
                        <div class="sim-speed-dial" :style="{ '--speed-progress': Math.min(100, frame?.ego_speed_kmh || 0) + '%' }"><strong>{{ Math.round(frame?.ego_speed_kmh || 0) }}</strong><span>km/h</span></div>
                        <div><span>GEAR</span><strong>D</strong></div>
                        <div><span>TTC</span><strong>{{ formatTtc(currentTtc) }}</strong></div>
                    </div>
                    <div class="sim-route-map"><i></i><span>前方 {{ primaryTarget ? primaryTarget.distance_m.toFixed(0) : '--' }}m</span><strong>保持车道</strong></div>
                    <div v-if="frame?.aeb_active" class="sim-aeb-alert">
                        <strong>AEB</strong><span>自动紧急制动</span><small>-{{ frame.brake_deceleration_mps2 }} m/s2 · TTC {{ formatTtc(currentTtc) }}</small>
                    </div>
                    <div class="sim-steering"><span></span></div>
                    <div class="sim-vehicle-hood"></div>
                    <div class="sim-risk-banner" :class="riskClass(frame?.max_risk_level)">
                        <span>{{ riskLabel(frame?.max_risk_level) }}</span><strong>{{ frame?.max_risk_score }}</strong>
                    </div>
                </div>

                <div class="sim-playback">
                    <button class="sim-icon-btn" title="重新播放" @click="restartPlayback">?</button>
                    <button class="sim-play-btn" :title="isPlaying ? '暂停' : '播放'" @click="togglePlayback">{{ isPlaying ? 'Ⅱ' : '?' }}</button>
                    <span>{{ frame?.time_sec.toFixed(2) }}s</span>
                    <input type="range" min="0" :max="timeline.length - 1" :value="frameIndex" @input="seekPlayback($event.target.value)">
                    <span>{{ result.duration_sec.toFixed(2) }}s</span>
                    <div class="sim-rate-control" aria-label="播放速度">
                        <button v-for="rate in [0.5, 1, 2]" :key="rate" :class="{ active: playbackRate === rate }" @click="setPlaybackRate(rate)">{{ rate }}×</button>
                    </div>
                </div>
            </div>

            <aside class="sim-telemetry">
                <div class="sim-kpi-grid">
                    <article class="sim-kpi" :class="'kpi-' + (frame?.max_risk_level || 'low')"><span>风险评分</span><strong>{{ frame?.max_risk_score }}</strong><small>/ 100</small></article>
                    <article class="sim-kpi"><span>预计碰撞 TTC</span><strong>{{ formatTtc(currentTtc) }}</strong><small>{{ currentTtc != null && currentTtc < 3 ? '立即干预' : '动态计算' }}</small></article>
                    <article class="sim-kpi"><span>目标距离</span><strong>{{ primaryTarget ? primaryTarget.distance_m.toFixed(1) : '--' }}m</strong><small>相对纵向距离</small></article>
                    <article class="sim-kpi"><span>感知状态</span><strong>{{ primaryTarget ? Math.round(primaryTarget.confidence * 100) : '--' }}%</strong><small>{{ frame?.perception_fps }} FPS</small></article>
                </div>
                <div class="sim-decision" :class="'decision-' + (frame?.max_risk_level || 'low')">
                    <div><span>决策建议</span><strong>{{ riskLabel(frame?.max_risk_level) }}</strong></div>
                    <p>{{ frame?.advice }}</p>
                </div>
                <div class="sim-events">
                    <div class="sim-subhead"><span>事件流</span><strong>{{ eventLog.length }}</strong></div>
                    <div v-for="event in eventLog" :key="event.time + event.level" class="sim-event-row">
                        <time>{{ event.time.toFixed(2) }}s</time><i :class="'event-' + event.level"></i><span>{{ riskLabel(event.level) }}</span>
                    </div>
                </div>
            </aside>
        </div>

        <div v-if="result" class="sim-analysis-band">
            <div class="sim-chart-wrap">
                <div class="sim-subhead"><span>风险时间曲线</span><strong>RISK / TIME</strong></div>
                <svg class="sim-risk-chart" viewBox="0 0 600 160" preserveAspectRatio="none" aria-label="风险时间曲线">
                    <line x1="10" y1="52" x2="590" y2="52" class="chart-threshold chart-high"></line>
                    <line x1="10" y1="89" x2="590" y2="89" class="chart-threshold chart-medium"></line>
                    <polygon :points="chartAreaPoints" class="chart-area"></polygon>
                    <polyline :points="chartPoints" class="chart-line"></polyline>
                    <line :x1="chartCursorX" y1="18" :x2="chartCursorX" y2="142" class="chart-cursor"></line>
                    <circle :cx="chartCursorX" :cy="142 - (frame?.max_risk_score || 0) * 1.18" r="5" class="chart-point"></circle>
                    <text x="14" y="48">高风险 76</text><text x="14" y="85">中风险 45</text>
                </svg>
                <div class="sim-chart-axis"><span>0s</span><span>{{ result.duration_sec }}s</span></div>
            </div>
            <div class="sim-report">
                <div class="sim-subhead"><span>本次仿真报告</span><strong>REPORT</strong></div>
                <div class="sim-report-grid">
                    <div><span>峰值风险</span><strong>{{ peakRisk.score }}</strong><small>{{ peakRisk.time_sec }}s</small></div>
                    <div><span>最小 TTC</span><strong>{{ formatTtc(result.metrics.min_ttc_sec) }}</strong><small>安全边界</small></div>
                    <div><span>首次预警</span><strong>{{ result.metrics.first_warning_sec == null ? '--' : result.metrics.first_warning_sec + 's' }}</strong><small>响应时刻</small></div>
                    <div><span>高风险持续</span><strong>{{ result.metrics.high_risk_duration_sec }}s</strong><small>累计时长</small></div>
                    <div><span>平均置信度</span><strong>{{ Math.round(result.metrics.average_confidence * 100) }}%</strong><small>{{ result.weather_name }}</small></div>
                    <div><span>碰撞结果</span><strong :class="result.metrics.collision ? 'risk-high' : 'risk-low'">{{ result.metrics.collision ? '发生碰撞' : '安全通过' }}</strong><small>仿真判定</small></div>
                    <div><span>AEB 介入</span><strong>{{ result.metrics.aeb_activation_sec == null ? '未触发' : result.metrics.aeb_activation_sec + 's' }}</strong><small>闭环控制</small></div>
                    <div><span>最终车速</span><strong>{{ (result.metrics.final_speed_kmh ?? result.ego_speed_kmh).toFixed(1) }}</strong><small>km/h</small></div>
                </div>
            </div>
        </div>

        <section v-if="comparisonResult" class="sim-comparison-band">
            <div class="sim-subhead"><span>AEB 干预效果对比</span><strong>SAME SCENARIO / CONTROL VARIABLE</strong></div>
            <div class="sim-comparison-grid">
                <article v-for="item in [
                    { key: 'with', label: '启用 AEB', result: comparisonResult.withAeb },
                    { key: 'without', label: '关闭 AEB', result: comparisonResult.withoutAeb }
                ]" :key="item.key" class="sim-comparison-item">
                    <header><strong>{{ item.label }}</strong><span>{{ item.result.weather_name }}</span></header>
                    <svg viewBox="0 0 300 100" preserveAspectRatio="none" aria-label="风险对比曲线">
                        <line x1="8" y1="33" x2="292" y2="33" class="chart-threshold chart-high"></line>
                        <line x1="8" y1="57" x2="292" y2="57" class="chart-threshold chart-medium"></line>
                        <polyline :points="comparisonChartPoints(item.result)" class="chart-line"></polyline>
                    </svg>
                    <div class="sim-comparison-metrics">
                        <div><span>碰撞</span><strong :class="item.result.metrics.collision ? 'risk-high' : 'risk-low'">{{ item.result.metrics.collision ? '是' : '否' }}</strong></div>
                        <div><span>最终车速</span><strong>{{ item.result.metrics.final_speed_kmh.toFixed(1) }} km/h</strong></div>
                        <div><span>行驶距离</span><strong>{{ item.result.metrics.ego_distance_m.toFixed(1) }} m</strong></div>
                        <div><span>AEB 介入</span><strong>{{ item.result.metrics.aeb_activation_sec == null ? '--' : item.result.metrics.aeb_activation_sec + 's' }}</strong></div>
                    </div>
                </article>
            </div>
        </section>
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
        return { allItems: [], viewItem: null, modalVideoPlaying: false, modalVideoProgress: 0 }
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
        toggleModalVideo() {
            var video = document.querySelector('.ph-modal-video')
            if (!video) return
            if (video.paused) {
                video.play()
                this.modalVideoPlaying = true
            } else {
                video.pause()
                this.modalVideoPlaying = false
            }
        },
        onModalVideoPlay() { this.modalVideoPlaying = true },
        onModalVideoPause() { this.modalVideoPlaying = false },
        onModalVideoEnded() { this.modalVideoPlaying = false; this.modalVideoProgress = 0 },
        onModalVideoTimeUpdate() {
            var video = document.querySelector('.ph-modal-video')
            if (video && video.duration) {
                this.modalVideoProgress = (video.currentTime / video.duration) * 100
            }
        },
        seekModalVideo(e) {
            var video = document.querySelector('.ph-modal-video')
            if (!video || !video.duration) return
            var bar = e.currentTarget
            var rect = bar.getBoundingClientRect()
            var ratio = (e.clientX - rect.left) / rect.width
            video.currentTime = ratio * video.duration
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
                            <video :src="item.result_video + '#t=0.5'" muted preload="metadata"></video>
                            <div class="ph-play-icon">?</div>
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
                    <div v-else-if="isVideo(viewItem) && viewItem.result_video" class="ph-modal-video-wrap" @click="toggleModalVideo">
                        <video :src="viewItem.result_video" class="ph-modal-media ph-modal-video" @play="onModalVideoPlay" @pause="onModalVideoPause" @ended="onModalVideoEnded" @timeupdate="onModalVideoTimeUpdate"></video>
                        <div class="ph-modal-play-btn" v-if="!modalVideoPlaying">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="white"><polygon points="6 3 20 12 6 21 6 3"/></svg>
                        </div>
                        <div class="ph-modal-progress-bar" @click.stop="seekModalVideo">
                            <div class="ph-modal-progress-fill" :style="{ width: modalVideoProgress + '%' }"></div>
                        </div>
                    </div>
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
    LaneInsightPanel,
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
