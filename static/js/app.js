const { createApp, ref, reactive } = Vue

const app = createApp({
    setup() {
        const currentFile = ref(null)
        const filePreviewUrl = ref('')
        const fileType = ref('')
        const resultImageUrl = ref('')
        const isDetecting = ref(false)
        const showBadge = ref(false)
        const threshold = ref(0.5)
        const isAdmin = ref(false)

        const stats = reactive({
            totalCount: 0,
            overallRisk: '—',
            riskClass: 'risk-low',
            inferenceTime: '— ms',
            classCounts: {}
        })

        const historyList = ref([])

        function toggleAdmin() {
            isAdmin.value = !isAdmin.value
        }

        function onThresholdChange(val) {
            threshold.value = val
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

            try {
                const formData = new FormData()
                formData.append('file', currentFile.value)
                formData.append('threshold', threshold.value)

                const res = await fetch('/api/detect', {
                    method: 'POST',
                    body: formData
                })
                const data = await res.json()

                resultImageUrl.value = data.result_image || ''
                updateStats(data)
                addHistory(currentFile.value.name, data.overall_risk)

                showBadge.value = true
                setTimeout(() => { showBadge.value = false }, 3000)
            } catch (err) {
                console.error(err)
                alert('检测失败，请检查后端服务')
            } finally {
                isDetecting.value = false
            }
        }

        function updateStats(data) {
            const total = Object.values(data.total_counts).reduce((a, b) => a + b, 0)
            stats.totalCount = total
            stats.overallRisk = data.overall_risk
            stats.riskClass = data.overall_risk.includes('高') ? 'risk-high'
                : data.overall_risk.includes('中') ? 'risk-medium' : 'risk-low'
            stats.inferenceTime = data.inference_time + ' ms'
            stats.classCounts = data.class_counts
        }

        function addHistory(filename, risk) {
            const now = new Date().toLocaleString()
            historyList.value.unshift({ time: now, filename, risk })
            if (historyList.value.length > 10) historyList.value.pop()
        }

        function onDownloadLog() {
            window.open('/api/download_log', '_blank')
        }

        return {
            currentFile, filePreviewUrl, fileType, resultImageUrl,
            isDetecting, showBadge, threshold, isAdmin, stats, historyList,
            toggleAdmin, onThresholdChange, onFileSelected, onClear, onDetect, onDownloadLog
        }
    }
})

const { AppHeader, ControlPanel, DisplayArea, StatsGrid, HistoryPanel } = window.AppComponents
app.component('app-header', AppHeader)
app.component('control-panel', ControlPanel)
app.component('display-area', DisplayArea)
app.component('stats-grid', StatsGrid)
app.component('history-panel', HistoryPanel)

app.mount('#app')