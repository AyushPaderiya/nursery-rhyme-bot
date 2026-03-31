"""Tests for src/content_generator.py."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from src.content_generator import (
    load_prompt_template,
    get_used_titles,
    generate_script,
    load_tracker,
    update_tracker,
    commit_tracker
)

@pytest.fixture
def mock_valid_rhyme_script():
    return {
        "title": "Test Title",
        "seo_title": "Test SEO",
        "description": "Test Desc",
        "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12", "tag13", "tag14", "tag15"],
        "mood": "happy",
        "length_tier": "short",
        "category": "classic",
        "stanzas": [
            {
                "text": "Line 1\nLine 2\nLine 3\nLine 4",
                "image_prompt": "Test image prompt",
                "duration_estimate_seconds": 20.0
            }
        ],
        "outro_text": "Outro",
        "title_announcement": "Announcement"
    }

class TestLoadPromptTemplate:
    """Tests for loading the prompt template file."""
    def test_load_returns_string(self) -> None:
        template = load_prompt_template()
        assert isinstance(template, str)
        assert len(template) > 0

    def test_template_contains_placeholders(self) -> None:
        template = load_prompt_template()
        assert "{category}" in template
        assert "{length_tier}" in template
        assert "{used_titles}" in template

class TestGetUsedTitles:
    """Tests for extracting used titles from the tracker."""
    def test_empty_tracker(self) -> None:
        assert get_used_titles({"videos": []}) == []

    def test_tracker_with_videos(self) -> None:
        tracker = {
            "videos": [
                {"title": "Twinkle Twinkle"},
                {"title": "Humpty Dumpty"},
            ]
        }
        titles = get_used_titles(tracker)
        assert titles == ["Twinkle Twinkle", "Humpty Dumpty"]

class TestGenerateScript:
    """Tests for generate_script with Gemini API."""

    @patch("src.content_generator.genai.GenerativeModel")
    @patch("src.content_generator.load_env")
    def test_valid_response(self, mock_load_env, mock_model, mock_valid_rhyme_script) -> None:
        mock_load_env.return_value = "dummy_key"
        
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_valid_rhyme_script)
        
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model.return_value = mock_instance
        
        # Call the unwrapped function to avoid retry delays in test if it fails
        result = generate_script.__wrapped__("classic", "short", [])
        
        assert result["title"] == "Test Title"
        assert len(result["stanzas"]) == 1
        assert "text" in result["stanzas"][0]

    @patch("src.content_generator.genai.GenerativeModel")
    @patch("src.content_generator.load_env")
    def test_malformed_response_raises_value_error(self, mock_load_env, mock_model) -> None:
        mock_load_env.return_value = "dummy_key"
        
        mock_response = MagicMock()
        # Missing 'title' root field
        mock_response.text = json.dumps({"seo_title": "Test"})
        
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model.return_value = mock_instance
        
        with pytest.raises(ValueError, match="Missing required field in RhymeScript"):
            generate_script.__wrapped__("classic", "short", [])

    @patch("src.content_generator.genai.GenerativeModel")
    @patch("src.content_generator.load_env")
    def test_duplicate_title_raises_value_error(self, mock_load_env, mock_model, mock_valid_rhyme_script) -> None:
        mock_load_env.return_value = "dummy_key"
        
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_valid_rhyme_script)
        
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model.return_value = mock_instance
        
        with pytest.raises(ValueError, match="is already in used_titles"):
            generate_script.__wrapped__("classic", "short", ["Test Title"])

class TestTrackerOperations:
    """Tests for load_tracker, update_tracker, commit_tracker."""

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_tracker_missing_file(self, mock_open) -> None:
        tracker = load_tracker()
        assert tracker == {"videos": []}

    @patch("builtins.open")
    @patch("src.content_generator.json.load")
    def test_load_tracker_valid_file(self, mock_json_load, mock_open) -> None:
        expected = {"videos": [{"title": "Test"}]}
        mock_json_load.return_value = expected
        tracker = load_tracker()
        assert tracker == expected

    @patch("builtins.open")
    @patch("src.content_generator.os.makedirs")
    @patch("src.content_generator.iso_now")
    def test_update_tracker(self, mock_iso_now, mock_makedirs, mock_open) -> None:
        mock_iso_now.return_value = "2026-03-30T12:00:00Z"
        tracker = {"videos": []}
        upload_result = {"video_id": "123", "video_url": "http://test"}
        script = {"title": "Test", "category": "classic", "length_tier": "short", "mood": "happy", "stanzas": [{}]}
        
        update_tracker(tracker, upload_result, script)
        
        assert len(tracker["videos"]) == 1
        entry = tracker["videos"][0]
        assert entry["video_id"] == "123"
        assert entry["video_url"] == "http://test"
        assert entry["title"] == "Test"
        assert entry["uploaded_at"] == "2026-03-30T12:00:00Z"
        assert entry["stanza_count"] == 1

    @patch("src.content_generator.requests.put")
    @patch("src.content_generator.requests.get")
    @patch("src.content_generator.load_env")
    @patch("builtins.open")
    def test_commit_tracker(self, mock_open, mock_load_env, mock_get, mock_put) -> None:
        mock_load_env.return_value = "fake_pat"
        mock_open.return_value.__enter__.return_value.read.return_value = b"tracker_content"
        
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {"sha": "fake_sha"}
        mock_get.return_value = mock_get_resp
        
        mock_put_resp = MagicMock()
        mock_put.return_value = mock_put_resp
        
        commit_tracker.__wrapped__()
        
        mock_get.assert_called_once()
        mock_put.assert_called_once()
        
        put_args, put_kwargs = mock_put.call_args
        assert "AyushPaderiya/nursery-rhyme-bot" in put_args[0]
        assert put_kwargs["json"]["sha"] == "fake_sha"
        assert put_kwargs["json"]["message"] == "chore: update content tracker [skip ci]"
        assert "Authorization" in put_kwargs["headers"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
