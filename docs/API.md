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

## 3. 图片目标检测

```http
POST /api/detections/images
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | 待检测道路图片 |
| confidence | Number | 否 | 置信度阈值，默认 0.5，范围 0 到 1 |

成功返回的 `data` 包含上传文件、结果图、模型、图片尺寸、风险统计、演示讲解字段和 `detections` 明细。数据库保存成功时会额外包含 `record_id` 和 `database_saved: true`。

## 4. 同步视频目标检测

```http
POST /api/detections/videos
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | 待检测道路视频 |
| confidence | Number | 否 | 置信度阈值，默认 0.5，范围 0 到 1 |

该接口会在请求内完成视频读取、逐帧检测、结果视频写入、风险汇总和历史记录保存。视频较大时建议使用异步任务接口。

成功返回的 `data` 主要字段：

```json
{
  "type": "video",
  "original_filename": "road.mp4",
  "filename": "upload.mp4",
  "result_filename": "upload_result.mp4",
  "result_video": "/results/upload_result.mp4",
  "fps": 25,
  "source_frame_count": 300,
  "processed_frame_count": 300,
  "duration_sec": 12,
  "count": 3,
  "max_risk_level": "high",
  "max_risk_score": 88,
  "risk_counts": {
    "low": 1,
    "info": 0,
    "medium": 1,
    "high": 1
  },
  "detections": []
}
```

## 5. 异步视频检测任务

```http
POST /api/detections/videos/jobs
Content-Type: multipart/form-data
```

请求参数同同步视频检测。接口会立即创建后台任务并返回 `202`。

成功返回示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "job_id": "b8f3...",
    "status": "queued",
    "progress": 0,
    "original_filename": "road.mp4",
    "latest_frame": null,
    "detection_timeline": [],
    "detections": [],
    "result": null,
    "error": ""
  }
}
```

查询任务状态：

```http
GET /api/detections/videos/jobs/<job_id>
```

运行中返回 `status: "running"`，并持续更新 `progress`、`latest_frame`、`detection_timeline`、`detections` 和风险统计。完成后返回 `status: "completed"`，完整检测结果位于 `data.result`。

## 6. 检测历史

```http
GET /api/detections/history
```

返回最近检测记录和统计看板：

```json
{
  "items": [],
  "dashboard": {
    "total_records": 0,
    "total_objects": 0,
    "high_risk_records": 0
  }
}
```

清空本地历史：

```http
POST /api/detections/history/clear
```

## 7. 检测记录详情

```http
GET /api/detections/records/<record_id>
```

从 MySQL 查询单条检测记录及其目标明细。记录不存在时返回 `404`。

## 8. 风险仿真

```http
GET /api/simulation/presets
POST /api/simulation/risk
```

`/api/simulation/presets` 返回内置场景预设。`/api/simulation/risk` 根据场景、车速、时长和步长生成风险时间线、峰值风险和安全建议。
