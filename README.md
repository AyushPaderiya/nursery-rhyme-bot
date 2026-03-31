# Nursery Rhyme Bot 🤖👶

An automated, daily pipeline that generates unique, high-quality, and YouTube-compliant nursery rhyme videos. It uses Gemini for scripting, edge_tts for voiceovers, AI image generation, and FFmpeg for video assembly with dynamic Ken Burns effects. 

## Architecture

```text
 ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
 │ 1. Scheduler │────▶│ 2. Generator │────▶│ 3. Assembly  │
 │ (GitHub Act.)│     │ (Gemini AI)  │     │ (FFmpeg/Py)  │
 └──────────────┘     └──────────────┘     └──────────────┘
                             │                    │
                             ▼                    ▼
                      ┌──────────────┐     ┌──────────────┐
                      │ 4. Media AI  │     │ 5. Publisher │
                      │ (TTS/Images) │────▶│ (YouTube API)│
                      └──────────────┘     └──────────────┘
```

## Prerequisites
- Python 3.11
- FFmpeg installed system-wide (must be available in PATH)
- Git

## Step-by-Step One-Time Setup

**a. Fork/clone this repository**
```bash
git clone https://github.com/yourusername/nursery-rhyme-bot.git
cd nursery-rhyme-bot
pip install -r requirements.txt
```

**b. Create a YouTube channel and enable YouTube Data API v3** 
Go to the [Google Cloud Console](https://console.cloud.google.com/), create a new project, and enable the "YouTube Data API v3" library.

**c. Create OAuth2 credentials (Desktop app type)** 
Configure the OAuth consent screen. Under Credentials, create an OAuth client ID of type "Desktop app". Download the JSON and note your Client ID and Client Secret.

**d. Run the local auth helper script** 
Set your credentials in your `.env` or environment variables, then run:
```bash
python scripts/get_refresh_token.py
```
Follow the browser prompts to generate your `YOUTUBE_REFRESH_TOKEN`.

**e. Get Gemini API key** 
Visit [Google AI Studio](https://aistudio.google.com/) and grab a free Gemini API key to power the script generation.

**f. Create a Hugging Face account and get access token** 
Go to [Hugging Face](https://huggingface.co/), create an account, and generate a write-capable access token for image inference.

**g. Create a Telegram bot via @BotFather** 
Message `@BotFather` on Telegram to create a new bot. Save the `TELEGRAM_BOT_TOKEN`, and get your `TELEGRAM_CHAT_ID` via `@userinfobot`.

**h. Download CC0 music tracks** 
Download royalty-free CC0 background music (e.g., from the [Free Music Archive](https://freemusicarchive.org/)) and place the tracks in the `assets/music/` directory. Be sure you map moods to correct subfolders if necessary.

**i. Add GitHub Secrets** 
Go to your forked repository settings -> Secrets and variables -> Actions. Add all 8 secrets:
- `GEMINI_API_KEY`
- `HF_API_TOKEN`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GH_PAT` (Personal Access Token with repo commit access)

**j. Set OAuth app to Production (critical)** 
In the Google Cloud Console, ensure your OAuth consent screen is published to **Production**. If left in "Testing", the refresh token will expire after 7 days, breaking the pipeline.

**k. Trigger a manual workflow run** 
Go to the "Actions" tab in GitHub, select "Daily Nursery Rhyme Video", and click "Run workflow" to test the pipeline end-to-end.

## Customisation
- **Schedule**: Edit `.github/workflows/daily_video.yml` to change the `cron` schedule.
- **Categories**: Add new themes in the prompts passed to Gemini in `src/content_generator.py`.
- **Voices**: Change TTS voices inside `src/tts_generator.py`.

## Monetization Roadmap
Aiming for the YouTube Partner Program (YPP) requires:
- **1,000 Subscribers** and **4,000 watch hours** (or 10 million Short views).
- Focus on consistency, high-resolution thumbnails, and catchy titles.
- Once eligible, ensure no content mimics misleading practices (always adhere strictly to YouTube Kids guidelines).

## Troubleshooting
- **Runaway Billing**: This script has a hard kill switch configured at 60 minutes in CI/CD to prevent runaway processes.
- **Empty Refeshes**: Ensure the app is in "Production" inside GCP.
- **Stuck Videos**: Verify you are providing accurate metadata and the video contains valid audio streams.
- **FFmpeg Errors**: Confirm `ffmpeg` is system path accessible and using exactly version 3.11 for Python.

## License
MIT License
