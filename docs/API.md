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

用于前端确认后端服务是否在线。

## 2. 当前模型信息

```http
GET /api/models/current
```

用于展示当前模型文件、模型是否存在、支持的检测类别。

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

成功返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "type": "image",
    "original_filename": "road_001.jpg",
    "filename": "a1b2c3.jpg",
    "upload_path": "uploads/a1b2c3.jpg",
    "result_filename": "a1b2c3_result.jpg",
    "result_path": "results/a1b2c3_result.jpg",
    "model_name": "yolov8s",
    "confidence": 0.5,
    "confidence_threshold": 0.5,
    "image_width": 1280,
    "image_height": 720,
    "count": 1,
    "total_objects": 1,
    "max_risk_level": "high",
    "risk_counts": {
      "low": 0,
      "info": 0,
      "medium": 0,
      "high": 1
    },
    "inference_time_ms": 85.2,
    "detections": [
      {
        "class_name": "person",
        "class_name_cn": "行人",
        "confidence": 0.8765,
        "bbox": [520, 360, 650, 700],
        "bbox_area": 44200,
        "center_x": 585,
        "center_y": 530,
        "area_ratio": 0.04796,
        "risk_level": "high",
        "risk_message": "高风险：前方中央区域检测到行人",
        "risk_reason": "检测到 person，且目标中心位于画面下半部分的中央区域",
        "risk": {
          "level": "high",
          "message": "高风险：前方中央区域检测到行人",
          "reason": "检测到 person，且目标中心位于画面下半部分的中央区域"
        }
      }
    ]
  }
}
```

## 4. 视频目标检测

```http
POST /api/detections/videos
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | 待检测道路视频 |

说明：当前接口用于保留上传流程，返回 `501`，后续接入逐帧检测、结果视频生成和视频风险日志。

## 5. 检测历史

```http
GET /api/detections/history
```

返回最近 50 条检测记录，便于前端展示历史检测列表。
