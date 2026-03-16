"""Generate multi-angle character turnaround sheet using Gemini 2.0 Flash."""

import base64, sys, os
from pathlib import Path
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: please set GEMINI_API_KEY environment variable")
    sys.exit(1)
INPUT_IMG = Path(__file__).parent / "face_sreenshot.png"
OUTPUT_IMG = Path(__file__).parent / "character_multiangle.png"

client = genai.Client(api_key=API_KEY)

img_bytes = INPUT_IMG.read_bytes()

prompt = "画出这个角色的多视角图，保证原角色面部特征，五官和发型不变。白色背景，清晰的正面、侧面和背面全身图。"

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[
        types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
        prompt,
    ],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
    ),
)

for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        OUTPUT_IMG.write_bytes(part.inline_data.data)
        print(f"Saved: {OUTPUT_IMG}")
        break
    elif part.text:
        print(f"Text: {part.text}")
else:
    print("No image generated in response")
    sys.exit(1)
