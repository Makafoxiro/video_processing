import os
import sys
import subprocess
import time
import json

# ================== НАСТРОЙКИ ==================
YOUR_USERNAME   = "ВАШ_НИКНЕЙМ"          # твой ник в TikTok (без @)
DOWNLOAD_PATH   = r"C:\video_processing\favorites"   # куда сохранять
COOKIES_FILE    = r"C:\video_processing\tiktok_cookies.txt"  # файл с куками
DELAY_BETWEEN   = 3                        # пауза между видео (сек)
MAX_VIDEOS      = 0                        # 0 = все, N = первые N
BLOCK_COUNT     = 2                        # количество input_block папок
# ================================================

FAVORITES_URL = f"https://www.tiktok.com/@{YOUR_USERNAME}/favorites"


def check_dependencies():
    """Проверяем наличие yt-dlp"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--version"],
            capture_output=True, text=True, check=True
        )
        print(f"✓ yt-dlp версия: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ yt-dlp не найден. Установи: py -m pip install yt-dlp")
        sys.exit(1)


def check_cookies():
    """Проверяем наличие файла с куками"""
    if not os.path.exists(COOKIES_FILE):
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║              КАК ПОЛУЧИТЬ COOKIES ИЗ БРАУЗЕРА               ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Установи расширение для Chrome/Firefox:                  ║
║     "Get cookies.txt LOCALLY" (Chrome)                       ║
║     "cookies.txt" (Firefox)                                  ║
║                                                              ║
║  2. Зайди на tiktok.com и АВТОРИЗУЙСЯ в своём аккаунте      ║
║                                                              ║
║  3. Нажми на расширение → Export → сохрани файл как:        ║
║     {COOKIES_FILE:<52}║
║                                                              ║
║  4. Запусти скрипт снова                                     ║
║                                                              ║
║  ИЛИ используй yt-dlp напрямую из браузера:                 ║
║     py -m yt_dlp --cookies-from-browser chrome URL          ║
╚══════════════════════════════════════════════════════════════╝
""")
        ask = input("Попробовать взять куки прямо из Chrome? (y/n): ").strip().lower()
        if ask == 'y':
            return "chrome"
        sys.exit(1)
    return COOKIES_FILE


def get_video_list(cookies_source):
    """Получаем список видео из избранного"""
    print(f"\n🔍 Получаю список видео из избранного: {FAVORITES_URL}")

    if cookies_source == "chrome":
        cookie_args = ["--cookies-from-browser", "chrome"]
    else:
        cookie_args = ["--cookies", cookies_source]

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--flat-playlist",
        "--print", "url",
        "--no-download",
        *cookie_args,
        FAVORITES_URL
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"✗ Ошибка получения списка:\n{result.stderr[:500]}")
            print("\n💡 Подсказка: если ошибка 'Private', убедись что:")
            print("   - Куки взяты из браузера где ты залогинен")
            print("   - Вкладка tiktok.com была открыта перед экспортом кук")
            return []

        urls = [u for u in result.stdout.strip().split("\n") if u.strip()]
        print(f"✓ Найдено видео в избранном: {len(urls)}")
        return urls

    except subprocess.TimeoutExpired:
        print("✗ Таймаут при получении списка. Попробуй ещё раз.")
        return []


def download_video(url, idx, total, cookies_source, output_dir):
    """Скачиваем одно видео"""
    if cookies_source == "chrome":
        cookie_args = ["--cookies-from-browser", "chrome"]
    else:
        cookie_args = ["--cookies", cookies_source]

    # Распределяем по блокам (совместимо с твоей старой системой)
    import hashlib
    hash_int = int(hashlib.sha256(url.encode()).hexdigest()[:8], 16)
    block = (hash_int % BLOCK_COUNT) + 1
    block_dir = os.path.join(r"C:\video_processing", f"input_block{block}")
    os.makedirs(block_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    print(f"  [{idx}/{total}] Скачиваю → блок {block}: {url[:60]}...")

    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-o", os.path.join(output_dir, "%(uploader)s_%(upload_date)s_%(id)s.%(ext)s"),
        "--no-playlist",
        "--quiet",
        "--progress",
        *cookie_args,
        url
    ]

    try:
        subprocess.run(cmd, check=True, timeout=300)
        print(f"    ✓ Готово")
        return True
    except subprocess.CalledProcessError:
        print(f"    ✗ Ошибка скачивания (пропускаю)")
        return False
    except subprocess.TimeoutExpired:
        print(f"    ✗ Таймаут (пропускаю)")
        return False


def download_photos_from_favorites(cookies_source):
    """Скачиваем фото-посты из избранного через gallery-dl"""
    print("\n📸 Попытка скачать фото-посты через gallery-dl...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "gallery_dl", "--version"],
            capture_output=True, check=True
        )
    except:
        print("  gallery-dl не установлен, пропускаю фото. Установи: py -m pip install gallery-dl")
        return

    photo_dir = os.path.join(DOWNLOAD_PATH, "photos")
    os.makedirs(photo_dir, exist_ok=True)

    if cookies_source == "chrome":
        cookie_args = ["--cookies-from-browser", "chrome:default"]
    else:
        cookie_args = ["--cookies", cookies_source]

    cmd = [
        sys.executable, "-m", "gallery_dl",
        "-d", photo_dir,
        "--sleep", str(DELAY_BETWEEN),
        *cookie_args,
        FAVORITES_URL
    ]

    try:
        subprocess.run(cmd, check=True, timeout=600)
        print(f"  ✓ Фото сохранены в: {photo_dir}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ gallery-dl ошибка: {e}")


def save_failed_urls(urls, failed_file="failed_favorites.txt"):
    """Сохраняем упавшие ссылки для повтора"""
    with open(failed_file, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")
    print(f"\n📄 Неудачные ссылки сохранены в: {failed_file}")


def main():
    print("=" * 60)
    print("   TikTok Favorites Downloader")
    print("=" * 60)

    if YOUR_USERNAME == "ВАШ_НИКНЕЙМ":
        print("✗ Сначала укажи свой никнейм в переменной YOUR_USERNAME!")
        sys.exit(1)

    check_dependencies()
    cookies_source = check_cookies()

    # Получаем список видео
    video_urls = get_video_list(cookies_source)
    if not video_urls:
        print("\n❌ Не удалось получить список видео из избранного.")
        sys.exit(1)

    if MAX_VIDEOS > 0:
        video_urls = video_urls[:MAX_VIDEOS]
        print(f"Ограничение: скачиваю первые {MAX_VIDEOS} видео.")

    os.makedirs(DOWNLOAD_PATH, exist_ok=True)

    # Скачиваем видео
    print(f"\n⬇️  Начинаю скачивание {len(video_urls)} видео...")
    downloaded = 0
    failed_urls = []

    for idx, url in enumerate(video_urls, 1):
        success = download_video(url, idx, len(video_urls), cookies_source, DOWNLOAD_PATH)
        if success:
            downloaded += 1
        else:
            failed_urls.append(url)
        time.sleep(DELAY_BETWEEN)

    # Скачиваем фото
    download_photos_from_favorites(cookies_source)

    # Итог
    print("\n" + "=" * 60)
    print(f"✅ Готово! Скачано видео: {downloaded}/{len(video_urls)}")
    print(f"   Папка: {DOWNLOAD_PATH}")
    if failed_urls:
        print(f"⚠️  Не скачано: {len(failed_urls)}")
        save_failed_urls(failed_urls)
    print("=" * 60)


if __name__ == "__main__":
    main()
