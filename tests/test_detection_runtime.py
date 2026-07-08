import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from detect import detect_image


class DetectionRuntimeTest(unittest.TestCase):
    def test_detect_image_passes_configured_image_size_to_model(self):
        image_path = Path("uploads/runtime_test.jpg")
        result = type(
            "Result",
            (),
            {
                "names": {},
                "boxes": [],
            },
        )()
        model = Mock()
        model.predict.return_value = [result]

        with (
            patch("detect.get_model", return_value=model),
            patch("cv2.imread", return_value=object()),
            patch("detect._read_image_size", return_value=(1280, 720)),
        ):
            detect_image(image_path, confidence=0.4, inference_mode="fast")

        model.predict.assert_called_once()
        _, kwargs = model.predict.call_args
        self.assertEqual(kwargs["imgsz"], 640)
        self.assertEqual(kwargs["conf"], 0.4)

    def test_balanced_mode_refines_large_image_when_first_pass_finds_nothing(self):
        image_path = Path("uploads/runtime_test.jpg")
        first_result = type("Result", (), {"names": {}, "boxes": []})()
        second_result = type("Result", (), {"names": {}, "boxes": []})()
        model = Mock()
        model.predict.side_effect = [[first_result], [second_result]]

        with (
            patch("detect.get_model", return_value=model),
            patch("cv2.imread", return_value=object()),
            patch("detect._read_image_size", return_value=(1920, 1080)),
        ):
            result = detect_image(image_path, confidence=0.4)

        self.assertEqual(model.predict.call_count, 2)
        self.assertEqual(model.predict.call_args_list[0].kwargs["imgsz"], 640)
        self.assertEqual(model.predict.call_args_list[1].kwargs["imgsz"], 960)
        self.assertEqual(result["inference_mode"], "balanced")
        self.assertEqual(result["refined"], True)

    def test_balanced_mode_keeps_fast_result_when_confidence_is_high(self):
        image_path = Path("uploads/runtime_test.jpg")
        box = type(
            "Box",
            (),
            {
                "cls": [0],
                "conf": [0.86],
                "xyxy": [Mock(tolist=Mock(return_value=[10, 20, 120, 220]))],
            },
        )()
        result_item = type("Result", (), {"names": {0: "person"}, "boxes": [box]})()
        model = Mock()
        model.predict.return_value = [result_item]

        with (
            patch("detect.get_model", return_value=model),
            patch("cv2.imread", return_value=object()),
            patch("detect._read_image_size", return_value=(1280, 720)),
        ):
            result = detect_image(image_path, confidence=0.4)

        self.assertEqual(model.predict.call_count, 1)
        self.assertEqual(result["refined"], False)
        self.assertEqual(result["inference_size"], 640)


if __name__ == "__main__":
    unittest.main()
