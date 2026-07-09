import unittest
from pathlib import Path


class FrontendDisplayAreaTest(unittest.TestCase):
    def setUp(self):
        self.component_source = Path("static/js/components.js").read_text(encoding="utf-8")
        self.app_source = Path("static/js/app.js").read_text(encoding="utf-8")
        self.detection_service_source = Path("backend/services/detection_service.py").read_text(encoding="utf-8")
        self.video_job_service_source = Path("backend/services/video_job_service.py").read_text(encoding="utf-8")

    def test_result_panel_shows_selected_file_preview_before_detection_result(self):
        self.assertIn('v-if="isDetecting && !filePreviewUrl"', self.component_source)
        self.assertIn('v-if="isDetecting" class="panel-badge"', self.component_source)
        self.assertIn('v-else-if="filePreviewUrl"', self.component_source)
        self.assertIn(':src="filePreviewUrl"', self.component_source)
        self.assertIn(':type="fileType"', self.component_source)

    def test_file_selection_starts_detection_after_preview_is_ready(self):
        self.assertIn("const detectionRequestId = ref(0)", self.app_source)
        self.assertIn("await onDetect(requestId)", self.app_source)
        self.assertIn("if (requestId !== detectionRequestId.value) return", self.app_source)

    def test_video_detection_uses_background_job_polling(self):
        self.assertIn("async function startVideoDetectionJob(requestId)", self.app_source)
        self.assertIn("'/api/detections/videos/jobs'", self.app_source)
        self.assertIn("async function pollVideoDetectionJob(jobId, requestId)", self.app_source)
        self.assertIn("latest_frame", self.video_job_service_source)
        self.assertIn("pollTimerId", self.app_source)

    def test_video_playback_uses_canvas_overlay_timeline(self):
        self.assertIn("videoRef", self.component_source)
        self.assertIn("videoOverlayRef", self.component_source)
        self.assertIn("drawVideoOverlay", self.component_source)
        self.assertIn("requestAnimationFrame(drawVideoOverlayFrame)", self.component_source)
        self.assertIn("cancelAnimationFrame(videoOverlayFrameId.value)", self.component_source)
        self.assertIn("@play=\"startVideoOverlayLoop\"", self.component_source)
        self.assertIn("@pause=\"stopVideoOverlayLoop\"", self.component_source)
        self.assertIn("@ended=\"stopVideoOverlayLoop\"", self.component_source)
        self.assertIn("@seeked=\"drawVideoOverlay\"", self.component_source)
        self.assertIn("detectionTimeline", self.component_source)
        self.assertIn("detectionTimeline.value = data.detection_timeline || []", self.app_source)
        self.assertIn("detection_timeline", self.video_job_service_source)

    def test_video_overlay_uses_original_playback_source_and_holds_last_detection_frame(self):
        self.assertIn(':src="filePreviewUrl || resultVideoUrl"', self.component_source)
        self.assertNotIn("Math.abs((frame.timestamp_sec || 0) - current) > 1.2", self.component_source)

    def test_video_result_keeps_recent_boxes_between_sampled_inference_frames(self):
        self.assertIn("last_frame_detections = []", self.detection_service_source)
        self.assertIn("detections_to_draw = frame_detections or last_frame_detections", self.detection_service_source)


if __name__ == "__main__":
    unittest.main()
