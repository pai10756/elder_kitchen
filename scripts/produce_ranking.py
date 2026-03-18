"""
營養素排行榜 — 全圖卡動畫生產腳本

用法:
  python scripts/produce_ranking.py ep04_calcium_top5.json

流程:
  Step 1: Gemini 3.1 Flash Preview 生成食材場景圖
  Step 2: Pillow 合成排行榜圖卡（文字疊加於場景圖上）
  Step 3: ElevenLabs v3 生成配音（含 Audio Tags 情緒標註）
  Step 4: ffmpeg 組裝最終影片（圖卡動畫 + 配音 + 字幕 + BGM）
"""

import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if os.name == "nt":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

BASE = Path(__file__).resolve().parents[1]


# ── .env loader ───────────────────────────────────────────

def load_env(env_path: Path):
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env(BASE / ".env")

GOOGLE_KEY = os.environ.get(
    "GOOGLE_API_KEY",
    os.environ.get("GEMINI_API_KEY", "AIzaSyA6QRc22XT5h9mkfPqGp0oh_bM9Rc3tw2Q"),
)
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "")
DRY_RUN = os.environ.get("DRY_RUN") == "1"


# ── Gemini 3.1 Flash Preview — 圖片生成 ──────────────────

def generate_image(prompt: str, output_path: Path):
    """用 Gemini 3.1 Flash Preview API 生成 9:16 場景圖"""
    print(f"  [IMG] {output_path.name}")
    if DRY_RUN:
        output_path.write_bytes(b"")
        print("  [IMG] DRY_RUN placeholder")
        return True

    if not GOOGLE_KEY:
        print("  [IMG] GOOGLE_API_KEY not set, skip")
        return False

    full_prompt = (
        "Generate a high-quality vertical portrait image (9:16 ratio, 1080x1920). "
        f"{prompt}"
    )
    payload = json.dumps({
        "contents": [{"parts": [{"text": full_prompt}]}],
    }).encode()

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{IMAGE_MODEL}:generateContent?key={GOOGLE_KEY}"
    )
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
            for part in (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            ):
                if "inlineData" in part:
                    img_bytes = base64.b64decode(part["inlineData"]["data"])
                    output_path.write_bytes(img_bytes)
                    print(f"  [IMG] saved {len(img_bytes):,} bytes")
                    return True
            print(f"  [IMG] no image in response: {json.dumps(data)[:200]}")
            return False
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                print(f"  [IMG] retry {attempt+1}/2 after HTTP {e.code}")
                time.sleep(3 * (attempt + 1))
                continue
            print(f"  [IMG] HTTP {e.code}: {body[:300]}")
            return False
        except Exception as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            print(f"  [IMG] failed: {e}")
            return False
    return False


# ── ElevenLabs v3 TTS（含 Audio Tags）────────────────────

