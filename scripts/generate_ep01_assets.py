#!/usr/bin/env python3
"""
EP01 白粥 — 場景圖 + 人物多角度圖 + Seedance Prompts
使用 Gemini 2.5 Flash Image 生成場景圖與人物定裝照。

用法:
  python scripts/generate_ep01_assets.py
"""

import io
import json
import os
import sys
import time
from pathlib import Path

if os.name == "nt":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Config ──
BASE = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE / "ep01_seedance"
SCRIPT_JSON = BASE / "ep01_white_porridge.json"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash-image"

# ── 角色描述（55歲亞洲女性，廚房居家風格）──
CHARACTER_DESC = (
    "一位55岁亚洲女性，黑色短发微卷，自然银丝点缀，圆润温暖的脸庞。"
    "穿着浅米色棉麻围裙，内搭暖橘色针织上衣。"
    "自然淡妆，气色红润健康，眼神温暖慈祥，"
    "笑容亲切像邻家阿姨，站在居家厨房料理台前。"
)

# ── 角色多角度定裝照 Prompt ──
CHARACTER_CARD_PROMPT = (
    "3:2 横版角色设定卡/转面板（turnaround sheet / model sheet），纯白干净背景。"
    f"角色描述：{CHARACTER_DESC}"
    "脸型轮廓（下颌线、颧骨、下巴形状）、眼型、眉形、鼻梁与鼻翼、嘴唇厚薄与嘴角形状、"
    "年龄气质必须严格一致；发际线与发型尽量一致。只允许同一个角色，禁止换脸、禁止五官漂移。"
    "\n\n版式（单张合成图，干净网格，统一光影与色彩）：\n"
    "左侧（约60%宽度）：两张大图上下排列：\n"
    "1）全身正视站姿（中性站姿，手臂自然下垂，穿围裙）\n"
    "2）全身90°侧视站姿（中性站姿）\n\n"
    "右侧（约40%宽度）：2×3 网格六张头部小图：\n"
    "1）头部正面（neutral）\n"
    "2）头部背面（back of head，用于发型与头型一致性）\n"
    "3）头部左45°（neutral）\n"
    "4）头部右45°（neutral）\n"
    "5）表情特写：开心/愉悦（happy，慈祥的笑容）\n"
    "6）表情特写：认真/关切（concerned，微微皱眉但温暖）\n\n"
    "质感与画质：高端写实棚拍/电影级人像质感，眼睛清晰锐利对焦，"
    "真实皮肤微观质感（毛孔与细纹，不磨皮不塑料），全图各分区曝光与色彩一致，"
    "8K细节，轻胶片颗粒，超干净白底，脚下干净柔和投影。\n\n"
    "强约束：画面内不允许任何可读文字（不要 FRONT/SIDE 等标签），"
    "不要字幕、不要logo、不要UI叠层、不要水印块；不要卡通二次元；"
    "不要多余人物；不要畸形手指/多肢体/脸崩；六张小图必须是同一张脸同一发际线。"
)

# ── 場景圖 Prompts（從 ep01 JSON 取）──
SCENE_PROMPTS = [
    {
        "id": "scene_1",
        "filename": "scene_1.png",
        "description": "居家廚房料理台，砂鍋白粥冒蒸汽",
        "prompt": (
            "居家厨房木质料理台上，一个陶瓷砂锅里盛着白色米粥，蒸汽缓缓升起，"
            "旁边放着小碟酱菜和一双筷子，暖色灯光，温馨厨房氛围。"
            "写实摄影风格，9:16竖屏。不要任何文字、人物、水印、LOGO。"
        ),
    },
    {
        "id": "scene_2",
        "filename": "scene_2.png",
        "description": "五穀粥食材特寫：糙米、燕麥、地瓜、雞蛋",
        "prompt": (
            "木质砧板上整齐摆放着糙米、燕麦片、切块地瓜和两颗鸡蛋，色彩丰富，"
            "自然光照射，背景是温暖的居家厨房，写实摄影风格，9:16竖屏。"
            "不要任何文字、人物、水印、LOGO。"
        ),
    },
    {
        "id": "scene_3",
        "filename": "scene_3.png",
        "description": "一碗色彩豐富的五穀粥，配蛋和青菜",
        "prompt": (
            "木质餐桌上一碗浓稠的五谷粥，上面放着半颗水煮蛋和翠绿青菜，"
            "色彩丰富营养感十足，旁边有一双木筷，暖色自然光，居家早餐氛围。"
            "写实摄影风格，9:16竖屏。不要任何文字、人物、水印、LOGO。"
        ),
    },
]

