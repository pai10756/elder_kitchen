"""用參考圖 + Gemini 3.1 Flash Preview 重新生成指定場景圖"""
import base64
import io
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parents[1]

# load .env
env_path = BASE / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "")
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")


def get_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext.lstrip("."), "image/jpeg")


def generate_with_reference(ref_image: Path, prompt: str, output: Path):
    print(f"  [IMG] generating {output.name} with ref {ref_image.name}...")
    ref_b64 = base64.b64encode(ref_image.read_bytes()).decode()
    mime = get_mime(ref_image)

    payload = json.dumps({
        "contents": [{
            "parts": [
                {"inlineData": {"mimeType": mime, "data": ref_b64}},
                {"text": (
                    "Generate a high-quality vertical portrait image (9:16 ratio, 1080x1920). "
                    "Use the attached reference image as a style and subject guide. "
                    f"{prompt}"
                )}
            ]
        }],
        "generationConfig": {
            "responseModalities": ["image", "text"],
        },
    }).encode("utf-8")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{IMAGE_MODEL}:generateContent?key={GOOGLE_KEY}"
    )
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                img_bytes = base64.b64decode(part["inlineData"]["data"])
                output.write_bytes(img_bytes)
                print(f"  [IMG] saved {len(img_bytes):,} bytes → {output.name}")
                return True
        # check for text response
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "text" in part:
                print(f"  [IMG] text response: {part['text'][:200]}")
        print(f"  [IMG] no image in response")
        return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"  [IMG] HTTP {e.code}: {body[:300]}")
        return False
    except Exception as e:
        print(f"  [IMG] failed: {e}")
        return False


def main():
    asset_dir = BASE / "ep04_assets"

    # scene_2: 莧菜 — 參考 1af976bddb99cb58.jpg
    ref2 = asset_dir / "1af976bddb99cb58.jpg"
    out2 = asset_dir / "scene_2.png"
    if ref2.exists():
        generate_with_reference(
            ref2,
            "A bowl of freshly stir-fried amaranth greens (莧菜) on a wooden dining table. "
            "The leaves should be dark green with reddish-purple stems, glistening with oil. "
            "A pair of wooden chopsticks beside the bowl. Warm natural lighting, cozy home dining atmosphere. "
            "Realistic food photography style, 9:16 vertical. "
            "No text, no people, no watermarks, no logos.",
            out2,
        )
    else:
        print(f"  [SKIP] ref image not found: {ref2}")

    # scene_6: 小魚乾 — 參考 c83dcd05d2170c2e564391a72dc1e958.jpg
    ref6 = asset_dir / "c83dcd05d2170c2e564391a72dc1e958.jpg"
    out6 = asset_dir / "scene_6.png"
    if ref6.exists():
        generate_with_reference(
            ref6,
            "A small white dish with golden dried small fish (小魚乾/丁香魚) neatly arranged. "
            "The fish are small, whole, and crispy-looking. "
            "Warm lighting, wooden table surface, homey snack atmosphere. "
            "Realistic food photography style, 9:16 vertical. "
            "No text, no people, no watermarks, no logos.",
            out6,
        )
    else:
        print(f"  [SKIP] ref image not found: {ref6}")

    print("\nDone. Now re-run card synthesis:")
    print("  python scripts/produce_ranking.py ep04_calcium_top5.json --skip-images --skip-assemble")


if __name__ == "__main__":
    main()
