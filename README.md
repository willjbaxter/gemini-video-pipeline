# Gemini Video Pipeline

This repository automates the process of downloading a TikTok video, uploading it to Gemini (Bard) for audiovisual processing, and extracting a detailed cooking recipe from the video.

## Features

- Download TikTok videos using `yt-dlp`
- Upload video to Gemini File API
- Prompt Gemini 1.5 Pro to extract a structured recipe
- Print the final recipe output to console

## Requirements

- Docker
- A valid Gemini API Key (available as `GEMINI_API_KEY` environment variable)

## Getting Started

1. **Clone** this repo:
   ```bash
   git clone https://github.com/<your-username>/gemini-video-pipeline.git
   cd gemini-video-pipeline
