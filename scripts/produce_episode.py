"""
長輩廚房｜吃對了嗎？ — 半自動化生產腳本

用法:
  python scripts/produce_episode.py ep01_white_porridge.json

流程:
  Step 1: 讀取劇本 JSON
  Step 2: 用 Gemini API 生成場景圖（自動）
  Step 3: 印出 Seedance Part1 prompt（手動貼到即夢）
  Step 4: 等待確認 → 印出 Part2 prompt
  Step 5: 等待確認 → 呼叫 assemble 組裝
"""

import io
import json
import os
import shutil
import sys
import time
from pathlib import Path

if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parents[1]
FACTORY = BASE.parent / "health-digest-factory"

# ── Gemini API ──
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    "AIzaSyA6QRc22XT5h9mkfPqGp0oh_bM9Rc3tw2Q"
)
GEMINI_MODEL = "gemini-2.5-flash-image"


def load_episode(json_path: str) -> dict:
    """讀取劇本 JSON"""
    p = BASE / json_path
    if not p.exists():
        print(f"找不到劇本: {p}")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════
#  Step 1: 生成場景圖（Gemini API）
# ═══════════════════════════════════════════

def generate_scene_images(ep: dict, output_dir: Path):
    """用 Gemini API 生成場景圖"""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("請先安裝 google-genai: pip install -U google-genai pillow")
        sys.exit(1)

    client = genai.Client(api_key=GEMINI_API_KEY)
    output_dir.mkdir(parents=True, exist_ok=True)

    scenes = ep.get("scene_images", [])
    for scene in scenes:
        sid = scene["id"]
        desc = scene["description"]
        prompt = scene["prompt"]
        out_path = output_dir / f"scene_{sid}.png"

        if out_path.exists():
            print(f"  場景圖 {sid} 已存在，跳過: {out_path.name}")
            continue

        print(f"  生成場景圖 {sid}：{desc}")
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio="9:16",
                    ),
                ),
            )

            saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    from PIL import Image as PILImage
                    from io import BytesIO
                    image = PILImage.open(BytesIO(part.inline_data.data))
                    image.save(str(out_path))
                    print(f"    ✓ 已儲存: {out_path.name}")
                    saved = True
                    break

            if not saved:
                print(f"    ✗ 未收到圖片，請手動生成")

        except Exception as e:
            print(f"    ✗ 生成失敗: {e}")
            print(f"      請手動用 Nano Banana 生成，prompt 已存在 seedance 資料夾")

        # 避免 API rate limit
        time.sleep(2)


# ═══════════════════════════════════════════
#  Seedance prompt 模板（套用 SKILL.md 規範）
# ═══════════════════════════════════════════

