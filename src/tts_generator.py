"""Text-to-Speech generator module for the Nursery Rhyme Bot pipeline.

Uses Microsoft Edge-TTS (zero cost, no API key required) to synthesise
voiceover audio for each stanza, the title announcement, and the outro.
"""

import os
import asyncio
import subprocess
from typing import Any

from edge_tts import Communicate
from moviepy import AudioFileClip

from src.utils import retry

VOICE_MODEL: str = "en-US-AnaNeural"


@retry(max_attempts=3, backoff_factor=2)
def _generate_single_tts(text: str, output_path: str) -> None:
    """Generate a single TTS audio file synchronously.

    Args:
        text: Text to synthesize.
        output_path: Path to save the MP3.
    """
    communicate = Communicate(text, VOICE_MODEL)
    asyncio.run(communicate.save(output_path))


def _generate_silence(output_path: str, duration: float = 0.4) -> None:
    """Generate an empty MP3 file of specified duration using FFmpeg.

    Args:
        output_path: Path to save the silence MP3.
        duration: Length of silence in seconds.
    """
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(duration), "-q:a", "9", "-acodec", "libmp3lame",
            output_path
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def generate_voiceover(script: dict[str, Any], output_dir: str) -> dict[str, Any]:
    """Generate voiceovers for all script elements and pads with silence.

    Args:
        script: RhymeScript dictionary.
        output_dir: Directory to save generated MP3 files.

    Returns:
        Dictionary mapping audio paths as required by VideoAssets.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    result: dict[str, Any] = {
        "title_audio_path": "",
        "stanza_audio_paths": [],
        "outro_audio_path": ""
    }

    # 1. Title Announcement
    title_path = os.path.join(output_dir, "title.mp3")
    _generate_single_tts(script["title_announcement"], title_path)
    result["title_audio_path"] = title_path

    # 2. Base Silence file
    silence_path = os.path.join(output_dir, "silence.mp3")
    _generate_silence(silence_path, duration=0.4)

    # 3. Stanzas and Silence Padding
    stanzas = script.get("stanzas", [])
    for i, stanza in enumerate(stanzas):
        stanza_path = os.path.join(output_dir, f"stanza_{i:02d}.mp3")
        _generate_single_tts(stanza["text"], stanza_path)

        padded_path = os.path.join(output_dir, f"stanza_{i:02d}_padded.mp3")

        # Safely concatenate audio tracks using a complex filter graph
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", stanza_path, "-i", silence_path,
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[outa]",
                "-map", "[outa]", "-acodec", "libmp3lame", padded_path
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        os.replace(padded_path, stanza_path)
        result["stanza_audio_paths"].append(stanza_path)

    # 4. Outro Text
    outro_path = os.path.join(output_dir, "outro.mp3")
    _generate_single_tts(script["outro_text"], outro_path)
    result["outro_audio_path"] = outro_path

    # Cleanup temporary silence
    if os.path.exists(silence_path):
        os.remove(silence_path)

    return result


def get_audio_duration(path: str) -> float:
    """Return the duration of an audio file in seconds.

    Args:
        path: Path to the audio file.

    Returns:
        Duration in seconds as float.
    """
    clip = AudioFileClip(path)
    try:
        return float(clip.duration)
    finally:
        clip.close()
