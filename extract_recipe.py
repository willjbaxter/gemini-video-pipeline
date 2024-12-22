import os
import sys
import time
import subprocess
import json

import google.generativeai as genai

# Get Gemini API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def download_tiktok_video(video_url: str, output_name: str = "tiktok_video.mp4"):
    """
    Download TikTok video using yt-dlp.
    """
    print(f"Downloading TikTok video from URL: {video_url}")
    cmd = [
        "yt-dlp",
        "-o",
        output_name,
        video_url
    ]
    subprocess.run(cmd, check=True)
    print(f"Video downloaded as {output_name}")
    return output_name

def upload_and_extract_recipe(video_path: str):
    """
    Upload the video to Gemini File API, wait for it to become ACTIVE,
    then prompt the model for a recipe extraction.
    """
    print(f"Uploading '{video_path}' to Gemini File API...")
    uploaded_file = genai.upload_file(path=video_path)

    print("Upload started. File name:", uploaded_file.name)
    print("File state:", uploaded_file.state.name)

    # Wait until the file is ACTIVE
    while uploaded_file.state.name == "PROCESSING":
        print("Video is processing...", end="", flush=True)
        time.sleep(10)
        uploaded_file = genai.get_file(uploaded_file.name)
        print(".", end="", flush=True)

    if uploaded_file.state.name == "FAILED":
        raise ValueError("Video processing failed in Gemini. State=FAILED.")

    print(f"\nVideo file is ACTIVE. URI = {uploaded_file.uri}")

    # Create your recipe prompt
    recipe_prompt = """
You are a professional recipe writer tasked with converting this TikTok cooking video into a clear, detailed recipe. 
Watch the video carefully (including audio and visuals at 1 FPS) and extract all relevant information using these sections:

RECIPE NAME:
Creator: @username
Estimated Total Time: X minutes
Servings: X

EQUIPMENT NEEDED:
- [Equipment]

INGREDIENTS:
- [Ingredient 1]: [Amount], [Notes]

INSTRUCTIONS:
1. [Step 1]
2. [Step 2]

RECIPE NOTES:
- [Any tips, clarifications, safety warnings]
- [Missing info if uncertain]

If you cannot confidently extract the recipe, return:
RECIPE NAME:
Could not extract recipe - insufficient information
"""

    model = genai.GenerativeModel(model_name="gemini-1.5-pro")

    print("Sending prompt to Gemini 1.5 Pro...")
    response = model.generate_content(
        [uploaded_file, recipe_prompt],
        request_options={"timeout": 600}  # 10 minutes
    )

    raw_text = response.text
    print("\n===== RAW GEMINI RESPONSE =====\n")
    print(raw_text)
    print("\n================================")

    # If you want to parse the text further (extract JSON or specific sections), do it here.
    # For now, just return the raw text.
    return raw_text

def main():
    """
    Main CLI entry point:
    - python extract_recipe.py https://www.tiktok.com/@someuser/video/12345
    """
    if len(sys.argv) < 2:
        print("Usage: python extract_recipe.py <TikTok_URL>")
        sys.exit(1)

    video_url = sys.argv[1]

    # 1) Download the TikTok video
    local_video = download_tiktok_video(video_url, "tiktok_video.mp4")

    # 2) Upload to Gemini, prompt, print result
    final_text = upload_and_extract_recipe(local_video)

    # Print final structured output
    print("\n===== FINAL RECIPE EXTRACTION =====\n")
    print(final_text)
    print("\n====================================")

if __name__ == "__main__":
    main()
