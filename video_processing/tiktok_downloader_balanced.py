import os
import sys
import subprocess
import time
import hashlib

# ================== НАСТРОЙКИ ==================
USER_FILE = "users.txt"
BASE_PATH = r"C:\video_processing"
DELAY_BETWEEN = 2
MAX_VIDEOS = 0
BLOCK_COUNT = 2
# ================================================

def ensure_yt_dlp():
    try:
        subprocess.run([sys.executable, "-m", "yt_dlp", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("yt-dlp не найден. Установи: py -m pip install yt-dlp")
        sys.exit(1)

def get_block_number(url):
    hash_int = int(hashlib.sha256(url.encode()).hexdigest()[:8], 16)
    return (hash_int % BLOCK_COUNT) + 1

def download_user_videos(username):
    profile_url = f"https://www.tiktok.com/@{username.lstrip('@')}"
    print(f"\n--- Обрабатываю пользователя: {username} ---")

    # Получаем список всех видео через модуль yt_dlp
    cmd_list = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--print", "url",
        "--no-download",
        profile_url
    ]
    
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
        video_urls = result.stdout.strip().split("\n")
        if not video_urls or video_urls == ['']:
            print(f"У пользователя {username} нет видео (или аккаунт приватный).")
            return 0

        print(f"Найдено видео: {len(video_urls)}")
        if MAX_VIDEOS > 0:
            video_urls = video_urls[:MAX_VIDEOS]
            print(f"Скачивается первых {MAX_VIDEOS} видео.")

        downloaded = 0
        for idx, video_url in enumerate(video_urls, 1):
            block = get_block_number(video_url)
            download_dir = os.path.join(BASE_PATH, f"input_block{block}")
            os.makedirs(download_dir, exist_ok=True)

            print(f"  [{idx}/{len(video_urls)}] Блок {block}, скачиваю: {video_url}")
            download_cmd = [
                sys.executable, "-m", "yt_dlp",
                "-o", os.path.join(download_dir, "%(uploader)s_%(upload_date)s_%(title)s.%(ext)s"),
                "--no-playlist",
                "--quiet",
                video_url
            ]
            try:
                subprocess.run(download_cmd, check=True)
                downloaded += 1
                print(f"    ✓ Готово")
            except subprocess.CalledProcessError:
                print(f"    ✗ Ошибка при скачивании (пропускаю)")
            
            time.sleep(DELAY_BETWEEN)
        
        return downloaded

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при получении списка видео для {username}: {e}")
        return -1

def remove_user_from_file(username):
    if not os.path.exists(USER_FILE):
        return
    with open(USER_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    with open(USER_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip() != username:
                f.write(line)

def main():
    ensure_yt_dlp()

    if not os.path.exists(USER_FILE):
        print(f"Файл {USER_FILE} не найден. Создай его и запиши по одному пользователю в строке.")
        sys.exit(1)

    with open(USER_FILE, "r", encoding="utf-8") as f:
        users = [line.strip() for line in f if line.strip()]

    if not users:
        print("Файл с пользователями пуст.")
        return

    print(f"Загружено пользователей: {len(users)}")

    for i, username in enumerate(users, 1):
        count = download_user_videos(username)
        if count >= 0:
            print(f"Пользователь {username}: скачано {count} видео. Удаляю из списка.")
            remove_user_from_file(username)
        else:
            print(f"Пользователь {username}: ошибка, оставляю в списке.")

        print(f"Прогресс: {i}/{len(users)} пользователей обработано.\n")

    print("\n✅ Все пользователи обработаны!")

if __name__ == "__main__":
    main()