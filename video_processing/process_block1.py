import os
import subprocess
import sys
import whisper
import requests
import json
import time
import uuid
from pathlib import Path

# ================== НАСТРОЙКИ (измени под свой блок) ==================
# Для блока 1 – если блок 2, замени все "1" на "2" и т.д.
INPUT_DIR = r"C:\video_processing\input_block1"
OUTPUT_DIR = r"C:\video_processing\output"
MANUAL_DIR = r"C:\video_processing\manual"
PROCESSED_DIR = r"C:\video_processing\processed"

USE_SUBTITLES = True                # сначала пробуем встроенные субтитры
MIN_WORDS = 10                       # минимальное кол-во слов для успешной расшифровки
WHISPER_MODEL = "base"                # можно "tiny" для скорости
WHISPER_LANGUAGE = "ru"               # язык видео
OLLAMA_MODEL = "mistral"              # модель для пересказа (предварительно скачай: ollama pull mistral)
OLLAMA_URL = "http://localhost:11434/api/generate"
# ==========================================================================

# Создаём папки, если их нет
for d in [OUTPUT_DIR, MANUAL_DIR, PROCESSED_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)

# Загружаем модель Whisper (один раз)
print("Загрузка модели Whisper...")
model = whisper.load_model(WHISPER_MODEL)
print("Whisper готов.\n")

# --- Вспомогательные функции ---
def extract_subtitles(video_path):
    """Извлекает субтитры из видео (первая дорожка). Возвращает текст или None."""
    temp_srt = f"temp_subs_{uuid.uuid4().hex}.srt"
    cmd = [
        "ffmpeg", "-i", video_path,
        "-map", "0:s:0",          # первая дорожка субтитров
        "-f", "srt", temp_srt,
        "-y", "-loglevel", "error"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(temp_srt):
        return None
    with open(temp_srt, "r", encoding="utf-8") as f:
        content = f.read()
    os.remove(temp_srt)
    # Убираем номера и временные метки
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.isdigit() and "-->" not in line:
            lines.append(line)
    return " ".join(lines) if lines else None

def extract_audio(video_path):
    """Извлекает аудио в уникальный WAV-файл.
       Возвращает путь к файлу или None, если аудио отсутствует/повреждено."""
    audio_path = f"temp_audio_{uuid.uuid4().hex}.wav"
    cmd = [
        "ffmpeg", "-i", video_path,
        "-q:a", "0", "-map", "a",
        audio_path, "-y", "-loglevel", "error"
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"   → ошибка FFmpeg при извлечении аудио: {e.stderr}")
        return None

    # Проверяем, создался ли файл и не пустой ли он
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        print("   → аудиофайл не создан или пуст")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return None

    return audio_path

def transcribe_audio(audio_path):
    """Распознаёт речь через Whisper."""
    result = model.transcribe(audio_path, language=WHISPER_LANGUAGE)
    return result["text"].strip()

def summarize_text(text):
    """Отправляет текст в Ollama и возвращает краткий пересказ."""
    prompt = f"Сделай краткий пересказ (2-3 предложения) этого текста:\n{text}"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 200}
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json()["response"].strip()
        else:
            return f"[Ошибка суммаризации: {response.status_code}]"
    except Exception as e:
        return f"[Ошибка связи с Ollama: {e}]"

def save_result(video_name, summary, full_text=""):
    """Сохраняет результат в .txt файл."""
    txt_name = Path(video_name).stem + ".txt"
    txt_path = os.path.join(OUTPUT_DIR, txt_name)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Видео: {video_name}\n")
        f.write(f"\nКраткий пересказ:\n{summary}\n")
        if full_text:
            f.write(f"\nПолная расшифровка:\n{full_text}\n")
    return txt_path

def safe_move(src, dst_dir):
    """Перемещает файл в папку dst_dir, если файл уже существует – добавляет числовой суффикс."""
    base = os.path.basename(src)
    name, ext = os.path.splitext(base)
    dst = os.path.join(dst_dir, base)
    if not os.path.exists(dst):
        os.rename(src, dst)
        return dst
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        new_dst = os.path.join(dst_dir, new_name)
        if not os.path.exists(new_dst):
            os.rename(src, new_dst)
            return new_dst
        counter += 1

# --- Основной цикл ---
def main():
    # Собираем все видео из INPUT_DIR (рекурсивно)
    video_files = []
    for root, dirs, files in os.walk(INPUT_DIR):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                video_files.append(os.path.join(root, file))
    total = len(video_files)
    print(f"Найдено видео для обработки: {total}\n")

    for idx, video_path in enumerate(video_files, 1):
        video_name = os.path.basename(video_path)
        txt_name = Path(video_name).stem + ".txt"
        txt_path = os.path.join(OUTPUT_DIR, txt_name)

        # Если .txt уже существует – видео уже обработано
        if os.path.exists(txt_path):
            print(f"[{idx}/{total}] Пропускаем (уже есть .txt): {video_name}")
            continue

        print(f"[{idx}/{total}] Обработка: {video_name}")

        # 1. Пробуем субтитры
        text = None
        if USE_SUBTITLES:
            print("   → пробуем субтитры...")
            text = extract_subtitles(video_path)
            if text:
                print(f"   → субтитры найдены ({len(text)} символов)")

        # 2. Если субтитров нет – Whisper
        if not text:
            print("   → субтитров нет, запускаем Whisper...")
            audio_path = extract_audio(video_path)
            if audio_path is None:
                print("   → не удалось извлечь аудио, видео перемещается в manual")
                safe_move(video_path, MANUAL_DIR)
                continue
            try:
                text = transcribe_audio(audio_path)
                print(f"   → распознано {len(text)} символов")
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)

        # 3. Проверяем, есть ли осмысленный текст
        word_count = len(text.split())
        if word_count < MIN_WORDS:
            print(f"   → мало слов ({word_count}), видео перемещается в manual")
            safe_move(video_path, MANUAL_DIR)
            continue

        # 4. Суммаризация через Ollama
        print("   → суммаризация...")
        summary = summarize_text(text)

        # 5. Сохраняем результат
        save_result(video_name, summary, full_text=text)
        print("   → .txt сохранён")

        # 6. Перемещаем обработанное видео в processed
        safe_move(video_path, PROCESSED_DIR)
        print("   → видео перемещено в processed")

        # Небольшая пауза, чтобы не перегружать процессор
        time.sleep(0.5)

    print("\n🎉 Все видео обработаны! Проверь папки output и manual_review.")

if __name__ == "__main__":
    main()