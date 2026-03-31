"""Tests for src/thumbnail_generator.py."""

import os
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from src.thumbnail_generator import generate_thumbnail


class TestGenerateThumbnail:
    """Tests for YouTube thumbnail generation."""

    @patch("src.thumbnail_generator._get_font")
    def test_generates_valid_jpeg(
        self, mock_get_font: MagicMock, tmp_path: str
    ) -> None:
        """Generated thumbnail should exist and be exactly 1280×720 JPEG."""
        from PIL import ImageFont

        # Use default font to avoid network call
        mock_get_font.return_value = ImageFont.load_default()

        # Create a test source image
        src_path = os.path.join(str(tmp_path), "test_source.png")
        img = Image.new("RGB", (2048, 2048), color=(50, 120, 200))
        img.save(src_path)

        out_path = os.path.join(str(tmp_path), "thumbnail.jpg")

        result = generate_thumbnail(src_path, "Twinkle Twinkle Little Star", out_path)

        assert result == out_path
        assert os.path.exists(out_path)

        with Image.open(out_path) as thumb:
            assert thumb.size == (1280, 720), (
                f"Expected 1280×720, got {thumb.size}"
            )
            assert thumb.format == "JPEG"

    @patch("src.thumbnail_generator._get_font")
    def test_long_title_auto_resized(
        self, mock_get_font: MagicMock, tmp_path: str
    ) -> None:
        """A very long title should still produce a valid thumbnail."""
        from PIL import ImageFont

        mock_get_font.return_value = ImageFont.load_default()

        src_path = os.path.join(str(tmp_path), "test_source.png")
        img = Image.new("RGB", (1024, 1024), color=(200, 100, 50))
        img.save(src_path)

        out_path = os.path.join(str(tmp_path), "thumbnail_long.jpg")

        long_title = "The Adventures of the Very Hungry Caterpillar Who Loved Singing Songs All Day Long in the Garden"
        result = generate_thumbnail(src_path, long_title, out_path)

        assert result == out_path
        assert os.path.exists(out_path)

        with Image.open(out_path) as thumb:
            assert thumb.size == (1280, 720), (
                f"Expected 1280×720, got {thumb.size}"
            )

    @patch("src.thumbnail_generator._get_font")
    def test_short_title(
        self, mock_get_font: MagicMock, tmp_path: str
    ) -> None:
        """A short title should produce a valid thumbnail without issues."""
        from PIL import ImageFont

        mock_get_font.return_value = ImageFont.load_default()

        src_path = os.path.join(str(tmp_path), "test_source.png")
        img = Image.new("RGB", (800, 600), color=(100, 200, 100))
        img.save(src_path)

        out_path = os.path.join(str(tmp_path), "thumbnail_short.jpg")

        result = generate_thumbnail(src_path, "ABC", out_path)

        assert result == out_path
        assert os.path.exists(out_path)

        with Image.open(out_path) as thumb:
            assert thumb.size == (1280, 720)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
