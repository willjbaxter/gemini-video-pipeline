# Gemini Video Pipeline

This repository automates the process of:

1. Downloading a TikTok video (via `yt-dlp` with a custom User-Agent).
2. Uploading the video to Gemini (Bard) File API.
3. Prompting for recipe extraction.
4. Printing the final recipe text or JSON.

## Prerequisites

- Docker
- A valid Gemini API Key (set in `GEMINI_API_KEY`).

## Setup

1. **Clone** this repo:
   ```bash
   git clone https://github.com/<your-name>/gemini-video-pipeline.git
   cd gemini-video-pipeline
