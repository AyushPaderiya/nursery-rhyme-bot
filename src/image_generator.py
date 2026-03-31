"""Image generator module for the Nursery Rhyme Bot pipeline.

Generates one cartoon-style image per stanza using the Hugging Face
Inference API (FLUX.1-schnell model) with automatic fallback to
Pollinations.ai if HF is unavailable or rate-limited.
"""

import os
import time
import urllib.parse
from typing import Any

import requests
from PIL import Image

from src.utils import load_env, retry


def load_image_prompt_prefix() -> str:
    """Load the safety prefix prepended to every image prompt.

    Returns:
        The image prompt prefix string.
    """
    prefix_path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", "image_prompt_prefix.txt"
    )
    with open(prefix_path, "r", encoding="utf-8") as f:
        return f.read().strip()


@retry(max_attempts=3, backoff_factor=2)
def _call_hf_api(prompt: str) -> bytes:
    """Call Hugging Face Inference API to generate an image.

    Args:
        prompt: Full image generation prompt.

    Returns:
        Image bytes.
    """
    token = load_env("HF_API_TOKEN")
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt}

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.content


@retry(max_attempts=3, backoff_factor=2)
def _call_pollinations_api(prompt: str) -> bytes:
    """Call Pollinations.ai API to generate an image.

    Args:
        prompt: Full image generation prompt.

    Returns:
        Image bytes.
    """
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def validate_image(path: str) -> bool:
    """Validate that the image is not corrupt and is 1024x1024.

    Args:
        path: Path to the image file.

    Returns:
        True if valid.

    Raises:
        ValueError: If the image is corrupt or has incorrect dimensions.
    """
    try:
        with Image.open(path) as img:
            img.verify()  # Check for corruption
    except Exception as e:
        raise ValueError(f"Image {path} is corrupt or cannot be opened: {e}")

    # Reopen because verify() closes the file mechanism for some formats
    with Image.open(path) as img:
        if img.size != (1024, 1024):
            raise ValueError(f"Image {path} has invalid dimensions {img.size}. Expected (1024, 1024).")

    return True


def generate_images(script: dict[str, Any], output_dir: str) -> list[str]:
    """Generate images for every stanza in a RhymeScript.

    Args:
        script: Parsed RhymeScript dictionary.
        output_dir: Directory to write image files into.

    Returns:
        Ordered list of image file paths.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    prefix = load_image_prompt_prefix()
    stanzas = script.get("stanzas", [])
    image_paths = []

    for i, stanza in enumerate(stanzas):
        prompt = f"{prefix}{stanza['image_prompt']}"
        filename = f"image_{i:02d}.png"
        output_path = os.path.join(output_dir, filename)

        image_bytes = None
        service_used = "Hugging Face"
        try:
            image_bytes = _call_hf_api(prompt)
        except Exception as hf_err:
            print(f"Hugging Face API failed: {hf_err}. Falling back to Pollinations...")
            service_used = "Pollinations.ai"
            image_bytes = _call_pollinations_api(prompt)

        with open(output_path, "wb") as f:
            f.write(image_bytes)

        print(f"Generated {filename} using {service_used}")

        validate_image(output_path)
        image_paths.append(output_path)

        # 1-second sleep to avoid rate limiting
        time.sleep(1)

    if not image_paths:
        raise RuntimeError(
            "All image generation attempts failed. No images were produced."
        )

    return image_paths
