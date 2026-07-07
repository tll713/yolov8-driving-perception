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

## 1. 健康检查

```http
GET /api/health
```

用途：前端启动后检测后端服务是否在线。

## 2. 查询当前模型信息

```http
GET /api/models/current
```

用途：展示当前模型文件、模型是否存在、支持检测类别。

## 3. 图片目标检测

```http
POST /api/detections/images
Content-Type: multipart/form-data
```

请求参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| file | File | 是 | 待检测道路图片 |
| confidence | Number | 否 | 置信度阈值，默认 0.5 |

成功返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "type": "image",
    "filename": "xxx.jpg",
    "confidence": 0.5,
    "count": 1,
    "detections": [
      {
        "class_name": "person",
        "confidence": 0.86,
        "bbox": [420, 360, 560, 700],
        "risk": {
          "level": "high",
          "message": "高风险：前方中央区域检测到行人"
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

说明：该接口已预留，当前用于前端联调上传流程。后续接入逐帧检测、结果视频生成和视频风险日志。

## 5. 查看检测历史

```http
GET /api/detections/history
```

用途：获取最近检测记录，用于前端历史记录列表。

## Vue 对接建议

建议前端封装一个 `api` 模块：

```js
const BASE_URL = 'http://127.0.0.1:5000'

export async function detectImage(file, confidence = 0.5) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('confidence', confidence)

  const response = await fetch(`${BASE_URL}/api/detections/images`, {
    method: 'POST',
    body: formData
  })

  return response.json()
}
```
