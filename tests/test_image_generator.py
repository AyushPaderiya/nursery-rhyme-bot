"""Tests for src/image_generator.py."""

import os
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from src.image_generator import generate_images, validate_image


class TestImageGenerator:
    """Tests for image generation and validation."""

    @patch("src.image_generator._call_hf_api")
    @patch("src.image_generator._call_pollinations_api")
    @patch("src.image_generator.load_image_prompt_prefix")
    @patch("src.image_generator.validate_image")
    @patch("time.sleep")
    def test_generate_images_hf_success(
        self, mock_sleep: MagicMock, mock_val: MagicMock, mock_prefix: MagicMock,
        mock_poll: MagicMock, mock_hf: MagicMock, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test HF API generates images correctly."""
        output_dir = str(tmp_path)
        script = {
            "stanzas": [
                {"image_prompt": "Dog"},
                {"image_prompt": "Cat"}
            ]
        }
        mock_prefix.return_value = "Prefix: "
        mock_hf.return_value = b"fake_image_bytes"

        paths = generate_images(script, output_dir)
        
        assert len(paths) == 2
        assert mock_hf.call_count == 2
        assert mock_poll.call_count == 0
        assert mock_val.call_count == 2
        assert mock_sleep.call_count == 2

    @patch("src.image_generator._call_hf_api")
    @patch("src.image_generator._call_pollinations_api")
    @patch("src.image_generator.load_image_prompt_prefix")
    @patch("src.image_generator.validate_image")
    @patch("time.sleep")
    def test_generate_images_hf_fallback(
        self, mock_sleep: MagicMock, mock_val: MagicMock, mock_prefix: MagicMock,
        mock_poll: MagicMock, mock_hf: MagicMock, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test fallback to Pollinations when HF API fails."""
        output_dir = str(tmp_path)
        script = {
            "stanzas": [
                {"image_prompt": "Dog"}
            ]
        }
        mock_prefix.return_value = "Prefix: "
        mock_hf.side_effect = Exception("429 Too Many Requests")
        mock_poll.return_value = b"fake_poll_bytes"

        paths = generate_images(script, output_dir)
        
        assert len(paths) == 1
        assert mock_hf.call_count == 1
        assert mock_poll.call_count == 1
        assert mock_val.call_count == 1

    def test_validate_image_valid(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test true returned on valid 1024x1024 image."""
        img_path = os.path.join(str(tmp_path), "valid.png")
        img = Image.new("RGB", (1024, 1024), color="blue")
        img.save(img_path)

        assert validate_image(img_path) is True

    def test_validate_image_invalid_dimensions(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test ValueError raised on incorrect dimensions."""
        img_path = os.path.join(str(tmp_path), "invalid_dim.png")
        img = Image.new("RGB", (512, 512), color="red")
        img.save(img_path)

        with pytest.raises(ValueError):
            validate_image(img_path)

    def test_validate_image_corrupt(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test ValueError raised on corrupt bytes."""
        img_path = os.path.join(str(tmp_path), "corrupt.png")
        with open(img_path, "wb") as f:
            f.write(b"not an image file content")

        with pytest.raises(ValueError):
            validate_image(img_path)
