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
- **人物**：從 `characters/` 資產庫選用（預設：auntie_chen）
- **BGM**：溫暖歡快，居家氛圍
- **場景圖 prompt 結尾**：`不要任何文字、人物、水印、LOGO。`
- **字幕**：繁體中文，每句 6-12 字

## 角色資產庫

角色定裝照集中管理於 `characters/` 目錄，可跨集重用：

```
characters/
  ├── auntie_chen/          ← EP01 起用的主角
  │   ├── turnaround.png    ← Gemini 生成（多角度定裝照）
  │   └── character.json    ← 角色描述 metadata
  └── （未來可新增更多角色）
```

每集劇本 JSON 透過 `character_id` 指定使用哪個角色，asset_gen 從資產庫讀取定裝照。

## 生產流程（每集）

```
1. 劇本 JSON 建立（含研究來源查證）
2. 角色選定（從 characters/ 資產庫選用，或即夢圖片生成新角色定裝照）
3. 場景圖 × 3 → Gemini 生成（免費）
4. Part1 prompt + 定裝照 + 場景圖 → Seedance 生成 → 人工審片
5. Part2 prompt + 同一定裝照 + 場景圖 → Seedance 生成 → 人工審片
6. 兩段影片 → assemble_episode.py 組裝（片頭+字幕+去浮水印）
7. YouTube 上傳（標題、說明從 JSON 取）
```

### Seedance 人物一致性：定裝照前置法

**Part1 和 Part2 都導入同一張定裝照**，從頭到尾保持人物一致。

#### 工具分工

- **定裝照 / 場景圖 / 食材圖**：統一用 Gemini 生成（免費）
- **Seedance（即夢）**：只用於影片生成，不用於圖片生成

#### 建立新角色定裝照（Gemini）

使用 `scripts/gen_turnaround.py`，搭配以下 prompt：

**三視圖法（推薦）**
```
画出这个角色正面，侧面，背面三视图，保持原角色面部特征，五官和发型不变。白色背景，清晰的正面、侧面和背面全身图。
```

**多視角法**
```
画出这个角色的多视角图，保证原角色面部特征，五官和发型不变
```

**全彩插畫法**
```
画出这个角色的全彩电影分镜插画，白色背景，保证原角色面部特征，五官和发型不变
```

#### 使用方式

- Part1 和 Part2 都上傳同一張定裝照作為 `@图片1`（角色參考）
- 場景圖作為 `@图片2`、`@图片3`
- Gemini 生成的定裝照可通過 Seedance 人臉審查
- 同一角色跨集重用，無需每集重新生成

### 成本估算

- Seedance 500 點 = 233 元，每段 15s = 22 點
- 理想（一次過）：每集 44 點 ≈ **20.5 元**
- 保守（各跑 2 次）：每集 88 點 ≈ **41 元**
- 場景圖用 Gemini Nano Banana，不佔 Seedance 點數

## 新子系列：營養素排行榜（TOP 排行榜倒數揭曉型）

延伸自長輩廚房，專做食物營養素含量的比較排行。

### 研究資料
- 完整研究報告：`../night-thinking/task2_trending_analysis/06_superfood_nutrient_comparison_research.md`
- 涵蓋：爆量心理機制、5 種圖卡格式、15 個選題、權威資料來源

### 爆量關鍵
- **數字反差**：差距越大越震撼（3 倍、5 倍、10 倍）
- **排行榜效應**：倒數揭曉驅動完播率
- **顛覆認知**：結果跟大眾認知不同才有傳播力
- **標注來源**：TikTok 營養內容僅 2.1% 準確，標注 USDA/PubMed 立即差異化
- **換算實際份量**：不只比 100g，要比「一碗」「一杯」的實際攝取量
- **提及吸收率**：深一層的知識建立信任

### 權威資料來源
| 用途 | 來源 | 網址 |
|------|------|------|
| 營養素含量（主力） | USDA FoodData Central | https://fdc.nal.usda.gov/ |
| 台灣在地食材 | 衛福部食品營養成分資料庫 | https://consumer.fda.gov.tw/Food/TFND.aspx |
| 驗證健康宣稱 | PubMed（搜「食物名 + systematic review」） | https://pubmed.ncbi.nlm.nih.gov/ |
| 通俗化參考 | Harvard Nutrition Source | https://nutritionsource.hsph.harvard.edu/ |
| 謠言查核 | MyGoPen | https://www.mygopen.com/ |

### 影片結構（混合型 ~30s）
```
[0-3s]   即夢：廚房場景 55歲女性 + Hook 口播
[3-25s]  圖卡動畫：Pillow 自動生成，排行榜從第5名倒數到第1名
         每張 3-4 秒，ffmpeg 加淡入動畫
         底部角落標注資料來源
[25-30s] 即夢：回到廚房 + CTA「收藏起來，傳給家裡煮飯的人！」
```

### 圖卡自動化方案
- **不需要 Canva/PPT** — Pillow + ffmpeg 完全自動化
- **不需要新依賴** — 現有管線已有 Pillow + imageio-ffmpeg
- JSON 增加 `"type": "ranking"` 和 `ranking_data` 欄位
- 新增 `generate_ranking_cards()` 函式，讀 JSON → Pillow 畫圖卡 → ffmpeg 串成影片段
- assemble 主流程：中間段從「即夢 Part1+Part2」換成「圖卡影片段」
- 食物照片：用即夢圖片生成（免費額度），可跨集重用

### JSON 結構（ranking 型）
```json
{
  "type": "ranking",
  "ranking_data": [
    {"rank": 5, "food": "豆腐", "value": 350, "unit": "mg/100g", "food_image": "tofu.png"},
    ...
  ],
  "comparison_note": "牛奶僅 104mg/100g",
  "data_source": "USDA FoodData Central"
}
```

### 優先選題
1. 補鈣食物 TOP 5：第一名不是牛奶！
2. 菠菜含鐵量其實很普通，真正的補鐵冠軍是它
3. 紅棗補血是假的！真正能補血的食物排行
4. 維生素 C 含量 TOP 5：柳橙居然沒上榜
5. 骨頭湯的鈣含量，竟然只有牛奶的 1/50

### 注意陷阱
- 避免使用「超級食物」一詞（歐盟 2007 年已禁止，無醫學定義）
- 必須換算實際攝取份量（芝麻含鈣高但沒人一次吃 100g）
- 提及生物利用率（植物性鈣吸收率低於乳製品）
- 不做療效宣稱，框架為「均衡飲食的一部分」
- 正面框架（「換這個吃更好」）優於恐嚇框架（「不吃就完了」）

---

## 注意事項
- Seedance prompt 用**简体中文**，字幕和 YouTube 元資料用**繁體中文**
- 場景圖不可有人臉，人物用文字描述
- 口播短句 6-12 字，句句斷開
- 台灣口音指定：「用台湾口音普通话说」
- 結尾必須提到頻道名「時時靜好」+ 告別語（允許措辭變體）
- 每集劇本必須附上研究來源（期刊論文或官方機構），Hook 數據需查證