def build_seedance_prompt(ep: dict, part_num: int) -> str:
    """
    從 JSON 結構化資料組裝 Seedance 2.0 prompt。

    套用 seedance skill 的最佳實踐：
    - 時間戳用「0-5秒」格式
    - 台詞用引號 + 「台湾口音普通话」
    - 「||」斷句 → 「短暂停顿」
    - Sound / Music 獨立成行
    - 禁止項放結尾
    - Part2 加定裝照 @引用
    """
    global_spec = ep.get("global_spec", "")
    character = ep.get("character", "")
    sound = ep.get("sound", "")
    music = ep.get("music", "")

    # 找到對應 part
    parts = ep.get("parts", [])
    part_data = None
    for p in parts:
        if p["part"] == part_num:
            part_data = p
            break
    if not part_data:
        return f"[錯誤] 找不到 part {part_num} 的資料"

    # 計算該 part 用到哪些場景圖（按 scene_ref 排序去重）
    scene_refs = sorted(set(s["scene_ref"] for s in part_data["scenes"]))
    # 建立 scene_ref → @图片N 的映射
    # Part2 多一張定裝照，場景圖從 @图片1 開始，定裝照放最後
    ref_to_img = {}
    for i, ref in enumerate(scene_refs, start=1):
        ref_to_img[ref] = f"@图片{i}"

    lines = []

    # ── 全域規格 ──
    lines.append(global_spec)
    lines.append("")

    # ── Part2 人物參考 ──
    if part_num == 2:
        costume_idx = len(scene_refs) + 1
        lines.append(f"人物形象参考@图片{costume_idx}。{character}。")
    else:
        lines.append(f"{character}。")
    lines.append("")

    # ── 各場景 ──
    for scene in part_data["scenes"]:
        img_ref = ref_to_img[scene["scene_ref"]]
        time_tag = scene["time"]
        scene_desc = scene["scene_desc"]
        action = scene["action"]
        camera = scene["camera"]
        dialogue = scene["dialogue"]

        # 組裝場景描述
        scene_line = f"{time_tag}：{img_ref}的{scene_desc}。{action}。镜头{camera}。"

        # 組裝台詞（|| → 短暂停顿）
        parts_dialogue = dialogue.split("||")
        dialogue_lines = []
        for j, d in enumerate(parts_dialogue):
            d = d.strip()
            dialogue_lines.append(f'她用台湾口音普通话说："{d}"')
            if j < len(parts_dialogue) - 1:
                dialogue_lines.append("短暂停顿。")

        lines.append(scene_line)
        for dl in dialogue_lines:
            lines.append(dl)
        lines.append("")

    # ── Sound / Music ──
    if sound:
        lines.append(f"Sound：{sound}")
    if music:
        lines.append(f"Music：{music}")

    # ── 禁止項 ──
    lines.append("禁止：任何文字、字幕、LOGO或水印。")

    return "\n".join(lines)


def get_part_upload_guide(ep: dict, part_num: int, output_dir: Path) -> str:
    """產生該 part 的場景圖上傳指引"""
    parts = ep.get("parts", [])
    part_data = None
    for p in parts:
        if p["part"] == part_num:
            part_data = p
            break
    if not part_data:
        return ""

    scenes = ep.get("scene_images", [])
    scene_map = {s["id"]: s for s in scenes}
    scene_refs = sorted(set(s["scene_ref"] for s in part_data["scenes"]))

    lines = []
    for i, ref in enumerate(scene_refs, start=1):
        scene = scene_map.get(ref, {})
        img_path = output_dir / f"scene_{ref}.png"
        status = "✓" if img_path.exists() else "✗ 缺少"
        desc = scene.get("description", f"場景 {ref}")
        lines.append(f"  {status} scene_{ref}.png → @图片{i} — {desc}")

    if part_num == 2:
        costume_idx = len(scene_refs) + 1
        lines.append(f"  ＋ 定裝照 → @图片{costume_idx} — 三視圖定裝照（人物一致性）")

    return "\n".join(lines)


# ═══════════════════════════════════════════
#  Step 2-4: Seedance prompt 引導
# ═══════════════════════════════════════════

def print_separator():
    print("\n" + "=" * 60)


def print_prompt_block(title: str, prompt: str):
    """格式化印出 prompt，方便複製"""
    print_separator()
    print(f"  {title}")
    print_separator()
    print()
    print(prompt)
    print()
    print("-" * 60)


def wait_for_user(message: str) -> str:
    """等待使用者確認"""
    print()
    return input(f">>> {message} ").strip()


