"""Tests for src/youtube_uploader.py."""

from unittest.mock import patch, MagicMock

import pytest

from src.youtube_uploader import get_youtube_service, upload_video


class TestGetYouTubeService:
    """Tests for YouTube API authentication (mocked)."""

    @patch("src.youtube_uploader.build")
    @patch("src.youtube_uploader.Credentials")
    def test_get_youtube_service(self, mock_creds: MagicMock, mock_build: MagicMock) -> None:
        """Should build YouTube service with valid credentials."""
        with patch.dict(
            "os.environ",
            {
                "YOUTUBE_CLIENT_ID": "client_id",
                "YOUTUBE_CLIENT_SECRET": "client_secret",
                "YOUTUBE_REFRESH_TOKEN": "refresh_token",
            },
        ):
            mock_creds_instance = MagicMock()
            mock_creds.return_value = mock_creds_instance
            
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            service = get_youtube_service()
            
            assert service == mock_service
            mock_creds.assert_called_once_with(
                token=None,
                refresh_token="refresh_token",
                token_uri="https://oauth2.googleapis.com/token",
                client_id="client_id",
                client_secret="client_secret",
            )
            mock_build.assert_called_once_with("youtube", "v3", credentials=mock_creds_instance)


class TestUploadVideo:
    """Tests for YouTube video upload (mocked)."""

    @patch("src.youtube_uploader.MediaFileUpload")
    @patch("src.youtube_uploader.get_youtube_service")
    def test_upload_video_success(self, mock_get_service: MagicMock, mock_media: MagicMock) -> None:
        """Should upload video with proper Kids compliance and truncated title."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Mock video insert response
        mock_insert = MagicMock()
        mock_service.videos().insert.return_value = mock_insert
        
        mock_status = MagicMock()
        mock_status.progress.return_value = 1.0
        mock_insert.next_chunk.return_value = (mock_status, {"id": "test_vid_123"})
        
        # Mock thumbnail set response
        mock_thumbnails_set = MagicMock()
        mock_service.thumbnails().set.return_value = mock_thumbnails_set
        
        script = {
            "seo_title": "A" * 150,  # 150 characters
            "description": "Test description",
            "tags": ["test", "rhyme"]
        }
        
        result = upload_video("fake/video.mp4", "fake/thumb.jpg", script)
        
        # Assert returned result
        assert result["video_id"] == "test_vid_123"
        assert result["video_url"] == "https://youtu.be/test_vid_123"
        assert result["thumbnail_set"] is True
        
        # Check insert call payload
        insert_kwargs = mock_service.videos().insert.call_args[1]
        body = insert_kwargs["body"]
        
        # Assert truncate to 100 max (no spaces in input, so fallback to [:97] + "...")
        assert len(body["snippet"]["title"]) <= 100
        assert body["snippet"]["title"].endswith("...")
        assert body["snippet"]["title"] == "A" * 97 + "..."
        
        # Assert Kids compliance
        assert body["status"]["madeForKids"] is True
        assert body["status"]["selfDeclaredMadeForKids"] is True
        
        # Verify thumbnail called
        mock_service.thumbnails().set.assert_called_once()
        assert mock_service.thumbnails().set.call_args[1]["videoId"] == "test_vid_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
