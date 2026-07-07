import unittest

from backend.api_contract import API_ENDPOINTS, build_error_response, build_success_response


class ApiContractTest(unittest.TestCase):
    def test_vue_api_endpoints_are_registered_in_contract(self):
        self.assertEqual(API_ENDPOINTS["health"], "/api/health")
        self.assertEqual(API_ENDPOINTS["image_detection"], "/api/detections/images")
        self.assertEqual(API_ENDPOINTS["video_detection"], "/api/detections/videos")
        self.assertEqual(API_ENDPOINTS["history"], "/api/detections/history")
        self.assertEqual(API_ENDPOINTS["model_info"], "/api/models/current")

    def test_success_response_has_stable_shape(self):
        response = build_success_response({"count": 2})

        self.assertEqual(response["code"], 0)
        self.assertEqual(response["message"], "success")
        self.assertEqual(response["data"], {"count": 2})

    def test_error_response_has_stable_shape(self):
        response = build_error_response("文件格式不支持", code=400)

        self.assertEqual(response["code"], 400)
        self.assertEqual(response["message"], "文件格式不支持")
        self.assertIsNone(response["data"])


if __name__ == "__main__":
    unittest.main()
