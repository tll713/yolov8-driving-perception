(() => {
const { createApp, reactive, onMounted, ref } = Vue

const app = createApp({
    setup() {
        const activeTab = ref('detect')
        const currentFile = ref(null)
        const filePreviewUrl = ref('')
        const fileType = ref('')
        const detections = ref([])
        const detectionTimeline = ref([])
        const resultVideoUrl = ref('')
        const resultImageUrl = ref('')
        const isDetecting = ref(false)
        const showBadge = ref(false)
        const confidence = ref(null)
        const healthStatus = ref(null)
        const modelInfo = ref(null)
        const safetyAdvice = ref([])
        const sceneSummary = ref(null)
        const laneAnalysis = ref(null)
        const decisionTrace = ref([])
        const demoScript = ref([])
        const dashboard = ref({})
        const simulationPresets = ref([])
        const simulationCustomScenarios = ref([])
        const simulationWeatherOptions = ref([])
        const simulationScenario = ref('pedestrian_crossing')
        const simulationWeather = ref('clear')
        const simulationSpeed = ref(35)
        const simulationDuration = ref(5)
        const simulationResult = ref(null)
        const simulationComparisonResult = ref(null)
        const isSimulating = ref(false)
        const maxRiskLevel = ref('')
        const isComparingSimulation = ref(false)
        const currentUser = ref(localStorage.getItem('currentUser') || '')
        const showLoginModal = ref(false)
        const detectionRequestId = ref(0)
        const pollTimerId = ref(null)

        const stats = reactive({
            totalCount: 0,
            overallRisk: '-',
            riskClass: 'risk-low',
            inferenceTime: '- ms',
            classCounts: {},
            riskCounts: { low: 0, info: 0, medium: 0, high: 0 },

        })

        const historyList = ref([])

        onMounted(async () => {
            await fetchHealth()
            await fetchModelInfo()
            await fetchHistory()
            await fetchSimulationPresets()
            await fetchSimulationScenarios()
            await runSimulation()
        })

        async function fetchHealth() {
            try {
                const res = await authFetch('/api/health')
                const json = await res.json()
                if (json.code === 0) healthStatus.value = json.data
            } catch { healthStatus.value = null }
        }

        async function fetchModelInfo() {
            try {
                const res = await authFetch('/api/models/current')
                const json = await res.json()
                if (json.code === 0) modelInfo.value = json.data
            } catch { modelInfo.value = null }
        }

        async function fetchHistory() {
            try {
                const userQuery = currentUser.value ? `?username=${encodeURIComponent(currentUser.value)}` : ''
                const res = await authFetch('/api/detections/history' + userQuery)
                const json = await res.json()
                if (json.code === 0) {
                    dashboard.value = json.data.dashboard || {}
                    historyList.value = (json.data.items || []).map(item => ({
                        created_at: item.created_at || '',
                        filename: item.filename || item.original_filename || '',
                        count: item.count || item.total_objects || 0,
                        inference_time_ms: item.inference_time_ms || '',
                        overall_risk: item.max_risk_level || computeOverallRisk(item.detections || []),
                    }))
                }
            } catch { historyList.value = [] }
        }

        async function fetchSimulationPresets() {
            try {
                const res = await authFetch('/api/simulation/presets')
                const json = await res.json()
                if (json.code === 0) {
                    simulationPresets.value = json.data.items || []
                    simulationWeatherOptions.value = json.data.weather_options || []
                }
            } catch { simulationPresets.value = [] }
        }

        async function fetchSimulationScenarios() {
            try {
                const res = await authFetch('/api/simulation/scenarios')
                const json = await res.json()
                simulationCustomScenarios.value = json.code === 0 ? (json.data.items || []) : []
            } catch { simulationCustomScenarios.value = [] }
        }

        function computeOverallRisk(detList) {
            const levels = detList.map(d => d.risk?.level || d.risk_level || 'low')
            if (levels.includes('high')) return 'high'
            if (levels.includes('medium')) return 'medium'
            if (levels.includes('info')) return 'info'
            return 'low'
        }

        function currentOperator() {
            return currentUser.value || localStorage.getItem('currentUser') || ''
        }

        function withUsername(url) {
            const username = currentOperator()
            if (!url || !username) return url || ''
            const joiner = url.indexOf('?') === -1 ? '?' : '&'
            return `${url}${joiner}username=${encodeURIComponent(username)}`
        }

        function authFetch(url, options) {
            const nextOptions = Object.assign({}, options || {})
            const headers = new Headers(nextOptions.headers || {})
            const username = currentOperator()
            if (username && !headers.has('X-Username')) {
                headers.set('X-Username', username)
            }
            nextOptions.headers = headers
            return fetch(url, nextOptions)
        }

        function onFileSelected(file) {
            const MAX_SIZE = 200 * 1024 * 1024
            const isVideo = file.type && file.type.startsWith('video/')
            if (isVideo && file.size > MAX_SIZE) {
                const sizeMB = (file.size / 1024 / 1024).toFixed(1)
                alert('视频文件大小为 ' + sizeMB + 'MB，超过 200MB 限制，请压缩后重新上传')
                return
            }
            const requestId = ++detectionRequestId.value
            currentFile.value = file
            filePreviewUrl.value = ''
            fileType.value = ''
            resetDetectionResults()
            const reader = new FileReader()
            reader.onload = async (e) => {
                if (requestId !== detectionRequestId.value) return
                filePreviewUrl.value = e.target.result
                fileType.value = file.type
                await onDetect(requestId)
            }
            reader.readAsDataURL(file)
        }

        function resetStats() {
            stats.totalCount = 0
            stats.overallRisk = '-'
            stats.riskClass = 'risk-low'
            stats.inferenceTime = '- ms'
            stats.classCounts = {}
            stats.riskCounts = { low: 0, info: 0, medium: 0, high: 0 }

        }

        function resetDetectionResults() {
            stopVideoPolling()
            isDetecting.value = false
            detections.value = []
            detectionTimeline.value = []
            resultVideoUrl.value = ''
            resultImageUrl.value = ''
            maxRiskLevel.value = ''
            stats.totalCount = 0
            stats.overallRisk = '—'
            stats.riskClass = 'risk-low'
            stats.inferenceTime = '— ms'
            stats.classCounts = {}
            stats.riskCounts = { low: 0, info: 0, medium: 0, high: 0 }
            safetyAdvice.value = []
            sceneSummary.value = null
            laneAnalysis.value = null
            decisionTrace.value = []
            demoScript.value = []
            confidence.value = null
            showBadge.value = false
            resetStats()
        }

        function onClear() {
            ++detectionRequestId.value
            currentFile.value = null
            filePreviewUrl.value = ''
            fileType.value = ''
            resetDetectionResults()
        }

        async function onDetect(requestId = ++detectionRequestId.value) {
            if (!currentFile.value) return
            isDetecting.value = true
            detections.value = []
            detectionTimeline.value = []
            resultVideoUrl.value = ''
            resultImageUrl.value = ''

            const isImage = fileType.value.startsWith('image/')
            if (!isImage) {
                await startVideoDetectionJob(requestId)
                return
            }

            try {
                const formData = new FormData()
                formData.append('file', currentFile.value)
                formData.append('confidence', 0.5)
                formData.append('username', currentUser.value || '')

                const res = await authFetch('/api/detections/images', { method: 'POST', body: formData })
                const json = await res.json()

                if (requestId !== detectionRequestId.value) return

                if (json.code !== 0) {
                    alert(json.message || '检测失败')
                    return
                }

                const data = json.data
                applyDetectionResult(data, true)
                await fetchHistory()

                showBadge.value = true
                setTimeout(() => { showBadge.value = false }, 3000)
            } catch (err) {
                if (requestId !== detectionRequestId.value) return
                console.error(err)
                alert('检测失败，请检查后端服务是否启动')
            } finally {
                if (requestId === detectionRequestId.value) {
                    isDetecting.value = false
                }
            }
        }

        async function startVideoDetectionJob(requestId) {
            try {
                const formData = new FormData()
                formData.append('file', currentFile.value)
                formData.append('confidence', 0.5)
                formData.append('username', currentUser.value || '')

                const res = await authFetch('/api/detections/videos/jobs', { method: 'POST', body: formData })
                const json = await res.json()

                if (requestId !== detectionRequestId.value) return

                if (json.code !== 0) {
                    alert(json.message || '视频检测任务创建失败')
                    isDetecting.value = false
                    return
                }

                await pollVideoDetectionJob(json.data.job_id, requestId)
            } catch (err) {
                if (requestId !== detectionRequestId.value) return
                console.error(err)
                alert('视频检测任务创建失败，请检查后端服务是否启动')
                isDetecting.value = false
            }
        }

        async function pollVideoDetectionJob(jobId, requestId) {
            stopVideoPolling()

            const fetchJob = async () => {
                if (requestId !== detectionRequestId.value) {
                    stopVideoPolling()
                    return false
                }

                try {
                    const res = await authFetch(`/api/detections/videos/jobs/${jobId}`)
                    const json = await res.json()
                    if (json.code !== 0) {
                        throw new Error(json.message || '视频检测任务查询失败')
                    }

                    const data = json.data
                    detectionTimeline.value = data.detection_timeline || []
                    applyDetectionResult(data, false)

                    if (data.status === 'completed') {
                        stopVideoPolling()
                        applyDetectionResult(data.result || data, false)
                        await fetchHistory()
                        showBadge.value = true
                        setTimeout(() => { showBadge.value = false }, 3000)
                        isDetecting.value = false
                        return false
                    } else if (data.status === 'failed') {
                        stopVideoPolling()
                        alert(data.error || '视频检测任务失败')
                        isDetecting.value = false
                        return false
                    }
                    return true
                } catch (err) {
                    stopVideoPolling()
                    if (requestId !== detectionRequestId.value) return false
                    console.error(err)
                    alert('视频检测任务查询失败，请检查后端服务是否启动')
                    isDetecting.value = false
                    return false
                }
            }

            if (await fetchJob()) {
                pollTimerId.value = setInterval(fetchJob, 350)
            }
        }

        function stopVideoPolling() {
            if (pollTimerId.value) {
                clearInterval(pollTimerId.value)
                pollTimerId.value = null
            }
        }

        function applyDetectionResult(data, isImage) {
            resultVideoUrl.value = withUsername(data.result_video || '')
            resultImageUrl.value = isImage && data.result_filename ? withUsername(`/results/${data.result_filename}`) : ''
            detectionTimeline.value = data.detection_timeline || detectionTimeline.value
            detections.value = data.detections || []
            safetyAdvice.value = data.safety_advice || []
            sceneSummary.value = data.scene_summary || null
            laneAnalysis.value = data.lane_analysis || data.latest_frame?.lane_analysis || null
            decisionTrace.value = data.decision_trace || []
            demoScript.value = data.demo_script || []
            updateStats(data, isImage)
        }

        function updateStats(data, isImage) {
            const detList = isImage ? (data.detections || []) : (data.detections || [])
            stats.totalCount = data.count || detList.length
            confidence.value = data.confidence ?? null

            const overallRisk = data.max_risk_level || computeOverallRisk(detList)
            maxRiskLevel.value = overallRisk
            const riskInfo = window.RISK_STYLE_MAP[overallRisk] || window.RISK_STYLE_MAP.low
            stats.overallRisk = riskInfo.label
            stats.riskClass = riskInfo.cls

            stats.inferenceTime = data.inference_time_ms ? `${data.inference_time_ms} ms` : '— ms'
            stats.inferenceTime = data.inference_time_ms ? `${data.inference_time_ms} ms` : '- ms'
            stats.riskCounts = data.risk_counts || summarizeRiskCounts(detList)


            const counts = {}
            detList.forEach(d => {
                const cls = d.class_name_cn || d.class_name || 'unknown'
                counts[cls] = (counts[cls] || 0) + 1
            })
            stats.classCounts = counts
        }

        function summarizeRiskCounts(detList) {
            const counts = { low: 0, info: 0, medium: 0, high: 0 }
            detList.forEach(d => {
                const level = d.risk?.level || d.risk_level || 'low'
                counts[level] = (counts[level] || 0) + 1
            })
            return counts
        }



        async function onDownloadLog() {
            try {
                const userQuery = currentUser.value ? `?username=${encodeURIComponent(currentUser.value)}` : ''
                const res = await authFetch('/api/detections/history' + userQuery)
                const json = await res.json()
                if (json.code !== 0 || !json.data.items?.length) {
                    alert('暂无历史记录可导出')
                    return
                }
                const items = json.data.items
                const dashboard = json.data.dashboard || {}
                const riskMap = { high: '高风险', medium: '中风险', info: '交通提示', low: '低风险' }
                function overallRisk(dets) {
                    const levels = (dets || []).map(d => d.risk?.level || d.risk_level || 'low')
                    if (levels.includes('high')) return 'high'
                    if (levels.includes('medium')) return 'medium'
                    if (levels.includes('info')) return 'info'
                    return 'low'
                }
                const rows = items.map((item, i) => {
                    const risk = item.max_risk_level || overallRisk(item.detections)
                    const detRows = (item.detections || []).map(d => `<tr>
                        <td>${d.class_name_cn || d.class_name || '-'}</td>
                        <td>${((d.confidence || 0) * 100).toFixed(1)}%</td>
                        <td>${riskMap[d.risk?.level || d.risk_level || 'low'] || '-'}</td>
                        <td>${d.risk?.message || d.risk_message || '-'}</td>
                    </tr>`).join('')
                    return `<tr>
                        <td>${i + 1}</td>
                        <td>${item.created_at || '-'}</td>
                        <td>${item.original_filename || item.filename || '-'}</td>
                        <td>${item.count || item.total_objects || 0}</td>
                        <td>${riskMap[risk] || '-'}</td>
                        <td>${item.inference_time_ms || '-'} ms</td>
                        <td>${item.confidence != null ? item.confidence.toFixed(2) : '-'}</td>
                    </tr>
                    ${detRows ? `<tr><td colspan="7" style="padding:0;"><table style="width:100%;border:1px solid #e5e7eb;margin:4px 0;"><thead><tr><th>类别</th><th>置信度</th><th>风险</th><th>说明</th></tr></thead><tbody>${detRows}</tbody></table></td></tr>` : ''}`
                }).join('')
                const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>检测历史记录</title>
                <style>body{font-family:Arial,"Microsoft YaHei",sans-serif;padding:32px;color:#111827;}
                h1{margin-bottom:4px;} .meta{color:#6b7280;font-size:14px;margin-bottom:20px;}
                .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0;}
                .card{border:1px solid #d1d5db;padding:14px;border-radius:8px;}
                .card span{display:block;color:#6b7280;font-size:12px;} .card strong{font-size:20px;}
                table{width:100%;border-collapse:collapse;margin-top:16px;}
                th,td{border:1px solid #d1d5db;padding:8px;text-align:left;font-size:13px;}
                th{background:#f3f4f6;}</style></head>
                <body><h1>自动驾驶场景风险感知 - 检测历史记录</h1>
                <div class="meta">导出时间：${new Date().toLocaleString('zh-CN')}</div>
                <div class="cards">
                    <div class="card"><span>检测次数</span><strong>${dashboard.total_records || items.length}</strong></div>
                    <div class="card"><span>累计目标</span><strong>${dashboard.total_objects || 0}</strong></div>
                    <div class="card"><span>高风险占比</span><strong>${Math.round((dashboard.high_risk_ratio || 0) * 100)}%</strong></div>
                </div>
                <table><thead><tr><th>#</th><th>时间</th><th>文件</th><th>目标数</th><th>风险</th><th>耗时</th><th>置信度</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="7">暂无记录</td></tr>'}</tbody></table>
                </body></html>`
                const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
                const link = document.createElement('a')
                link.download = '检测历史记录.html'
                link.href = URL.createObjectURL(blob)
                link.click()
                URL.revokeObjectURL(link.href)
            } catch {
                alert('导出失败，请检查后端服务')
            }
        }

        async function onClearHistory() {
            await authFetch('/api/detections/history/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: currentUser.value || '' }),
            })
            await fetchHistory()
        }

        function onSimulationScenarioChange(value) {
            simulationScenario.value = value
            simulationComparisonResult.value = null
            const preset = [...simulationPresets.value, ...simulationCustomScenarios.value]
                .find(item => item.key === value)
            if (preset) {
                simulationSpeed.value = preset.ego_speed_kmh
                simulationDuration.value = preset.duration_sec
                simulationWeather.value = preset.weather || 'clear'
            }
        }

        function simulationPayload(autoBrake = true) {
            const customScenario = simulationCustomScenarios.value.find(
                item => item.key === simulationScenario.value
            )
            return {
                ...(customScenario || {}),
                scenario: simulationScenario.value,
                weather: simulationWeather.value,
                ego_speed_kmh: Number(simulationSpeed.value),
                duration_sec: Number(simulationDuration.value),
                step_sec: Number(customScenario?.step_sec || 0.25),
                auto_brake: autoBrake,
            }
        }

        async function requestSimulation(payload) {
            const res = await authFetch('/api/simulation/risk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            const json = await res.json()
            if (json.code !== 0) throw new Error(json.message || '仿真计算失败')
            return json.data
        }

        async function runSimulation() {
            isSimulating.value = true
            try {
                simulationResult.value = await requestSimulation(simulationPayload(true))
                simulationComparisonResult.value = null
            } catch (err) {
                console.error(err)
                alert(err.message || '仿真计算失败，请检查后端服务是否启动')
            } finally {
                isSimulating.value = false
            }
        }

        async function compareSimulationAeb() {
            isComparingSimulation.value = true
            try {
                const [withAeb, withoutAeb] = await Promise.all([
                    requestSimulation(simulationPayload(true)),
                    requestSimulation(simulationPayload(false)),
                ])
                simulationComparisonResult.value = { withAeb, withoutAeb }
            } catch (err) {
                console.error(err)
                alert(err.message || '对比仿真失败')
            } finally {
                isComparingSimulation.value = false
            }
        }

        async function saveSimulationScenario(scenario) {
            try {
                const res = await authFetch('/api/simulation/scenarios', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(scenario),
                })
                const json = await res.json()
                if (json.code !== 0) throw new Error(json.message || '场景保存失败')
                await fetchSimulationScenarios()
                onSimulationScenarioChange(json.data.key)
            } catch (err) {
                console.error(err)
                alert(err.message || '场景保存失败')
            }
        }

        async function deleteSimulationScenario(scenarioId) {
            if (!scenarioId || !confirm('确定删除这个自定义场景吗？')) return
            try {
                const res = await authFetch(`/api/simulation/scenarios/${encodeURIComponent(scenarioId)}`, {
                    method: 'DELETE',
                })
                const json = await res.json()
                if (json.code !== 0) throw new Error(json.message || '场景删除失败')
                await fetchSimulationScenarios()
                onSimulationScenarioChange('pedestrian_crossing')
                await runSimulation()
            } catch (err) {
                console.error(err)
                alert(err.message || '场景删除失败')
            }
        }



        function onRequireLogin() { showLoginModal.value = true }
        function closeLoginModal() { showLoginModal.value = false }
        function goToLogin() { window.location.href = '/login' }

        return {
            activeTab,
            currentFile, filePreviewUrl, fileType, detections, detectionTimeline, resultVideoUrl, resultImageUrl,
            isDetecting, showBadge, confidence, maxRiskLevel,
            healthStatus, modelInfo, stats, historyList, safetyAdvice, dashboard,
            sceneSummary, laneAnalysis, decisionTrace, demoScript, currentUser, showLoginModal,
            simulationPresets, simulationCustomScenarios, simulationWeatherOptions, simulationScenario, simulationWeather,
            simulationSpeed, simulationDuration,
            simulationResult, simulationComparisonResult, isSimulating, isComparingSimulation,
            onFileSelected, onClear, onDetect, onDownloadLog, onClearHistory,
            onSimulationScenarioChange, runSimulation, compareSimulationAeb,
            saveSimulationScenario, deleteSimulationScenario,
            onRequireLogin, closeLoginModal, goToLogin
        }
    }
})

app.component('app-header', window.AppComponents.AppHeader)
app.component('control-panel', window.AppComponents.ControlPanel)
app.component('display-area', window.AppComponents.DisplayArea)
app.component('lane-insight-panel', window.AppComponents.LaneInsightPanel)
app.component('stats-grid', window.AppComponents.StatsGrid)
app.component('risk-analysis-panel', window.AppComponents.RiskAnalysisPanel)
app.component('safety-advice-panel', window.AppComponents.SafetyAdvicePanel)
app.component('scene-insight-panel', window.AppComponents.SceneInsightPanel)

app.component('simulation-panel', window.AppComponents.SimulationPanel)
app.component('dashboard-panel', window.AppComponents.DashboardPanel)

app.component('history-panel', window.AppComponents.HistoryPanel)

if (!localStorage.getItem('currentUser')) {
    window.location.href = '/login'
} else {
    app.mount('#app')
}
})()
