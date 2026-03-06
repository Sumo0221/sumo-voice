"""
蘇茉語音助手 - 本地語音對話程式 (優化版 v2)

功能：
1. 麥克風錄音 → 2. FasterWhisper 轉文字 → 3. OpenClaw Gateway → 4. Edge TTS 說話

優化重點：
1. 收音時不播音，播音時不收音
2. 檢測音量是否 > -40分貝
3. 文字必須以"蘇茉"開頭
4. 空白鍵控制錄音時間
5. 過濾掉非文字字符（emoji、符號等）
6. 播放完後自動關閉播放程式

使用方法：
    python sumo_voice.py
"""

import asyncio
import logging
import os
import re
import time
import numpy as np
import edge_tts
import sounddevice as sd
import keyboard
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from openclaw_client import OpenClawClient

# 載入環境變數
load_dotenv(".env.local")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sumo-voice")

# 設定
GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789")
GATEWAY_TOKEN = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
WHISPER_MODEL = "medium"  # tiny, base, small, medium, large-v3
TTS_VOICE = "zh-TW-HsiaoChenNeural"  # 甜美女生聲音
SAMPLE_RATE = 16000
RECORD_DURATION = 15  # 預設錄音秒數
MIN_VOLUME_DB = -60  # 最小音量分貝

# 修正字典：常見的"蘇茉"同音字錯誤
# 第一個字可能是：蘇舒疏酥穌苏書輸殊梳蔬樞
# 第二個字可能是：茉默墨莫末沫沒陌寞眽
SUMO_FIRST_CHARS = set(['蘇', '舒', '疏', '酥', '穌', '苏', '書', '輸', '殊', '梳', '蔬', '樞'])
SUMO_SECOND_CHARS = set(['茉', '默', '墨', '莫', '末', '沫', '沒', '陌', '寞', '眽'])

def is_sumo_name(text: str) -> bool:
    """檢查文字開頭是否是"蘇茉"（支援多種同音字組合）"""
    if not text or len(text) < 2:
        return False
    
    first_char = text[0]
    second_char = text[1]
    
    return (first_char in SUMO_FIRST_CHARS) and (second_char in SUMO_SECOND_CHARS)


def extract_sumo_command(text: str) -> str | None:
    """如果文字開頭是"蘇茉"相關字，回傳去掉開頭後的指令；否則回傳 None"""
    if not text:
        return None
    
    if is_sumo_name(text):
        # 去掉前2個字
        command = text[2:].strip()
        return command
    
    return None


def remove_non_text(text: str) -> str:
    """移除非文字字符（emoji、符號等），只保留中文、英文、數字"""
    if not text:
        return text
    
    # 只保留中文、英文、數字、空格
    # \u4e00-\u9fff = 中文
    # \u0030-\u0039 = 數字
    # \u0041-\u005a, \u0061-\u007a = 英文
    # \u3000-\u303f, \uff00-\uffef = 中文標點（保留）
    cleaned = re.sub(r'[^\u4e00-\u9fff\u0030-\u0039\u0041-\u005a\u0061-\u007a\u3000-\u303f\uff00-\uffef\s]', '', text)
    
    # 移除多餘空白
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


