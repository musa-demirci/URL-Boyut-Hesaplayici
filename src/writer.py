# -*- coding: utf-8 -*-
"""
Çıktı işlemleri: XLSX oluşturucu ve URL parça/biçim yardımcıları.
Harici paket YOK (zip + basit XML).
"""

from datetime import datetime, timezone
import os
import posixpath
import zipfile
from xml.sax.saxutils import escape as xml_escape
from urllib.parse import urlparse, unquote
from typing import Optional, List, Tuple

# --- URL yardımcıları ---

def url_extension(url: str) -> str:
    try:
        p = urlparse(url)
        tail = posixpath.basename(p.path)
        _, ext = os.path.splitext(tail)
        return ext.lstrip(".").lower()
    except Exception:
        return ""

def url_filename_no_ext(url: str) -> str:
    """URL'den dosya adını (uzantısız) çıkarır; %xx kodlamalarını çözer."""
    try:
        p = urlparse(url)
        tail = posixpath.basename(p.path)
        tail = unquote(tail)
        name, _ = os.path.splitext(tail)
        return name
    except Exception:
        return ""

# --- XLSX oluşturucu ---

def excel_quote(s: str) -> str:
    if s is None:
        return ""
    return s.replace('"', '""')

def xml_sanitize(s: str) -> str:
    if s is None:
        return ""
    out = []
    for ch in s:
        oc = ord(ch)
        if oc in (0x09, 0x0A, 0x0D) or (0x20 <= oc <= 0xD7FF) or (0xE000 <= oc <= 0xFFFD):
            out.append(ch)
    return "".join(out)

def pixels_to_col_width(pixels: int) -> float:
    return round(max(0, (pixels - 5) / 7.0), 2)

