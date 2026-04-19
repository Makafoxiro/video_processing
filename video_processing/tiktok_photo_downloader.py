import os
import sys
import subprocess
import time

# ================== НАСТРОЙКИ ==================
USER_FILE = "users.txt"                # файл со списком пользователей
DOWNLOAD_PATH = "./tiktok_photos"       # корневая папка для сохранения
DELAY_BETWEEN = 2                        # пауза между пользователями (сек)
# ================================================

def ensure_gallery_dl():
    try:
        subprocess.run([sys.executable, "-m", "gallery_dl", "--version"], capture_output=True, check=True)
    except:
        print("gallery-dl не найден. Установи: py -m pip install gallery-dl")
        sys.exit(1)

def download_user_photos(username):
    profile_url = f"https://www.tiktok.com/@{username.lstrip('@')}"
    user_dir = os.path.join(DOWNLOAD_PATH, username)
    os.makedirs(user_dir, exist_ok=True)

    print(f"\n--- Обрабатываю пользователя: {username} ---")

    # gallery-dl сам рекурсивно скачает всё
    cmd = [
        sys.executable, "-m", "gallery_dl",
        "-d", user_dir,          # папка назначения
        "--sleep", str(DELAY_BETWEEN),
        profile_url
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Пользователь {username}: загрузка завершена.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при загрузке {username}: {e}")
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
    ensure_gallery_dl()

    if not os.path.exists(USER_FILE):
        print(f"Файл {USER_FILE} не найден. Создай его и запиши по одному пользователю в строке.")
        sys.exit(1)

    with open(USER_FILE, "r", encoding="utf-8") as f:
        users = [line.strip() for line in f if line.strip()]

    print(f"Загружено пользователей: {len(users)}")

    for i, username in enumerate(users, 1):
        result = download_user_photos(username)
        if result == 0:
            print(f"Пользователь {username}: удаляю из списка.")
            remove_user_from_file(username)
        else:
            print(f"Пользователь {username}: ошибка, оставляю в списке.")
        print(f"Прогресс: {i}/{len(users)} пользователей обработано.\n")
        time.sleep(DELAY_BETWEEN)

    print("\n✅ Все пользователи обработаны!")

if __name__ == "__main__":
    main()