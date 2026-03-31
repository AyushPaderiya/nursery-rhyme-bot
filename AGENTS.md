# Project Rules — Nursery Rhyme Bot

## Language & Style

- Python 3.11 only
- Type hints on all function signatures
- Docstrings on all functions (Google style)
- No hardcoded credentials — all secrets via os.environ
- f-strings for string formatting, no .format() or %

## Architecture Rules

- Never import alerting at module level from utils.py — use lazy import inside retry decorator
- Every external API call must be wrapped with the @retry decorator from src/utils.py
- All file paths use os.path.join(), never string concatenation
- Temp files go to /tmp/rhyme\_\* directories only

## Testing Rules

- All external API calls must be mockable via unittest.mock
- Every module must have a corresponding test file in tests/
- Tests must pass before marking any task complete

## YouTube Compliance (NON-NEGOTIABLE)

- madeForKids: True must appear in EVERY YouTube upload request
- selfDeclaredMadeForKids: True must also be set
- seo_title must be truncated to 100 characters maximum
- No adult themes, violence, or scary content in any prompt

## Git Rules

- Commit messages for tracker updates must include [skip ci] to prevent pipeline loops
- Do not commit API keys or .env files

## Performance Rules

- FFmpeg preset must be 'ultrafast' in video assembly
- Target total pipeline runtime under 50 minutes
