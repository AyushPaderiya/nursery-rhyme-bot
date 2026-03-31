"""Main orchestrator for the Nursery Rhyme Bot pipeline.

Coordinates the full daily pipeline:
1. Load content tracker and determine today's category + length tier.
2. Generate a nursery rhyme script via Gemini.
3. Generate TTS audio for all stanzas, title, and outro.
4. Generate cartoon images for each stanza.
5. Select background music based on mood.
6. Assemble the 1080p MP4 video with Ken Burns effects.
7. Generate a YouTube thumbnail.
8. Upload video + thumbnail to YouTube.
9. Update content_tracker.json and commit back to the repo.
10. Send Telegram alert on any failure.
"""

import os
import shutil
import sys
import traceback
from typing import Any

from src.utils import (
    ensure_dir,
    cleanup_files,
    get_today_category,
    get_today_length_tier,
    iso_now,
)
from src.alerting import send_telegram_alert, send_success_notification
from src.content_generator import load_tracker, generate_script, get_used_titles, update_tracker, commit_tracker
from src.tts_generator import generate_voiceover, get_audio_duration
from src.image_generator import generate_images
from src.music_selector import select_track, trim_and_duck_music
from src.video_assembler import assemble_video, validate_video, calculate_total_duration
from src.thumbnail_generator import generate_thumbnail
from src.youtube_uploader import upload_video


def build_voice_segments(voice_assets: dict[str, Any]) -> list[tuple[float, float]]:
    """Calculate start and end times for all voiceover segments to duck background music.

    Args:
        voice_assets: Dictionary containing audio paths.

    Returns:
        List of (start_time, end_time) tuples in seconds.
    """
    segments = []
    current_time = 0.0

    # Title audio
    title_path = voice_assets.get("title_audio_path")
    if title_path and os.path.exists(title_path):
        dur = get_audio_duration(title_path)
        segments.append((current_time, current_time + dur))
    
    current_time += 2.5 # TITLE_DURATION

    # Stanza audios
    stanza_paths = voice_assets.get("stanza_audio_paths", [])
    inter_gap = 0.4  # Matches video_assembler INTER_STANZA_GAP
    
    for path in stanza_paths:
        if os.path.exists(path):
            dur = get_audio_duration(path)
            segments.append((current_time, current_time + dur))
            current_time += dur + inter_gap

    # Outro audio
    outro_path = voice_assets.get("outro_audio_path")
    if outro_path and os.path.exists(outro_path):
        dur = get_audio_duration(outro_path)
        segments.append((current_time, current_time + dur))

    return segments


def run_pipeline() -> None:
    """Main daily pipeline orchestrator."""
    import time
    
    def log(msg: str) -> None:
        print(f"[main] {msg}")

    try:
        t_start = time.perf_counter()
        
        # ── Step 1: Load state
        tracker = load_tracker()
        category = get_today_category(tracker)
        length_tier = get_today_length_tier(tracker)
        used_titles = get_used_titles(tracker)

        # ── Step 2: Generate script
        t0 = time.perf_counter()
        script = generate_script(category, length_tier, used_titles)
        log(f"Script generated in {time.perf_counter() - t0:.1f}s: {script['title']}")

        # ── Step 3: Create temp working directory
        work_dir = f"/tmp/rhyme_{iso_now().replace(':', '-')}"
        ensure_dir(work_dir)

        # ── Step 4: Generate media assets (sequential — respects API rate limits)
        t0 = time.perf_counter()
        voice_assets = generate_voiceover(script, work_dir)
        log(f"TTS generated in {time.perf_counter() - t0:.1f}s.")
        
        t0 = time.perf_counter()
        image_paths = generate_images(script, work_dir)
        log(f"Images generated in {time.perf_counter() - t0:.1f}s.")
        
        music_path = select_track(script["mood"])

        # ── Step 5: Calculate timing and duck music
        total_duration = calculate_total_duration({**voice_assets, "image_paths": image_paths})
        voice_segments = build_voice_segments(voice_assets)   # list of (start, end) tuples
        ducked_music_path = trim_and_duck_music(
            music_path, 
            total_duration, 
            voice_segments,
            f"{work_dir}/music_ducked.mp3"
        )

        # ── Step 6: Assemble video
        t0 = time.perf_counter()
        assets = {
            "script": script,
            **voice_assets,
            "image_paths": image_paths,
            "ducked_music_path": ducked_music_path # Adjusted key name from prompt to match video_assembler
        }
        video_path = f"{work_dir}/final_video.mp4"
        assemble_video(assets, video_path)
        validate_video(video_path)
        log(f"Video assembly finished in {time.perf_counter() - t0:.1f}s.")

        # ── Step 7: Generate thumbnail
        thumbnail_path = f"{work_dir}/thumbnail.jpg"
        generate_thumbnail(image_paths[0], script["seo_title"], thumbnail_path)

        # ── Step 8: Upload to YouTube
        t0 = time.perf_counter()
        upload_result = upload_video(video_path, thumbnail_path, script)
        log(f"YouTube upload finished in {time.perf_counter() - t0:.1f}s: {upload_result['video_url']}")

        # ── Step 9: Update tracker and commit
        update_tracker(tracker, upload_result, script)
        commit_tracker()

        # ── Step 10: Cleanup and notify
        cleanup_files([video_path, thumbnail_path] + voice_assets["stanza_audio_paths"]
                      + [voice_assets["title_audio_path"], voice_assets["outro_audio_path"]]
                      + image_paths + [ducked_music_path])

        # Remove the work directory itself to prevent temp file leaks
        if os.path.isdir(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

        send_success_notification(script["title"], upload_result["video_url"], total_duration)
        
        total_time = time.perf_counter() - t_start
        log(f"Pipeline complete in {total_time / 60:.1f} minutes! (Total: {total_time:.1f}s)")

    except Exception as e:
        tb = traceback.format_exc()
        try:
            send_telegram_alert(str(e), tb)
        except Exception as alert_exc:
            print(f"[alerting] Failed to send alert: {alert_exc}", file=sys.stderr)
        
        # Trigger the retry decorator logic if this script is invoked by an outer @retry, or just fail CI.
        raise


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        import traceback
        send_telegram_alert(str(e), traceback.format_exc())
        sys.exit(1)
