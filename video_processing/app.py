import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import subprocess
import sys
import os
import hashlib
import time
import json

BG      = "#0d0d0d"
BG2     = "#161616"
BG3     = "#1e1e1e"
BG4     = "#252525"
ACCENT  = "#fe2c55"
ACCENT2 = "#25f4ee"
TEXT    = "#ffffff"
TEXT2   = "#888888"
TEXT3   = "#444444"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
ERROR   = "#ef4444"
BORDER  = "#2a2a2a"

FH1  = ("Segoe UI", 17, "bold")
FH2  = ("Segoe UI", 11, "bold")
FH3  = ("Segoe UI", 10, "bold")
FB   = ("Segoe UI", 10)
FSM  = ("Segoe UI", 9)
MONO = ("Consolas", 9)

CONFIG_FILE = "app_config.json"

# ── Config ──────────────────────────────────
def load_cfg():
    d = {
        "username": "", "cookies_file": "", "use_browser": False,
        "fav_path": r"C:\video_processing\favorites",
        "vid_path": r"C:\video_processing",
        "photo_path": r"C:\video_processing\tiktok_photos",
        "delay": "2", "max_videos": "0", "block_count": "2",
        "users": [],
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                d.update(json.load(f))
        except: pass
    return d

def save_cfg(d):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except: pass

# ── Helpers ──────────────────────────────────
def cookie_args(cfg):
    if cfg.get("use_browser"):
        return ["--cookies-from-browser", "chrome"]
    cf = cfg.get("cookies_file", "")
    if cf and os.path.exists(cf):
        return ["--cookies", cf]
    return []

def block_dir(url, base, count):
    h = int(hashlib.sha256(url.encode()).hexdigest()[:8], 16)
    b = (h % int(count)) + 1
    d = os.path.join(base, f"input_block{b}")
    os.makedirs(d, exist_ok=True)
    return d

def check_tool(module):
    try:
        r = subprocess.run([sys.executable, "-m", module, "--version"],
                           capture_output=True, text=True)
        return r.returncode == 0
    except: return False

# ── Widget helpers ───────────────────────────
def section_lbl(parent, text):
    f = tk.Frame(parent, bg=BG)
    f.pack(fill="x", pady=(14, 5))
    tk.Label(f, text=text, font=("Segoe UI", 8, "bold"),
             bg=BG, fg=ACCENT2).pack(side="left")
    tk.Frame(f, bg=BORDER, height=1).pack(
        side="left", fill="x", expand=True, padx=(8, 0), pady=6)

def entry_row(parent, label, var, browse=None, btype=None):
    tk.Label(parent, text=label, font=FSM, bg=BG, fg=TEXT2, anchor="w").pack(fill="x")
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", pady=(2, 4))
    e = tk.Entry(row, textvariable=var, font=FB,
                 bg=BG3, fg=TEXT, insertbackground=TEXT, relief="flat", bd=0)
    e.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 1))
    if browse:
        def _b():
            p = filedialog.askdirectory() if btype == "dir" else \
                filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All", "*.*")])
            if p: var.set(p)
        tk.Button(row, text="…", font=FB, bg=BG4, fg=TEXT2,
                  relief="flat", cursor="hand2", padx=6,
                  command=_b).pack(side="left", ipady=7)
    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
    return e

def sbtn(parent, text, cmd, color=ACCENT, fg=TEXT, **kw):
    return tk.Button(parent, text=text, command=cmd, font=FH3,
                     bg=color, fg=fg, activebackground=color,
                     relief="flat", cursor="hand2", padx=18, pady=9, **kw)

def make_log(parent):
    b = scrolledtext.ScrolledText(parent, font=MONO, bg=BG2, fg=TEXT2,
                                   insertbackground=TEXT, relief="flat",
                                   state="disabled", wrap="word", padx=10, pady=8)
    for tag, col in [("info", TEXT2), ("success", SUCCESS), ("error", ERROR),
                     ("warning", WARNING), ("dim", TEXT3), ("accent", ACCENT2)]:
        b.tag_config(tag, foreground=col)
    return b

def log_w(box, msg, tag="info"):
    box.config(state="normal")
    box.insert("end", msg + "\n", tag)
    box.see("end")
    box.config(state="disabled")

def make_progress(parent, style_name):
    s = ttk.Style()
    s.configure(style_name, troughcolor=BG3, background=ACCENT, bordercolor=BG3)
    var = tk.DoubleVar()
    pb = ttk.Progressbar(parent, variable=var, style=style_name, maximum=100)
    pb.pack(fill="x", pady=(6, 2))
    lbl = tk.Label(parent, text="", font=FSM, bg=BG, fg=TEXT2, anchor="w")
    lbl.pack(fill="x")
    return var, lbl

