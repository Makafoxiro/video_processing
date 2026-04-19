import os
import glob
import shutil
from datetime import datetime

# ================== НАСТРОЙКИ ==================
OUTPUT_DIR = r"C:\video_processing\output"      # папка с одиночными .txt
ARCHIVE_DIR = r"C:\video_processing\archive"    # сюда перемещаем исходные
BATCH_SIZE = 500                                # объединять, если файлов ≥ 1000
# ===============================================

# Создаём архивную папку, если её нет
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def merge_txt_files(file_list, batch_name):
    """Объединяет список файлов в один большой .txt с разделителями"""
    merged_path = os.path.join(OUTPUT_DIR, batch_name)
    with open(merged_path, 'w', encoding='utf-8') as outfile:
        for fpath in sorted(file_list):
            fname = os.path.basename(fpath)
            outfile.write(f"\n--- {fname} ---\n")
            with open(fpath, 'r', encoding='utf-8') as infile:
                outfile.write(infile.read())
            outfile.write("\n\n")
    return merged_path

def main():
    # Получаем все .txt, кроме уже объединённых (batch_*)
    all_txt = glob.glob(os.path.join(OUTPUT_DIR, "*.txt"))
    all_txt = [f for f in all_txt if not os.path.basename(f).startswith("batch_")]

    total = len(all_txt)
    if total < BATCH_SIZE:
        print(f"✅ Файлов меньше {BATCH_SIZE} ({total}). Ничего не делаем.")
        return

    print(f"📁 Найдено {total} .txt. Начинаю объединение...")

    # Сортируем по дате изменения (старые первые)
    all_txt.sort(key=lambda x: os.path.getmtime(x))

    # Разбиваем на партии по BATCH_SIZE
    batches = [all_txt[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    for idx, batch in enumerate(batches, start=1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_name = f"batch_{idx:03d}_{timestamp}.txt"
        merged = merge_txt_files(batch, batch_name)
        print(f"   ✅ Создан {merged}")

        # Перемещаем исходные файлы в архив
        for f in batch:
            shutil.move(f, os.path.join(ARCHIVE_DIR, os.path.basename(f)))
        print(f"   📦 Перемещено {len(batch)} исходных файлов в архив")

    print("\n🎉 Готово! Все партии обработаны. Папка output теперь содержит только batch_*.txt")

if __name__ == "__main__":
    main()