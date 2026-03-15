# 長輩廚房｜吃對了嗎？

YouTube Shorts 系列，頻道「時時靜好」。每集一個食材或烹飪方式，揭示營養真相。

## 系列定位
- **格式**：廚房居家（Seedance 形式 E）
- **目標觀眾**：負責煮飯的中老年人、關心家人飲食的中年人
- **節奏**：每週 2 集
- **影片結構**：3s 片頭標題卡 + 15s Part1 + 15s Part2 = ~33s

## 參考資料（night_thinking 專案研究成果）

以下檔案位於 `../night_thinking/`，需要時直接讀取：

| 用途 | 路徑 |
|------|------|
| 系列原始構想 | `task2_trending_analysis/04_new_series_ideas.md`（系列 2） |
| 影片形式目錄與 Seedance 模板 | `task2_trending_analysis/03_format_catalog.md` |
| 跨平台爆款要素 | `task2_trending_analysis/02_cross_platform_patterns.md` |
| 營養類已有劇本（格式參考） | `task1_health_content/02_seedance_prompts.json`（尤其 format E 的主題 7,13,14,17,37,44） |
| YouTube 元資料模板 | `task1_health_content/03_youtube_metadata.json` |
| 生產指南（字幕規範、BGM、排程） | `task1_health_content/04_production_guide.md` |
| 50 主題研究（營養類 #9-18） | `task1_health_content/01_topics_50.md` |

## 現有影片生產管線

位於 `../health-digest-factory/`：

| 檔案 | 用途 |
|------|------|
| `SEEDANCE_WORKFLOW.md` | Seedance 劇本結構、字幕規範、YouTube 元資料模板 |
| `scripts/assemble_seedance.py` | 影片組裝腳本（Part1+Part2 拼接、字幕疊加） |

## 形式 E 廚房居家規格

- **全域規格**：warm 暖色溫，自然光+暖燈光，木質桌面，居家廚房氛圍
- **場景圖**：1 張廚房（可重用）+ 1-2 張食材特寫/餐桌場景
- **人物**：55歲亞洲女性，站在料理台前
- **BGM**：溫暖歡快，居家氛圍
- **場景圖 prompt 結尾**：`不要任何文字、人物、水印、LOGO。`
- **字幕**：繁體中文，每句 6-12 字

## 生產流程（每集）

```
1. 劇本 JSON 建立（含研究來源查證）
2. 場景圖 × 3 → Gemini Nano Banana 生成（免費）
3. Part1 prompt → Seedance 生成 → 人工審片
4. Part1 截圖人物 → 即夢圖片生成 → 三視圖定裝照（繞過人臉審查）
5. Part2 prompt + 定裝照上傳 → Seedance 生成 → 人工審片
6. 兩段影片 → assemble_seedance.py 組裝（片頭+字幕+去浮水印）
7. YouTube 上傳（標題、說明從 JSON 取）
```

### Seedance 人物一致性：三視圖定裝照法

Seedance 禁止上傳真人臉圖片，但**即夢自己生成的圖不受限制**。
利用這點讓 Part1 和 Part2 人物一致：

1. Part1 生成完成 → 截圖滿意的人物臉部
2. 截圖丟進即夢「圖片生成」，搭配以下任一 prompt：

**三視圖法（推薦）**
```
画出这个角色正面，侧面，背面三视图，保持原角色面部特征，五官和发型不变。
```

**全彩插畫法**
```
画出这个角色的全彩电影分镜插画，白色背景，保证原角色面部特征，五官和发型不变
```

**多視角法**
```
画出这个角色的多视角图，保证原角色面部特征，五官和发型不变
```

3. 生成的定裝照上傳給 Part2 當參考圖 → 人物一致性大幅提升

### 成本估算

- Seedance 500 點 = 233 元，每段 15s = 22 點
- 理想（一次過）：每集 44 點 ≈ **20.5 元**
- 保守（各跑 2 次）：每集 88 點 ≈ **41 元**
- 場景圖用 Gemini Nano Banana，不佔 Seedance 點數

## 注意事項
- Seedance prompt 用**简体中文**，字幕和 YouTube 元資料用**繁體中文**
- 場景圖不可有人臉，人物用文字描述
- 口播短句 6-12 字，句句斷開
- 台灣口音指定：「用台湾口音普通话说」
- Part2 結尾固定：「這裡是時時靜好。我們下次見。」
- 每集劇本必須附上研究來源（期刊論文或官方機構），Hook 數據需查證
