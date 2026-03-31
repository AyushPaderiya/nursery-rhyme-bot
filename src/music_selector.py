"""Music selector module for the Nursery Rhyme Bot pipeline.

Selects a royalty-free background music track from the pre-bundled
CC0 library in assets/music/ based on the rhyme's mood tag.
"""

import json
import os
import random
import subprocess
from typing import Any


def load_mood_map() -> dict[str, list[str]]:
    """Load the mood-to-track mapping from mood_map.json.

    Returns:
        Dictionary mapping mood strings to lists of MP3 filenames.
    """
    mood_map_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "music", "mood_map.json"
    )
    with open(mood_map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_track(mood: str) -> str:
    """Select a music track matching the given mood.

    Returns the absolute path to a randomly selected MP3 for that mood.
    If the file size is 0 bytes, a specific RuntimeError is returned to 
    indicate placeholder status.

    Args:
        mood: The mood string (e.g. 'lullaby', 'upbeat', 'educational', 'seasonal').

    Returns:
        Absolute file path to the track.

    Raises:
        ValueError: If mood doesn't exist.
        RuntimeError: If track is a 0-byte placeholder.
    """
    mood_map = load_mood_map()

    if mood not in mood_map:
        raise ValueError(f"Unknown mood '{mood}'. Available: {list(mood_map.keys())}")

    track_filename = random.choice(mood_map[mood])
    track_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "music", track_filename
    )
    track_path = os.path.abspath(track_path)

    if not os.path.exists(track_path):
        raise FileNotFoundError(f"Music track not found at {track_path}")

    if os.path.getsize(track_path) == 0:
        raise RuntimeError(
            f"Music track {track_filename} is a placeholder. Download CC0 tracks before running."
        )

    return track_path


def trim_and_duck_music(
    music_path: str,
    video_duration: float,
    voice_segments: list[tuple[float, float]],
    output_path: str
) -> str:
    """Trim background music to duration, ducking during voice segments.

    Duck volume to 20% during given voice segments, leaving base volume at 70%.
    A 2-second fade-out applies at the end of the duration.

    Args:
        music_path: Path to the selected background audio.
        video_duration: Target duration of the final background music.
        voice_segments: List of (start_time, end_time) segments for ducking.
        output_path: Target saved file path.

    Returns:
        The output path (matches output_path arg).
    """
    ducking_terms = []
    for start, end in voice_segments:
        ducking_terms.append(f"between(t,{start},{end})")

    if ducking_terms:
        # Sum of clipping ensures 1 inside any segment, 0 outside.
        duck_expr = " + ".join(ducking_terms)
        vol_expr = f"0.7 - 0.5*clip({duck_expr}, 0, 1)"
    else:
        vol_expr = "0.7"

    fade_start = max(0.0, video_duration - 2.0)
    filter_expr = f"volume=eval=frame:volume='{vol_expr}',afade=t=out:st={fade_start}:d=2"

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1",  # Loop music if it's shorter than the video
            "-i", music_path,
            "-af", filter_expr,
            "-t", str(video_duration),
            "-acodec", "libmp3lame",
            output_path
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return output_path
