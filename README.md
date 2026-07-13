# YOLOv8 自动驾驶场景感知与仿真系统

这是一个面向软件工程实训的自动驾驶场景感知与仿真系统，基于 Flask + Vue + YOLOv8 实现道路目标检测、风险评估、车道趋势感知、驾驶建议生成、检测历史管理、用户权限管理和第一人称 3D 风险仿真。

系统从早期的道路目标风险分析扩展为完整的场景感知与仿真平台：普通用户可以上传图片或视频进行检测，查看自己的检测历史；管理员可以维护用户、管理检测记录、查看系统状态和调整检测阈值。

## 核心功能

- 用户认证与权限管理：支持用户注册、登录、个人信息维护；管理员可创建、编辑、禁用、启用和删除普通用户。
- 道路目标检测：支持图片检测、同步视频检测和异步视频检测任务，识别车辆、行人、公交车、卡车、摩托车等道路目标。
- 风险评估与预警：根据目标类别、置信度、画面位置、目标面积、行驶区域和距离估计计算低/中/高风险。
- 车道与道路趋势感知：结合车道线和目标分布分析直行、左转、右转、变道或保持观察等驾驶建议。
- 检测历史管理：普通用户只能查看自己的检测记录；管理员可以查看、筛选、详情查看和删除所有用户检测记录。
- MySQL 数据持久化：用户信息、检测记录、检测目标和风险日志统一存储到 MySQL，不再使用本地 JSON 作为业务数据来源。
- 3D 风险仿真：支持预设场景、自定义场景、天气影响、车速调节、风险时间线、倍速回放和 AEB 对比仿真。
- 后台管理系统：提供置信度阈值设置、检测记录管理、系统状态监控、错误日志查看和用户管理。

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
│  │  ├─ admin.py
│  │  ├─ auth.py
│  │  ├─ detections.py
│  │  ├─ health.py
│  │  ├─ models.py
│  │  └─ simulation.py
│  └─ services/
│     ├─ database_service.py
│     ├─ detection_service.py
│     ├─ demo_analysis_service.py
│     ├─ history_service.py
│     ├─ lane_service.py
│     ├─ model_service.py
│     ├─ result_renderer.py
│     ├─ simulation_service.py
│     ├─ user_service.py
│     └─ video_job_service.py
├─ templates/
├─ static/
├─ uploads/
├─ results/
├─ logs/
├─ models/
└─ tests/
```

## 运行环境

- Python 3.13+ / 3.14
- MySQL 8.x
- YOLOv8 / Ultralytics
- Flask
- Vue 3
- OpenCV
- PyTorch

## 配置

复制 `.env.example` 为 `.env`，并填写数据库连接信息：

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=yolov8_driving
USER_STORAGE=mysql
USER_TABLE_NAME=用户表
```

当前项目的用户数据和检测业务数据均使用 MySQL。上传文件和检测结果文件保存在项目本地目录中，MySQL 保存对应文件路径。

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
GET    /api/health
GET    /api/models/current

POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/profile/<username>
PUT    /api/auth/profile/<username>

POST   /api/detections/images
POST   /api/detections/videos
POST   /api/detections/videos/jobs
GET    /api/detections/videos/jobs/<job_id>
GET    /api/detections/history?username=<username>
POST   /api/detections/history/clear
GET    /api/detections/records/<record_id>

POST   /api/admin/login
GET    /api/admin/users
POST   /api/admin/users
PUT    /api/admin/users/<username>
DELETE /api/admin/users/<username>
GET    /api/admin/records
GET    /api/admin/records/<record_id>
DELETE /api/admin/records/<record_id>
GET    /api/admin/system-status

GET    /api/simulation/presets
POST   /api/simulation/risk
GET    /api/simulation/scenarios
POST   /api/simulation/scenarios
DELETE /api/simulation/scenarios/<scenario_id>
```

统一响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

## 数据存储说明

- `用户表`：保存普通用户和管理员账号信息。
- `检测记录表`：保存每次图片或视频检测的主记录。
- `检测目标表`：保存每条检测记录中的目标框、类别、置信度和位置。
- `风险日志表`：保存中高风险目标的风险等级、提示和原因。
- `uploads/`：保存用户上传的原始图片或视频。
- `results/`：保存渲染后的检测结果图片或视频。

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
