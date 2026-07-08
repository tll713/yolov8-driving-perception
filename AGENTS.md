# AGENTS.md

## 项目定位
这是一个基于 Flask + YOLOv8 的自动驾驶场景感知 Demo，核心目标是完成图片检测、风险判断、结果展示与历史记录管理。

主要入口：
- [app.py](app.py)：应用启动入口
- [backend/app.py](backend/app.py)：Flask 应用与蓝图注册
- [backend/routes](backend/routes)：API 路由层
- [backend/services](backend/services)：检测、数据库、历史记录等业务逻辑
- [detect.py](detect.py)、[risk.py](risk.py)、[utils.py](utils.py)：检测与风险处理核心逻辑
- [tests](tests)：接口与服务测试

## 约定优先级
在本仓库中，优先遵循以下工作原则：

1. 先想再写：编码前先梳理需求、数据流和假设；有歧义时主动确认，避免直接猜测。
2. 简洁优先：优先用最小改动完成目标，不引入多余功能、冗余抽象或复杂写法。
3. 精准改动：只修改与当前需求直接相关的代码，尽量避免顺手重构无关部分。
4. 目标驱动：始终围绕业务核心目标推进，明确验证标准，避免偏离需求。

## 代码风格与结构
- 路由层尽量保持薄：接收请求、参数校验和统一返回，核心逻辑放进 service。
- 修改检测流程时，优先保持现有接口返回结构稳定，尤其是字段如 `type`、`original_filename`、`confidence`、`detections`、`risk` 等。
- 新增功能时优先复用现有服务模块，而不是在路由里直接堆逻辑。
- 涉及文件路径时，优先使用仓库内现有目录：uploads、results、logs、models。

## 关键注意点
- 检测接口依赖 YOLOv8 模型文件，默认路径在 [models/yolov8s.pt](models/yolov8s.pt)。
- 数据持久化与历史记录逻辑位于 [backend/services/database_service.py](backend/services/database_service.py) 和 [backend/services/history_service.py](backend/services/history_service.py)。
- 修改 API 行为时，最好同步检查 [backend/api_contract.py](backend/api_contract.py) 与相关测试。
- 若改动数据库相关逻辑，需要注意 MySQL 配置来自环境变量，避免引入不必要的硬编码。

## 验证建议
在完成改动后，优先用相关测试或最小复现方式验证结果。常见验证入口包括：
- [tests/test_detection_service.py](tests/test_detection_service.py)
- [tests/test_api_contract.py](tests/test_api_contract.py)
- [tests/test_database_service.py](tests/test_database_service.py)

如果改动较大，建议先跑相关测试，再做最小回归检查，避免“看起来对，但实际破坏了现有行为”。