def seedance_workflow(ep: dict, output_dir: Path):
    """引導使用者完成 Seedance 影片生成"""
    ep_num = ep.get("episode", "?")
    title = ep.get("topic_title", "")

    print_separator()
    print(f"  EP{ep_num:02d}｜{title}")
    print(f"  Seedance 影片生成流程")
    print_separator()

    # ── Part1 ──
    part1_prompt = build_seedance_prompt(ep, 1)
    part1_guide = get_part_upload_guide(ep, 1, output_dir)

    print("\n【步驟 1/4】上傳場景圖 → 複製 Part1 prompt → 按生成")
    print(f"\n  場景圖位置: {output_dir}")
    print(f"\n  Part1 上傳順序：")
    print(part1_guide)

    print_prompt_block("PART 1 PROMPT（複製以下全部）", part1_prompt)

    wait_for_user("Part1 場景圖已上傳、prompt 已提交生成？按 Enter 繼續...")

    # ── 定裝照（人物一致性）──
    print("\n【步驟 2/4】Part1 完成後，製作定裝照")
    print("""
  1. Part1 影片完成 → 截圖滿意的人物臉部
  2. 到即夢「圖片生成」上傳截圖，貼以下 prompt：

  ┌─────────────────────────────────────────────┐
  │ 画出这个角色正面，侧面，背面三视图，          │
  │ 保持原角色面部特征，五官和发型不变。          │
  └─────────────────────────────────────────────┘

  3. 生成的三視圖定裝照，留著 Part2 上傳用
""")

    wait_for_user("定裝照已準備好？按 Enter 繼續...")

    # ── Part2 ──
    part2_prompt = build_seedance_prompt(ep, 2)
    part2_guide = get_part_upload_guide(ep, 2, output_dir)

    print("\n【步驟 3/4】上傳場景圖 + 定裝照 → 複製 Part2 prompt → 按生成")
    print(f"\n  Part2 上傳順序：")
    print(part2_guide)

    print_prompt_block("PART 2 PROMPT（複製以下全部）", part2_prompt)

    wait_for_user("Part2 場景圖+定裝照已上傳、prompt 已提交生成？按 Enter 繼續...")

    # ── 下載 ──
    print("\n【步驟 4/4】下載影片")
    print("\n  兩段影片都完成後，下載到 health-digest-factory 根目錄。")


# ═══════════════════════════════════════════
#  Step 5: 組裝（呼叫 assemble_seedance.py）
# ═══════════════════════════════════════════

def generate_assemble_config(ep: dict):
    """從劇本 JSON 產生 assemble 所需的參數"""
    tc = ep.get("title_card", {})
    subs = ep.get("subtitles", [])

    print_separator()
    print("  組裝參數（貼到 assemble_seedance.py）")
    print_separator()

    print(f"""
# ── 片頭標題卡 ──
TITLE_TEXT_LINE1 = "{tc.get('line1', '')}"
TITLE_TEXT_LINE2 = "{tc.get('line2', '')}"

# ── 字幕 ──
SUBTITLES = [""")

    for sub in subs:
        print(f'    {{"text": "{sub["text"]}", '
              f'"start": {sub["start"]}, "end": {sub["end"]}, '
              f'"color": "white", "size": 48}},')

    print("]")
    print()


# ═══════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/produce_episode.py <episode.json>")
        print("範例: python scripts/produce_episode.py ep01_white_porridge.json")
        sys.exit(1)

    json_file = sys.argv[1]
    ep = load_episode(json_file)

    ep_num = ep.get("episode", 1)
    title = ep.get("topic_title", "")
    output_dir = BASE / f"ep{ep_num:02d}_seedance"

    print("=" * 60)
    print(f"  長輩廚房｜吃對了嗎？ — EP{ep_num:02d} 生產")
    print(f"  主題：{title}")
    print("=" * 60)

    # ── Step 1: 場景圖 ──
    print("\n[1/3] 生成場景圖（Gemini API）...")
    generate_scene_images(ep, output_dir)

    # ── Step 2-4: Seedance 影片 ──
    print("\n[2/3] Seedance 影片生成...")
    resp = wait_for_user("開始 Seedance 流程？(y/n): ")
    if resp.lower() in ("y", "yes", ""):
        seedance_workflow(ep, output_dir)

    # ── Step 5: 組裝參數 ──
    print("\n[3/3] 產生組裝參數...")
    generate_assemble_config(ep)

    # ── 完成 ──
    print_separator()
    print("  生產流程完成！")
    print_separator()
    print(f"""
  下一步：
  1. 下載 Part1 + Part2 影片到 {FACTORY}
  2. 把上面的組裝參數貼到 assemble_seedance.py
  3. 執行: cd {FACTORY} && python scripts/assemble_seedance.py
  4. 用 {json_file} 裡的 youtube_metadata 上傳 YouTube
""")


if __name__ == "__main__":
    main()