def generate_audio(text: str, output_path: Path, voice_settings: dict | None = None):
    """ElevenLabs v3 TTS — 支援 [emotion] Audio Tags"""
    print(f"  [TTS] {output_path.name}: {text[:50]}...")
    if DRY_RUN:
        output_path.write_bytes(b"")
        print("  [TTS] DRY_RUN placeholder")
        return True

    if not ELEVENLABS_KEY or not ELEVENLABS_VOICE:
        print("  [TTS] ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID not set, skip")
        return False

    settings = voice_settings or {
        "stability": 0.35,
        "similarity_boost": 0.85,
        "style": 0.15,
        "use_speaker_boost": True,
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}"
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": settings,
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={
            "xi-api-key": ELEVENLABS_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                output_path.write_bytes(resp.read())
            print(f"  [TTS] saved {output_path.stat().st_size:,} bytes")
            return True
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                print(f"  [TTS] retry {attempt+1}/2 after HTTP {e.code}")
                time.sleep(1.5 * (attempt + 1))
                continue
            print(f"  [TTS] HTTP {e.code}: {body[:300]}")
            return False
        except Exception:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    return False


# ── Pillow — 排行榜圖卡合成 ──────────────────────────────

def generate_ranking_cards(ep: dict, asset_dir: Path, card_dir: Path):
    """用 Pillow 在場景圖上疊加排名文字，生成圖卡"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  [CARD] 請安裝 Pillow: pip install Pillow")
        return False

    card_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for part in ep.get("parts", []):
        if part.get("part") == "ranking_cards":
            cards = part.get("cards", [])
            break

    if not cards:
        print("  [CARD] 找不到 ranking_cards 段落")
        return False

    # 嘗試載入中文字型
    font_candidates = [
        "C:/Windows/Fonts/msjhbd.ttc",   # 微軟正黑粗體
        "C:/Windows/Fonts/msjh.ttc",      # 微軟正黑
        "C:/Windows/Fonts/msyh.ttc",      # 微軟雅黑
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    font_path = None
    for fp in font_candidates:
        if Path(fp).exists():
            font_path = fp
            break

    def get_font(size):
        if font_path:
            return ImageFont.truetype(font_path, size)
        return ImageFont.load_default()

    # 排名色彩
    rank_colors = {
        5: "#4CAF50",   # 綠
        4: "#2196F3",   # 藍
        3: "#FF9800",   # 橙
        2: "#E91E63",   # 粉紅
        1: "#FFD700",   # 金
        0: "#9E9E9E",   # 灰（牛奶對照）
    }

    W, H = 1080, 1920

    for card in cards:
        rank = card["rank"]
        food = card["food"]
        value_display = card["value_display"]
        highlight = card.get("highlight", "")
        bar_ratio = card.get("bar_ratio", 0.5)
        img_ref = card.get("food_image_ref")

        out_path = card_dir / f"card_rank{rank}.png"
        if out_path.exists():
            print(f"  [CARD] rank{rank} 已存在，跳過")
            continue

        # 載入背景食材圖或建立純色底
        bg_path = asset_dir / f"scene_{img_ref}.png" if img_ref else None
        if bg_path and bg_path.exists() and bg_path.stat().st_size > 100:
            try:
                bg = Image.open(bg_path).resize((W, H), Image.LANCZOS)
            except Exception:
                bg = Image.new("RGB", (W, H), "#2C2C2C")
        else:
            bg = Image.new("RGB", (W, H), "#2C2C2C")

        # 半透明暗層
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 140))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay)

        draw = ImageDraw.Draw(bg)
        color = rank_colors.get(rank, "#FFFFFF")

        # 排名數字（大）
        if rank > 0:
            rank_font = get_font(200)
            rank_text = f"#{rank}"
            bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
            rw = bbox[2] - bbox[0]
            draw.text(((W - rw) // 2, 300), rank_text, font=rank_font, fill=color)
        else:
            rank_font = get_font(100)
            rank_text = "VS"
            bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
            rw = bbox[2] - bbox[0]
            draw.text(((W - rw) // 2, 350), rank_text, font=rank_font, fill=color)

        # 食物名稱
        food_font = get_font(120)
        bbox = draw.textbbox((0, 0), food, font=food_font)
        fw = bbox[2] - bbox[0]
        draw.text(((W - fw) // 2, 580), food, font=food_font, fill="white")

        # 數值
        val_font = get_font(90)
        val_text = f"{value_display}/100g"
        bbox = draw.textbbox((0, 0), val_text, font=val_font)
        vw = bbox[2] - bbox[0]
        draw.text(((W - vw) // 2, 760), val_text, font=val_font, fill=color)

        # 數據條
        bar_y = 920
        bar_h = 60
        bar_max_w = W - 200
        bar_w = max(int(bar_max_w * bar_ratio), 40)
        draw.rounded_rectangle(
            [100, bar_y, 100 + bar_w, bar_y + bar_h],
            radius=30, fill=color,
        )
        # 牛奶對照線
        milk_x = 100 + int(bar_max_w * 0.08)
        if rank > 0:
            draw.line(
                [(milk_x, bar_y - 10), (milk_x, bar_y + bar_h + 10)],
                fill="#FFFFFF", width=3,
            )
            milk_label_font = get_font(28)
            draw.text((milk_x + 8, bar_y + bar_h + 15), "牛奶 113mg",
                       font=milk_label_font, fill="#AAAAAA")

        # 高亮文字
        if highlight:
            hl_font = get_font(56)
            bbox = draw.textbbox((0, 0), highlight, font=hl_font)
            hw = bbox[2] - bbox[0]
            draw.text(((W - hw) // 2, 1100), highlight, font=hl_font, fill="#FFD700")

        # 來源標注
        src_font = get_font(28)
        draw.text((60, H - 120), "資料來源：USDA FoodData Central",
                   font=src_font, fill="#888888")

        bg.convert("RGB").save(str(out_path), quality=95)
        print(f"  [CARD] saved rank{rank}: {out_path.name}")

    # Hook 卡（片頭標題 — 大字搶眼設計）
    hook_path = card_dir / "card_hook.png"
    if not hook_path.exists():
        hook_bg_path = asset_dir / "scene_1.png"
        if hook_bg_path.exists() and hook_bg_path.stat().st_size > 100:
            try:
                bg = Image.open(hook_bg_path).resize((W, H), Image.LANCZOS)
            except Exception:
                bg = Image.new("RGB", (W, H), "#1A1A2E")
        else:
            bg = Image.new("RGB", (W, H), "#1A1A2E")
        # 較深的暗層讓文字更突出
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 160))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay)
        draw = ImageDraw.Draw(bg)

        tc = ep.get("title_card", {})
        line1 = tc.get("line1", "")
        line2 = tc.get("line2", "")
        src = tc.get("source_text", "")

        def draw_outlined_text(draw, xy, text, font, fill, outline_fill="#000000", outline_width=6):
            """描邊文字 — 先畫黑色外框再畫彩色內文"""
            x, y = xy
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx * dx + dy * dy <= outline_width * outline_width:
                        draw.text((x + dx, y + dy), text, font=font, fill=outline_fill)
            draw.text(xy, text, font=font, fill=fill)

        # 主標題 — 超大金色描邊字
        t1_font = get_font(140)
        bbox = draw.textbbox((0, 0), line1, font=t1_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        t1_y = 580
        # 金色半透明底色塊
        pad = 30
        draw.rounded_rectangle(
            [(W - tw) // 2 - pad, t1_y - pad,
             (W + tw) // 2 + pad, t1_y + th + pad],
            radius=20,
            fill=(255, 215, 0, 40),
        )
        draw_outlined_text(
            draw, ((W - tw) // 2, t1_y), line1, t1_font,
            fill="#FFD700", outline_fill="#000000", outline_width=8,
        )

        # 副標題 — 大白字描邊
        t2_font = get_font(110)
        bbox = draw.textbbox((0, 0), line2, font=t2_font)
        tw = bbox[2] - bbox[0]
        t2_y = t1_y + th + 60
        draw_outlined_text(
            draw, ((W - tw) // 2, t2_y), line2, t2_font,
            fill="#FFFFFF", outline_fill="#000000", outline_width=6,
        )

        # 紅色強調底線
        line_y = t2_y + (bbox[3] - bbox[1]) + 20
        draw.rounded_rectangle(
            [(W - tw) // 2, line_y, (W + tw) // 2, line_y + 8],
            radius=4, fill="#FF4444",
        )

        # 來源小字
        if src:
            src_font = get_font(32)
            bbox = draw.textbbox((0, 0), src, font=src_font)
            sw = bbox[2] - bbox[0]
            draw.text(((W - sw) // 2, line_y + 50), src, font=src_font, fill="#AAAAAA")

        bg.convert("RGB").save(str(hook_path), quality=95)
        print(f"  [CARD] saved hook: {hook_path.name}")

    # CTA 卡（結尾）
    cta_path = card_dir / "card_cta.png"
    if not cta_path.exists():
        cta_bg_path = asset_dir / "scene_7.png"
        if cta_bg_path.exists() and cta_bg_path.stat().st_size > 100:
            try:
                bg = Image.open(cta_bg_path).resize((W, H), Image.LANCZOS)
            except Exception:
                bg = Image.new("RGB", (W, H), "#2C1810")
        else:
            bg = Image.new("RGB", (W, H), "#2C1810")
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 100))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay)
        draw = ImageDraw.Draw(bg)

        cta_font = get_font(64)
        lines_cta = ["收藏起來", "下次煮飯就用得上！"]
        y = 750
        for line in lines_cta:
            bbox = draw.textbbox((0, 0), line, font=cta_font)
            lw = bbox[2] - bbox[0]
            draw.text(((W - lw) // 2, y), line, font=cta_font, fill="white")
            y += 100

        ch_font = get_font(48)
        ch_text = "時時靜好"
        bbox = draw.textbbox((0, 0), ch_text, font=ch_font)
        cw = bbox[2] - bbox[0]
        draw.text(((W - cw) // 2, 1050), ch_text, font=ch_font, fill="#FFD700")

        bg.convert("RGB").save(str(cta_path), quality=95)
        print(f"  [CARD] saved cta: {cta_path.name}")

    return True


# ── ffmpeg — 圖卡串成影片 + 配音疊加 ─────────────────────

def assemble_video(ep: dict, card_dir: Path, audio_dir: Path, output_path: Path):
    """用 ffmpeg 把圖卡 + 配音組裝成最終影片"""
    import shutil
    import subprocess

    if DRY_RUN:
        print("  [ASSEMBLE] DRY_RUN — 跳過 ffmpeg 組裝")
        return True

    # 尋找 ffmpeg：優先系統安裝，fallback 到 imageio-ffmpeg
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"  [ASSEMBLE] 使用 imageio-ffmpeg: {ffmpeg_bin}")
        except ImportError:
            pass
    if not ffmpeg_bin:
        print("  [ASSEMBLE] ffmpeg 未安裝，請 pip install imageio-ffmpeg")
        return False

    # ── 取得每段配音的實際時長 ──
    def get_audio_duration(path):
        """用 mutagen 取得 MP3 時長"""
        try:
            from mutagen.mp3 import MP3
            return MP3(str(path)).info.length
        except Exception:
            # fallback: 從檔案大小估算 (128kbps)
            return path.stat().st_size * 8 / 128000

    audio_files = sorted(audio_dir.glob("seg_*.mp3"))
    seg_durations = {}
    for f in audio_files:
        # seg_00.mp3 → 0
        seg_id = int(f.stem.split("_")[1])
        seg_durations[seg_id] = get_audio_duration(f)
        print(f"  [AUDIO] {f.name}: {seg_durations[seg_id]:.2f}s")

    # ── 圖卡 ↔ 配音段落對應（從 voiceover segments 動態建立）──
    vo_segments = ep.get("voiceover", {}).get("segments", [])
    part_to_card = {
        "hook": "card_hook.png",
        "rank5": "card_rank5.png",
        "rank4": "card_rank4.png",
        "rank3": "card_rank3.png",
        "rank2": "card_rank2.png",
        "rank1": "card_rank1.png",
        "comparison": "card_rank0.png",
        "cta": "card_cta.png",
    }
    card_sequence = []
    for seg in vo_segments:
        seg_id = seg["id"]
        part_name = seg["part"]
        card_name = part_to_card.get(part_name)
        if card_name and seg_id in seg_durations:
            card_sequence.append((card_name, seg_durations[seg_id]))
    # fallback: 如果沒有 voiceover segments，用預設
    if not card_sequence:
        card_sequence = [
            ("card_hook.png",  seg_durations.get(0, 5.0)),
            ("card_rank5.png", seg_durations.get(1, 5.0)),
            ("card_rank4.png", seg_durations.get(2, 5.0)),
            ("card_rank3.png", seg_durations.get(3, 5.0)),
            ("card_rank2.png", seg_durations.get(4, 5.0)),
            ("card_rank1.png", seg_durations.get(5, 5.0)),
            ("card_cta.png",   seg_durations.get(6, 7.0)),
        ]

    # 建立圖卡序列檔
    concat_file = card_dir / "concat.txt"
    entries = []
    for card_name, dur in card_sequence:
        card_path = card_dir / card_name
        if not card_path.exists():
            print(f"  [WARN] {card_name} 不存在，跳過")
            continue
        entries.append(f"file '{card_path}'\nduration {dur:.2f}")
        print(f"  [SEQ] {card_name} → {dur:.2f}s")

    # ffmpeg concat 需要最後一張重複（不帶 duration）
    if entries:
        last_card = card_sequence[-1][0]
        entries.append(f"file '{card_dir / last_card}'")

    concat_file.write_text("\n".join(entries), encoding="utf-8")

    # 合併所有配音片段
    if audio_files:
        audio_concat = audio_dir / "audio_concat.txt"
        audio_entries = [f"file '{f}'" for f in audio_files]
        audio_concat.write_text("\n".join(audio_entries), encoding="utf-8")

        merged_audio = audio_dir / "voiceover_merged.mp3"
        result = subprocess.run([
            ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
            "-i", str(audio_concat),
            "-c", "copy", str(merged_audio),
        ], capture_output=True)
        if result.returncode != 0:
            print(f"  [ASSEMBLE] audio concat failed: {result.stderr.decode('utf-8', errors='ignore')[-300:]}")
            merged_audio = None
    else:
        merged_audio = None

    # 圖卡 → 影片
    video_only = card_dir / "video_only.mp4"
    subprocess.run([
        ffmpeg_bin, "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        str(video_only),
    ], check=True, capture_output=True)

    # 疊加配音
    if merged_audio and merged_audio.exists() and merged_audio.stat().st_size > 0:
        result = subprocess.run([
            ffmpeg_bin, "-y",
            "-i", str(video_only),
            "-i", str(merged_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output_path),
        ], capture_output=True)
        if result.returncode != 0:
            print(f"  [ASSEMBLE] ffmpeg merge failed (code {result.returncode})")
            print(f"  [ASSEMBLE] stderr: {result.stderr.decode('utf-8', errors='ignore')[-500:]}")
            # fallback: 輸出無聲版
            shutil.copy2(video_only, output_path)
            print(f"  [ASSEMBLE] fallback: 無聲版影片已輸出")
    else:
        shutil.copy2(video_only, output_path)

    print(f"  [ASSEMBLE] output: {output_path}")
    print(f"  [ASSEMBLE] size: {output_path.stat().st_size:,} bytes")
    return True


# ── 主流程 ────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/produce_ranking.py <episode.json>")
        print("範例: python scripts/produce_ranking.py ep04_calcium_top5.json")
        print()
        print("選項:")
        print("  --skip-images   跳過 Gemini 圖片生成")
        print("  --skip-audio    跳過 ElevenLabs 配音")
        print("  --skip-cards    跳過 Pillow 圖卡合成")
        print("  --skip-assemble 跳過 ffmpeg 組裝")
        sys.exit(1)

    json_file = sys.argv[1]
    flags = set(sys.argv[2:])

    ep_path = BASE / json_file
    if not ep_path.exists():
        print(f"找不到劇本: {ep_path}")
        sys.exit(1)

    ep = json.loads(ep_path.read_text(encoding="utf-8"))
    ep_num = ep.get("episode", "?")
    title = ep.get("topic_title", "")

    asset_dir = BASE / f"ep{ep_num:02d}_assets"
    card_dir = asset_dir / "cards"
    audio_dir = asset_dir / "audio"
    output_dir = BASE / "outputs"

    asset_dir.mkdir(parents=True, exist_ok=True)
    card_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"  營養素排行榜 — EP{ep_num:02d} 生產")
    print(f"  {title}")
    print(f"  模式：全圖卡動畫 + ElevenLabs 配音")
    print(f"  圖片模型：{IMAGE_MODEL}")
    print("=" * 60)

    # ── Step 1: Gemini 場景圖 ──
    if "--skip-images" not in flags:
        print(f"\n[1/4] 生成場景圖（{IMAGE_MODEL}）...")
        scenes = ep.get("scene_images", [])
        for scene in scenes:
            sid = scene["id"]
            out_path = asset_dir / f"scene_{sid}.png"
            if out_path.exists():
                print(f"  scene_{sid}.png 已存在，跳過")
                continue
            generate_image(scene["prompt"], out_path)
            time.sleep(2)  # rate limit
    else:
        print("\n[1/4] 跳過場景圖生成")

    # ── Step 2: Pillow 圖卡 ──
    if "--skip-cards" not in flags:
        print("\n[2/4] 合成排行榜圖卡（Pillow）...")
        generate_ranking_cards(ep, asset_dir, card_dir)
    else:
        print("\n[2/4] 跳過圖卡合成")

    # ── Step 3: ElevenLabs 配音 ──
    if "--skip-audio" not in flags:
        print("\n[3/4] 生成配音（ElevenLabs v3 + Audio Tags）...")
        vo = ep.get("voiceover", {})
        voice_settings = vo.get("voice_settings")
        for seg in vo.get("segments", []):
            seg_id = seg["id"]
            text = seg["text"]
            out_path = audio_dir / f"seg_{seg_id:02d}.mp3"
            if out_path.exists() and out_path.stat().st_size > 0:
                print(f"  seg_{seg_id:02d}.mp3 已存在，跳過")
                continue
            generate_audio(text, out_path, voice_settings)
            time.sleep(0.5)
    else:
        print("\n[3/4] 跳過配音生成")

    # ── Step 4: ffmpeg 組裝 ──
    if "--skip-assemble" not in flags:
        print("\n[4/4] 組裝最終影片（ffmpeg）...")
        final_path = output_dir / f"ep{ep_num:02d}_ranking.mp4"
        assemble_video(ep, card_dir, audio_dir, final_path)
    else:
        print("\n[4/4] 跳過組裝")

    # ── 完成 ──
    print("\n" + "=" * 60)
    print("  生產完成！")
    print("=" * 60)
    print(f"""
  資產目錄: {asset_dir}
    場景圖: {asset_dir}/scene_*.png
    圖卡:   {card_dir}/card_*.png
    配音:   {audio_dir}/seg_*.mp3

  輸出: {output_dir}/ep{ep_num:02d}_ranking.mp4

  下一步:
  1. 檢查圖卡效果，不滿意可刪除後重跑 --skip-images --skip-audio
  2. 用 ep{ep_num:02d}_calcium_top5.json 裡的 youtube_metadata 上傳
""")


if __name__ == "__main__":
    main()
