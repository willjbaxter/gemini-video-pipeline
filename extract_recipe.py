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

def parse_recipe_text(raw_text: str) -> dict:
    """Parse the raw recipe text into frontend-compatible format"""
    try:
        lines = raw_text.split('\n')
        current_section = None
        
        recipe_data = {
            "recipe_overview": {
                "title": "",
                "prep_time": "0 minutes",
                "cook_time": "0 minutes",
                "servings": 0,
                "difficulty": "Medium",
                "cuisine_type": "Unknown"
            },
            "ingredients": [],
            "equipment": [],
            "instructions": []
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse recipe name and creator
            if line.startswith('RECIPE NAME:'):
                recipe_data['recipe_overview']['title'] = line.replace('RECIPE NAME:', '').strip()
            
            # Parse time and servings
            elif 'Total Time:' in line:
                total_time = line.split('Total Time:')[1].strip()
                time_value = total_time.split()[0]  # Extract numeric value
                try:
                    total_minutes = int(time_value)
                    # Split total time between prep and cook
                    recipe_data['recipe_overview']['prep_time'] = f"{total_minutes // 2} minutes"
                    recipe_data['recipe_overview']['cook_time'] = f"{total_minutes // 2} minutes"
                except ValueError:
                    pass
            
            elif 'Servings:' in line:
                servings = line.split('Servings:')[1].strip()
                if servings.lower() != 'unknown':
                    try:
                        recipe_data['recipe_overview']['servings'] = int(servings)
                    except ValueError:
                        pass

            # Track current section
            elif line == 'EQUIPMENT NEEDED:':
                current_section = 'equipment'
            elif line == 'INGREDIENTS:':
                current_section = 'ingredients'
            elif line == 'INSTRUCTIONS:':
                current_section = 'instructions'
            
            # Parse content based on section
            elif line.startswith('- ') and current_section == 'equipment':
                equipment = line.replace('- ', '').strip()
                recipe_data['equipment'].append(equipment)
            
            elif line.startswith('- ') and current_section == 'ingredients':
                ingredient_line = line.replace('- ', '').strip()
                parts = ingredient_line.split(':')
                if len(parts) == 2:
                    item = parts[0].strip()
                    details = parts[1].strip().split(',', 1)
                    amount_str = details[0].strip() if details else 'to taste'
                    notes = details[1].strip() if len(details) > 1 else ''
                    
                    # Split amount into number and unit
                    import re
                    amount_match = re.match(r'^([\d./-]+)\s*(.*)$', amount_str)
                    if amount_match:
                        amount_num, unit = amount_match.groups()
                    else:
                        amount_num, unit = amount_str, None
                    
                    recipe_data['ingredients'].append({
                        'item': item,
                        'amount': amount_num,
                        'unit': unit if unit else None,
                        'notes': notes if notes else None
                    })
            
            elif line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) and current_section == 'instructions':
                instruction = line.split('.', 1)[1].strip()
                recipe_data['instructions'].append(instruction)

        return recipe_data
    except Exception as e:
        print(f"Error parsing recipe: {e}")
        raise ValueError(f"Failed to parse recipe format: {str(e)}")

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