# ── Seedance Part1 & Part2 Prompts ──
SEEDANCE_PART1 = (
    "电影级短片，居家风格，9:16竖屏。"
    "全域规格：warm暖色温，自然光+暖灯光，木质桌面，居家厨房氛围，温馨舒适。"
    "\n\n"
    "人物形象参考@图片2。"
    "\n\n"
    "[00:00-00:05] @图片1的居家厨房场景。"
    "@图片2的人物站在料理台前，面前砂锅白粥冒着蒸汽，她表情认真看向镜头。"
    "镜头从中景缓慢推近至近景。\n"
    '她用台湾口音普通话说："白粥煮越烂，升糖指数越高。'
    '煮太久的粥，血糖反应跟糖水差不多。"'
    "\n\n"
    "[00:05-00:10] @图片1的砂锅白粥特写。"
    "白粥翻滚冒泡，蒸汽升腾。镜头特写，缓慢横移展示粥的绵密质地。\n"
    '旁白（台湾口音温暖女性声线）："国际食品期刊研究发现，'
    '白米煮超过30分钟，升糖指数飙到96。糖水才100。"'
    "\n\n"
    "[00:10-00:15] 厨房场景。"
    "她站在料理台前微微摇头，表情关切。镜头推至近景。\n"
    '她用台湾口音普通话说："很多人觉得喝粥养胃又健康，'
    '但煮太烂的白粥，反而让血糖忽高忽低。"'
    "\n\n"
    "Sound：厨房轻微环境声，粥冒泡的咕噜声\n"
    "Music：温暖欢快配乐，居家氛围，轻快节奏\n"
    "禁止：任何文字、字幕、LOGO或水印。"
)

SEEDANCE_PART2 = (
    "电影级短片，居家风格，9:16竖屏。"
    "全域规格：warm暖色温，自然光+暖灯光，木质桌面，居家厨房氛围，温馨舒适。"
    "\n\n"
    "@图片1的人物形象作为本片主角。"
    "\n\n"
    "[00:00-00:05] 场景参考@图片2。"
    "她在料理台前展示糙米、燕麦和地瓜，表情变得轻松。镜头中景。\n"
    '她用台湾口音普通话说："怎么办？用五谷粥取代白粥。'
    '加糙米、燕麦、地瓜，纤维多，血糖就稳。"'
    "\n\n"
    "[00:05-00:10] 厨房场景。"
    "她将一颗蛋打入锅中，蛋液滑入粥面。镜头特写食材入锅，再拉回中景。\n"
    '她用台湾口音普通话说："粥里加蛋或豆腐，蛋白质可以减缓血糖上升。'
    '记得先吃菜和蛋白质，最后才喝粥。"'
    "\n\n"
    "[00:10-00:15] 场景参考@图片3。"
    "她端起一碗色彩丰富的五谷粥，微笑看向镜头。镜头缓推定格温暖画面。\n"
    '她用台湾口音普通话说："粥可以喝，但要喝对。'
    '这里是时时静好。我们下次见。"'
    "\n\n"
    "Sound：厨房轻微环境声，筷子轻碰碗的声音\n"
    "Music：温暖欢快配乐，居家氛围，轻快节奏\n"
    "禁止：任何文字、字幕、LOGO或水印。"
)


# ═══════════════════════════════════════════
#  Gemini Image Generation
# ═══════════════════════════════════════════

def generate_image(client, prompt: str, output_path: Path,
                   aspect: str = "9:16", retry: int = 3) -> bool:
    """用 Gemini native image generation 產出圖片"""
    from google.genai import types

    for attempt in range(retry):
        try:
            print(f"  生成 {output_path.name}（第 {attempt + 1}/{retry} 次）...")
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect,
                    ),
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    from PIL import Image as PILImage
                    from io import BytesIO
                    image = PILImage.open(BytesIO(part.inline_data.data))
                    image.save(str(output_path))
                    print(f"    ✓ 已儲存: {output_path.name}")
                    return True

            print(f"    ✗ 未收到圖片（第 {attempt + 1} 次）")
        except Exception as e:
            print(f"    ✗ 生成失敗（第 {attempt + 1} 次）: {e}")

        if attempt < retry - 1:
            time.sleep(3)

    return False


