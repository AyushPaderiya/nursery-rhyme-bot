"""Tests for src/music_selector.py."""

import os
from unittest.mock import patch, MagicMock

import pytest

from src.music_selector import select_track, trim_and_duck_music


class TestMusicSelector:
    """Tests for music track selection and editing logic."""

    @patch("src.music_selector.load_mood_map")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_select_track_valid(
        self, mock_getsize: MagicMock, mock_exists: MagicMock, mock_load: MagicMock
    ) -> None:
        """Test returning track path for valid real files."""
        mock_load.return_value = {"upbeat": ["song1.mp3"]}
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1MB file

        path = select_track("upbeat")
        assert "song1.mp3" in path

    @patch("src.music_selector.load_mood_map")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_select_track_placeholder(
        self, mock_getsize: MagicMock, mock_exists: MagicMock, mock_load: MagicMock
    ) -> None:
        """Test placeholder file (0 bytes) raises RuntimeError."""
        mock_load.return_value = {"lullaby": ["placeholder.mp3"]}
        mock_exists.return_value = True
        mock_getsize.return_value = 0

        with pytest.raises(RuntimeError, match="is a placeholder"):
            select_track("lullaby")

    @patch("src.music_selector.load_mood_map")
    def test_select_track_unknown_mood(self, mock_load: MagicMock) -> None:
        """Test invalid mood raises ValueError."""
        mock_load.return_value = {"lullaby": ["placeholder.mp3"]}

        with pytest.raises(ValueError):
            select_track("metal")

    @patch("subprocess.run")
    def test_trim_and_duck_music(self, mock_run: MagicMock) -> None:
        """Test ffmpeg call constructs filter correctly."""
        segments = [(2.0, 5.0), (10.0, 15.0)]
        out_path = trim_and_duck_music("input.mp3", 30.0, segments, "out.mp3")

        assert out_path == "out.mp3"
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffmpeg" in args
        assert "libmp3lame" in args
        assert "-t" in args
        assert "30.0" in args

        # Ensure af string contains the ducking logic
        af_idx = args.index("-af") + 1
        filter_str = args[af_idx]
        assert "volume=eval=frame" in filter_str
        assert "between(t,2.0,5.0) + between(t,10.0,15.0)" in filter_str
        assert "afade=t=out:st=28.0:d=2" in filter_str
