# -*- coding: utf-8 -*-
"""
GÖRSEL ARAYÜZ (tkinter/ttk): Pencere düzeni, interaktif davranışlar, iş parçacıkları.
İnternet/okuma/yazma ve mesaj metinleri ilgili modüllere taşınmıştır.
"""

import os
import sys
import re
import time
import threading
import concurrent.futures
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox

from src.internet_connection import is_internet_ok, status_and_size_mb, INTERNET_MSG
from src.error_checking import (
    is_file_locked_for_write, show_info, show_warning, show_error,
    msg_need_input_file, msg_input_not_found, msg_need_output_dir,
    msg_need_excel_header, msg_file_open_excel, msg_file_open_xml,
    msg_file_state_unknown, msg_count_result, msg_read_error,
    msg_unsupported_filetype, msg_output_write_error, msg_generic_error,
)
from src.reader import is_excel, is_xml, read_urls_from_xlsx, read_urls_from_wxr
from src.writer import XlsxBuilder, url_filename_no_ext, url_extension


class App(tk.Tk):
    def __init__(self, icon_path_ico: str, logo_path: str, about_path: str, license_path: str, thanks_path: str):
        super().__init__()
        self.title("URL Boyut Hesaplayıcı")
        self.geometry("1250x350")
        self.resizable(False, False)

        self.icon_path_ico = icon_path_ico or ""
        self.logo_path = logo_path or ""
        self.about_path = about_path or ""
        self.license_path = license_path or ""
        self.thanks_path = thanks_path or ""
        self._set_window_icon()

        # UI font (isteğe göre ana .pyw üzerinden de ayarlanır — burada yedek)
        try:
            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(family="Segoe UI", size=9)
            self.option_add("*Font", default_font)
        except Exception:
            pass

        # Paralel işçi sayısı
        import os as _os
        self.max_workers = min(32, (_os.cpu_count() or 4) * 4)

        # === Ana yerleşim (SOL logo paneli + SAĞ içerik) ===
        container = ttk.Frame(self)
        container.grid(row=0, column=0, sticky="nsew")
        try:
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(0, weight=1)
            container.grid_columnconfigure(0, minsize=350)
            container.grid_columnconfigure(1, weight=1)
            container.grid_rowconfigure(0, minsize=350)
        except Exception:
            pass

        # Sol: Logo paneli
        self.logo_frame = ttk.Frame(container, width=350, height=350)
        self.logo_frame.grid(row=0, column=0, sticky="nw")
        try:
            self.logo_frame.grid_propagate(False)
        except Exception:
            pass
        self.logo_image = None
        self._place_logo()

        # Sağ: İçerik
        root = ttk.Frame(container, padding=30)
        root.grid(row=0, column=1, sticky="nsew")
        try:
            root.grid_columnconfigure(1, weight=1)
        except Exception:
            pass
        pad = {"padx": 8, "pady": 8}

        self.var_file = tk.StringVar()
        self.var_header = tk.StringVar(value="URL")
        self.var_save = tk.StringVar()

        self.var_progress = tk.IntVar(value=0)
        self.var_pct = tk.StringVar(value="0%")
        self.var_eta = tk.StringVar(value=f'{INTERNET_MSG["eta_prefix"]}--:--:--')
        self.var_count = tk.StringVar(value="")
        self.var_total_urls = tk.StringVar(value="")

        # Satır 0: Girdi dosyası
        ttk.Label(root, text="Girdi dosyası (.xlsx / .xml):").grid(row=0, column=0, sticky="w", **pad)
        self.ent_file = ttk.Entry(root, textvariable=self.var_file, width=60)
        self.ent_file.grid(row=0, column=1, sticky="we", **pad)
        self.btn_browse = ttk.Button(root, text="Gözat…", command=self.on_browse, width=10)
        self.btn_browse.grid(row=0, column=2, sticky="e", **pad)

        # Satır 1: Excel sütun adı
        self.lbl_header = ttk.Label(root, text="URL sütun adı:")
        self.lbl_header.grid(row=1, column=0, sticky="w", **pad)
        self.ent_header = ttk.Entry(root, textvariable=self.var_header, width=20)
        self.ent_header.grid(row=1, column=1, sticky="w", **pad)

        # Satır 2: Çıktı klasörü
        ttk.Label(root, text="Çıktı klasörü:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_save = ttk.Entry(root, textvariable=self.var_save, width=60)
        self.ent_save.grid(row=2, column=1, sticky="we", **pad)
        self.btn_save = ttk.Button(root, text="Gözat…", command=self.on_browse_save, width=10)
        self.btn_save.grid(row=2, column=2, sticky="e", **pad)

        # Dosya değişince header state
        try:
            self.var_file.trace_add("write", lambda *a: self._update_header_state())
        except Exception:
            pass
        self._update_header_state()

        # Satır 3: Progress bar + %
        self.pb = ttk.Progressbar(root, orient="horizontal", mode="determinate", maximum=100, variable=self.var_progress)
        self.pb.grid(row=3, column=0, columnspan=2, sticky="we", **pad)
        self.lbl_pct = ttk.Label(root, textvariable=self.var_pct)
        self.lbl_pct.grid(row=3, column=2, sticky="e", **pad)

        # Satır 4: ETA & sayaç
        self.lbl_eta = ttk.Label(root, textvariable=self.var_eta)
        self.lbl_eta.grid(row=4, column=0, columnspan=2, sticky="w", **pad)
        self.lbl_count = ttk.Label(root, textvariable=self.var_count)
        self.lbl_count.grid(row=4, column=2, sticky="e", **pad)

        # Spacer
        self.spacer = ttk.Frame(root)
        self.spacer.grid(row=5, column=0, columnspan=3, sticky="nsew")
        try:
            root.grid_rowconfigure(5, weight=1)
        except Exception:
            pass

        # Satır 6: Butonlar
        btn_bar = ttk.Frame(root)
        btn_bar.grid(row=6, column=0, columnspan=2, sticky="w", **pad)
        self.btn_start = ttk.Button(btn_bar, text="Başlat", command=self.on_start, width=12)
        self.btn_start.pack(side="left", padx=6)
        self.btn_cancel = ttk.Button(btn_bar, text="İptal Et", command=self.on_cancel, width=12)
        self.btn_cancel.pack_forget()

        self.btn_count = ttk.Button(btn_bar, text="URL Ön Sayım", command=self.on_count_click, width=15)
        self.btn_count.pack(side="left", padx=6)

        self.btn_about = ttk.Button(root, text="Uygulama Hakkında", command=self.on_about, width=18)
        self.btn_about.grid(row=6, column=2, sticky="e", **pad)

        # Durum bayrakları
        self.cancel_event = threading.Event()
        self.worker = None
        self.was_cancelled = False
        self.net_lost = threading.Event()
        self.net_waiting = threading.Event()
        self.reconnect_event = threading.Event()
        self.reconnect_choice = None
        self.reconnect_retry_mode = threading.Event()

        # Progress öğelerini ilk başta gizle
        self._set_progress_widgets_visible(False)

        # Açılışta internet kontrolü (pencere açıldıktan sonra 0 ms ile)
        try:
            self.after(0, self._check_internet_on_launch)
        except Exception:
            pass

        # Kapatma onayı
        try:
            self.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:
            pass

    # --- UI yardımcıları ---

    def _set_window_icon(self):
        try:
            if sys.platform == "win32" and os.path.exists(self.icon_path_ico):
                self.iconbitmap(self.icon_path_ico)
        except Exception:
            pass

    def _place_logo(self):
        for w in self.logo_frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        try:
            if self.logo_path and os.path.isfile(self.logo_path):
                self.logo_image = tk.PhotoImage(file=self.logo_path)
                lbl = ttk.Label(self.logo_frame, image=self.logo_image, anchor="center")
                lbl.place(relx=0.5, rely=0.5, anchor="center")
                return
        except Exception:
            self.logo_image = None
        ph = ttk.Label(self.logo_frame, text="Logo\n(350px)", anchor="center", justify="center")
        ph.place(relx=0.5, rely=0.5, anchor="center")

    def _set_progress_widgets_visible(self, show: bool):
        try:
            if show:
                self.pb.grid()
                self.lbl_pct.grid()
                self.lbl_eta.grid()
                self.lbl_count.grid()
            else:
                self.pb.grid_remove()
                self.lbl_pct.grid_remove()
                self.lbl_eta.grid_remove()
                self.lbl_count.grid_remove()
        except Exception:
            pass

    def _update_header_state(self):
        path = self.var_file.get()
        xml_mode = is_xml(path)
        state = "disabled" if xml_mode else "normal"
        try:
            self.ent_header.configure(state=state)
            self.lbl_header.configure(state=state)
        except Exception:
            pass

    # --- Hakkında ---

    def on_about(self):
        # İçerikleri oku
        try:
            with open(self.about_path, "r", encoding="utf-8") as f:
                content_about = f.read()
        except Exception as e:
            content_about = f"hakkinda.txt okunamadı:\n{e}"

        try:
            with open(self.license_path, "r", encoding="utf-8") as f:
                content_license = f.read()
        except Exception as e:
            content_license = f"lisans.txt okunamadı:\n{e}"

        try:
            with open(self.thanks_path, "r", encoding="utf-8") as f:
                content_thanks = f.read()
        except Exception as e:
            content_thanks = f"tesekkurler.txt okunamadı:\n{e}"

        if hasattr(self, "about_window") and self.about_window and self.about_window.winfo_exists():
            try:
                self.about_window.deiconify()
                self.about_window.lift()
                self.about_window.focus_force()
            except Exception:
                pass
            return

        self.about_window = tk.Toplevel(self)
        self.about_window.title("Uygulama Hakkında")
        self.about_window.geometry("720x350")
        self.about_window.minsize(720, 350)
        self.about_window.resizable(False, False)
        self.about_window.protocol("WM_DELETE_WINDOW", lambda: self._close_about())

        try:
            if os.path.isfile(self.icon_path_ico):
                self.about_window.iconbitmap(self.icon_path_ico)
        except Exception:
            pass

        try:
            self.about_window.update_idletasks()
            win_width, win_height = 720, 350
            screen_w = self.about_window.winfo_screenwidth()
            screen_h = self.about_window.winfo_screenheight()
            x = max(0, (screen_w // 2) - (win_width // 2))
            y = max(0, (screen_h // 2) - (win_height // 2))
            self.about_window.geometry(f"{win_width}x{win_height}+{x}+{y}")
        except Exception:
            pass

        # --- Sekmeli görünüm ---
        # Sekme başlıklarına (tab labels) padding vermek için özel stil
        style = ttk.Style(self.about_window)
        tab_style_name = "AboutTabs.TNotebook"
        # Sekmelerin etrafındaki marj (L,Üst,R,Aşağı) ve başlık içi padding
        style.configure(tab_style_name, tabmargins=(8, 6, 8, 0))
        style.configure(f"{tab_style_name}.Tab", padding=(14, 8))

        nb = ttk.Notebook(self.about_window, style=tab_style_name)
        # Pencere başlığı ile sekmeler arasına dış boşluk
        nb.pack(expand=True, fill="both", padx=8, pady=(10, 0))

        def _make_tab(parent, text, make_links=False):
            frame = ttk.Frame(parent)
            scrollbar = tk.Scrollbar(frame, cursor="arrow")
            scrollbar.pack(side="right", fill="y")
            try:
                segoe_ui_font = tkfont.Font(family="Segoe UI", size=9)
            except Exception:
                try:
                    segoe_ui_font = tkfont.nametofont("TkDefaultFont")
                except Exception:
                    segoe_ui_font = None
            txt = tk.Text(
                frame,
                wrap="word",
                yscrollcommand=scrollbar.set,
                font=segoe_ui_font if segoe_ui_font else None,
                padx=12, pady=12
            )
            txt.pack(expand=True, fill="both", padx=10, pady=10)
            try:
                txt.insert("1.0", text or "")
            except Exception:
                txt.insert("1.0", "Metin yüklenemedi.")

            # Tıklanabilir URL’ler (yalnızca make_links True ise)
            try:
                if make_links and text:
                    url_re = re.compile(r'https?://[^\s<>\")]+', re.IGNORECASE)
                    for i, m in enumerate(url_re.finditer(text)):
                        start = f"1.0+{m.start()}c"
                        end = f"1.0+{m.end()}c"
                        tag = f"url_{i}"
                        txt.tag_add(tag, start, end)
                        txt.tag_config(tag, foreground="#0000EE", underline=1)
                        # use default args to capture url per-iteration
                        def _on_enter(e, t=txt): t.config(cursor="hand2")
                        def _on_leave(e, t=txt): t.config(cursor="arrow")
                        txt.tag_bind(tag, "<Enter>", _on_enter)
                        txt.tag_bind(tag, "<Leave>", _on_leave)
                        txt.tag_bind(tag, "<Button-1>", lambda e, u=m.group(0): __import__("webbrowser").open(u))
            except Exception:
                pass

            # musa-demirci linkini özel olarak işle (sadece teşekkürler sekmesi için)
            if "musa-demirci" in (text or ""):
                try:
                    # Pozitif lookbehind/ahead ile parantezleri hariç tutarak daha kesin eşleşme:
                    # örn: "(musa-demirci)" veya "( musa-demirci )" -> sadece "musa-demirci" seçilir
                    author_re = re.compile(r'(?<=\()\s*(musa-demirci)\s*(?=\))', re.IGNORECASE)
                    for i, m in enumerate(author_re.finditer(text or "")):
                        start = f"1.0+{m.start(1)}c"
                        end = f"1.0+{m.end(1)}c"
                        tag = f"author_link_{i}"
                        txt.tag_add(tag, start, end)
                        txt.tag_config(tag, foreground="#0000EE", underline=1)
                        def _on_enter_a(e, t=txt): t.config(cursor="hand2")
                        def _on_leave_a(e, t=txt): t.config(cursor="arrow")
                        txt.tag_bind(tag, "<Enter>", _on_enter_a)
                        txt.tag_bind(tag, "<Leave>", _on_leave_a)
                        txt.tag_bind(tag, "<Button-1>", lambda e: self._switch_to_license_tab())
                except Exception:
                    pass

            # Disable editing but keep bindings. We need to prevent selection/copy for normal text,
            # yet allow tag handlers to receive clicks. Instead of blanket-binding to break,
            # bind handlers that check if click occurred on a link tag and only block otherwise.
            txt.config(state="disabled", cursor="arrow")

            def _is_click_on_link(widget, x, y):
                try:
                    tags = widget.tag_names(f"@{x},{y}")
                    for t in tags:
                        if t.startswith("url_") or t.startswith("author_link_"):
                            return True
                except Exception:
                    pass
                return False

            def _click_handler(e):
                if _is_click_on_link(e.widget, e.x, e.y):
                    # allow tag handler to run
                    return None
                return "break"

            def _double_click_handler(e):
                if _is_click_on_link(e.widget, e.x, e.y):
                    return None
                return "break"

            def _b1_motion_handler(e):
                return "break"

            txt.bind("<Button-1>", _click_handler)
            txt.bind("<Double-Button-1>", _double_click_handler)
            txt.bind("<B1-Motion>", _b1_motion_handler)
            for seq in ("<Control-c>", "<Control-a>", "<<Copy>>"):
                txt.bind(seq, lambda e: "break")

            txt.config(state="disabled", cursor="arrow")
            # Genel widget-level binding'leri linkleri engellemeyecek şekilde ayarla.
            # Fare tıklaması olduğunda, tıklanan konumdaki tag'leri kontrol et.
            def _text_click_handler(e):
                try:
                    # mouse koordinatından o noktadaki tag'leri al
                    tags = e.widget.tag_names(f"@{e.x},{e.y}")
                    # Eğer orada url_ veya author_link_ varsa; link handler'larının çalışmasına izin ver
                    for t in tags:
                        if t.startswith("url_") or t.startswith("author_link_"):
                            return None  # None => event işlemeye devam etsin (tag handler çalışacak)
                except Exception:
                    pass
                return "break"  # link yoksa seçimi/sürüklemeyi engelle

            # İki-kez tıklama ve sürüklemeyi de benzer mantıkla engelle (çift tıkta link varsa izin ver)
            def _text_double_click_handler(e):
                try:
                    tags = e.widget.tag_names(f"@{e.x},{e.y}")
                    for t in tags:
                        if t.startswith("url_") or t.startswith("author_link_"):
                            return None
                except Exception:
                    pass
                return "break"

            # B1-Motion (sürükleme) genelde engellensin
            def _text_b1_motion_handler(e):
                return "break"

            txt.bind("<Button-1>", _text_click_handler)
            txt.bind("<Double-Button-1>", _text_double_click_handler)
            txt.bind("<B1-Motion>", _text_b1_motion_handler)
            # Klavye kopyalama/alan seçim event'lerini eskisi gibi engelle
            for seq in ("<Control-c>", "<Control-a>", "<<Copy>>"):
                txt.bind(seq, lambda e: "break")
            scrollbar.config(command=txt.yview)
            return frame

        tab_about   = _make_tab(nb, content_about, make_links=False)
        tab_license = _make_tab(nb, content_license, make_links=True)   # Lisans sekmesindeki linkler tıklanabilir olsun
        tab_thanks  = _make_tab(nb, content_thanks, make_links=False)
        nb.add(tab_about, text="Hakkında")
        nb.add(tab_license, text="Lisans")
        nb.add(tab_thanks,  text="Teşekkürler")

    def _switch_to_license_tab(self):
        try:
            # about_window'daki notebook'u bul ve lisans sekmesine geç
            for widget in self.about_window.winfo_children():
                if isinstance(widget, ttk.Notebook):
                    widget.select(1)  # 1 = Lisans sekmesi (0=Hakkında, 1=Lisans, 2=Teşekkürler)
                    break
        except Exception:
            pass

    def _close_about(self):
        try:
            if hasattr(self, "about_window") and self.about_window:
                self.about_window.destroy()
        except Exception:
            pass
        finally:
            self.about_window = None

    # --- İnternet açılış kontrolü ---

    def _check_internet_on_launch(self):
        try:
            if not is_internet_ok(timeout=4.0):
                show_error(INTERNET_MSG["startup_error"], title="İnternet bağlantısı")
                try:
                    self.destroy()
                except Exception:
                    pass
        except Exception:
            show_error("Bağlantı kontrolü başarısız oldu. Lütfen tekrar deneyin.", title="İnternet bağlantısı")
            try:
                self.destroy()
            except Exception:
                pass

    # --- Dosya seçimleri / sayım ---

    def on_browse(self):
        path = filedialog.askopenfilename(
            title="Girdi dosyası seçin",
            filetypes=[
                ("Excel Çalışma Kitabı (*.xlsx)", "*.xlsx"),
                ("WordPress XML (*.xml)", "*.xml"),
                ("Tüm Dosyalar", "*.*"),
            ],
        )
        if path:
            self.var_file.set(path)
            self._update_header_state()
            try:
                if is_excel(path) or is_xml(path):
                    self.btn_count.config(state="normal")
            except Exception:
                pass
            try:
                if getattr(self, "was_cancelled", False):
                    self.pb.config(value=0, maximum=100)
                    self.var_progress.set(0)
                    self.var_pct.set("0%")
                    self.was_cancelled = False
            except Exception:
                pass

    def on_browse_save(self):
        out_dir = filedialog.askdirectory(
            title="Çıktı klasörünü seçin",
            mustexist=True,
            initialdir=os.getcwd()
        )
        if out_dir:
            self.var_save.set(out_dir)

    def on_count_click(self):
        path = (self.var_file.get() or "").strip()
        header = (self.var_header.get() or "").strip()
        if not path:
            msg_need_input_file(); return
        if not os.path.exists(path):
            msg_input_not_found(); return

        try:
            if (is_excel(path) or is_xml(path)) and is_file_locked_for_write(path):
                if is_excel(path):
                    msg_file_open_excel()
                else:
                    msg_file_open_xml()
                return
        except Exception:
            msg_file_state_unknown(); return

        try:
            if is_excel(path):
                if not header:
                    msg_need_excel_header(); return
                urls = read_urls_from_xlsx(path, header)
            elif is_xml(path):
                urls = read_urls_from_wxr(path)
            else:
                msg_unsupported_filetype(); return
        except Exception as e:
            msg_read_error(e); return

        try:
            self.var_total_urls.set(f"Toplam URL: {len(urls)}")
        except Exception:
            pass
        msg_count_result(len(urls))

    # --- Başlat / İptal ---

    def on_start(self):
        path = self.var_file.get().strip()
        header = self.var_header.get().strip()
        if not path:
            msg_need_input_file(); return

        try:
            if (is_excel(path) or is_xml(path)) and is_file_locked_for_write(path):
                if is_excel(path):
                    msg_file_open_excel()
                else:
                    msg_file_open_xml()
                return
        except Exception:
            msg_file_state_unknown(); return

        save_dir = self.var_save.get().strip()
        if not save_dir:
            msg_need_output_dir(); return

        base = os.path.splitext(os.path.basename(path))[0]
        save_path = os.path.join(save_dir, f"{base}_sonuc.xlsx")
        save_path = self._unique_save_path(save_path)

        # UI state
        self.btn_start.pack_forget()
        self.btn_cancel.pack(side="left", padx=6)
        try:
            self.btn_cancel.config(state="normal")
        except Exception:
            pass
        try:
            self.btn_count.pack_forget()
            self.btn_count.pack(side="left", padx=6)
        except Exception:
            pass

        self.ent_file.config(state="disabled")
        try:
            self.ent_save.config(state="disabled"); self.btn_save.config(state="disabled")
        except Exception:
            pass
        if is_excel(path):
            self.ent_header.config(state="disabled")

        self.pb.config(value=0, maximum=100)
        self.var_progress.set(0)
        self.var_pct.set("0%")
        self.var_eta.set(f'{INTERNET_MSG["eta_prefix"]}--:--:--')
        try:
            self.var_count.set("")
            self.lbl_count.grid_remove()
        except Exception:
            pass

        self.cancel_event.clear()
        self.net_lost.clear()
        self.net_waiting.clear()
        self.reconnect_retry_mode.clear()
        self.btn_browse.config(state="disabled")
        try:
            self.btn_count.config(state="disabled")
        except Exception:
            pass

        self.worker = threading.Thread(target=self._run_worker, args=(path, header, save_path), daemon=True)
        self.worker.start()

    def _unique_save_path(self, initial_path: str) -> str:
        path = initial_path
        root, ext = os.path.splitext(path)
        n = 1
        while os.path.exists(path) or os.path.exists(path + ".tmp"):
            n += 1
            path = f"{root}_{n}{ext}"
        return path

    def on_cancel(self):
        if not (self.worker and self.worker.is_alive()):
            return
        try:
            sure = messagebox.askyesno("İptal Et", "İşlemi iptal etmek istediğinizden emin misiniz?")
        except Exception:
            sure = True
        if not sure:
            return
        self.cancel_event.set()
        self.btn_cancel.config(state="disabled")

    # --- Worker ---

    def _run_worker(self, input_path: str, header_name: str, save_path: str):
        start_ts = time.time()
        last_update = start_ts

        # Başlatıldıktan hemen sonra internet kontrolü
        try:
            if not is_internet_ok(timeout=4.0):
                self.after(0, lambda: msg_generic_error(INTERNET_MSG["startup_error"]))
                self.after(0, self._reset_ui)
                return
        except Exception:
            self.after(0, lambda: msg_generic_error("Bağlantı kontrolü başarısız oldu. Lütfen tekrar deneyin."))
            self.after(0, self._reset_ui)
            return

        # Girdiyi oku
        try:
            if not os.path.exists(input_path):
                raise RuntimeError("Seçilen dosya bulunamadı.")
            if is_excel(input_path):
                if not header_name:
                    raise RuntimeError('Excel için URL sütun adını girin (örn. "URL").')
                urls = read_urls_from_xlsx(input_path, header_name)
            elif is_xml(input_path):
                urls = read_urls_from_wxr(input_path)
            else:
                raise RuntimeError("Desteklenmeyen dosya türü. Lütfen .xlsx veya .xml seçin.")
            total = len(urls)
            if total == 0:
                raise RuntimeError("Hiç URL bulunamadı.")
        except Exception as e:
            self.after(0, lambda e=e: msg_generic_error(f"Hata: {e}"))
            self.after(0, self._reset_ui)
            return

        self.after(0, lambda: (self._set_progress_widgets_visible(True), self._init_progress(total)))

        builder = XlsxBuilder()
        results = [None] * total
        completed = 0

        # İnternet izleyicisi
        def net_watch():
            fail_count = 0
            threshold = 3
            interval = 2.0
            self.net_cancelled_by_user = threading.Event()

            while not self.cancel_event.is_set():
                try:
                    online = is_internet_ok(timeout=3.0)
                except Exception:
                    online = False

                if online:
                    if self.net_waiting.is_set():
                        self.net_waiting.clear()
                        self.after(0, lambda: self.var_eta.set(f'{INTERNET_MSG["eta_prefix"]}--:--:--'))
                    if self.reconnect_retry_mode.is_set():
                        self.reconnect_retry_mode.clear()
                    fail_count = 0
                    time.sleep(interval)
                    continue

                fail_count += 1
                if not self.net_waiting.is_set():
                    self.net_waiting.set()

                if self.reconnect_retry_mode.is_set():
                    self.after(0, lambda: self.var_eta.set(INTERNET_MSG["waiting"]))
                    time.sleep(interval)
                    continue

                if fail_count < threshold:
                    self.after(0, lambda: self.var_eta.set(INTERNET_MSG["waiting"]))
                    time.sleep(interval)
                    continue

                countdown = 10
                recovered = False
                while countdown > 0 and not self.cancel_event.is_set():
                    try:
                        online_now = is_internet_ok(timeout=2.5)
                    except Exception:
                        online_now = False
                    if online_now:
                        recovered = True
                        break
                    self.after(0, lambda c=countdown: self.var_eta.set(f'{INTERNET_MSG["waiting"]} ({c})'))
                    time.sleep(1.0)
                    countdown -= 1

                if recovered and not self.cancel_event.is_set():
                    if self.net_waiting.is_set():
                        self.net_waiting.clear()
                    if self.reconnect_retry_mode.is_set():
                        self.reconnect_retry_mode.clear()
                    self.after(0, lambda: self.var_eta.set(f'{INTERNET_MSG["eta_prefix"]}--:--:--'))
                    fail_count = 0
                    continue

                if not self.cancel_event.is_set():
                    self.after(0, lambda: self.var_eta.set(f'{INTERNET_MSG["waiting"]} (0)'))

                if not self.cancel_event.is_set():
                    while not self.cancel_event.is_set():
                        def open_dialog():
                            self._show_reconnect_dialog()
                        self.reconnect_choice = None
                        self.reconnect_event.clear()
                        self.after(0, open_dialog)
                        self.reconnect_event.wait()
                        if self.reconnect_choice == "cancel":
                            self.net_cancelled_by_user.set()
                            self.cancel_event.set()
                            break
                        self.reconnect_retry_mode.set()
                        fail_count = 0
                        try:
                            online_now = is_internet_ok(timeout=2.5)
                        except Exception:
                            online_now = False
                        if online_now:
                            if self.net_waiting.is_set():
                                self.net_waiting.clear()
                            self.reconnect_retry_mode.clear()
                            self.after(0, lambda: self.var_eta.set(f'{INTERNET_MSG["eta_prefix"]}--:--:--'))
                            fail_count = 0
                            break
                        continue

        net_thread = threading.Thread(target=net_watch, daemon=True)
        net_thread.start()

        final_path = save_path
        tmp_path = save_path + ".tmp"

        def fetch_one(i_u):
            i, u = i_u
            while self.net_waiting.is_set() and not self.cancel_event.is_set():
                time.sleep(0.2)
            if self.cancel_event.is_set():
                fname = url_filename_no_ext(u)
                return (i, u, fname, len(fname), url_extension(u), None, "ERR")
            try:
                fname = url_filename_no_ext(u)
                ext = url_extension(u)
                length = len(fname)
                status, size_mb = status_and_size_mb(u)
                return (i, u, fname, length, ext, size_mb, status)
            except Exception:
                fname = url_filename_no_ext(u)
                return (i, u, fname, len(fname), url_extension(u), None, "ERR")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            idx_iter = iter(enumerate(urls))
            in_flight = set()
            try:
                for _ in range(min(self.max_workers, total)):
                    i, u = next(idx_iter)
                    in_flight.add(ex.submit(fetch_one, (i, u)))
            except StopIteration:
                pass

            while in_flight and not self.cancel_event.is_set():
                while self.net_waiting.is_set() and not self.cancel_event.is_set():
                    time.sleep(0.2)

                done, in_flight = concurrent.futures.wait(
                    in_flight, timeout=0.05, return_when=concurrent.futures.FIRST_COMPLETED
                )

                for fut in done:
                    if self.cancel_event.is_set():
                        break
                    try:
                        i, u, fname, length, ext, size_mb, status = fut.result()
                    except Exception:
                        i = None
                    if i is not None and 0 <= i < total:
                        results[i] = (u, fname, length, ext, size_mb, status)
                        completed += 1

                    if not self.cancel_event.is_set():
                        if not self.net_waiting.is_set():
                            try:
                                i2, u2 = next(idx_iter)
                                in_flight.add(ex.submit(fetch_one, (i2, u2)))
                            except StopIteration:
                                pass

                now = time.time()
                if now - last_update >= 0.05 or completed == total:
                    elapsed = now - start_ts
                    eta = "--:--:--"
                    if completed > 0:
                        per = elapsed / max(1, completed)
                        remain = max(0, int(round(per * (total - completed))))
                        h, rem = divmod(remain, 3600)
                        m, s = divmod(rem, 60)
                        eta = f"{h}:{m:02d}:{s:02d}"
                    self.after(0, lambda c=completed, t=total, e=eta: self._update_progress(c, t, e))
                    last_update = now

        for rec in results:
            if rec is None:
                continue
            u, fname, length, ext, size_mb, status = rec
            builder.add_row(u, fname, length, ext, size_mb, status)

        processed = sum(1 for r in results if r is not None)
        ok_count  = sum(1 for r in results if r is not None and r[5] == "OK")
        other_cnt = processed - ok_count

        try:
            builder.save(tmp_path)
        except Exception as e:
            self.after(0, lambda e=e: msg_output_write_error(e))
            self.after(0, self._reset_ui)
            return

        try:
            if os.path.exists(final_path):
                os.remove(final_path)
            os.replace(tmp_path, final_path)
        except Exception:
            final_path = tmp_path  # .tmp kalsın

        cancelled = self.cancel_event.is_set()
        try:
            self.was_cancelled = bool(cancelled)
        except Exception:
            pass

        def after_msg():
            try:
                if getattr(self, "net_cancelled_by_user", None) and self.net_cancelled_by_user.is_set():
                    info = INTERNET_MSG["net_cancelled"]
                elif cancelled:
                    info = INTERNET_MSG["cancelled"]
                else:
                    info = INTERNET_MSG["done"]
                show_info(info, title="URL Boyut Hesaplayıcı")
            finally:
                try:
                    self.lbl_eta.grid()
                    self.lbl_count.grid()
                except Exception:
                    pass
                try:
                    if getattr(self, "net_cancelled_by_user", None) and self.net_cancelled_by_user.is_set():
                        self.var_eta.set(INTERNET_MSG["net_cancelled"])
                    elif cancelled:
                        self.var_eta.set(INTERNET_MSG["cancelled"])
                    else:
                        self.var_eta.set(INTERNET_MSG["done"])
                    self.var_count.set(f"{processed}/{total}")
                except Exception:
                    pass
                try:
                    if not cancelled and processed == total and total > 0:
                        self.var_progress.set(self.pb["maximum"])
                        self.var_pct.set("100%")
                except Exception:
                    pass

                # Windows Gezgini'nde seçili göster
                try:
                    if sys.platform == "win32" and os.path.exists(final_path):
                        norm = os.path.normpath(final_path)
                        import ctypes, time as _t
                        result = ctypes.windll.shell32.ShellExecuteW(None, "open", "explorer.exe", f'/select,"{norm}"', None, 1)
                        if result > 32:
                            _t.sleep(0.2)
                            explorer_hwnd = ctypes.windll.user32.FindWindowW("CabinetWClass", None)
                            if explorer_hwnd:
                                ctypes.windll.user32.SetForegroundWindow(explorer_hwnd)
                except Exception:
                    pass

                self._reset_ui()

        self.after(0, after_msg)

    # --- UI progress ---

    def _init_progress(self, total: int):
        self.pb.config(value=0, maximum=max(1, total))
        self.var_progress.set(0)
        self.var_pct.set("0%")
        self.var_count.set(f"0/{total}")

    def _update_progress(self, completed: int, total: int, eta_text: str):
        self.var_progress.set(completed)
        if total <= 0 or completed <= 0:
            pct = 0
        elif completed >= total:
            pct = 100
        else:
            pct = int((completed / total) * 100)
        self.var_pct.set(f"{pct}%")
        self.var_count.set(f"{completed}/{total}")
        if not self.net_waiting.is_set():
            self.var_eta.set(f'{INTERNET_MSG["eta_prefix"]}{eta_text}')

    def _finish_with_error(self, msg: str):
        show_error(msg)
        self._reset_ui()

    def _reset_ui(self):
        try:
            self.btn_cancel.pack_forget()
        except Exception:
            pass
        self.btn_start.pack(side="left", padx=6)
        try:
            self.btn_count.pack_forget()
            self.btn_count.pack(side="left", padx=6)
        except Exception:
            pass
        self.ent_file.config(state="normal")
        self._update_header_state()
        self.btn_browse.config(state="normal")
        try:
            self.ent_save.config(state="normal")
            self.btn_save.config(state="normal")
        except Exception:
            pass

    # --- Kapanış onayı ---

    def _on_close(self):
        try:
            sure = messagebox.askyesno("Çıkış", "Uygulamadan çıkmak istediğinizden emin misiniz?")
        except Exception:
            sure = True
        if not sure:
            return
        try:
            if hasattr(self, "cancel_event"):
                self.cancel_event.set()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    # --- Özel yeniden bağlan diyalogu ---

    def _show_reconnect_dialog(self):
        try:
            retry = messagebox.askretrycancel(INTERNET_MSG["dialog_title"], INTERNET_MSG["dialog_body"])
        except Exception:
            retry = False
        self.reconnect_choice = "retry" if retry else "cancel"
        try:
            self.reconnect_event.set()
        except Exception:
            pass
