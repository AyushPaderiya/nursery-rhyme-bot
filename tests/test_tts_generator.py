"""Tests for src/tts_generator.py."""

import os
from unittest.mock import patch, MagicMock

import pytest

from src.tts_generator import generate_voiceover, get_audio_duration


class TestTTSGenerator:
    """Tests for TTS generation."""

    @patch("src.tts_generator.os.replace")
    @patch("src.tts_generator._generate_silence")
    @patch("src.tts_generator._generate_single_tts")
    @patch("subprocess.run")
    def test_generate_voiceover(
        self, mock_subprocess: MagicMock, mock_single_tts: MagicMock, mock_silence: MagicMock, mock_replace: MagicMock, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test generating voiceover files creates correctly named outputs."""
        output_dir = str(tmp_path)
        script = {
            "title_announcement": "Welcome to the show!",
            "stanzas": [
                {"text": "Line 1"},
                {"text": "Line 2"}
            ],
            "outro_text": "Thanks for watching!"
        }

        result = generate_voiceover(script, output_dir)

        assert result["title_audio_path"] == os.path.join(output_dir, "title.mp3")
        assert result["outro_audio_path"] == os.path.join(output_dir, "outro.mp3")
        assert len(result["stanza_audio_paths"]) == 2
        assert result["stanza_audio_paths"][0] == os.path.join(output_dir, "stanza_00.mp3")
        assert result["stanza_audio_paths"][1] == os.path.join(output_dir, "stanza_01.mp3")

        # Called once for title, once for outro, and once per stanza
        assert mock_single_tts.call_count == 4
        assert mock_silence.call_count == 1
        # Subprocess called once per stanza to concat
        assert mock_subprocess.call_count == 2

    @patch("src.tts_generator.AudioFileClip")
    def test_get_audio_duration(self, mock_audio_clip: MagicMock) -> None:
        """Test audio duration returns expected float > 0."""
        # Setup mock
        mock_instance = mock_audio_clip.return_value
        mock_instance.duration = 4.5

        duration = get_audio_duration("fake_path.mp3")
        
        assert isinstance(duration, float)
        assert getattr(mock_instance, "close").called
        assert duration == 4.5
