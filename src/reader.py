# -*- coding: utf-8 -*-
"""
Girdi işlemleri: Excel (.xlsx) ve WordPress WXR (.xml) okuma ve URL çıkarımı.
Tüm kullanıcıya görünen hata metinleri de burada raise edilen mesajlar içinde.
Harici paket KULLANILMAZ (zipfile + xml.etree kullanılır).
"""

import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict

# XML Namespace'ler
NS: Dict[str, str] = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

def _ext_of(path: str) -> str:
    return os.path.splitext((path or "").lower())[1]

def is_excel(path: str) -> bool:
    return _ext_of(path) == ".xlsx"

def is_xml(path: str) -> bool:
    return _ext_of(path) == ".xml"

def letters_to_index(col_letters: str) -> int:
    v = 0
    for ch in col_letters:
        if "A" <= ch <= "Z":
            v = v * 26 + (ord(ch) - ord("A") + 1)
    return v

def read_urls_from_xlsx(xlsx_path: str, header_name: str) -> List[str]:
    """
    İlk sayfadaki header satırında `header_name` başlığını bulur; altındaki URL'leri listeler.
    """
    with zipfile.ZipFile(xlsx_path, "r") as z:
        wb_xml = ET.fromstring(z.read("xl/workbook.xml"))
        sheet = wb_xml.find("a:sheets/a:sheet", NS)
        if sheet is None:
            raise RuntimeError("Çalışma sayfası bulunamadı.")
        rid = sheet.attrib.get("{%s}id" % NS["r"])

        wb_rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = None
        for rel in wb_rels.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
            if rel.attrib.get("Id") == rid:
                target = rel.attrib.get("Target")
                break
        if not target:
            raise RuntimeError("Sayfa ilişkisi bulunamadı.")
        sheet_path = "xl/" + target if not target.startswith("xl/") else target
        sheet_xml = ET.fromstring(z.read(sheet_path))

        # sharedStrings (varsa)
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sst.findall("a:si", NS):
                texts = []
                for t in si.findall(".//a:t", NS):
                    texts.append(t.text or "")
                shared.append("".join(texts))

        sheetData = sheet_xml.find("a:sheetData", NS)
        if sheetData is None:
            return []
        rows = sheetData.findall("a:row", NS)
        if not rows:
            return []
        header_row = rows[0]

        def cell_text(cell):
            t = cell.attrib.get("t")
            if t == "s":  # shared string
                v = cell.find("a:v", NS)
                if v is not None and v.text and v.text.isdigit():
                    idx = int(v.text)
                    return shared[idx] if 0 <= idx < len(shared) else ""
                return ""
            elif t == "inlineStr":
                tnode = cell.find("a:is/a:t", NS)
                return (tnode.text if tnode is not None else "")
            else:
                v = cell.find("a:v", NS)
                return v.text if v is not None else ""

        # başlığı bul
        header_idx = None
        for c in header_row.findall("a:c", NS):
            r = c.attrib.get("r", "A1")
            letters = "".join(ch for ch in r if ch.isalpha())
            idx = letters_to_index(letters)
            txt = (cell_text(c) or "").strip()
            if txt.lower() == (header_name or "").strip().lower():
                header_idx = idx
                break
        if header_idx is None:
            raise RuntimeError(f"'{header_name}' başlıklı sütun bulunamadı.")

        # veri satırları
        urls: List[str] = []
        for row in rows[1:]:
            target_cell = None
            for c in row.findall("a:c", NS):
                r = c.attrib.get("r", "")
                letters = "".join(ch for ch in r if ch.isalpha())
                if letters_to_index(letters) == header_idx:
                    target_cell = c
                    break
            if target_cell is None:
                urls.append("")
                continue
            u = (cell_text(target_cell) or "").strip()
            urls.append(u)
        return [u for u in urls if u]

def read_urls_from_wxr(path: str) -> List[str]:
    """
    WordPress WXR (XML) dosyasından medya (attachment_url) ve içerik içindeki mutlak URL'leri çıkarır.
    Sadece https? ile başlayan URL’leri döndürür.
    """
    urls: List[str] = []

    def add(u: str):
        if not u:
            return
        u = u.strip()
        if u.lower().startswith(("http://", "https://")):
            urls.append(u)

    if not is_xml(path):
        raise RuntimeError("XML modu yalnızca .xml dosyası kabul eder.")

    with open(path, "rb") as f:
        data = f.read()

    try:
        for _event, elem in ET.iterparse(io.BytesIO(data), events=("end",)):
            tag = elem.tag
            if tag.endswith("item"):
                post_type = None
                att_url = None
                content_text = None
                for child in elem:
                    ttag = child.tag
                    if ttag.endswith("post_type"):
                        post_type = (child.text or "").strip()
                    elif ttag.endswith("attachment_url"):
                        att_url = (child.text or "").strip()
                    elif ttag.endswith("encoded"):
                        content_text = child.text or ""
                if post_type == "attachment" and att_url:
                    add(att_url)
                if content_text:
                    for m in re.finditer(r'(?:href|src)=[\'\"]([^\'\"]+)', content_text, re.IGNORECASE):
                        add(m.group(1))
                elem.clear()
    except ET.ParseError as e:
        raise RuntimeError(f"XML parse hatası: {e}") from e

    # Tekilleştir (sıra korunur)
    seen = set()
    uniq = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq
