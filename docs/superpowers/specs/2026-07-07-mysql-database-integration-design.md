# MySQL Database Integration Design

## Goal

Connect the YOLOv8 driving perception backend to a MySQL database, using environment variables for credentials and writing each completed image detection into the provided tables.

## Current State

The Flask backend saves uploaded files and keeps recent detection history in `logs/detection_history.json`. Detection output contains `class_name`, `confidence`, `bbox`, and `risk`; the database handoff requires a parent detection record, child detected objects, and risk log rows for medium or high risks.

## Chosen Approach

Use a small MySQL service module, called from `backend/services/detection_service.py` after YOLO inference succeeds. The service inserts one row into `detection_record`, then inserts all object rows into `detected_object`, then inserts `risk_log` rows for `medium` and `high` risks in one transaction. The response keeps the existing fields and adds `record_id` when database persistence succeeds.

## Configuration

Database settings come from `.env`:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=yolov8_driving
```

The checked-in `.env.example` documents the required variables without exposing real secrets.

## Data Mapping

`detection_record` stores upload metadata, model name, confidence threshold, image size, object count, maximum risk level, and inference time. `detected_object` stores class labels, confidence, bbox coordinates, center point, area, risk level, message, and reason. `risk_log` stores only medium and high risk prompts linked to the detection record and detected object.

`dataset_sample` is not written during detection because the handoff document only requires storing uploaded test image or video information there and does not define its exact columns. Keeping it out avoids guessing the schema and breaking inserts.

## Error Handling

Detection remains usable if MySQL is temporarily unavailable. The backend logs the database error, still returns detection results, and keeps the JSON history fallback. History reads from MySQL when available and falls back to the JSON file on database errors.

## Verification

Add unit tests around payload mapping and transaction calls using a fake connection. Run the existing risk/API tests plus the new database service tests with the bundled Python runtime.