# ── Workers ──────────────────────────────────
class BaseWorker:
    def __init__(self, cfg, log, prog, status):
        self.cfg = cfg; self.log = log
        self.prog = prog; self.status = status
        self._stop = False
    def stop(self): self._stop = True

    def _download_url(self, url, out_dir):
        ca = cookie_args(self.cfg)
        cmd = [sys.executable, "-m", "yt_dlp",
               "-o", os.path.join(out_dir, "%(uploader)s_%(upload_date)s_%(id)s.%(ext)s"),
               "--no-playlist", "--quiet", *ca, url]
        try:
            subprocess.run(cmd, check=True, timeout=300)
            return True
        except: return False

    def _get_urls(self, profile_url):
        ca = cookie_args(self.cfg)
        cmd = [sys.executable, "-m", "yt_dlp",
               "--flat-playlist", "--print", "url", "--no-download",
               *ca, profile_url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            return [u.strip() for u in r.stdout.strip().split("\n") if u.strip()]
        except: return []


class FavWorker(BaseWorker):
    def run(self):
        self.status("running")
        uname = self.cfg.get("username", "").lstrip("@")
        if not uname:
            self.log("✗ Никнейм не указан", "error"); self.status("idle"); return
        if not cookie_args(self.cfg):
            self.log("✗ Куки не настроены → вкладка Настройки", "error")
            self.status("idle"); return

        self.log(f"🔍 Получаю список избранного @{uname}...", "accent")
        urls = self._get_urls(f"https://www.tiktok.com/@{uname}/favorites")
        if not urls:
            self.log("❌ Список пуст. Проверь куки.", "error")
            self.status("idle"); return

        mx = int(self.cfg.get("max_videos", 0))
        if mx > 0: urls = urls[:mx]
        self.log(f"✓ Найдено: {len(urls)} видео", "success")

        out = self.cfg["fav_path"]
        os.makedirs(out, exist_ok=True)
        delay = float(self.cfg.get("delay", 2))
        ok = fail = 0

        for i, u in enumerate(urls, 1):
            if self._stop: self.log("⛔ Остановлено", "warning"); break
            self.log(f"[{i}/{len(urls)}] {u[:55]}...", "dim")
            if self._download_url(u, out):
                ok += 1; self.log("  ✓", "success")
            else:
                fail += 1; self.log("  ✗", "error")
            self.prog(i, len(urls)); time.sleep(delay)

        self.log(f"\n✅ Готово! Скачано: {ok} | Ошибок: {fail}", "success")
        self.status("idle")


class UsersWorker(BaseWorker):
    def __init__(self, cfg, users, log, prog, status):
        super().__init__(cfg, log, prog, status)
        self.users = users

    def run(self):
        self.status("running")
        if not self.users:
            self.log("✗ Список пуст", "error"); self.status("idle"); return

        delay = float(self.cfg.get("delay", 2))
        mx = int(self.cfg.get("max_videos", 0))

        for ui, uname in enumerate(self.users, 1):
            if self._stop: self.log("⛔ Остановлено", "warning"); break
            uname = uname.lstrip("@")
            self.log(f"\n── @{uname} ({ui}/{len(self.users)}) ──", "accent")
            urls = self._get_urls(f"https://www.tiktok.com/@{uname}")
            if not urls:
                self.log("  Нет видео / приватный", "warning"); continue
            if mx > 0: urls = urls[:mx]
            self.log(f"  Найдено: {len(urls)}", "info")

            ok = fail = 0
            for i, u in enumerate(urls, 1):
                if self._stop: break
                bd = block_dir(u, self.cfg["vid_path"], self.cfg.get("block_count", 2))
                if self._download_url(u, bd):
                    ok += 1
                else: fail += 1
                self.prog(i, len(urls)); time.sleep(delay)

            self.log(f"  ✓{ok} скачано  ✗{fail} ошибок", "success")

        self.log("\n✅ Все аккаунты обработаны!", "success")
        self.status("idle")


class PhotoWorker(BaseWorker):
    def __init__(self, cfg, users, log, prog, status):
        super().__init__(cfg, log, prog, status)
        self.users = users

    def run(self):
        self.status("running")
        if not check_tool("gallery_dl"):
            self.log("✗ gallery-dl не установлен!", "error")
            self.log("  Установи: py -m pip install gallery-dl", "warning")
            self.status("idle"); return
        if not self.users:
            self.log("✗ Список пуст", "error"); self.status("idle"); return

        delay = float(self.cfg.get("delay", 2))
        ca = []
        if self.cfg.get("use_browser"):
            ca = ["--cookies-from-browser", "chrome:default"]
        elif self.cfg.get("cookies_file") and os.path.exists(self.cfg["cookies_file"]):
            ca = ["--cookies", self.cfg["cookies_file"]]

        for ui, uname in enumerate(self.users, 1):
            if self._stop: self.log("⛔ Остановлено", "warning"); break
            uname = uname.lstrip("@")
            self.log(f"\n── Фото @{uname} ({ui}/{len(self.users)}) ──", "accent")
            out = os.path.join(self.cfg["photo_path"], uname)
            os.makedirs(out, exist_ok=True)
            cmd = [sys.executable, "-m", "gallery_dl",
                   "-d", out, "--sleep", str(delay),
                   *ca, f"https://www.tiktok.com/@{uname}"]
            try:
                subprocess.run(cmd, check=True, timeout=600)
                self.log(f"  ✓ → {out}", "success")
            except Exception as e:
                self.log(f"  ✗ {e}", "error")
            self.prog(ui, len(self.users))

        self.log("\n✅ Фото скачаны!", "success")
        self.status("idle")


# ── Base panel ───────────────────────────────
class BasePanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._worker = None

    def _make_log_panel(self, parent):
        right = tk.Frame(parent, bg=BG2,
                         highlightthickness=1, highlightbackground=BORDER)
        right.pack(side="left", fill="both", expand=True, pady=16, padx=(0, 20))
        hdr = tk.Frame(right, bg=BG3)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Лог", font=FH3, bg=BG3, fg=TEXT2, pady=7).pack(side="left")
        tk.Button(hdr, text="очистить", font=FSM, bg=BG3, fg=TEXT3,
                  relief="flat", cursor="hand2",
                  command=self._clear_log).pack(side="right", padx=8)
        self.log_box = make_log(right)
        self.log_box.pack(fill="both", expand=True)

    def _log(self, msg, tag="info"):
        self.after(0, lambda: log_w(self.log_box, msg, tag))

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _set_prog(self, done, total):
        pct = done / total * 100 if total else 0
        self.after(0, lambda: [
            self._pb_var.set(pct),
            self._pb_lbl.config(text=f"{done}/{total}  ({pct:.0f}%)")
        ])

    def _set_status(self, state):
        def _do():
            if state == "running":
                self._lbl_status.config(text="● Загрузка...", fg=WARNING)
                self._btn_s.config(state="disabled")
                self._btn_x.config(state="normal")
            else:
                self._lbl_status.config(text="● Готов", fg=SUCCESS)
                self._btn_s.config(state="normal")
                self._btn_x.config(state="disabled")
        self.after(0, _do)

    def _make_controls(self, parent, style_id):
        self._lbl_status = tk.Label(parent, text="● Готов", font=FB,
                                     bg=BG, fg=SUCCESS, anchor="w")
        self._lbl_status.pack(fill="x", pady=(14, 0))
        self._pb_var, self._pb_lbl = make_progress(parent, f"{style_id}.H.TProgressbar")
        br = tk.Frame(parent, bg=BG)
        br.pack(fill="x", pady=(12, 0))
        self._btn_s = sbtn(br, "▶  СТАРТ", self._start)
        self._btn_s.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._btn_x = sbtn(br, "■  СТОП", self._stop, color=BG4, fg=TEXT2)
        self._btn_x.pack(side="left")
        self._btn_x.config(state="disabled")

    def _stop(self):
        if self._worker: self._worker.stop()

    def _start(self): pass
    def load(self): pass


# ── Favorites tab ────────────────────────────
class FavTab(BasePanel):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=BG, width=300)
        left.pack(side="left", fill="y", padx=(20, 12), pady=16)
        left.pack_propagate(False)

        section_lbl(left, "СКАЧАТЬ ИЗБРАННОЕ")
        tk.Label(left, text="Скачивает видео из раздела «Избранное»\nтвоего аккаунта TikTok.",
                 font=FSM, bg=BG, fg=TEXT2, justify="left").pack(anchor="w", pady=(0, 8))

        section_lbl(left, "АККАУНТ")
        self.v_user = tk.StringVar()
        entry_row(left, "Никнейм (без @)", self.v_user)

        section_lbl(left, "ПАРАМЕТРЫ")
        pr = tk.Frame(left, bg=BG); pr.pack(fill="x")
        self.v_delay = tk.StringVar(value="2")
        self.v_max   = tk.StringVar(value="0")
        for lbl, v, w in [("Задержка сек", self.v_delay, 5),
                           ("Макс (0=все)", self.v_max, 7)]:
            f = tk.Frame(pr, bg=BG); f.pack(side="left", padx=(0, 14))
            tk.Label(f, text=lbl, font=FSM, bg=BG, fg=TEXT2).pack(anchor="w")
            tk.Entry(f, textvariable=v, font=FB, width=w,
                     bg=BG3, fg=TEXT, insertbackground=TEXT,
                     relief="flat", bd=0).pack(ipady=6)

        self._make_controls(left, "FAV")
        self._make_log_panel(self)

    def _start(self):
        cfg = self.app.get_cfg()
        cfg["username"]   = self.v_user.get().strip()
        cfg["delay"]      = self.v_delay.get()
        cfg["max_videos"] = self.v_max.get()
        self._worker = FavWorker(cfg, self._log, self._set_prog, self._set_status)
        threading.Thread(target=self._worker.run, daemon=True).start()

    def load(self):
        self.v_user.set(self.app.cfg.get("username", ""))
        self.v_delay.set(self.app.cfg.get("delay", "2"))


