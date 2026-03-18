"""
長輩廚房｜吃對了嗎？ — 影片組裝工具
1. 從 JSON 讀取劇本設定（標題、字幕）
2. 生成片頭標題卡（3s，暗化主播背景 + Hook 大字）
3. 接合 片頭 + Part1 + Part2
4. 去即夢浮水印 + 燒入 ASS 字幕 + 頻道浮水印
5. 產出封面圖（供 YouTube Shorts 上傳用）

用法:
  python scripts/assemble_episode.py ep01_white_porridge.json
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 路徑 ──
BASE = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 720, 1280
FPS = 24

# ── 字型 ──
FONT_BOLD = "C:/Windows/Fonts/msjhbd.ttc"
FONT_REGULAR = "C:/Windows/Fonts/msjh.ttc"

# ── 片頭設定 ──
TITLE_DURATION = 3.0

# ── 浮水印 ──
WATERMARK_TEXT = "時時靜好｜長輩廚房"

# ── 即夢浮水印位置（原始 405x720 → 需按比例換算到 720x1280）──
# 原始位置大約在右下角，upscale 後重新定位
DELOGO_X = 580
DELOGO_Y = 1195
DELOGO_W = 130
DELOGO_H = 75


def to_ffmpeg_path(p) -> str:
    return str(p).replace("\\", "/")


def get_ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(cmd: list[str], step_name: str = ""):
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        print(f"  ✗ {step_name} 失敗:")
        print(result.stderr[-800:])
        sys.exit(1)
    return result


# ═══════════════════════════════════════════
#  片頭標題卡
# ═══════════════════════════════════════════

def _draw_outlined_text(draw, text, font, color, outline_color, outline_width, y_center):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (WIDTH - tw) // 2
    y = int(y_center - th // 2)

    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                   (-1, -1), (1, -1), (-1, 1), (1, 1)]:
        draw.text((x + dx * outline_width, y + dy * outline_width),
                  text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=color)


def create_title_card(part1_path: Path, title_card_cfg: dict,
                      source_text: str, out_dir: Path) -> Path:
    ffmpeg_exe = get_ffmpeg_exe()

    # 截取 Part1 第 2 秒當背景
    bg_path = out_dir / "title_bg.jpg"
    run_ffmpeg([
        ffmpeg_exe, "-y",
        "-ss", "2",
        "-i", to_ffmpeg_path(part1_path),
        "-vframes", "1",
        "-s", f"{WIDTH}x{HEIGHT}",
        to_ffmpeg_path(bg_path),
    ], "截取背景")

    # 製作標題卡圖片
    if bg_path.exists():
        img = Image.open(str(bg_path)).convert("RGB")
        if img.size != (WIDTH, HEIGHT):
            img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
        img = ImageEnhance.Brightness(img).enhance(0.30)
        img = ImageEnhance.Color(img).enhance(0.4)
        # 暖色調遮罩（配合廚房風格）
        overlay = Image.new("RGB", (WIDTH, HEIGHT), (30, 15, 5))
        img = Image.blend(img, overlay, 0.25)
    else:
        img = Image.new("RGB", (WIDTH, HEIGHT), (20, 12, 8))

    draw = ImageDraw.Draw(img)

    line1 = title_card_cfg.get("line1", "")
    line2 = title_card_cfg.get("line2", "")

    # 第 1 行：金黃大字
    font1 = ImageFont.truetype(FONT_BOLD, 110)
    _draw_outlined_text(draw, line1, font1,
                        color=(255, 200, 50),
                        outline_color=(0, 0, 0),
                        outline_width=6,
                        y_center=HEIGHT * 0.38)

    # 第 2 行：白色大字
    font2 = ImageFont.truetype(FONT_BOLD, 90)
    _draw_outlined_text(draw, line2, font2,
                        color=(255, 255, 255),
                        outline_color=(0, 0, 0),
                        outline_width=5,
                        y_center=HEIGHT * 0.52)

    # 底部來源
    font_src = ImageFont.truetype(FONT_REGULAR, 30)
    _draw_outlined_text(draw, source_text, font_src,
                        color=(180, 150, 100),
                        outline_color=(0, 0, 0),
                        outline_width=2,
                        y_center=HEIGHT * 0.66)

    img_path = out_dir / "title_card.png"
    img.save(str(img_path), quality=95)

    # 同時存一份封面圖（YouTube Shorts 封面用）
    cover_path = out_dir / "cover.png"
    img.save(str(cover_path), quality=95)
    print(f"  封面圖: {cover_path}")

    # 靜態圖 → 3s 影片（含淡入淡出）
    video_path = out_dir / "title_card.mp4"
    run_ffmpeg([
        ffmpeg_exe, "-y",
        "-loop", "1",
        "-i", to_ffmpeg_path(img_path),
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(TITLE_DURATION),
        "-vf", f"fade=in:0:d=0.5,fade=out:st={TITLE_DURATION - 0.5}:d=0.5",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-r", str(FPS),
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "yuv420p",
        "-shortest",
        to_ffmpeg_path(video_path),
    ], "片頭影片")

    print(f"  片頭標題卡: {video_path.name} ({TITLE_DURATION}s)")
    return video_path


# ═══════════════════════════════════════════
#  ASS 字幕
# ═══════════════════════════════════════════

def to_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def color_to_ass(color: str) -> str:
    if color == "white":
        return "&HFFFFFF&"
    elif color == "yellow":
        return "&H00FFFF&"
    elif color.startswith("0x"):
        r, g, b = color[2:4], color[4:6], color[6:8]
        return f"&H{b}{g}{r}&"
    return "&HFFFFFF&"


def build_ass(subtitles: list[dict], total_duration: float) -> str:
    lines = [
        "[Script Info]",
        f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}",
        "ScriptType: v4.00+",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
    ]

    # 浮水印樣式（右上角）
    lines.append(
        "Style: Watermark,Microsoft JhengHei,22,&H80FFFFFF,&H000000FF,"
        "&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,2,0,9,0,20,20,1"
    )

    # 每條字幕獨立樣式
    for i, sub in enumerate(subtitles):
        color = color_to_ass(sub.get("color", "white"))
        size = sub.get("size", 48)
        margin_v = 220
        lines.append(
            f"Style: Sub{i},Microsoft JhengHei,{size},{color},&H000000FF,"
            f"&H00000000,&H80000000,1,0,0,0,100,100,2,0,1,4,1,2,20,20,{margin_v},1"
        )

    lines += [
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    # 浮水印
    wm_start = to_ass_time(TITLE_DURATION)
    wm_end = to_ass_time(total_duration)
    lines.append(f"Dialogue: 1,{wm_start},{wm_end},Watermark,,0,0,0,,{WATERMARK_TEXT}")

    # 字幕
    for i, sub in enumerate(subtitles):
        start = to_ass_time(sub["start"])
        end = to_ass_time(sub["end"])
        lines.append(f"Dialogue: 0,{start},{end},Sub{i},,0,0,0,,{sub['text']}")

    return "\n".join(lines)


# ═══════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════

def find_videos(ep_dir: Path) -> tuple[Path | None, Path | None]:
    """在 ep_dir 裡找 Part1 和 Part2 影片"""
    part1 = None
    part2 = None

    # Part2: 優先找 fixed 版
    fixed = list(ep_dir.glob("*fixed*"))
    if fixed:
        part2 = fixed[0]

    # Part1: 找不是 Part2、不是 title_card、不是 fixed 的 mp4
    for f in sorted(ep_dir.glob("*.mp4")):
        if f == part2:
            continue
        if "title_card" in f.name or "fixed" in f.name or "final" in f.name:
            continue
        if part1 is None:
            part1 = f

    return part1, part2


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/assemble_episode.py <episode.json>")
        print("範例: python scripts/assemble_episode.py ep01_white_porridge.json")
        sys.exit(1)

    # ── 讀取 JSON ──
    json_path = BASE / sys.argv[1]
    if not json_path.exists():
        print(f"找不到: {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        ep = json.load(f)

    ep_num = ep.get("episode", 1)
    topic = ep.get("topic_title", "")
    title_card_cfg = ep.get("title_card", {})
    source_text = title_card_cfg.get("source_text", "")
    subtitles = ep.get("subtitles", [])

    ep_dir = BASE / f"ep{ep_num:02d}_seedance"

    print("=" * 55)
    print(f"  長輩廚房｜吃對了嗎？ — EP{ep_num:02d} 組裝")
    print(f"  主題：{topic}")
    print("=" * 55)

    # ── 找影片 ──
    part1, part2 = find_videos(ep_dir)
    if not part1 or not part2:
        print(f"  找不到影片！Part1={part1}, Part2={part2}")
        print(f"  請確認 {ep_dir} 裡有 Part1 mp4 和 part2_fixed.mp4")
        sys.exit(1)

    print(f"  Part1: {part1.name}")
    print(f"  Part2: {part2.name}")

    # 取得影片時長
    from moviepy import VideoFileClip
    with VideoFileClip(str(part1)) as c1:
        dur1 = c1.duration
    with VideoFileClip(str(part2)) as c2:
        dur2 = c2.duration
    print(f"  時長: Part1={dur1:.2f}s + Part2={dur2:.2f}s")

    ffmpeg_exe = get_ffmpeg_exe()
    out_dir = BASE / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── [1/3] 片頭 ──
    print("\n[1/3] 生成片頭標題卡...")
    title_card = create_title_card(part1, title_card_cfg, source_text, out_dir)

    # ── [2/3] 接合 ──
    print("\n[2/3] 統一格式 → 接合三段...")
    with tempfile.TemporaryDirectory(prefix="elder_kitchen_") as tmpdir:
        tmp = Path(tmpdir)

        # 複製到 temp（避免中文路徑問題）
        tmp_title = tmp / "title.mp4"
        tmp_part1 = tmp / "part1.mp4"
        tmp_part2 = tmp / "part2.mp4"
        shutil.copy2(str(title_card), str(tmp_title))
        shutil.copy2(str(part1), str(tmp_part1))
        shutil.copy2(str(part2), str(tmp_part2))

        # 統一格式（720x1280, 24fps, h264+aac）
        for src, dst_name in [(tmp_title, "n_title.mp4"),
                               (tmp_part1, "n_part1.mp4"),
                               (tmp_part2, "n_part2.mp4")]:
            dst = tmp / dst_name
            run_ffmpeg([
                ffmpeg_exe, "-y", "-i", to_ffmpeg_path(src),
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
                "-r", str(FPS),
                "-s", f"{WIDTH}x{HEIGHT}",
                "-pix_fmt", "yuv420p",
                to_ffmpeg_path(dst),
            ], f"統一格式 {dst_name}")

        # concat
        concat_file = tmp / "concat.txt"
        concat_file.write_text(
            "file 'n_title.mp4'\nfile 'n_part1.mp4'\nfile 'n_part2.mp4'\n",
            encoding="utf-8",
        )

        concat_out = tmp / "concat.mp4"
        run_ffmpeg([
            ffmpeg_exe, "-y",
            "-f", "concat", "-safe", "0",
            "-i", to_ffmpeg_path(concat_file),
            "-c", "copy",
            to_ffmpeg_path(concat_out),
        ], "接合")

        total_duration = TITLE_DURATION + dur1 + dur2
        print(f"  接合完成: {total_duration:.2f}s")

        # ── [3/3] 字幕 + 去浮水印 ──
        print("\n[3/3] 燒入字幕 + 去浮水印...")

        # 補上 color/size 預設值
        for sub in subtitles:
            sub.setdefault("color", "white")
            sub.setdefault("size", 48)

        ass_content = build_ass(subtitles, total_duration)
        ass_file = tmp / "subs.ass"
        ass_file.write_text(ass_content, encoding="utf-8-sig")

        ass_escaped = to_ffmpeg_path(ass_file).replace(":", "\\:")
        vf = f"delogo=x={DELOGO_X}:y={DELOGO_Y}:w={DELOGO_W}:h={DELOGO_H},ass='{ass_escaped}'"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_name = f"ep{ep_num:02d}_{ts}.mp4"
        final_tmp = tmp / final_name

        run_ffmpeg([
            ffmpeg_exe, "-y",
            "-i", to_ffmpeg_path(concat_out),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "15",
            "-c:a", "copy",
            to_ffmpeg_path(final_tmp),
        ], "字幕+去浮水印")

        # 輸出
        final_dir = out_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        final_path = final_dir / final_name
        shutil.copy2(str(final_tmp), str(final_path))

    size_mb = final_path.stat().st_size / 1024 / 1024
    print(f"\n{'=' * 55}")
    print(f"  完成！")
    print(f"  檔案: {final_path}")
    print(f"  大小: {size_mb:.1f} MB")
    print(f"  結構: {TITLE_DURATION}s 片頭 + {dur1:.1f}s + {dur2:.1f}s = {total_duration:.1f}s")
    print(f"  封面: {out_dir / 'cover.png'}")
    print(f"{'=' * 55}")

    # ── YouTube 元資料 ──
    yt = ep.get("youtube_metadata", {})
    if yt:
        print(f"\n  YouTube 標題: {yt.get('title', '')}")
        print(f"  (說明文字在 JSON 的 youtube_metadata.description)")


if __name__ == "__main__":
    main()
