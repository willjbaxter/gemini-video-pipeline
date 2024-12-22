from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sys
import time
import subprocess
import uvicorn
import traceback
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

def parse_recipe_text(raw_text: str) -> dict:
    # Implement the function logic here
    # For example:
    return {"recipe": raw_text}  # Replace with actual parsing logic

def download_tiktok_video(video_url: str, output_name: str = "tiktok_video.mp4"):
    print(f"Attempting to download TikTok video from URL: {video_url}")
    try:
        cmd = [
            "yt-dlp",
            "--add-header", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "-o", output_name,
            video_url
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Video downloaded successfully as {output_name}")
        return output_name
    except subprocess.CalledProcessError as e:
        print(f"Video download failed. Error output: {e.stderr}")
        raise

def upload_and_extract_recipe(video_path: str):
    print(f"Uploading '{video_path}' to Gemini File API...")

    try:
        # Use files.upload_file() from submodule
        uploaded_file = files.upload_file(path=video_path)
        print("Upload started. File name:", uploaded_file.name)
        print("File state:", uploaded_file.state.name)

        # Wait until the file is ACTIVE
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        while uploaded_file.state.name == "PROCESSING":
            if time.time() - start_time > max_wait_time:
                raise TimeoutError("File processing timed out after 5 minutes")
            
            print("Video is processing...", end="", flush=True)
            time.sleep(10)
            # Refresh uploaded_file info
            uploaded_file = files.get_file(uploaded_file.name)
            print(".", end="", flush=True)

        if uploaded_file.state.name == "FAILED":
            raise ValueError("Video processing failed in Gemini. State=FAILED.")

        print(f"\nVideo file is ACTIVE. URI = {uploaded_file.uri}")

        # [Rest of your existing upload_and_extract_recipe function remains the same]
        # ... [Keep the rest of the function as it was in your previous implementation]

    except Exception as e:
        print(f"Error in upload_and_extract_recipe: {e}")
        print(traceback.format_exc())
        raise

@app.post("/api/extract")
async def extract_recipe(request: VideoRequest):
    try:
        print(f"Received video URL: {request.video_url}")
        
        # Download video
        try:
            video_path = download_tiktok_video(request.video_url)
        except subprocess.CalledProcessError as download_error:
            print(f"Video download failed: {download_error}")
            print(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=400, detail=f"Failed to download video: {str(download_error)}")
        
        try:
            # Process with Gemini
            recipe_text = upload_and_extract_recipe(video_path)
            
            # Parse the recipe text
            try:
                parsed_recipe = parse_recipe_text(recipe_text)
                
                return {
                    "status": "success",
                    "data": parsed_recipe,
                    "recipe": recipe_text  # Keep original text as fallback
                }
            except Exception as parse_error:
                print(f"Recipe parsing error: {parse_error}")
                print(f"Full traceback: {traceback.format_exc()}")
                return {
                    "status": "partial",
                    "recipe": recipe_text,
                    "error": str(parse_error)
                }
        
        except Exception as process_error:
            print(f"Video processing error: {process_error}")
            print(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to process video: {str(process_error)}")
        finally:
            # Cleanup downloaded video
            if os.path.exists(video_path):
                os.remove(video_path)
                
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)