# ── Users/Photos tab ─────────────────────────
class UsersTab(BasePanel):
    def __init__(self, parent, app, mode="video"):
        super().__init__(parent, app)
        self.mode = mode
        self._build()

    def _build(self):
        left = tk.Frame(self, bg=BG, width=300)
        left.pack(side="left", fill="y", padx=(20, 12), pady=16)
        left.pack_propagate(False)

        title = "ВИДЕО ПО АККАУНТАМ" if self.mode == "video" else "ФОТО ПО АККАУНТАМ"
        desc  = ("Скачивает все видео с профилей\nуказанных аккаунтов." if self.mode == "video"
                 else "Скачивает фото-посты с профилей\nуказанных аккаунтов (gallery-dl).")
        section_lbl(left, title)
        tk.Label(left, text=desc, font=FSM, bg=BG, fg=TEXT2,
                 justify="left").pack(anchor="w", pady=(0, 8))

        section_lbl(left, "СПИСОК АККАУНТОВ")
        tk.Label(left, text="Один ник в строке (без @):",
                 font=FSM, bg=BG, fg=TEXT2).pack(anchor="w")
        lf = tk.Frame(left, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
        lf.pack(fill="x", pady=(4, 0))
        self.users_box = tk.Text(lf, font=MONO, bg=BG3, fg=TEXT,
                                  insertbackground=TEXT, relief="flat",
                                  height=9, padx=8, pady=6)
        self.users_box.pack(fill="x")

        br = tk.Frame(left, bg=BG); br.pack(fill="x", pady=(4, 0))
        tk.Button(br, text="💾 Сохранить", font=FSM, bg=BG4, fg=TEXT2,
                  relief="flat", cursor="hand2",
                  command=self._save_users).pack(side="left")
        tk.Button(br, text="🗑 Очистить", font=FSM, bg=BG4, fg=TEXT2,
                  relief="flat", cursor="hand2",
                  command=lambda: self.users_box.delete("1.0", "end")
                  ).pack(side="left", padx=(6, 0))

        section_lbl(left, "ПАРАМЕТРЫ")
        pr = tk.Frame(left, bg=BG); pr.pack(fill="x")
        self.v_delay = tk.StringVar(value="2")
        self.v_max   = tk.StringVar(value="0")
        for lbl, v, w in [("Задержка сек", self.v_delay, 5),
                           ("Макс видео (0=все)", self.v_max, 8)]:
            f = tk.Frame(pr, bg=BG); f.pack(side="left", padx=(0, 14))
            tk.Label(f, text=lbl, font=FSM, bg=BG, fg=TEXT2).pack(anchor="w")
            tk.Entry(f, textvariable=v, font=FB, width=w,
                     bg=BG3, fg=TEXT, insertbackground=TEXT,
                     relief="flat", bd=0).pack(ipady=6)

        self._make_controls(left, "USR" if self.mode == "video" else "PHO")
        self._make_log_panel(self)

    def _save_users(self):
        users = self._get_users()
        self.app.cfg["users"] = users
        save_cfg(self.app.cfg)
        self._log(f"✓ Сохранено {len(users)} аккаунтов", "success")

    def _get_users(self):
        raw = self.users_box.get("1.0", "end").strip()
        return [u.strip().lstrip("@") for u in raw.split("\n") if u.strip()]

    def _start(self):
        self._save_users()
        users = self._get_users()
        cfg = self.app.get_cfg()
        cfg["delay"] = self.v_delay.get()
        cfg["max_videos"] = self.v_max.get()
        if self.mode == "video":
            self._worker = UsersWorker(cfg, users, self._log, self._set_prog, self._set_status)
        else:
            self._worker = PhotoWorker(cfg, users, self._log, self._set_prog, self._set_status)
        threading.Thread(target=self._worker.run, daemon=True).start()

    def load(self):
        users = self.app.cfg.get("users", [])
        self.users_box.delete("1.0", "end")
        self.users_box.insert("1.0", "\n".join(users))
        self.v_delay.set(self.app.cfg.get("delay", "2"))


# ── Settings tab ─────────────────────────────
class SettingsTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="both", expand=True, padx=28, pady=20)

        left = tk.Frame(wrap, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 32))

        section_lbl(left, "АВТОРИЗАЦИЯ")
        self.v_browser = tk.BooleanVar()
        tk.Checkbutton(left, text="Брать куки из Chrome автоматически",
                       variable=self.v_browser, bg=BG, fg=TEXT2,
                       activebackground=BG, selectcolor=BG3, font=FB,
                       command=self._toggle).pack(anchor="w", pady=(0, 6))
        self.v_cookies = tk.StringVar()
        self.ce = entry_row(left, "Путь к cookies.txt", self.v_cookies, browse=True)

        section_lbl(left, "ПАПКИ СОХРАНЕНИЯ")
        self.v_fav   = tk.StringVar()
        self.v_vid   = tk.StringVar()
        self.v_photo = tk.StringVar()
        entry_row(left, "Избранное",        self.v_fav,   browse=True, btype="dir")
        entry_row(left, "Видео (блоки)",    self.v_vid,   browse=True, btype="dir")
        entry_row(left, "Фото",             self.v_photo, browse=True, btype="dir")

        section_lbl(left, "ПРОЧЕЕ")
        pr = tk.Frame(left, bg=BG); pr.pack(fill="x")
        self.v_delay  = tk.StringVar(value="2")
        self.v_blocks = tk.StringVar(value="2")
        for lbl, v, w in [("Задержка по умолч.", self.v_delay, 5),
                           ("Кол-во блоков",     self.v_blocks, 5)]:
            f = tk.Frame(pr, bg=BG); f.pack(side="left", padx=(0, 16))
            tk.Label(f, text=lbl, font=FSM, bg=BG, fg=TEXT2).pack(anchor="w")
            tk.Entry(f, textvariable=v, font=FB, width=w,
                     bg=BG3, fg=TEXT, insertbackground=TEXT,
                     relief="flat", bd=0).pack(ipady=6)

        sbtn(left, "💾  Сохранить настройки", self._save,
             color=ACCENT2, fg=BG).pack(pady=(18, 0), anchor="w")
        self.lbl_saved = tk.Label(left, text="", font=FSM, bg=BG, fg=SUCCESS)
        self.lbl_saved.pack(anchor="w", pady=(6, 0))

        # Right: deps + howto
        right = tk.Frame(wrap, bg=BG2,
                         highlightthickness=1, highlightbackground=BORDER,
                         padx=20, pady=16)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(right, text="Зависимости", font=FH2,
                 bg=BG2, fg=TEXT).pack(anchor="w", pady=(0, 8))
        self.dep_frame = tk.Frame(right, bg=BG2)
        self.dep_frame.pack(fill="x")
        sbtn(right, "🔄  Проверить", self._check_deps,
             color=BG4, fg=TEXT2).pack(anchor="w", pady=(8, 16))

        tk.Label(right, text="Как получить cookies.txt", font=FH3,
                 bg=BG2, fg=ACCENT2).pack(anchor="w")
        howto = (
            "1. Установи расширение в браузер:\n"
            "   Chrome: «Get cookies.txt LOCALLY»\n"
            "   Firefox: «cookies.txt»\n\n"
            "2. Открой tiktok.com и войди в аккаунт\n\n"
            "3. Нажми расширение → Export → сохрани файл\n\n"
            "4. Укажи путь к файлу выше\n\n"
            "   ИЛИ включи галочку «Брать из Chrome»"
        )
        tk.Label(right, text=howto, font=FSM, bg=BG2, fg=TEXT2,
                 justify="left").pack(anchor="w")

    def _toggle(self):
        self.ce.config(state="disabled" if self.v_browser.get() else "normal")

    def _save(self):
        self.app.cfg.update({
            "use_browser":  self.v_browser.get(),
            "cookies_file": self.v_cookies.get().strip(),
            "fav_path":     self.v_fav.get().strip(),
            "vid_path":     self.v_vid.get().strip(),
            "photo_path":   self.v_photo.get().strip(),
            "delay":        self.v_delay.get().strip(),
            "block_count":  self.v_blocks.get().strip(),
        })
        save_cfg(self.app.cfg)
        self.lbl_saved.config(text="✓ Сохранено!")
        self.after(2500, lambda: self.lbl_saved.config(text=""))

    def _check_deps(self):
        for w in self.dep_frame.winfo_children(): w.destroy()
        for name, mod, cmd in [
            ("yt-dlp",      "yt_dlp",     "py -m pip install yt-dlp"),
            ("gallery-dl",  "gallery_dl", "py -m pip install gallery-dl"),
        ]:
            ok = check_tool(mod)
            row = tk.Frame(self.dep_frame, bg=BG2); row.pack(fill="x", pady=2)
            tk.Label(row, text="●", font=FB, bg=BG2,
                     fg=SUCCESS if ok else ERROR).pack(side="left")
            status = "установлен ✓" if ok else f"НЕ найден  →  {cmd}"
            tk.Label(row, text=f"  {name}: {status}",
                     font=FSM, bg=BG2, fg=TEXT2).pack(side="left")

    def load(self):
        c = self.app.cfg
        self.v_browser.set(c.get("use_browser", False))
        self.v_cookies.set(c.get("cookies_file", ""))
        self.v_fav.set(c.get("fav_path", ""))
        self.v_vid.set(c.get("vid_path", ""))
        self.v_photo.set(c.get("photo_path", ""))
        self.v_delay.set(c.get("delay", "2"))
        self.v_blocks.set(c.get("block_count", "2"))
        self._toggle()


