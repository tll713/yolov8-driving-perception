from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import io
import json
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])

detection_logs = []


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/detect', methods=['POST'])
def detect():
    if 'file' not in request.files:
        return jsonify({'error': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    threshold = float(request.form.get('threshold', 0.5))

    # TODO: 替换为实际的 YOLOv8 推理逻辑
    # 以下为模拟结果
    mock_result = {
        'total_counts': {'car': 3, 'person': 1, 'traffic_light': 1},
        'overall_risk': '中风险',
        'inference_time': 256,
        'class_counts': {'car': 3, 'person': 1, 'traffic_light': 1},
        'result_image': ''
    }

    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'filename': file.filename,
        'threshold': threshold,
        'result': mock_result
    }
    detection_logs.append(log_entry)

    return jsonify(mock_result)


@app.route('/download_log')
def download_log():
    if not detection_logs:
        return jsonify({'error': '暂无日志'}), 404

    log_content = json.dumps(detection_logs, ensure_ascii=False, indent=2)
    buffer = io.BytesIO(log_content.encode('utf-8'))
    return send_file(
        buffer,
        as_attachment=True,
        download_name='detection_log.json',
        mimetype='application/json'
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)