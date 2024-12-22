from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sys
import time
import subprocess
import uvicorn
import google.generativeai as genai
from google.generativeai import files

app = FastAPI()

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

class VideoRequest(BaseModel):
    video_url: str

def download_tiktok_video(video_url: str, output_name: str = "tiktok_video.mp4"):
    print(f"Downloading TikTok video from URL: {video_url}")
    cmd = [
        "yt-dlp",
        "--add-header", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "-o", output_name,
        video_url
    ]
    subprocess.run(cmd, check=True)
    print(f"Video downloaded as {output_name}")
    return output_name

def upload_and_extract_recipe(video_path: str):
    print(f"Uploading '{video_path}' to Gemini File API...")

    # Use files.upload_file() from submodule
    uploaded_file = files.upload_file(path=video_path)
    print("Upload started. File name:", uploaded_file.name)
    print("File state:", uploaded_file.state.name)

    # Wait until the file is ACTIVE
    while uploaded_file.state.name == "PROCESSING":
        print("Video is processing...", end="", flush=True)
        time.sleep(10)
        # Refresh uploaded_file info
        uploaded_file = files.get_file(uploaded_file.name)
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
    print("Sending prompt to Gemini 1.5 Pro for recipe extraction...")

    response = model.generate_content(
        [uploaded_file, recipe_prompt],
        request_options={"timeout": 600}  # 10 minutes
    )

    raw_text = response.text
    print("\n===== RAW GEMINI RESPONSE =====\n")
    print(raw_text)
    print("\n================================")

    return raw_text

@app.post("/api/extract")
async def extract_recipe(request: VideoRequest):
    try:
        # Download video
        video_path = download_tiktok_video(request.video_url)
        
        try:
            # Process with Gemini
            recipe_text = upload_and_extract_recipe(video_path)
            
            return {
                "status": "success",
                "recipe": recipe_text
            }
        finally:
            # Cleanup downloaded video
            if os.path.exists(video_path):
                os.remove(video_path)
                
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)