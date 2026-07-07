# 基于 YOLOv8 的自动驾驶场景目标检测与风险提示系统

本项目是一个面向实训的道路视觉感知系统，使用 YOLOv8 检测道路场景中的车辆、行人、骑行者、交通信号灯等目标，并根据目标类别、位置和检测框大小给出风险提示。

## 项目意义

如果只做目标检测，项目容易停留在普通 Demo。这里增加了风险等级判断、目标统计和结果展示，使系统更接近自动驾驶辅助感知场景，可用于模拟驾驶安全预警、道路监控分析和实训答辩展示。

## 核心功能

- 图片目标检测
- 目标类别、置信度、检测框输出
- 风险等级判断：低风险、中风险、高风险、交通信息
- Web 页面上传和结果展示
- 上传文件、结果文件、日志目录预留

## 技术栈

- Python
- Flask
- OpenCV
- YOLOv8 / ultralytics
- Vue 作为前端页面框架

## 项目结构

```text
yolov8-driving-perception/
├─ backend/
│  ├─ app.py
│  ├─ api_contract.py
│  ├─ config.py
│  ├─ routes/
│  │  ├─ detections.py
│  │  ├─ health.py
│  │  └─ models.py
│  └─ services/
│     ├─ detection_service.py
│     └─ history_service.py
├─ app.py
├─ detect.py
├─ risk.py
├─ utils.py
├─ requirements.txt
├─ templates/
│  └─ index.html
├─ static/
│  ├─ css/
│  │  └─ style.css
│  └─ js/
│     └─ main.js
├─ uploads/
├─ results/
├─ logs/
├─ models/
├─ docs/
└─ tests/
```

## 运行步骤

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

启动后访问：

```text
http://127.0.0.1:5000
```

## Vue 前端接口

后端统一使用 JSON 返回，格式如下：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 健康检查

```http
GET /api/health
```

用于确认后端服务是否正常运行。

### 图片检测

```http
POST /api/detections/images
Content-Type: multipart/form-data
```

参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | 道路场景图片 |
| confidence | Number | 否 | 置信度阈值，默认 0.5，范围 0-1 |

返回内容包含文件名、检测数量、目标列表、风险等级和风险提示。

### 视频检测

```http
POST /api/detections/videos
Content-Type: multipart/form-data
```

该接口已预留，当前用于前端联调文件上传流程，后续接入逐帧检测和结果视频生成。

### 历史记录

```http
GET /api/detections/history
```

返回最近检测记录，方便前端展示历史检测列表。

### 当前模型信息

```http
GET /api/models/current
```

返回当前模型路径、模型文件是否存在、支持检测类别等信息。

## 模型说明

默认模型路径为：

```text
models/yolov8s.pt
```

如果本地没有模型，可以后续通过 ultralytics 下载预训练权重，或将训练好的权重放入 `models/` 目录。

## 风险判断规则

系统根据以下因素判断风险：

- 目标类别：行人、骑行者、摩托车优先级更高
- 目标位置：画面中央和下半部分风险更高
- 检测框面积：面积越大，通常表示目标越近
- 交通信息：红绿灯和停止标志作为交通提示

## 后续优化方向

- 支持视频逐帧检测并生成结果视频
- 增加摄像头实时检测
- 增加车道线检测
- 增加红绿灯状态识别
- 增加风险日志保存与可视化统计
- 使用自建道路数据集微调 YOLOv8
