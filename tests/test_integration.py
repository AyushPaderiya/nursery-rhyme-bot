"""Integration tests for the full Nursery Rhyme Bot pipeline.

Performs an end-to-end dry-run of the pipeline with all external API calls mocked.
"""

import os
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image
from moviepy import VideoFileClip

from src.main import run_pipeline


@pytest.fixture
def mock_rhyme_script():
    """Returns a valid 4-stanza RhymeScript."""
    return {
        "title": "Integration Test Title",
        "seo_title": "Integration Test SEO Title",
        "description": "Integration Test Description",
        "tags": ["integration", "test", "rhyme"],
        "mood": "upbeat",
        "length_tier": "short",
        "category": "classic",
        "stanzas": [
            {"text": "Line 1", "image_prompt": "Prompt 1", "duration_estimate_seconds": 15.0},
            {"text": "Line 2", "image_prompt": "Prompt 2", "duration_estimate_seconds": 15.0},
            {"text": "Line 3", "image_prompt": "Prompt 3", "duration_estimate_seconds": 15.0},
            {"text": "Line 4", "image_prompt": "Prompt 4", "duration_estimate_seconds": 15.0},
        ],
        "outro_text": "Integration Outro",
        "title_announcement": "Integration Announcement"
    }


@patch("src.main.iso_now", return_value="2024-01-01T00-00-00Z")
@patch("src.alerting.requests.post")  # Telegram
@patch("src.content_generator.requests.get")  # GitHub GET
@patch("src.content_generator.requests.put")  # GitHub PUT
@patch("src.youtube_uploader.get_youtube_service")  # YouTube
@patch("src.youtube_uploader.MediaFileUpload")  # Prevent video file lock
@patch("src.image_generator._call_hf_api")  # Hugging Face
@patch("src.tts_generator.Communicate")  # Edge-TTS
@patch("src.content_generator.genai.GenerativeModel")  # Gemini
@patch("src.main.select_track")  # Music Selection
@patch("src.main.assemble_video")  # Skip 20m rendering
def test_full_pipeline_dry_run(
    mock_assemble: MagicMock,
    mock_select_track: MagicMock,
    mock_gemini: MagicMock,
    mock_tts: MagicMock,
    mock_hf: MagicMock,
    mock_media_upload: MagicMock,
    mock_youtube: MagicMock,
    mock_git_put: MagicMock,
    mock_git_get: MagicMock,
    mock_telegram: MagicMock,
    mock_iso: MagicMock,
    mock_rhyme_script: dict,
    tmp_path: pytest.TempPathFactory
) -> None:
    """End-to-end dry run of the pipeline with mocked external APIs."""
    
    # Fast mock for assemble_video to instantly generate a 65s valid MP4 
    def _mock_assemble(assets: dict, output_path: str) -> None:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=65",
            "-f", "lavfi", "-i", "anullsrc=cl=mono:r=44100:d=65",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", output_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    mock_assemble.side_effect = _mock_assemble

    # ── MOCK SETUP ──
    # 1. Gemini
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_rhyme_script)
    mock_model_instance = MagicMock()
    mock_model_instance.generate_content.return_value = mock_response
    mock_gemini.return_value = mock_model_instance

    # 2. Edge-TTS
    # To ensure total duration > 60s, each stanza must be ~14 seconds
    # (2.5 + 5.0 + 4 * 14 + 1.6 = 65.1s)
    async def mock_save(path: str) -> None:
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", "14.0", "-q:a", "9", "-acodec", "libmp3lame", path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    mock_communicate_instance = MagicMock()
    mock_communicate_instance.save = mock_save
    mock_tts.return_value = mock_communicate_instance

    # 3. Hugging Face Inference API
    # Generate a solid 1024x1024 PNG byte string
    import io
    img_byte_arr = io.BytesIO()
    img = Image.new("RGB", (1024, 1024), color=(50, 200, 150))
    img.save(img_byte_arr, format="PNG")
    mock_hf.return_value = img_byte_arr.getvalue()

    # 4. YouTube API
    mock_service = MagicMock()
    mock_youtube.return_value = mock_service
    mock_insert = MagicMock()
    # next_chunk() returns (status, response)
    mock_status = MagicMock()
    mock_status.progress.return_value = 1.0
    mock_insert.next_chunk.return_value = (mock_status, {"id": "TEST_VIDEO_001"})
    mock_service.videos().insert.return_value = mock_insert

    # 5. GitHub API
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"sha": "mocked_sha"}
    mock_git_get.return_value = mock_get_resp
    
    mock_put_resp = MagicMock()
    mock_put_resp.status_code = 200
    mock_git_put.return_value = mock_put_resp

    # 6. Telegram API
    mock_telegram_resp = MagicMock()
    mock_telegram_resp.status_code = 200
    mock_telegram.return_value = mock_telegram_resp
    
    # 7. Local Music track selection
    # Mocking this since we don't assume assets/music/ has real MP3s during CI/CD
    def _mock_select_track(mood: str) -> str:
        dummy_music = os.path.join(tempfile.gettempdir(), "dummy_music.mp3")
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "30.0", "-q:a", "9", "-acodec", "libmp3lame", dummy_music
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dummy_music
    
    mock_select_track.side_effect = _mock_select_track

    # Use a temporary directory for trackers to not pollute main repo
    from unittest.mock import patch
    import os
    
    with tempfile.TemporaryDirectory() as temp_env_dir:
        # Override paths internally using mock
        # Specifically patch data/content_tracker.json
        tracker_path = os.path.join(temp_env_dir, "content_tracker.json")
        with open(tracker_path, "w") as f:
            json.dump({"videos": []}, f)
            
        def mock_tracker_path():
            return tracker_path

        # Let's mock the os.environ so all credentials are set
        env_vars = {
            "GEMINI_API_KEY": "fake",
            "HF_API_TOKEN": "fake",
            "YOUTUBE_CLIENT_ID": "fake",
            "YOUTUBE_CLIENT_SECRET": "fake",
            "YOUTUBE_REFRESH_TOKEN": "fake",
            "GH_PAT": "fake",
            "TELEGRAM_BOT_TOKEN": "fake",
            "TELEGRAM_CHAT_ID": "fake",
            "CHANNEL_NAME": "Test Channel"
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # We also need to mock `os.path.join` for the tracker paths in content_generator.py if needed, 
            # but an easier way is to just replace the hardcoded path logic via monkeypatch or directly.
            # Actually content_generator.load_tracker reads from `os.path.join(..., "..", "data", "content_tracker.json")`
            # Let's just create an actual file in that exact repo location temporarily, or patch `src.content_generator.os.path.dirname`
            
            repo_tracker_path = os.path.join(os.path.dirname(__file__), "..", "data", "content_tracker.json")
            original_tracker_data = None
            if os.path.exists(repo_tracker_path):
                with open(repo_tracker_path, "r") as f:
                    original_tracker_data = f.read()
            else:
                os.makedirs(os.path.dirname(repo_tracker_path), exist_ok=True)
                
            with open(repo_tracker_path, "w") as f:
                json.dump({"videos": []}, f)

            try:
                # ── EXECUTE ──
                run_pipeline()
                
                # ── ASSERTS ──
                # Check MP4 was created (Wait, run_pipeline uses /tmp/rhyme_2024-01-01T00-00-00Z)
                work_dir = "/tmp/rhyme_2024-01-01T00-00-00Z"
                
                # "Cleanup removed all temp files" => the work_dir itself should be removed!
                assert not os.path.exists(work_dir), "Temp directory was not fully cleaned up!"
                
                # Check tracker was updated
                with open(repo_tracker_path, "r") as f:
                    tracker_data = json.load(f)
                    
                assert len(tracker_data["videos"]) == 1
                assert tracker_data["videos"][0]["video_id"] == "TEST_VIDEO_001"
                assert tracker_data["videos"][0]["title"] == "Integration Test Title"
                
                # Assert GitHub PUT was called
                mock_git_put.assert_called_once()
                
                # Assert Telegram success notification was called
                # send_success_notification calls requests.post
                mock_telegram.assert_called()
                
                # Verify that the test proved the generated video was >60s...
                # Note: validate_video would have failed and raised ValueError if video was <= 60s
                # The fact that run_pipeline() completed without raising exception proves it passed!
                
            finally:
                # Restore original tracker
                if original_tracker_data is not None:
                    with open(repo_tracker_path, "w") as f:
                        f.write(original_tracker_data)
                elif os.path.exists(repo_tracker_path):
                    os.remove(repo_tracker_path)