class SumoVoice:
    def __init__(self):
        """初始化語音助手"""
        # 載入 FasterWhisper 模型
        logger.info("載入 FasterWhisper 模型...")
        self.whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        logger.info("模型載入完成！")
        
        # TTS 設定
        self.tts_voice = TTS_VOICE
        
        # 狀態標記
        self.is_speaking = False  # 是否正在說話（播音中）
        
    def calculate_db(self, audio_data: np.ndarray) -> float:
        """計算音量的分貝數"""
        if audio_data is None or len(audio_data) == 0:
            return -np.inf
        
        # 計算 RMS（均方根）
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms == 0:
            return -np.inf
        # 轉換為分貝
        db = 20 * np.log10(rms)
        return db
    
    def record_audio(self, duration=RECORD_DURATION, sample_rate=SAMPLE_RATE) -> np.ndarray:
        """錄製音訊（短話模式：固定錄音秒數）"""
        
        logger.info(f"錄音中... {duration} 秒")
        
        try:
            # 直接錄音固定的秒數
            audio_data = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='float32'
            )
            
            # 等待錄音完成
            sd.wait()
            
            # 轉換為 1D array
            audio_data = audio_data.flatten()
            
            duration_recorded = len(audio_data) / sample_rate
            logger.info(f"錄音完成，時長: {duration_recorded:.1f} 秒")
            return audio_data
            
        except Exception as e:
            logger.error(f"錄音失敗: {e}")
            return None
    
    """
    #  長話模式（暫時停用）
    def record_audio_with_space(self, duration=RECORD_DURATION, sample_rate=SAMPLE_RATE) -> np.ndarray:
       錄製音訊（支援空白鍵延長）
        
        logger.info(f"錄音中... {duration} 秒（按空白鍵繼續）")
        
        try:
            # 計算需要錄音的總幀數
            total_frames = int(duration * sample_rate)
            audio_chunks = []
            start_time = time.time()
            space_pressed = False
            
            while True:
                # 計算剩餘時間
                elapsed = time.time() - start_time
                remaining = duration - elapsed
                
                if remaining <= 0 and not space_pressed:
                    # 10秒到了，且沒有按空白鍵，結束錄音
                    break
                
                # 計算這次要錄多久
                chunk_duration = min(1.0, remaining) if remaining > 0 else 1.0
                chunk_frames = int(chunk_duration * sample_rate)
                
                # 錄音
                chunk = sd.rec(chunk_frames, samplerate=sample_rate, channels=1, dtype='float32')
                sd.wait()
                audio_chunks.append(chunk.flatten())
                
                # 檢查是否按下了空白鍵
                if keyboard.is_pressed('space'):
                    if not space_pressed:
                        space_pressed = True
                        logger.info("空白鍵按下，繼續錄音...")
                    else:
                        # 第二次按空白鍵，結束錄音
                        logger.info("空白鍵再次按下，結束錄音！")
                        break
                
                # 短暫休息
                time.sleep(0.1)
            
            # 合併所有音頻塊
            if audio_chunks:
                audio_data = np.concatenate(audio_chunks)
            else:
                audio_data = np.array([])
            
            duration_recorded = len(audio_data) / sample_rate
            logger.info(f"錄音完成，時長: {duration_recorded:.1f} 秒")
            return audio_data
            
        except Exception as e:
            logger.error(f"錄音失敗: {e}")
            return None
    """
    
    def save_audio_temp(self, audio_data: np.ndarray, filename: str = "temp_recording.wav") -> str:
        """儲存音頻到暫存檔案"""
        try:
            # 轉換為 int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # 儲存為 WAV
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())
            
            return filename
        except Exception as e:
            logger.error(f"儲存音頻失敗: {e}")
            return None
    
    def delete_audio_file(self, filename: str):
        """刪除音頻檔案"""
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"已刪除音頻檔案: {filename}")
        except Exception as e:
            logger.error(f"刪除音頻檔案失敗: {e}")
    
    def check_volume(self, audio_data: np.ndarray, min_db: float = MIN_VOLUME_DB) -> bool:
        """檢查音量是否超過設定的分貝數"""
        if audio_data is None or len(audio_data) == 0:
            return False
        
        db = self.calculate_db(audio_data)
        logger.info(f"音量: {db:.1f} dB (門檻: {min_db} dB)")
        
        return db > min_db
    
    def speech_to_text(self, audio_data: np.ndarray) -> str:
        """語音轉文字"""
        logger.info("辨識語音中...")
        
        if audio_data is None or len(audio_data) == 0:
            logger.warning("沒有錄到音頻")
            return None
        
        try:
            # 轉換為文字
            segments, info = self.whisper.transcribe(
                audio_data,
                language="zh",  # 強制中文
                beam_size=5,
                word_timestamps=False
            )
            
            text = ""
            for segment in segments:
                text += segment.text
            
            text = text.strip()
            
            logger.info(f"辨識結果: {text}")
            return text
            
        except Exception as e:
            logger.error(f"辨識失敗: {e}")
            return None
    
    def starts_with_sumo(self, text: str) -> bool:
        """檢查文字是否以'蘇茉'開頭（支援同音字）"""
        if not text:
            return False
        return text.startswith("蘇茉")
    
    async def text_to_speech(self, text: str, output_file: str = "sumo_response.mp3"):
        """文字轉語音並播放"""
        logger.info(f"說話: {text}")
        
        # 過濾掉非文字字符
        text_cleaned = remove_non_text(text)
        if text_cleaned != text:
            logger.info(f"過濾後: {text_cleaned}")
        
        if not text_cleaned:
            logger.warning("沒有文字可說")
            return
        
        # 標記為正在說話
        self.is_speaking = True
        
        try:
            # 使用 Edge TTS 生成語音
            communicate = edge_tts.Communicate(text_cleaned, self.tts_voice)
            await communicate.save(output_file)
            
            logger.info(f"已儲存: {output_file}")
            
            # 檢查檔案是否存在
            if not os.path.exists(output_file):
                logger.error(f"音頻檔案不存在: {output_file}")
                return
            
            # 檢查檔案大小
            file_size = os.path.getsize(output_file)
            logger.info(f"音頻檔案大小: {file_size} bytes")
            
            if file_size == 0:
                logger.error("音頻檔案是空的")
                return
            
            # 使用 sounddevice 直接播放音頻（不需要外部播放器）
            try:
                import subprocess
                
                # Edge TTS 產生的 MP3 需要先轉換為 WAV
                wav_file = output_file.replace('.mp3', '.wav')
                
                # 使用 ffmpeg 轉換
                result = subprocess.run([
                    r'C:\tools\ffmpeg-2026-02-26-git-6695528af6-essentials_build\bin\ffmpeg.exe',
                    '-i', output_file,
                    '-acodec', 'pcm_s16le',
                    '-ar', '16000',
                    '-ac', '1',
                    wav_file, '-y', '-loglevel', 'error'
                ], capture_output=True)
                
                if not os.path.exists(wav_file):
                    logger.error(f"轉換失敗")
                    return
                
                # 讀取 WAV 檔案
                import wave
                with wave.open(wav_file, 'rb') as wf:
                    # 讀取音頻數據
                    audio_data = wf.readframes(wf.getnframes())
                    sample_rate = wf.getframerate()
                    
                    # 轉換為 numpy array
                    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                    
                    logger.info(f"開始播放... (sample_rate={sample_rate})")
                    
                    # 播放
                    sd.play(audio_np, sample_rate)
                    sd.wait()  # 等待播放完成
                    
                    logger.info("播放完成")
                
                # 刪除臨時 WAV 檔案
                if os.path.exists(wav_file):
                    try:
                        os.remove(wav_file)
                    except:
                        pass
                    
            except Exception as e:
                logger.error(f"播放失敗: {e}")
            
                # 稍微等待一下
            time.sleep(1)
            
            
            # 刪除播放的音頻檔案
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                    logger.info(f"已刪除音頻檔案: {output_file}")
                except Exception as e:
                    logger.warning(f"刪除音頻檔案失敗: {e}")
            
            return output_file
            
        except Exception as e:
            logger.error(f"TTS 失敗: {e}")
            return None
        finally:
            # 標記為說話結束
            self.is_speaking = False
    
    async def chat(self, user_text: str) -> str:
        """對話流程：發送訊息到 OpenClaw Gateway"""
        
        if not user_text:
            return "我沒有聽清楚，請再說一次"
        
        logger.info(f"發送到 OpenClaw Gateway: {user_text}")
        
        try:
            # 連接 OpenClaw Gateway
            client = OpenClawClient(GATEWAY_URL, GATEWAY_TOKEN)
            await client.connect()
            logger.info("已連接到 OpenClaw Gateway")
            
            # 發送訊息並獲取串流回覆
            stream = await client.agent_message_streaming(
                message=user_text,
                deliver=False,
                agent_id="main"
            )
            
            # 收集完整回覆
            full_response = ""
            async for delta in stream:
                if delta:
                    full_response += delta
                    logger.info(f"收到回覆片段: {delta[:50]}...")
            
            await client.close()
            
            if full_response:
                return full_response
            else:
                return "我沒有收到回覆"
                
        except Exception as e:
            logger.error(f"連接 OpenClaw Gateway 失敗: {e}")
            return f"抱歉，連接失敗: {e}"
    
    async def run(self):
        """主執行迴圈"""
        logger.info("=" * 50)
        logger.info("蘇茉語音助手 (優化版 v2)")
        logger.info("按 Ctrl+C 結束程式")
        logger.info("功能說明:")
        logger.info("  - 預設錄音 10 秒")
        logger.info("  - 音量需超過 -60 dB")
        logger.info("  - 話語需以'蘇茉'開頭")
        logger.info("  - 蘇茉說話會過濾掉 emoji 和特殊符號")
        logger.info("  - 錄音/播音完成後會自動清理檔案")
        logger.info("=" * 50)
        
        while True:
            try:
                # ========================================
                # 步驟 1: 錄音（確保不在播音時錄音）
                # ========================================
                while self.is_speaking:
                    logger.info("等待播音結束...")
                    time.sleep(0.5)
                
                # 錄音（固定10秒）
                # 再次檢查是否正在播音
                if self.is_speaking:
                    logger.info("跳過錄音，正在播音中")
                    continue
                
                audio = self.record_audio()
                
                # ========================================
                # 步驟 2: 檢查音量
                # ========================================
                if not self.check_volume(audio):
                    logger.info("音量太小，請再說一次！")
                    continue
                
                # ========================================
                # 步驟 3: 語音轉文字
                # ========================================
                text = self.speech_to_text(audio)
                
                if not text:
                    logger.info("無法辨識，請再說一次！")
                    continue
                
                # ========================================
                # 步驟 4: 檢查是否以"蘇茉"開頭
                # ========================================
                # 使用新的判斷方式：只要前兩字符合"蘇茉"相關字的組合即可
                
                if not is_sumo_name(text):
                    logger.info(f"這句話不是叫蘇茉做事（{text[:10]}...），請再說一次！")
                    continue
                
                # 提取指令
                user_text = extract_sumo_command(text)
                if not user_text:
                    logger.info(f"這句話不是叫蘇茉做事，請再說一次！")
                    continue
                
                logger.info(f"你說: {user_text}")
                
                # ========================================
                # 步驟 5: 對話並獲取回覆
                # ========================================
                response = await self.chat(user_text)
                
                # ========================================
                # 步驟 6: 說話回覆（確保不在錄音時說話）
                # ========================================
                await self.text_to_speech(response)
                
                # ========================================
                # 步驟 7: 播放完畢，清理並開始下一次錄音
                # ========================================
                logger.info("準備下一次錄音...")
                
            except KeyboardInterrupt:
                logger.info("\n結束程式")
                break
            except Exception as e:
                logger.error(f"錯誤: {e}")


async def main():
    """主程式"""
    sumo = SumoVoice()
    await sumo.run()


if __name__ == "__main__":
    asyncio.run(main())
