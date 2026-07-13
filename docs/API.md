# 后端接口说明

后端基础地址：

```text
http://127.0.0.1:5000
```

统一返回格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

`code = 0` 表示成功，其他值表示失败。失败时前端可以直接展示 `message`。

## 1. 健康检查

```http
GET /api/health
```

用于确认后端服务是否在线。

## 2. 当前模型信息

```http
GET /api/models/current
```

用于展示当前模型路径、模型文件是否存在、推理模式、输入尺寸和运行设备。

## 3. 用户认证接口

### 注册

```http
POST /api/auth/register
Content-Type: application/json
```

```json
{
  "username": "user001",
  "email": "user001@example.com",
  "password": "123456"
}
```

### 登录

```http
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "username": "user001",
  "password": "123456"
}
```

### 个人信息

```http
GET /api/auth/profile/<username>
PUT /api/auth/profile/<username>
```

用于查询和修改普通用户个人资料。

## 4. 管理员接口

### 管理员登录

```http
POST /api/admin/login
```

### 用户管理

```http
GET    /api/admin/users
POST   /api/admin/users
PUT    /api/admin/users/<username>
DELETE /api/admin/users/<username>
```

支持管理员创建用户、编辑用户邮箱或密码、禁用/启用用户、删除用户。

### 检测记录管理

```http
GET    /api/admin/records
GET    /api/admin/records?username=<username>
GET    /api/admin/records/<record_id>
DELETE /api/admin/records/<record_id>
```

管理员可查看所有用户检测记录，也可以按用户名筛选检测记录，并查看或删除单条记录。

### 系统管理

```http
GET  /api/admin/confidence
POST /api/admin/confidence
GET  /api/admin/system-status
GET  /api/admin/error-logs
DELETE /api/admin/error-logs/<log_id>
```

用于置信度阈值设置、系统状态监控和错误日志查看。

## 5. 图片目标检测

```http
POST /api/detections/images
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | 待检测道路图片 |
| confidence | Number | 否 | 置信度阈值，默认 0.5，范围 0 到 1 |
| username | String | 是 | 当前登录用户名，用于关联检测记录 |

成功返回的 `data` 包含上传文件、结果图、模型、图片尺寸、风险统计、车道分析、驾驶建议、演示讲解字段和 `detections` 明细。保存成功时包含 `record_id` 和 `database_saved: true`。

## 6. 视频目标检测

### 同步视频检测

```http
POST /api/detections/videos
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | 待检测道路视频 |
| confidence | Number | 否 | 置信度阈值，默认 0.5，范围 0 到 1 |
| username | String | 是 | 当前登录用户名，用于关联检测记录 |

该接口会在请求内完成视频读取、逐帧检测、结果视频写入、风险汇总、车道趋势分析和检测记录保存。视频较大时建议使用异步任务接口。

### 异步视频检测任务

```http
POST /api/detections/videos/jobs
Content-Type: multipart/form-data
```

请求参数同同步视频检测。接口会立即创建后台任务并返回 `202`。

查询任务状态：

```http
GET /api/detections/videos/jobs/<job_id>
```

运行中返回 `status: "running"`，并持续更新 `progress`、`latest_frame`、`detection_timeline`、`detections`、风险统计和车道分析。完成后返回 `status: "completed"`，完整检测结果位于 `data.result`。

## 7. 检测历史

```http
GET /api/detections/history?username=<username>
```

普通用户按用户名查询自己的检测记录和统计看板：

```json
{
  "items": [],
  "dashboard": {
    "total_records": 0,
    "total_objects": 0,
    "high_risk_records": 0,
    "high_risk_ratio": 0
  }
}
```

清空当前用户在 MySQL 中的检测历史：

```http
POST /api/detections/history/clear
Content-Type: application/json
```

```json
{
  "username": "user001"
}
```

## 8. 检测记录详情

```http
GET /api/detections/records/<record_id>
```

从 MySQL 查询单条检测记录及其目标明细。记录不存在时返回 `404`。

## 9. 风险仿真

```http
GET  /api/simulation/presets
POST /api/simulation/risk
GET  /api/simulation/scenarios
POST /api/simulation/scenarios
DELETE /api/simulation/scenarios/<scenario_id>
```

`/api/simulation/presets` 返回内置场景预设。`/api/simulation/risk` 根据场景、天气、车速、时长、步长和 AEB 开关生成风险时间线、峰值风险、碰撞判断和安全建议。

自定义场景接口用于保存、读取和删除用户配置的仿真场景。

## 10. 数据存储

项目当前使用 MySQL 保存核心业务数据：

- 用户信息：`用户表`
- 检测主记录：`检测记录表`
- 检测目标明细：`检测目标表`
- 风险提示与原因：`风险日志表`

上传文件和检测结果文件保存在本地 `uploads/`、`results/` 目录中，数据库保存对应文件路径。
