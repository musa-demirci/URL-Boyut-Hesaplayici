# -*- coding: utf-8 -*-
"""
Giriş noktası (.pyw): DPI/Font/AppID ayarları, asset yolları ve uygulamayı başlatma.
"""

import os
import sys
import ctypes
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

# Modüller
from src.gui import App
from src.internet_connection import is_internet_ok, INTERNET_MSG

# --- DPI Awareness ---

def setup_dpi_awareness():
    if sys.platform != "win32":
        return
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2); return
        except Exception:
            pass
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1); return
        except Exception:
            pass
        try:
            ctypes.windll.user32.SetProcessDPIAware(); return
        except Exception:
            pass
    except Exception:
        pass

# --- AppUserModelID (Görev çubuğu gruplaması) ---

def setup_app_user_model_id(app_id="URLBoyutHesaplayici"):
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass

# --- Kaynak yolu (PyInstaller ve geliştirme modu) ---

def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)

if __name__ == "__main__":
    setup_dpi_awareness()
    setup_app_user_model_id("com.example.urlboyuthesaplayici")

    # Uygulama penceresi oluşturmadan önce internet kontrolü (hata için geçici root)
    try:
        if not is_internet_ok(timeout=4.0):
            _root = tk.Tk()
            try:
                _root.withdraw()
                messagebox.showerror("İnternet bağlantısı", INTERNET_MSG["startup_error"])
            finally:
                try:
                    _root.destroy()
                except Exception:
                    pass
            sys.exit(1)
    except Exception:
        _root = tk.Tk()
        try:
            _root.withdraw()
            messagebox.showerror("İnternet bağlantısı", INTERNET_MSG["startup_unknown"])
        finally:
            try:
                _root.destroy()
            except Exception:
                pass
        sys.exit(1)

    # Assets yolları
    icon_path_ico = resource_path("assets", "icon.ico")
    logo_path     = resource_path("assets", "logo.png")

    # Docs yolları
    about_path    = resource_path("docs", "hakkinda.txt")
    license_path  = resource_path("docs", "lisans.txt")
    thanks_path    = resource_path("docs", "tesekkurler.txt")

    # Uygulamayı başlat
    app = App(
        icon_path_ico=icon_path_ico,
        logo_path=logo_path,
        about_path=about_path,
        license_path=license_path,
        thanks_path=thanks_path,
    )

    # Varsayılan fontu (global) ayarla — UI stil ayarları
    try:
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=9)
        app.option_add("*Font", default_font)
    except Exception:
        pass

    # (Gerekirse) ikon/logoyu tekrar uygula
    try:
        app._set_window_icon()
        app._place_logo()
    except Exception:
        pass

    app.mainloop()
