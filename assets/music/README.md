# Background Music Assets

## ⚠️ Important: Replace Placeholder Files

The `.mp3` files in this directory are **0-byte placeholders**. You MUST replace
them with actual CC0-licensed music tracks before running the pipeline.

## Recommended Sources

All tracks must be **royalty-free** and **CC0 / Public Domain** licensed to avoid
YouTube copyright strikes.

### Lullaby Tracks
- [Free Music Archive – Lullaby](https://freemusicarchive.org/search?adv=1&music-filter-CC-attribution-only=&music-filter-CC-attribution-sharealike=&music-filter-CC-attribution-noderivs=&music-filter-public-domain=1&music-filter-commercial-allowed=1&music-filter-remix-allowed=1&quicksearch=lullaby)
- [Pixabay Music – Lullaby](https://pixabay.com/music/search/lullaby/)

### Upbeat Tracks
- [Free Music Archive – Upbeat Kids](https://freemusicarchive.org/search?adv=1&music-filter-public-domain=1&music-filter-commercial-allowed=1&music-filter-remix-allowed=1&quicksearch=upbeat+kids)
- [Pixabay Music – Happy Kids](https://pixabay.com/music/search/happy%20kids/)

### Educational Tracks
- [Free Music Archive – Playful](https://freemusicarchive.org/search?adv=1&music-filter-public-domain=1&music-filter-commercial-allowed=1&music-filter-remix-allowed=1&quicksearch=playful+children)
- [Pixabay Music – Playful](https://pixabay.com/music/search/playful/)

### Seasonal Tracks
- [Free Music Archive – Festive](https://freemusicarchive.org/search?adv=1&music-filter-public-domain=1&music-filter-commercial-allowed=1&music-filter-remix-allowed=1&quicksearch=festive)
- [Pixabay Music – Festive](https://pixabay.com/music/search/festive%20holiday/)

## File Naming Convention

Keep the exact filenames listed in `mood_map.json`. The `music_selector.py`
module references these filenames to pick a track based on the rhyme's mood tag.

## Requirements

- Format: MP3
- Duration: At least 3 minutes (will be looped if shorter than the video)
- Bitrate: 128kbps or higher
- Content: Instrumental only (no vocals)
