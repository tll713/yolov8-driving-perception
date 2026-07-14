import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.services.detection_service import detect_video_file


@unittest.skipIf(importlib.util.find_spec("cv2") is None, "OpenCV is not installed in this runtime")
class VideoDetectionServiceTest(unittest.TestCase):
    def test_video_file_detection_updates_timeline_for_each_processed_frame(self):
        upload_path = Path("uploads/road.mp4")
        frames = [Mock(), Mock(), Mock()]
        for frame in frames:
            frame.copy.return_value = frame
        cap = Mock()
        cap.isOpened.return_value = True
        cap.get.side_effect = [640, 360, 25, 30]
        cap.read.side_effect = [(True, frame) for frame in frames] + [(False, None)]

        writer = Mock()
        box = type(
            "Box",
            (),
            {
                "cls": [0],
                "conf": [0.8],
                "xyxy": [Mock(tolist=Mock(return_value=[10, 20, 110, 220]))],
            },
        )()
        result_item = type("Result", (), {"names": {0: "car"}, "boxes": [box]})()
        model = Mock()
        model.predict.return_value = [result_item]
        progress_items = []

        with (
            patch("cv2.VideoCapture", return_value=cap),
            patch("cv2.VideoWriter", return_value=writer),
            patch("cv2.VideoWriter_fourcc", return_value=0),
            patch("cv2.rectangle"),
            patch("cv2.getTextSize", return_value=((60, 14), 0)),
            patch("cv2.putText"),
            patch("backend.services.detection_service.get_model", return_value=model),
            patch("backend.services.detection_service._save_to_database"),
            patch(
                "backend.services.detection_service.time.perf_counter",
                side_effect=[0, 0.01, 1, 1.02, 2, 2.03],
            ),
        ):
            result = detect_video_file(upload_path, "road.mp4", progress_callback=progress_items.append)

        self.assertEqual(model.predict.call_count, 3)
        self.assertEqual(writer.write.call_count, 3)
        self.assertEqual([item["frame_index"] for item in progress_items], [0, 1, 2])
        self.assertEqual([item["timestamp_sec"] for item in progress_items], [0, 0.04, 0.08])
        self.assertEqual([item["frame_inference_time_ms"] for item in progress_items], [10, 20, 30])
        self.assertEqual(result["inference_time_ms"], 20)
        self.assertEqual(result["processed_frame_count"], 3)


if __name__ == "__main__":
    unittest.main()
