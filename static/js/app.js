const { createApp, reactive, onMounted } = Vue

const app = createApp({
    setup() {
        const currentFile = ref(null)
        const filePreviewUrl = ref('')
        const fileType = ref('')
        const detections = ref([])
        const isDetecting = ref(false)
        const showBadge = ref(false)
        const confidence = ref(null)
        const resultVideoUrl = ref('')
        const resultImageUrl = ref('')
        const healthStatus = ref(null)
        const modelInfo = ref(null)

        const currentUser = ref(localStorage.getItem('currentUser') || '')

        const stats = reactive({
            totalCount: 0,
            overallRisk: '—',
            riskClass: 'risk-low',
            inferenceTime: '— ms',
            classCounts: {}
        })

        const historyList = ref([])

        onMounted(async () => {
            await fetchHealth()
            await fetchModelInfo()
            await fetchHistory()
        })

        async function fetchHealth() {
            try {
                const res = await fetch('/api/health')
                const json = await res.json()
                if (json.code === 0) healthStatus.value = json.data
            } catch { healthStatus.value = null }
        }

        async function fetchModelInfo() {
            try {
                const res = await fetch('/api/models/current')
                const json = await res.json()
                if (json.code === 0) modelInfo.value = json.data
            } catch { modelInfo.value = null }
        }

        async function fetchHistory() {
            try {
                const res = await fetch('/api/detections/history')
                const json = await res.json()
                if (json.code === 0) {
                    historyList.value = (json.data.items || []).map(item => ({
                        created_at: item.created_at || '',
                        filename: item.filename || '',
                        count: item.count || 0,
                        overall_risk: computeOverallRisk(item.detections || [])
                    }))
                }
            } catch { historyList.value = [] }
        }

        function computeOverallRisk(detections) {
            const levels = detections.map(d => d.risk?.level || 'low')
            if (levels.includes('high')) return 'high'
            if (levels.includes('medium')) return 'medium'
            return 'low'
        }

        function onFileSelected(file) {
            currentFile.value = file
            const reader = new FileReader()
            reader.onload = (e) => {
                filePreviewUrl.value = e.target.result
                fileType.value = file.type
            }
            reader.readAsDataURL(file)
        }

        function onClear() {
            currentFile.value = null
            filePreviewUrl.value = ''
            fileType.value = ''
            detections.value = []
            confidence.value = null
            resultVideoUrl.value = ''
            resultImageUrl.value = ''
            stats.totalCount = 0
            stats.overallRisk = '—'
            stats.riskClass = 'risk-low'
            stats.inferenceTime = '— ms'
            stats.classCounts = {}
            showBadge.value = false
        }

        async function onDetect() {
            if (!currentFile.value) return
            isDetecting.value = true
            detections.value = []

            const isImage = fileType.value.startsWith('image/')
            const endpoint = isImage ? '/api/detections/images' : '/api/detections/videos'

            try {
                const formData = new FormData()
                formData.append('file', currentFile.value)
                formData.append('confidence', 0.5)

                const res = await fetch(endpoint, { method: 'POST', body: formData })
                const json = await res.json()

                if (json.code !== 0) {
                    alert(json.message || '检测失败')
                    return
                }

                const data = json.data


                detections.value = data.detections || []
                resultVideoUrl.value = data.result_video || ''
                resultImageUrl.value = data.result_path ? '/results/' + (data.result_filename || '') : ''
                updateStats(data)
                await fetchHistory()

                showBadge.value = true
                setTimeout(() => { showBadge.value = false }, 3000)
            } catch (err) {
                console.error(err)
                alert('检测失败，请检查后端服务是否启动')
            } finally {
                isDetecting.value = false
            }
        }

        function updateStats(data) {
            const detList = data.detections || []
            stats.totalCount = data.count || detList.length
            confidence.value = data.confidence ?? null

            const overallRisk = computeOverallRisk(detList)
            const riskInfo = window.RISK_STYLE_MAP[overallRisk] || window.RISK_STYLE_MAP.low
            stats.overallRisk = riskInfo.label
            stats.riskClass = riskInfo.cls

            stats.inferenceTime = data.inference_time_ms ? `${data.inference_time_ms} ms` : '— ms'

            const counts = {}
            detList.forEach(d => {
                const cls = d.class_name || 'unknown'
                counts[cls] = (counts[cls] || 0) + 1
            })
            stats.classCounts = counts
        }

        function onDownloadLog() {
            window.open('/api/detections/history', '_blank')
        }

        return {
            currentFile, filePreviewUrl, fileType, detections,
            isDetecting, showBadge, confidence, resultVideoUrl, resultImageUrl,
            healthStatus, modelInfo, stats, historyList, currentUser,
            onFileSelected, onClear, onDetect, onDownloadLog
        }
    }
})

app.component('app-header', window.AppComponents.AppHeader)
app.component('control-panel', window.AppComponents.ControlPanel)
app.component('display-area', window.AppComponents.DisplayArea)
app.component('stats-grid', window.AppComponents.StatsGrid)
app.component('history-panel', window.AppComponents.HistoryPanel)

app.mount('#app')
