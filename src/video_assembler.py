"""Video assembler module for the Nursery Rhyme Bot pipeline.

Combines stanza images, TTS audio, and background music into a 1080p
MP4 video using MoviePy + FFmpeg. Applies Ken Burns pan/zoom animation
on each image to create the illusion of motion.
"""

import os
from typing import Any

import numpy as np
from PIL import Image as PILImage
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)

from src.utils import ensure_dir, retry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VIDEO_WIDTH: int = 1920
VIDEO_HEIGHT: int = 1080
VIDEO_SIZE: tuple[int, int] = (VIDEO_WIDTH, VIDEO_HEIGHT)
FPS: int = 30
TITLE_DURATION: float = 2.5
OUTRO_DURATION: float = 5.0
INTER_STANZA_GAP: float = 0.4


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _create_title_card(
    title: str,
    channel_name: str,
    duration: float,
    audio_path: str,
) -> CompositeVideoClip:
    """Create a title card clip with channel name and rhyme title.

    Args:
        title: The rhyme title text.
        channel_name: Channel name to display above the title.
        duration: Duration of the title card in seconds.
        audio_path: Path to the title announcement audio file.

    Returns:
        A CompositeVideoClip for the title card with audio attached.
    """
    bg = ColorClip(size=VIDEO_SIZE, color=(10, 10, 40)).with_duration(duration)

    channel_txt = TextClip(
        text=channel_name,
        font_size=36,
        color="white",
        font="Arial",
        size=(VIDEO_WIDTH - 200, None),
        method="caption",
        text_align="center",
    ).with_duration(duration).with_position(("center", 0.35), relative=True)

    title_txt = TextClip(
        text=title,
        font_size=64,
        color="white",
        font="Arial",
        size=(VIDEO_WIDTH - 200, None),
        method="caption",
        text_align="center",
    ).with_duration(duration).with_position(("center", 0.50), relative=True)

    card = CompositeVideoClip([bg, channel_txt, title_txt], size=VIDEO_SIZE)

    audio = AudioFileClip(audio_path)
    card = card.with_audio(audio)

    return card


def _create_outro_card(
    duration: float,
    audio_path: str,
) -> CompositeVideoClip:
    """Create an outro card clip with subscribe CTA.

    Args:
        duration: Duration of the outro card in seconds.
        audio_path: Path to the outro audio file.

    Returns:
        A CompositeVideoClip for the outro with audio attached.
    """
    bg = ColorClip(size=VIDEO_SIZE, color=(10, 10, 40)).with_duration(duration)

    cta_txt = TextClip(
        text="Subscribe for more nursery rhymes!",
        font_size=56,
        color="white",
        font="Arial",
        size=(VIDEO_WIDTH - 200, None),
        method="caption",
        text_align="center",
    ).with_duration(duration).with_position(("center", 0.40), relative=True)

    # Animated bouncing arrow — simulate bounce via vertical position lambda
    arrow_txt = TextClip(
        text="⬇",
        font_size=72,
        color="#FFE600",
        font="Arial",
        method="label",
    ).with_duration(duration)

    def _bounce_position(t: float) -> tuple[str, float]:
        """Calculate vertical bounce position for the arrow.

        Args:
            t: Current time in seconds.

        Returns:
            Tuple of (horizontal, vertical) position.
        """
        import math

        base_y = 0.62
        bounce = 0.03 * abs(math.sin(t * 3.0))
        return ("center", base_y + bounce)

    arrow_txt = arrow_txt.with_position(_bounce_position, relative=True)

    card = CompositeVideoClip([bg, cta_txt, arrow_txt], size=VIDEO_SIZE)

    audio = AudioFileClip(audio_path)
    card = card.with_audio(audio)

    return card


def _create_subtitle_overlay(
    text: str,
    duration: float,
) -> CompositeVideoClip:
    """Create a subtitle overlay with a semi-transparent pill background.

    Args:
        text: The subtitle/lyric text to display.
        duration: Duration of the subtitle in seconds.

    Returns:
        A CompositeVideoClip containing the styled subtitle.
    """
    txt_clip = TextClip(
        text=text,
        font_size=42,
        color="white",
        font="Arial",
        size=(VIDEO_WIDTH - 300, None),
        method="caption",
        text_align="center",
    ).with_duration(duration)

    # Get text dimensions for the pill background
    txt_w, txt_h = txt_clip.size
    padding_x = 40
    padding_y = 20
    pill_w = txt_w + padding_x * 2
    pill_h = txt_h + padding_y * 2

    pill_bg = ColorClip(
        size=(pill_w, pill_h),
        color=(0, 0, 0),
    ).with_duration(duration).with_opacity(0.6)

    # Centre the text within the pill
    subtitle = CompositeVideoClip(
        [
            pill_bg.with_position(("center", "center")),
            txt_clip.with_position(("center", "center")),
        ],
        size=(pill_w, pill_h),
    ).with_duration(duration)

    return subtitle


