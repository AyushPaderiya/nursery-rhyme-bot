"""Tests for src/video_assembler.py."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from src.video_assembler import (
    assemble_video,
    calculate_total_duration,
    create_ken_burns_clip,
    validate_video,
)


class TestCalculateTotalDuration:
    """Tests for total video duration calculation."""

    def test_correct_sum_with_mock_assets(self, tmp_path: str) -> None:
        """Duration should equal title + stanza durations + gaps + outro."""
        # Create mock audio files with known durations
        audio_dir = os.path.join(str(tmp_path), "audio")
        os.makedirs(audio_dir, exist_ok=True)

        stanza_durations = [10.0, 12.0, 8.0]
        stanza_paths = []

        for i, dur in enumerate(stanza_durations):
            path = os.path.join(audio_dir, f"stanza_{i:02d}.mp3")
            stanza_paths.append(path)

        mock_assets = {
            "stanza_audio_paths": stanza_paths,
        }

        # Mock AudioFileClip to return known durations
        with patch("src.video_assembler.AudioFileClip") as mock_audio:
            mock_clips = []
            for dur in stanza_durations:
                mock_clip = MagicMock()
                mock_clip.duration = dur
                mock_clips.append(mock_clip)

            mock_audio.side_effect = mock_clips

            total = calculate_total_duration(mock_assets)

        # Expected: title(2.5) + stanzas(10+12+8) + gaps(0.4*3) + outro(5.0)
        expected = 2.5 + 30.0 + 1.2 + 5.0
        assert abs(total - expected) < 0.01, (
            f"Expected {expected}s, got {total}s"
        )

    def test_empty_stanzas(self) -> None:
        """Duration with no stanzas should be title + outro only."""
        mock_assets: dict = {"stanza_audio_paths": []}

        total = calculate_total_duration(mock_assets)

        expected = 2.5 + 5.0  # title + outro, no gaps
        assert abs(total - expected) < 0.01


class TestValidateVideo:
    """Tests for rendered video validation."""

    def test_valid_video_passes(self, tmp_path: str) -> None:
        """A video with correct duration, audio, and resolution should pass."""
        video_path = os.path.join(str(tmp_path), "test_valid.mp4")

        with patch("src.video_assembler.VideoFileClip") as mock_vfc:
            mock_clip = MagicMock()
            mock_clip.duration = 120.0
            mock_clip.audio = MagicMock()
            mock_clip.size = (1920, 1080)
            mock_vfc.return_value = mock_clip

            # Need file to exist for the os.path.exists check
            with open(video_path, "w") as f:
                f.write("fake")

            result = validate_video(video_path)
            assert result is True

    def test_missing_file_raises_error(self) -> None:
        """A non-existent file should raise ValueError."""
        with pytest.raises(ValueError, match="Video file not found"):
            validate_video("/nonexistent/path/video.mp4")

    def test_short_duration_raises_error(self, tmp_path: str) -> None:
        """A video shorter than 60 seconds should raise ValueError."""
        video_path = os.path.join(str(tmp_path), "test_short.mp4")

        with patch("src.video_assembler.VideoFileClip") as mock_vfc:
            mock_clip = MagicMock()
            mock_clip.duration = 5.0
            mock_clip.audio = MagicMock()
            mock_clip.size = (1920, 1080)
            mock_vfc.return_value = mock_clip

            with open(video_path, "w") as f:
                f.write("fake")

            with pytest.raises(ValueError, match="must be > 60s"):
                validate_video(video_path)

    def test_no_audio_raises_error(self, tmp_path: str) -> None:
        """A video with no audio track should raise ValueError."""
        video_path = os.path.join(str(tmp_path), "test_noaudio.mp4")

        with patch("src.video_assembler.VideoFileClip") as mock_vfc:
            mock_clip = MagicMock()
            mock_clip.duration = 120.0
            mock_clip.audio = None
            mock_clip.size = (1920, 1080)
            mock_vfc.return_value = mock_clip

            with open(video_path, "w") as f:
                f.write("fake")

            with pytest.raises(ValueError, match="no audio track"):
                validate_video(video_path)

    def test_wrong_resolution_raises_error(self, tmp_path: str) -> None:
        """A video with wrong resolution should raise ValueError."""
        video_path = os.path.join(str(tmp_path), "test_lowres.mp4")

        with patch("src.video_assembler.VideoFileClip") as mock_vfc:
            mock_clip = MagicMock()
            mock_clip.duration = 120.0
            mock_clip.audio = MagicMock()
            mock_clip.size = (1280, 720)
            mock_vfc.return_value = mock_clip

            with open(video_path, "w") as f:
                f.write("fake")

            with pytest.raises(ValueError, match="1920×1080"):
                validate_video(video_path)


class TestKenBurnsClip:
    """Tests for Ken Burns effect clip generation."""

    def test_lambda_functions_no_type_error(self, tmp_path: str) -> None:
        """Ken Burns clip should be creatable without TypeError."""
        # Create a test image
        img_path = os.path.join(str(tmp_path), "test_img.png")
        img = Image.new("RGB", (1024, 1024), color=(100, 150, 200))
        img.save(img_path)

        # This should not raise TypeError from the lambda functions
        clip = create_ken_burns_clip(img_path, duration=2.0)

        assert clip is not None
        assert clip.duration == 2.0

        # Verify we can get a frame at t=0 and t=1 without error
        frame_0 = clip.get_frame(0)
        frame_1 = clip.get_frame(1.0)

        assert frame_0 is not None
        assert frame_1 is not None

        clip.close()

    def test_zoom_parameters_applied(self, tmp_path: str) -> None:
        """Ken Burns clip should accept custom zoom parameters."""
        img_path = os.path.join(str(tmp_path), "test_img.png")
        img = Image.new("RGB", (1024, 1024), color=(100, 150, 200))
        img.save(img_path)

        clip = create_ken_burns_clip(
            img_path, duration=3.0, zoom_start=1.0, zoom_end=1.2
        )

        assert clip is not None
        assert clip.duration == 3.0
        clip.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
