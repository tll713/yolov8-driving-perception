# MySQL Database Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist YOLOv8 image detection records, detected objects, and risk logs into the existing `yolov8_driving` MySQL database.

**Architecture:** Add a focused database service behind the detection flow. Keep the existing JSON history as a fallback so detection still works when MySQL is not reachable.

**Tech Stack:** Flask, PyMySQL, python-dotenv, unittest, YOLOv8 detection output dictionaries.

---

## File Structure

- Create `backend/services/database_service.py`: connection creation, object normalization, MySQL inserts, and MySQL-backed history reads.
- Modify `backend/config.py`: database environment variables.
- Modify `backend/services/detection_service.py`: measure inference time, include image metadata, call database persistence.
- Modify `backend/services/history_service.py`: read MySQL history first, then JSON fallback.
- Modify `requirements.txt`: add `PyMySQL` and `python-dotenv`.
- Create `.env.example`: document database settings.
- Create `tests/test_database_service.py`: verify inserts and risk filtering with fake connection objects.

### Task 1: Configuration And Dependency

**Files:**
- Modify: `backend/config.py`
- Modify: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Add config variables**

Add `load_dotenv()` and the `DB_*` settings in `backend/config.py`.

- [ ] **Step 2: Add dependencies**

Add `PyMySQL>=1.1.0` and `python-dotenv>=1.0.0` to `requirements.txt`.

- [ ] **Step 3: Add `.env.example`**

Document `DB_HOST=127.0.0.1`, `DB_PORT=3306`, `DB_USER=your_db_user`, `DB_PASSWORD=your_db_password`, and `DB_NAME=yolov8_driving`.

### Task 2: Database Service

**Files:**
- Create: `backend/services/database_service.py`
- Test: `tests/test_database_service.py`

- [ ] **Step 1: Write tests**

Test that `save_detection_result()` inserts one detection record, all objects, and risk logs only for medium/high objects.

- [ ] **Step 2: Implement mapping helpers**

Create helpers for maximum risk level, relative paths, bbox metrics, Chinese class label fallback, and risk reason fallback.

- [ ] **Step 3: Implement transaction**

Open one PyMySQL connection, insert parent row, use `lastrowid` as `record_id`, insert children, insert risk logs, commit, and rollback on failure.

### Task 3: Detection Flow Integration

**Files:**
- Modify: `backend/services/detection_service.py`

- [ ] **Step 1: Measure inference time**

Wrap `detect_image()` with `time.perf_counter()` and store `inference_time_ms`.

- [ ] **Step 2: Include image dimensions**

Read image width and height with OpenCV after upload succeeds, before saving to MySQL.

- [ ] **Step 3: Persist after inference**

Call `save_detection_result()` after building the response, store `record_id` in the response when available, and keep JSON history behavior.

### Task 4: History Query

**Files:**
- Modify: `backend/services/history_service.py`

- [ ] **Step 1: Read MySQL history**

Call `list_detection_history()` from the database service.

- [ ] **Step 2: Preserve fallback**

If MySQL fails or returns no rows, read `logs/detection_history.json` exactly as before.

### Task 5: Verification

**Files:**
- Test: `tests/test_database_service.py`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_risk.py`

- [ ] **Step 1: Run unit tests**

Run `python -m unittest discover -s tests`.

- [ ] **Step 2: Optional live check**

If network access and the remote MySQL account are available, start Flask and submit one image to confirm `record_id` is returned and rows appear in MySQL.
