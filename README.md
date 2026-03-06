# 蘇茉語音助手 (Sumo Voice)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows-lightgrey?style=flat-square" alt="Platform">
</p>

透過麥克風直接和 AI 助手對話的語音助手程式。專為中文使用者設計，支援多種喚醒詞組合。

## 📑 Table of Contents

- [功能特色](#功能特色)
- [環境需求](#環境需求)
- [安裝指南](#安裝指南)
- [快速開始](#快速開始)
- [使用範例](#使用範例)
- [設定說明](#設定說明)
- [常見問題](#常見問題)
- [技術架構](#技術架構)
- [貢獻指南](#貢獻指南)
- [License](#license)

---

## ✨ 功能特色

| 功能 | 說明 |
|------|------|
| 🎤 語音辨識 | 使用 FasterWhisper 進行本地語音轉文字 |
| 🤖 AI 對話 | 連接 OpenClaw Gateway 進行智能對話 |
| 🔊 語音回覆 | 使用 Edge TTS 甜美女生聲音回覆 |
| ✅ 收音/播音互斥 | 播音時不收音，避免干擾 |
| 📊 音量檢測 | 自動過濾音量太小的錄音 |
| 🏷️ 喚醒詞檢測 | 支援多種"蘇茉"同音字組合 |
| 🧹 自動清理 | 錄音/播音完成後自動刪除暫存檔案 |

---

## 🖥️ 環境需求

- **作業系統**：Windows 10/11
- **Python**：3.12 或更高版本
- **麥克風**：電腦連接的麥克風
- **喇叭**：電腦喇叭或耳機
- **網路**：連接網際網路（用於 AI 對話）

---

## 📥 安裝指南

### 1. 複製專案

```bash
git clone https://github.com/your-username/sumo-voice.git
cd sumo-voice
```

### 2. 建立虛擬環境（建議）

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

### 4. 安裝 FFmpeg

**方式一：使用 winget（推薦）**
```bash
winget install ffmpeg
```

**方式二：手動安裝**
1. 下載 FFmpeg：https://ffmpeg.org/download.html
2. 將 `bin` 目錄加入系統 PATH

### 5. 設定環境變數

```bash
copy .env.local.example .env.local
```

編輯 `.env.local`，填入您的 OpenClaw Gateway 設定：
```env
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789
OPENCLAW_GATEWAY_TOKEN=您的Token
```

---

## 🚀 快速開始

### 啟動程式

```bash
python sumo_voice.py
```

### 操作流程

1. **等待錄音**：程式會自動開始錄音 15 秒
2. **對著麥克風說話**：音量需超過 -60dB
3. **使用喚醒詞**：話語需以"蘇茉"開頭
4. **聽取回覆**：蘇茉會用聲音回覆您

---

## 💬 使用範例

### 範例 1：推薦餐廳

> **老爺說**：「蘇茉推薦好吃的泰國菜餐廳」  
> **蘇茉回**：「好的！讓我幫您查一下好吃的泰國菜餐廳～根據評價和人气，我推薦以下幾家泰式餐廳：第一家是『瓦城泰式料理』，在台北有多家分店，檸檬魚和綠咖哩是非常招牌的菜色。第二家是『晶湯匙泰式主題餐廳』，主打精緻的泰式料理，氣氛很不錯。第三家是『泰街頭』，價格實惠，口味道地。如果您在台北，推薦可以去信義區的『泰王室』試試看，高級又不失傳統風味！想要我幫您查哪家餐廳的詳細資訊嗎？」

### 範例 2：查天氣

> **老爺說**：「蘇茉明天天氣如何？」  
> **蘇茉回**：「好的，讓我幫您查一下～明天是 2026年3月7日，根據中央氣象局的預測，明天全台灣天氣晴朗，北部地區氣溫大約在 18 到 26 度之間，中部 20 到 28 度，南部 22 到 30 度。整體來說是適合出門的好天氣，不過早晚溫差較大，建議帶一件薄外套哦！」

### 範例 3：查股票

> **老爺說**：「蘇茉華通股票現在多少？」  
> **蘇茉回**：「好的，讓我幫您查一下～根據最新資料，華通(2313)目前的股價是 203 元，漲跌幅是 -0.98%。今天最高曾經來到 212.5 元，最低是 198 元，目前在 200 元附近整理中。距離 52 週高點 246 元還有一些空間，如果您有持股可以繼續觀察。」

---

## ⚙️ 設定說明

### 錄音時間

修改 `sumo_voice.py` 中的 `RECORD_DURATION`：

```python
RECORD_DURATION = 15  # 預設錄音秒數
```

### 音量門檻

修改 `MIN_VOLUME_DB`：

```python
MIN_VOLUME_DB = -60  # 最小音量分貝
```

### 聲音選擇

修改 `TTS_VOICE`：

```python
# 可用的中文聲音：
# zh-TW-HsiaoChenNeural - 甜美女生（預設）
# zh-TW-YunJheNeural - 活力少女
# zh-TW-HsiaoYuNeural - 溫柔女生

TTS_VOICE = "zh-TW-HsiaoChenNeural"
```

### 喚醒詞設定

程式支援多種"蘇茉"同音字組合：

**第一個字**：蘇、舒、疏、酥、穌、书、書、輸、殊、梳、蔬、樞

**第二個字**：茉、默、墨、莫、末、沫、沒、陌、寞、眽

例如：「蘇茉你好」、「舒默幫我查資料」、「書莫天氣」都會被視為喚醒詞。

---

## ❓ 常見問題

### Q: 錄音辨識不完整？
A: 可以調整 `RECORD_DURATION` 增加錄音時間

### Q: 音量太小被忽略？
A: 可以調低 `MIN_VOLUME_DB`（如 -70）

### Q: "蘇茉"無法辨識？
A: 程式已支援多種同音字，如果還是不行，可以嘗試換一個麥克風

### Q: 播放沒有聲音？
A: 確認電腦喇叭有開啟，且音量正常

### Q: 連接 OpenClaw Gateway 失敗？
A: 確認 Gateway 有正在運行，且 Token 正確

---

## 🏗️ 技術架構

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   麥克風    │ ── │ FasterWhisper │ ── │  OpenClaw Gateway │
│  (錄音)    │     │  (語音辨識)   │     │    (AI 對話)     │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                      │
                                                      ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │ Edge TTS     │ ◄── │    蘇茉回覆      │
                    │ (語音合成)   │     │                 │
                    └──────────────┘     └─────────────────┘
```

### 使用的技術

| 技術 | 用途 |
|------|------|
| [FasterWhisper](https://github.com/SYSTRAN/faster-whisper) | 本地語音辨識 |
| [Edge TTS](https://github.com/rany2/edge-tts) | 語音合成 |
| [sounddevice](https://python-sounddevice.readthedocs.io/) | 音訊播放 |
| [OpenClaw](https://github.com/openclaw/openclaw) | AI Gateway |

---

## 🤝 貢獻指南

歡迎貢獻這個專案！請遵循以下步驟：

1. Fork 本專案
2. 建立您的特色分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的改動 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

---

## 📄 License

本專案採用 MIT License - 詳見 [LICENSE](LICENSE) 檔案

---

## 👩‍💻 作者

**蘇茉** - 張家的 AI 管家

---

## 🔗 相關連結

- [FasterWhisper](https://github.com/SYSTRAN/faster-whisper)
- [Edge TTS](https://github.com/rany2/edge-tts)
- [OpenClaw](https://github.com/openclaw/openclaw)
- [LiveKit](https://livekit.io/)

---

<p align="center">
  Made with ❤️ by 蘇茉
</p>