def generate_character_card(client, output_path: Path, retry: int = 3) -> bool:
    """無參考圖，直接用文字描述生成人物多角度定裝照"""
    from google.genai import types

    for attempt in range(retry):
        try:
            print(f"  生成人物定裝照（第 {attempt + 1}/{retry} 次）...")
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[CHARACTER_CARD_PROMPT],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio="3:2",
                    ),
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    from PIL import Image as PILImage
                    from io import BytesIO
                    image = PILImage.open(BytesIO(part.inline_data.data))
                    image.save(str(output_path))
                    print(f"    ✓ 已儲存: {output_path.name}")
                    return True

            print(f"    ✗ 未收到圖片（第 {attempt + 1} 次）")
        except Exception as e:
            print(f"    ✗ 生成失敗（第 {attempt + 1} 次）: {e}")

        if attempt < retry - 1:
            time.sleep(3)

    return False


def main():
    if not GEMINI_API_KEY:
        print("✗ 請設定環境變數 GEMINI_API_KEY")
        print("  export GEMINI_API_KEY=你的API金鑰")
        sys.exit(1)

    try:
        from google import genai
    except ImportError:
        print("請先安裝: pip install -U google-genai pillow")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=GEMINI_API_KEY)

    print("=" * 60)
    print("EP01 白粥 — Seedance 素材產生器")
    print("格式：E 廚房居家 ｜ 模型：" + GEMINI_MODEL)
    print("=" * 60)

    # ── 1. 生成場景圖（3 張，9:16）──
    print("\n── Step 1: 場景圖生成（9:16）──")
    for scene in SCENE_PROMPTS:
        path = OUTPUT_DIR / scene["filename"]
        if path.exists():
            print(f"  場景圖已存在，跳過: {path.name}")
            continue
        generate_image(client, scene["prompt"], path, aspect="9:16")
        time.sleep(2)

    # ── 2. 生成人物多角度定裝照（3:2，文字描述直接生成）──
    print("\n── Step 2: 人物多角度定裝照生成（3:2）──")
    char_path = OUTPUT_DIR / "character_turnaround.png"
    if char_path.exists():
        print(f"  定裝照已存在，跳過: {char_path.name}")
    else:
        generate_character_card(client, char_path)

    # ── 3. 更新 Seedance Prompts ──
    print("\n── Step 3: 更新 Seedance Prompts ──")

    # Part1 prompt
    part1_path = OUTPUT_DIR / "part1_prompt.txt"
    with open(part1_path, "w", encoding="utf-8") as f:
        f.write(SEEDANCE_PART1)
    print(f"  ✓ Part1 prompt: {part1_path.name}")

    # Part2 prompt
    part2_path = OUTPUT_DIR / "part2_prompt.txt"
    with open(part2_path, "w", encoding="utf-8") as f:
        f.write(SEEDANCE_PART2)
    print(f"  ✓ Part2 prompt: {part2_path.name}")

    # ── 4. 印出上傳指引 ──
    print("\n" + "=" * 60)
    print("【Part1 上傳指引】")
    print("=" * 60)
    print("上傳 2 張圖到即夢：")
    print("  @圖片1 = scene_1.png（廚房白粥場景）")
    print("  @圖片2 = character_turnaround.png（人物定裝照）")
    print()
    print("【Part1 Prompt】")
    print(SEEDANCE_PART1)

    print("\n" + "=" * 60)
    print("【Part2 上傳指引】")
    print("=" * 60)
    print("上傳 3 張圖到即夢：")
    print("  @圖片1 = character_turnaround.png（人物定裝照）")
    print("  @圖片2 = scene_2.png（五穀食材）")
    print("  @圖片3 = scene_3.png（五穀粥成品）")
    print()
    print("【Part2 Prompt】")
    print(SEEDANCE_PART2)

    print(f"\n✓ 所有素材已輸出至: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
