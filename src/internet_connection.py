# -*- coding: utf-8 -*-
"""
İnternet bağlantısı ve HTTP istekleriyle ilgili tüm yardımcılar + metinler.
Harici paket YOK (yalnızca standart kütüphane).
"""

from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse, quote
from urllib.request import Request, urlopen
from typing import Optional, Tuple

INTERNET_MSG = {
    "startup_error": (
        "İnternet bağlantısı kurulamadı.\n"
        "Bağlantı olmadan uygulama açılamaz. Lütfen bağlantınızı kontrol edin."
    ),
    "startup_unknown": (
        "Bağlantı kontrolü başarısız oldu. Uygulama kapatılıyor."
    ),
    "waiting": "İnternet bağlantısı bekleniyor...",
    "dialog_title": "İnternet bağlantısı",
    "dialog_body": (
        "İnternet bağlantısı yok veya sorunlu görünüyor.\n"
        "Lütfen bağlantınızı kontrol edip tekrar deneyin."
    ),
    "eta_prefix": "Tahmini kalan süre: ",
    "done": "İşlem tamamlandı.",
    "cancelled": "İşlem iptal edildi.",
    "net_cancelled": "İnternet bağlantısı işlem sırasında kesildi ve işlem iptal edildi.",
}

def is_internet_ok(timeout: float = 5.0) -> bool:
    """
    Ağ bağlanabilirliğini hızlıca sınar.
    - Birkaç hafif uç noktaya GET isteği atar (204/200 beklenir).
    - Herhangi biri 2xx/3xx dönerse bağlantı var kabul edilir.
    """
    test_urls = [
        "http://www.gstatic.com/generate_204",
        "http://clients3.google.com/generate_204",
        "http://example.com/",
        "https://www.microsoft.com/",
    ]
    for u in test_urls:
        try:
            req = Request(u)
            with urlopen(req, timeout=timeout) as resp:
                code = getattr(resp, "status", 200)
                if 200 <= code < 400:
                    return True
        except Exception:
            continue
    return False


def _safe_url(url: str) -> str:
    """Türkçe/boşluk vb. karakterleri path ve query kısmında güvenli biçime çevirir."""
    try:
        p = urlparse(url)
        safe_path = quote(p.path)
        safe_query = quote(p.query, safe="=&?")
        return urlunparse((p.scheme, p.netloc, safe_path, p.params, safe_query, p.fragment))
    except Exception:
        return url


def status_and_size_mb(url: str, timeout: float = 15.0) -> Tuple[str, Optional[float]]:
    """
    URL'yi HEAD ile yoklar; olmuyorsa kısmi GET dener.
    Dönen: (status_text, size_mb_float_or_None)
    - 200 => 'OK' yazdırılır, diğerleri doğrudan kod
    """
    url = _safe_url(url)
    size_bytes = None
    code = None

    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", 200)
            cl = resp.headers.get("Content-Length")
            if cl and cl.isdigit():
                size_bytes = int(cl)
    except HTTPError as e:
        code = e.code
        cl = e.headers.get("Content-Length") if hasattr(e, "headers") else None
        if cl and cl.isdigit():
            size_bytes = int(cl)
    except URLError:
        code = None
    except Exception:
        code = None

    # Eğer HEAD başarısız oldu ya da boyut yoksa, 0-0 Range ile GET dene
    if size_bytes is None:
        try:
            req = Request(url)
            req.add_header("Range", "bytes=0-0")
            with urlopen(req, timeout=timeout) as resp:
                if code is None:
                    code = getattr(resp, "status", 200)
                cr = resp.headers.get("Content-Range")
                # Örn: bytes 0-0/12345
                if cr and "/" in cr:
                    total = cr.split("/")[-1]
                    if total.isdigit():
                        size_bytes = int(total)
                if size_bytes is None:
                    cl = resp.headers.get("Content-Length")
                    if cl and cl.isdigit():
                        # Bu durumda sadece 1 byte olur; toplamı bilemeyiz
                        pass
        except HTTPError as e:
            if code is None:
                code = e.code
        except Exception:
            pass

    status_text = "OK" if code == 200 else (str(code) if code is not None else "ERR")
    size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes is not None else None
    return status_text, size_mb