class XlsxBuilder:
    """
    Minimal XLSX oluşturucu.
    - Stil: 0 normal, 1 başlık (bold), 2 hyperlink (mavi+altı çizili), 3 sayı 0.00
    - Sütunlar: A=Dosya URL'si, B=Dosya adı, C=Uzunluk, D=Uzantı, E=Boyut (MB), F=Durum
    """
    def __init__(self):
        self.rows: List[Tuple[str, str, int, str, Optional[float], str]] = []
        self._hyperlinks = []  # [(cell_ref, url)]

    def add_row(self, url: str, fname: str, fname_len: int, ext: str, size_mb: Optional[float], status: str):
        self.rows.append((url or "", fname or "", fname_len or 0, ext or "", size_mb, status or ""))

    def _sheet_xml(self):
        total_rows = len(self.rows) + 1
        dim_ref = f"A1:F{total_rows}"

        cw1 = pixels_to_col_width(900)
        cw2 = pixels_to_col_width(225)
        cw3 = pixels_to_col_width(75)
        cw4 = pixels_to_col_width(75)
        cw5 = pixels_to_col_width(100)
        cw6 = pixels_to_col_width(75)

        parts = []
        parts.append(
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        )
        parts.append(f'<dimension ref="{dim_ref}"/>')
        parts.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
        parts.append('<sheetFormatPr defaultRowHeight="15"/>')
        parts.append('<cols>'
                     f'<col min="1" max="1" width="{cw1}" customWidth="1"/>'
                     f'<col min="2" max="2" width="{cw2}" customWidth="1"/>'
                     f'<col min="3" max="3" width="{cw3}" customWidth="1"/>'
                     f'<col min="4" max="4" width="{cw4}" customWidth="1"/>'
                     f'<col min="5" max="5" width="{cw5}" customWidth="1"/>'
                     f'<col min="6" max="6" width="{cw6}" customWidth="1"/>'
                     '</cols>')
        parts.append("<sheetData>")

        headers = ["Dosya URL'si", "Dosya adı", "Uzunluk", "Uzantı", "Boyut (MB)", "Durum"]
        parts.append('<row r="1">')
        for i, text in enumerate(headers, start=1):
            col = "ABCDEF"[i - 1]
            safe = xml_escape(text)
            parts.append(
                f'<c r="{col}1" t="inlineStr" s="1">'
                f"<is><t>{safe}</t></is>"
                f"</c>"
            )
        parts.append("</row>")

        for idx, (url, fname, fname_len, ext, size_mb, status) in enumerate(self.rows, start=2):
            parts.append(f'<row r="{idx}">')

            raw_url = xml_sanitize(url or "")
            safe_display = xml_escape(raw_url)
            if raw_url and len(raw_url) <= 255:
                q = excel_quote(raw_url)
                formula = f'HYPERLINK("{q}")'
                safe_formula = xml_escape(formula)
                parts.append(f'<c r="A{idx}" s="2" t="str"><f>{safe_formula}</f><v>{safe_display}</v></c>')
            else:
                parts.append(f'<c r="A{idx}" t="inlineStr" s="2"><is><t>{safe_display}</t></is></c>')
                if raw_url:
                    self._hyperlinks.append((f"A{idx}", raw_url))

            safe_name = xml_escape(xml_sanitize(fname or ""))
            parts.append(f'<c r="B{idx}" t="inlineStr"><is><t>{safe_name}</t></is></c>')

            parts.append(f'<c r="C{idx}" s="0"><v>{fname_len}</v></c>')

            safe_ext = xml_escape(xml_sanitize(ext or ""))
            parts.append(f'<c r="D{idx}" t="inlineStr"><is><t>{safe_ext}</t></is></c>')

            if size_mb is None:
                parts.append(f'<c r="E{idx}" s="3"/>')
            else:
                parts.append(f'<c r="E{idx}" s="3"><v>{size_mb}</v></c>')

            safe_stat = xml_escape(xml_sanitize(status or ""))
            parts.append(f'<c r="F{idx}" t="inlineStr"><is><t>{safe_stat}</t></is></c>')

            parts.append("</row>")

        parts.append("</sheetData>")
        parts.append(f'<autoFilter ref="A1:F{total_rows}"/>')

        if self._hyperlinks:
            parts.append("<hyperlinks>")
            for i, (cell_ref, _url) in enumerate(self._hyperlinks, start=1):
                rid = f"rIdHL{i}"
                parts.append(f'<hyperlink ref="{cell_ref}" r:id="{rid}"/>')
            parts.append("</hyperlinks>")

        parts.append("</worksheet>")
        return "".join(parts)

    def _sheet_rels_xml(self):
        rels = ['<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i, (_ref, url) in enumerate(self._hyperlinks, start=1):
            rid = f"rIdHL{i}"
            tgt = xml_escape(xml_sanitize(url or ""))
            rels.append(
                f'<Relationship Id="{rid}" '
                f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
                f'Target="{tgt}" TargetMode="External"/>'
            )
        rels.append("</Relationships>")
        return "".join(rels)

    def _styles_xml(self):
        return (
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<numFmts count="1"><numFmt numFmtId="165" formatCode="0.00"/></numFmts>'
            '<fonts count="3">'
                '<font><sz val="11"/><name val="Calibri"/></font>'
                '<font><b/><sz val="11"/><name val="Calibri"/></font>'
                '<font><sz val="11"/><color rgb="FF0000FF"/><name val="Calibri"/><u/></font>'
            '</fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill>'
                '<fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="4">'
                '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
                '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
                '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
                '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
            '</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            '</styleSheet>'
        )

    def _workbook_xml(self):
        return (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="URL Boyut Hesaplayıcı" sheetId="1" r:id="rId1"/></sheets>'
            '<calcPr fullCalcOnLoad="1"/>'
            '</workbook>'
        )

    def _wb_rels_xml(self):
        return (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        )

    def _content_types_xml(self):
        return (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'
        )

    def _rels_root_xml(self):
        return (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

    def _docprops_app_xml(self):
        return (
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            '<Application>Python</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop>'
            '<HeadingPairs><vt:vector size="2" baseType="variant">'
            '<vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant>'
            '</vt:vector></HeadingPairs>'
            '<TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>URL Boyut Hesaplayıcı</vt:lpstr></vt:vector></TitlesOfParts>'
            '<Company/><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged>'
            '<AppVersion>16.0000</AppVersion>'
            '</Properties>'
        )

    def _docprops_core_xml(self):
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return (
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:title>URL Boyut Hesaplayıcı Sonuçları</dc:title>"
            "<dc:creator>URL Boyut Hesaplayıcı</dc:creator>"
            "<cp:lastModifiedBy>URL Boyut Hesaplayıcı</cp:lastModifiedBy>"
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            "</cp:coreProperties>"
        )

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", self._content_types_xml())
            z.writestr("_rels/.rels", self._rels_root_xml())
            z.writestr("docProps/app.xml", self._docprops_app_xml())
            z.writestr("docProps/core.xml", self._docprops_core_xml())
            z.writestr("xl/workbook.xml", self._workbook_xml())
            z.writestr("xl/_rels/workbook.xml.rels", self._wb_rels_xml())
            z.writestr("xl/styles.xml", self._styles_xml())
            z.writestr("xl/worksheets/sheet1.xml", self._sheet_xml())
            if self._hyperlinks:
                z.writestr("xl/worksheets/_rels/sheet1.xml.rels", self._sheet_rels_xml())
