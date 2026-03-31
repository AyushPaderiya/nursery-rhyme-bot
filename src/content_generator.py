"""Content generator module for the Nursery Rhyme Bot pipeline.

Uses Google Gemini 2.0 Flash API to generate nursery rhyme scripts
(lyrics, stanzas, image prompts, SEO metadata) based on the current
day's category and length tier from the content rotation schedule.
"""

import json
import os
import requests
import base64
from typing import Any
import google.generativeai as genai

from src.utils import load_env, retry, iso_now


def load_prompt_template() -> str:
    """Load the rhyme generator prompt template from disk.

    Returns:
        The raw prompt template string with {category}, {length_tier},
        and {used_titles} placeholders.
    """
    prompt_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "rhyme_generator.txt"
    )
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def get_used_titles(tracker: dict) -> list[str]:
    """Extract previously used titles from the content tracker.

    Args:
        tracker: Parsed content_tracker.json dictionary.

    Returns:
        List of title strings already used.
    """
    return [v.get("title", "") for v in tracker.get("videos", [])]


@retry(max_attempts=3, backoff_factor=2)
def generate_script(
    category: str, length_tier: str, used_titles: list[str]
) -> dict[str, Any]:
    """Generate a nursery rhyme script via Google Gemini API.

    Args:
        category: One of 'classic', 'educational', 'seasonal'.
        length_tier: One of 'short' or 'long'.
        used_titles: List of titles to avoid repeating.

    Returns:
        Parsed RhymeScript dictionary matching the shared contract.
    """
    # 1. Load the system prompt
    prompt_template = load_prompt_template()

    # 2. Build the user message
    used_titles_json = json.dumps(used_titles)
    user_message = prompt_template.replace(
        "{category}", category
    ).replace(
        "{length_tier}", length_tier
    ).replace(
        "{used_titles}", used_titles_json
    )

    # 3. Call the Gemini 2.0 Flash API
    api_key = load_env("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.0-flash")

    response = model.generate_content(
        contents=user_message,
        generation_config=genai.GenerationConfig(
            temperature=0.9,
            max_output_tokens=4096,
            response_mime_type="application/json"
        )
    )

    # 4. Parse the response JSON strictly
    try:
        script = json.loads(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}")

    required_root_fields = [
        "title", "seo_title", "description", "tags", "mood",
        "length_tier", "category", "stanzas", "outro_text", "title_announcement"
    ]

    for field in required_root_fields:
        if field not in script:
            raise ValueError(f"Missing required field in RhymeScript: '{field}'")

    # 5. Validate all stanzas
    if not isinstance(script["stanzas"], list):
        raise ValueError("Field 'stanzas' must be a list.")

    for i, stanza in enumerate(script["stanzas"]):
        for field in ["text", "image_prompt", "duration_estimate_seconds"]:
            if field not in stanza:
                raise ValueError(f"Missing required field in stanza {i}: '{field}'")

    # 6. Ensure the generated title is not in used_titles
    if script["title"] in used_titles:
        raise ValueError(f"Generated title '{script['title']}' is already in used_titles.")

    # 7. Return the validated dict
    return script


def load_tracker() -> dict:
    """Reads data/content_tracker.json and returns its contents."""
    tracker_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "content_tracker.json"
    )
    try:
        with open(tracker_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"videos": []}


def update_tracker(tracker: dict, upload_result: dict, script: dict) -> None:
    """Appends a new entry to tracker['videos'] and writes it back to disk."""
    entry = {
        "video_id": upload_result.get("video_id", ""),
        "video_url": upload_result.get("video_url", ""),
        "title": script.get("title", ""),
        "category": script.get("category", ""),
        "length_tier": script.get("length_tier", ""),
        "mood": script.get("mood", ""),
        "uploaded_at": iso_now(),
        "stanza_count": len(script.get("stanzas", []))
    }

    if "videos" not in tracker:
        tracker["videos"] = []

    tracker["videos"].append(entry)

    tracker_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "content_tracker.json"
    )

    os.makedirs(os.path.dirname(tracker_path), exist_ok=True)
    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(tracker, f, indent=2)


@retry(max_attempts=3, backoff_factor=2)
def commit_tracker() -> None:
    """Uses the GitHub REST API to commit the updated tracker to the repo."""
    gh_pat = load_env("GH_PAT")

    # Can get repository via GH_REPO env var, or fallback to default
    repo = os.environ.get("GH_REPO", "AyushPaderiya/nursery-rhyme-bot")

    file_path = "data/content_tracker.json"
    api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}"

    headers = {
        "Authorization": f"token {gh_pat}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. GET the current file SHA
    get_resp = requests.get(api_url, headers=headers)

    sha = None
    if get_resp.status_code == 200:
        sha = get_resp.json().get("sha")

    # Read the local tracker content
    local_tracker_path = os.path.join(
        os.path.dirname(__file__), "..", file_path
    )
    with open(local_tracker_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # 2. PUT the updated file
    put_data = {
        "message": "chore: update content tracker [skip ci]",
        "content": content
    }
    if sha:
        put_data["sha"] = sha

    put_resp = requests.put(api_url, headers=headers, json=put_data)

    if put_resp.status_code == 409:
        raise RuntimeError(
            f"GitHub API 409 Conflict: the SHA for '{file_path}' is stale. "
            f"Another pipeline run may have updated the file concurrently. "
            f"Retry the commit after re-fetching the latest SHA."
        )

    put_resp.raise_for_status()


if __name__ == "__main__":
    pass
