# YOLOv8 自动驾驶场景感知与风险分析系统

这是一个面向实训演示的 Flask + Vue + YOLOv8 项目，支持道路图片检测、视频逐帧检测、驾驶风险评估、检测历史统计、可解释算法展示和 2D 风险仿真。

## 功能

- 图片目标检测：识别车辆、行人、两轮车、交通灯、停止标志等道路目标。
- 视频目标检测：支持同步视频检测，也支持异步任务轮询，生成带标注的视频结果和逐帧检测时间线。
- 风险分析：结合目标类别、置信度、画面位置、自车行驶走廊重叠度和距离估计进行风险评分。
- 展示面板：展示检测结果、风险明细、安全建议、算法决策链、统计看板和 HTML 报告。
- 风险仿真：提供行人横穿、前车急停、两轮车并线、红灯路口等 2D 场景预设。
- 历史记录：优先读取 MySQL 检测记录，数据库不可用时回退到本地 JSON 历史。

## 项目结构

```text
yolov8-driving-perception/
├─ app.py
├─ detect.py
├─ risk.py
├─ utils.py
├─ requirements.txt
├─ backend/
│  ├─ app.py
│  ├─ api_contract.py
│  ├─ config.py
│  ├─ routes/
│  │  ├─ detections.py
│  │  ├─ health.py
│  │  ├─ models.py
│  │  └─ simulation.py
│  └─ services/
│     ├─ database_service.py
│     ├─ detection_service.py
│     ├─ demo_analysis_service.py
│     ├─ history_service.py
│     ├─ model_service.py
│     ├─ result_renderer.py
│     ├─ simulation_service.py
│     └─ video_job_service.py
├─ templates/
├─ static/
├─ uploads/
├─ results/
├─ logs/
├─ models/
└─ tests/
```

## 运行

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

访问：

```text
http://127.0.0.1:5000
```

## 模型文件

默认模型路径：

```text
models/yolov8s.pt
```

模型权重文件较大，已在 `.gitignore` 中排除。新环境运行前请自行下载或放入同名模型文件。

## 常用接口

```http
GET  /api/health
GET  /api/models/current
POST /api/detections/images
POST /api/detections/videos
POST /api/detections/videos/jobs
GET  /api/detections/videos/jobs/<job_id>
GET  /api/detections/history
POST /api/detections/history/clear
GET  /api/detections/records/<record_id>
GET  /api/simulation/presets
POST /api/simulation/risk
```

统一响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

## 验证

```powershell
python -m unittest discover -s tests
node --check static\js\components.js
node --check static\js\app.js
```

## GitHub 入库说明

以下内容不会提交到仓库：

- `.venv/`
- `.env`
- `uploads/*`
- `results/*`
- `logs/*`
- `models/*.pt`
- Python/Node 缓存和构建产物

目录中的 `.gitkeep` 用于保留运行所需空目录。
