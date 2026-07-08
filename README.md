# YOLOv8 自动驾驶场景感知与风险分析系统

这是一个面向实训演示的 Flask + Vue + YOLOv8 项目，支持道路图片/视频目标检测、驾驶风险评估、检测历史统计、可解释算法展示和 2D 风险仿真。

## 功能

- 图片目标检测：车辆、行人、两轮车、交通灯、停止标志等。
- 视频关键帧检测：抽取关键帧，返回每帧标注图和视频级风险汇总。
- 风险分析：结合目标类别、置信度、距离估计、自车行驶路径重叠度进行风险评分。
- 展示面板：检测结果、风险明细、安全建议、算法决策链、统计看板、HTML 报告。
- 风险仿真：行人横穿、前车急停、两轮车并线、红灯路口等 2D 场景预设。
- 历史记录：本地 JSON 历史记录，支持清空和导出。

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
│     ├─ detection_service.py
│     ├─ demo_analysis_service.py
│     ├─ history_service.py
│     ├─ model_service.py
│     ├─ result_renderer.py
│     └─ simulation_service.py
├─ templates/index.html
├─ static/
│  ├─ css/style.css
│  └─ js/
│     ├─ vue.global.prod.js
│     ├─ components.js
│     └─ app.js
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

模型权重文件较大，已在 `.gitignore` 中排除，不会进入 GitHub。新环境运行前请自行下载或放入同名模型文件。

## 常用接口

```http
GET  /api/health
GET  /api/models/current
POST /api/detections/images
POST /api/detections/videos
GET  /api/detections/history
POST /api/detections/history/clear
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