# ── Main app ─────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TikTok Downloader")
        self.geometry("900x640")
        self.minsize(760, 540)
        self.configure(bg=BG)
        self.cfg = load_cfg()
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=BG2)
        hdr.pack(fill="x")
        logo = tk.Frame(hdr, bg=BG2)
        logo.pack(side="left", padx=20, pady=12)
        tk.Label(logo, text="⬇ ", font=("Segoe UI Emoji", 18),
                 bg=BG2, fg=ACCENT).pack(side="left")
        tk.Label(logo, text="TikTok ", font=FH1,
                 bg=BG2, fg=TEXT).pack(side="left")
        tk.Label(logo, text="Downloader", font=FH1,
                 bg=BG2, fg=ACCENT).pack(side="left")

        # Tab bar
        tab_bar = tk.Frame(self, bg=BG3)
        tab_bar.pack(fill="x")

        self._tabs     = {}
        self._tab_btns = {}
        content = tk.Frame(self, bg=BG)
        content.pack(fill="both", expand=True)

        defs = [
            ("⭐  Избранное",     "fav",      FavTab,      {}),
            ("👤  По аккаунтам",  "users",    UsersTab,    {"mode": "video"}),
            ("🖼  Фото",          "photos",   UsersTab,    {"mode": "photo"}),
            ("⚙️  Настройки",    "settings", SettingsTab, {}),
        ]
        for label, key, cls, kw in defs:
            frame = cls(content, self, **kw)
            self._tabs[key] = frame
            btn = tk.Button(tab_bar, text=label, font=FB,
                            bg=BG3, fg=TEXT2,
                            activebackground=BG4, activeforeground=TEXT,
                            relief="flat", cursor="hand2",
                            padx=18, pady=10,
                            command=lambda k=key: self._switch(k))
            btn.pack(side="left")
            self._tab_btns[key] = btn

        self._switch("fav")

    def _switch(self, key):
        for f in self._tabs.values(): f.pack_forget()
        for k, b in self._tab_btns.items():
            b.config(bg=BG3, fg=TEXT2)
        self._tabs[key].pack(fill="both", expand=True)
        self._tab_btns[key].config(bg=BG4, fg=TEXT)
        if hasattr(self._tabs[key], "load"):
            self._tabs[key].load()

    def get_cfg(self): return dict(self.cfg)
    def save(self):    save_cfg(self.cfg)


if __name__ == "__main__":
    App().mainloop()
