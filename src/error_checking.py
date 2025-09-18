# -*- coding: utf-8 -*-
"""
Uyarı/Hata/Bilgi mesajları ve dosya/kilit kontrolü gibi doğrulama yardımcıları.
Tüm kullanıcıya gösterilen metinler bu modülde.
"""

import os
from tkinter import messagebox

TITLE = {
    "error": "Hata",
    "warn": "Uyarı",
    "info": "Bilgi",
    "file_open": "Dosya açık",
    "file_state": "Dosya durumu",
    "count": "URL sayısı",
}

def show_info(message: str, title: str = TITLE["info"]) -> None:
    try:
        messagebox.showinfo(title, message)
    except Exception:
        pass

def show_warning(message: str, title: str = TITLE["warn"]) -> None:
    try:
        messagebox.showwarning(title, message)
    except Exception:
        pass

def show_error(message: str, title: str = TITLE["error"]) -> None:
    try:
        messagebox.showerror(title, message)
    except Exception:
        pass

# --- Dosya/Kilit kontrolü ---

def is_file_locked_for_write(path: str) -> bool:
    """
    Dosyayı yazma erişimiyle açmayı dener.
    Windows'ta Excel açıkken genellikle yazma kilidi olur ve 'rb+' açılışı hataya düşer.
    """
    try:
        with open(path, "rb+"):
            return False
    except (PermissionError, OSError):
        return True
    except Exception:
        return True

# --- Hazır mesaj yardımcıları ---

def msg_need_input_file():
    show_warning("Lütfen bir .xlsx / .xml dosyası seçin.")

def msg_input_not_found():
    show_error("Seçilen dosya bulunamadı.")

def msg_need_output_dir():
    show_warning("Lütfen çıktı klasörünü seçin.")

def msg_need_excel_header():
    show_warning('Excel için URL sütun adını girin (örn. "URL").')

def msg_file_open_excel():
    show_info(
        "Seçtiğiniz Excel (.xlsx) dosyası şu anda açık görünüyor.\n"
        "Lütfen kapatıp tekrar deneyin.",
        title=TITLE["file_open"],
    )

def msg_file_open_xml():
    show_info(
        "Seçtiğiniz XML (.xml) dosyası şu anda açık görünüyor.\n"
        "Lütfen kapatıp tekrar deneyin.",
        title=TITLE["file_open"],
    )

def msg_file_state_unknown():
    show_info(
        "Dosyanın açık olup olmadığı kontrol edilemedi. Lütfen dosyayı kapatıp tekrar deneyin.",
        title=TITLE["file_state"],
    )

def msg_count_result(n: int):
    show_info(f"Toplam URL sayısı: {n}", title=TITLE["count"])

def msg_read_error(e: Exception):
    show_error(f"URL sayısı hesaplanırken hata: {e}")

def msg_unsupported_filetype():
    show_error("Desteklenmeyen dosya türü. Lütfen .xlsx veya .xml seçin.")

def msg_output_write_error(e: Exception):
    show_error(f"Çıktı yazılırken hata: {e}")

def msg_generic_error(text: str):
    show_error(text)