def create_ken_burns_clip(
    image_path: str, duration: float, zoom_start: float = 1.0, zoom_end: float = 1.12
) -> VideoClip:
    """Create a video clip with Ken Burns pan/zoom effect on a single image.

    Applies a slow zoom from zoom_start to zoom_end with a simultaneous
    horizontal pan covering ~8% of the image width, using linear
    interpolation: ``lambda t: zoom_start + (zoom_end - zoom_start) * (t / duration)``.

    Uses a make_frame approach with numpy array slicing so it is
    compatible with MoviePy v2's effect API.

    Args:
        image_path: Path to the source image.
        duration: Clip duration in seconds.
        zoom_start: Starting zoom factor.
        zoom_end: Ending zoom factor.

    Returns:
        A MoviePy VideoClip with the Ken Burns effect applied.
    """
    # Load full-resolution source image as numpy array
    pil_img = PILImage.open(image_path).convert("RGB")
    # Scale up so we have room for zoom + pan at all zoom levels
    base_w, base_h = pil_img.size
    upscale = max(
        VIDEO_WIDTH / base_w,
        VIDEO_HEIGHT / base_h,
    ) * zoom_end * 1.10  # 10 % safety margin

    scaled_w = int(base_w * upscale)
    scaled_h = int(base_h * upscale)
    pil_img = pil_img.resize((scaled_w, scaled_h), PILImage.Resampling.LANCZOS)
    src_array: np.ndarray = np.array(pil_img)

    pan_range = int(VIDEO_WIDTH * 0.08)

    def _make_frame(t: float) -> np.ndarray:
        """Render a single frame with zoom + pan applied.

        Args:
            t: Current time in seconds.

        Returns:
            A (VIDEO_HEIGHT, VIDEO_WIDTH, 3) uint8 numpy array.
        """
        # Linear zoom interpolation
        zoom = zoom_start + (zoom_end - zoom_start) * (t / duration)

        # Crop region size (inverse of zoom — larger zoom = smaller crop)
        crop_w = int(VIDEO_WIDTH / zoom * upscale / (VIDEO_WIDTH / base_w))
        crop_h = int(VIDEO_HEIGHT / zoom * upscale / (VIDEO_HEIGHT / base_h))
        crop_w = min(crop_w, scaled_w)
        crop_h = min(crop_h, scaled_h)

        # Horizontal pan: centre-left → centre-right over duration
        progress = t / duration
        offset_x = int(pan_range * (progress - 0.5))
        cx = scaled_w // 2 + offset_x
        cy = scaled_h // 2

        x1 = max(0, min(cx - crop_w // 2, scaled_w - crop_w))
        y1 = max(0, min(cy - crop_h // 2, scaled_h - crop_h))

        cropped = src_array[y1 : y1 + crop_h, x1 : x1 + crop_w]

        # Resize crop back to target resolution via PIL
        frame_pil = PILImage.fromarray(cropped).resize(
            VIDEO_SIZE, PILImage.Resampling.LANCZOS
        )
        return np.array(frame_pil)

    clip = VideoClip(_make_frame, duration=duration).with_fps(FPS)
    return clip


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@retry(max_attempts=3, backoff_factor=2)
def assemble_video(assets: dict[str, Any], output_path: str) -> str:
    """Assemble the final 1080p MP4 video from all assets.

    Uses FFmpeg preset 'ultrafast' for fast encoding within the
    GitHub Actions time budget.

    Pipeline: title_card → per-stanza clips (Ken Burns + subtitles) →
    outro_card → background music mix → MP4 render.

    Args:
        assets: Dictionary containing all asset paths and script data.
            Expected keys: script, image_paths, title_audio_path,
            stanza_audio_paths, outro_audio_path, ducked_music_path.
        output_path: Path to write the final MP4 file.

    Returns:
        The output file path.
    """
    ensure_dir(os.path.dirname(output_path))

    script = assets["script"]
    image_paths = assets["image_paths"]
    stanza_audio_paths = assets["stanza_audio_paths"]
    title_audio_path = assets["title_audio_path"]
    outro_audio_path = assets["outro_audio_path"]
    ducked_music_path = assets["ducked_music_path"]

    channel_name = os.environ.get("CHANNEL_NAME", "Nursery Rhymes World")
    clips: list[Any] = []

    # 1. Title card (2.5 seconds)
    title_card = _create_title_card(
        title=script["title"],
        channel_name=channel_name,
        duration=TITLE_DURATION,
        audio_path=title_audio_path,
    )
    clips.append(title_card)

    # 2. Per-stanza clips
    stanzas = script.get("stanzas", [])
    for i, (img_path, audio_path) in enumerate(
        zip(image_paths, stanza_audio_paths)
    ):
        # Load stanza audio and get its duration
        stanza_audio = AudioFileClip(audio_path)
        stanza_duration = stanza_audio.duration

        # Ken Burns effect on the stanza image
        kb_clip = create_ken_burns_clip(
            image_path=img_path,
            duration=stanza_duration,
            zoom_start=1.0,
            zoom_end=1.12,
        )

        # Subtitle overlay
        stanza_text = stanzas[i]["text"] if i < len(stanzas) else ""
        if stanza_text:
            subtitle = _create_subtitle_overlay(
                text=stanza_text,
                duration=stanza_duration,
            )
            # Position subtitle at 85% vertical height
            subtitle = subtitle.with_position(
                ("center", 0.85), relative=True
            )
            stanza_clip = CompositeVideoClip(
                [kb_clip, subtitle], size=VIDEO_SIZE
            )
        else:
            stanza_clip = kb_clip

        # Set stanza audio
        stanza_clip = stanza_clip.with_audio(stanza_audio)
        clips.append(stanza_clip)

    # 3. Outro card (5 seconds)
    outro_card = _create_outro_card(
        duration=OUTRO_DURATION,
        audio_path=outro_audio_path,
    )
    clips.append(outro_card)

    # 4. Concatenate all clips
    final = concatenate_videoclips(clips, method="compose")

    # 5. Add background music
    if ducked_music_path and os.path.exists(ducked_music_path):
        music_audio = AudioFileClip(ducked_music_path)
        # Trim music to match final video duration
        if music_audio.duration > final.duration:
            music_audio = music_audio.subclipped(0, final.duration)

        if final.audio is not None:
            mixed_audio = CompositeAudioClip([final.audio, music_audio])
        else:
            mixed_audio = music_audio
        final = final.with_audio(mixed_audio)

    # 6. Render to MP4
    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        ffmpeg_params=["-crf", "23"],
    )

    # Clean up clips
    for clip in clips:
        clip.close()
    final.close()

    return output_path


def calculate_total_duration(assets: dict[str, Any]) -> float:
    """Calculate the expected total video duration from assets.

    Sums durations of: title card (2.5s) + all stanza audios +
    inter-stanza gaps (0.4s × stanza_count) + outro (5.0s).

    Args:
        assets: Dictionary containing audio paths. Expected keys:
            stanza_audio_paths (list of paths).

    Returns:
        Total expected duration in seconds.
    """
    total = TITLE_DURATION + OUTRO_DURATION

    stanza_audio_paths = assets.get("stanza_audio_paths", [])
    stanza_count = len(stanza_audio_paths)

    for audio_path in stanza_audio_paths:
        clip = AudioFileClip(audio_path)
        total += clip.duration
        clip.close()

    # Inter-stanza gaps
    total += INTER_STANZA_GAP * stanza_count

    return total


def validate_video(path: str) -> bool:
    """Validate the rendered video meets quality requirements.

    Checks that:
    - Duration is greater than 60 seconds
    - Video has an audio track
    - Resolution is 1920×1080

    Args:
        path: Path to the rendered MP4 file.

    Returns:
        True if the video passes all checks.

    Raises:
        ValueError: If any validation check fails.
    """
    if not os.path.exists(path):
        raise ValueError(f"Video file not found: {path}")

    clip = VideoFileClip(path)
    try:
        # Check duration
        if clip.duration is None or clip.duration <= 60:
            raise ValueError(
                f"Video duration is {clip.duration}s — must be > 60s. "
                f"The render may be corrupt or truncated."
            )

        # Check audio
        if clip.audio is None:
            raise ValueError(
                "Video has no audio track. "
                "Ensure TTS and music were mixed correctly."
            )

        # Check resolution
        w, h = clip.size
        if w != VIDEO_WIDTH or h != VIDEO_HEIGHT:
            raise ValueError(
                f"Video resolution is {w}×{h} — expected {VIDEO_WIDTH}×{VIDEO_HEIGHT}."
            )
    finally:
        clip.close()

    return True


if __name__ == "__main__":
    print("video_assembler.py — all functions defined ✓")
