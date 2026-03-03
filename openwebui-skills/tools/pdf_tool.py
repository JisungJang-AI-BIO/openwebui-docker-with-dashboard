"""
title: PDF Document Tool
author: Internal Team
author_url: https://github.com/anthropics/skills
description: Read, create, merge, split, watermark, OCR, and encrypt PDF documents.
    Use when user uploads a PDF file or requests PDF operations such as
    reading, creating, merging, splitting, OCR, watermarking, or encryption.
required_open_webui_version: 0.8.5
requirements: pypdf, pdfplumber, reportlab, pdf2image, pytesseract, Pillow
version: 1.0.0
licence: MIT
"""

import asyncio
import base64
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


# =============================================================================
# EventEmitter Helper
# =============================================================================
class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Any] = None, user: dict = None):
        self.event_emitter = event_emitter
        self.user = user or {}

    async def emit(self, description="Unknown State", status="in_progress", done=False):
        if self.event_emitter:
            await self.event_emitter(
                {"type": "status", "data": {"status": status, "description": description, "done": done}}
            )

    async def progress(self, description: str):
        await self.emit(description)

    async def success(self, description: str):
        await self.emit(description, "success", True)

    async def error(self, description: str):
        await self.emit(description, "error", True)

    async def send_file_link(self, file_path: str, filename: str, mime_type: str = None):
        """Upload file to OpenWebUI Files API and emit download link.
        Falls back to base64 data URI if the API is unavailable.
        """
        if not self.event_emitter or not os.path.exists(file_path):
            return
        if mime_type is None:
            ext = Path(filename).suffix.lower()
            mime_map = {
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".pdf": "application/pdf", ".html": "text/html", ".txt": "text/plain",
                ".csv": "text/csv", ".odt": "application/vnd.oasis.opendocument.text",
                ".rtf": "application/rtf", ".png": "image/png",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
            }
            mime_type = mime_map.get(ext, "application/octet-stream")

        is_image = mime_type.startswith("image/")
        url = await self._upload_to_openwebui(file_path, filename, mime_type)

        if url:
            if is_image:
                content = f"\n\n📎 **{filename}**\n\n![{filename}]({url})\n\n[Download {filename}]({url})\n"
            else:
                content = f"\n\n📎 **{filename}**\n\n[Download {filename}]({url})\n"
        else:
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            data_uri = f"data:{mime_type};base64,{b64}"
            if is_image:
                content = f"\n\n📎 **{filename}**\n\n![{filename}]({data_uri})\n\n[Download {filename}]({data_uri})\n"
            else:
                content = f"\n\n📎 **{filename}**\n\n[Download {filename}]({data_uri})\n"

        await self.event_emitter({"type": "message", "data": {"content": content}})

    async def _upload_to_openwebui(self, file_path: str, filename: str, mime_type: str) -> Optional[str]:
        """Upload file via OpenWebUI's internal Files API. Returns download URL or None."""
        try:
            import httpx
            import jwt

            user_id = self.user.get("id", "")
            secret = os.environ.get("WEBUI_SECRET_KEY", "")
            if not user_id or not secret:
                return None

            token = jwt.encode({"id": user_id}, secret, algorithm="HS256")
            if isinstance(token, bytes):
                token = token.decode("utf-8")

            port = os.environ.get("PORT", "8080")
            with open(file_path, "rb") as f:
                resp = httpx.post(
                    f"http://localhost:{port}/api/v1/files/",
                    files={"file": (filename, f, mime_type)},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0,
                )

            if resp.status_code in (200, 201):
                file_id = resp.json().get("id")
                if file_id:
                    return f"/api/v1/files/{file_id}/content"
            return None
        except Exception:
            return None


# =============================================================================
# Main Tool Class
# =============================================================================
class Tools:
    class Valves(BaseModel):
        TEMP_DIR: str = Field(default="/tmp/openwebui-pdf", description="Temporary file storage path")
        MAX_FILE_SIZE_MB: int = Field(default=50, description="Maximum file size in MB")
        LIBREOFFICE_PATH: str = Field(default="soffice", description="LibreOffice binary path")
        TESSERACT_PATH: str = Field(default="tesseract", description="Tesseract binary path")
        TESSERACT_LANG: str = Field(default="eng+kor", description="Tesseract OCR languages (e.g. eng, kor, eng+kor)")
        POPPLER_PATH: str = Field(default="", description="Poppler utils path (leave empty for system default)")

    def __init__(self):
        self.valves = self.Valves()
        self.citation = False

    # =========================================================================
    # Tool Methods
    # =========================================================================

    async def read_pdf(
        self,
        mode: str = "text",
        pages: str = "",
        __files__: list = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Read and extract content from an uploaded PDF file.

        Modes:
        - "text": Extract all text content
        - "tables": Extract tables as markdown
        - "metadata": Show document metadata and structure info
        - "structured": Combined text with page numbers and structure

        :param mode: Extraction mode - "text", "tables", "metadata", or "structured"
        :param pages: Page range to extract (e.g. "1-3,5,8-10"). Empty = all pages.
        :return: Extracted content
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Reading PDF...")

        if not __files__:
            await emitter.error("No file uploaded")
            return "Error: No file uploaded. Please upload a PDF file."

        file_path = self._resolve_pdf_file(__files__)
        if not file_path:
            await emitter.error("No PDF file found")
            return "Error: No .pdf file found in uploaded files."

        try:
            page_set = self._parse_page_range(pages) if pages else None

            if mode == "metadata":
                result = self._read_metadata(file_path)
            elif mode == "tables":
                result = self._read_tables(file_path, page_set)
            elif mode == "structured":
                result = self._read_structured(file_path, page_set)
            else:
                result = self._read_text(file_path, page_set)

            await emitter.success(f"Read {Path(file_path).name}")
            return result

        except Exception as e:
            await emitter.error(f"Read error: {str(e)}")
            return f"Error reading PDF: {str(e)}"

    async def create_pdf(
        self,
        content: str,
        filename: str = "document.pdf",
        page_size: str = "A4",
        orientation: str = "portrait",
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Create a new PDF document using ReportLab.

        Content format (Markdown-like):
        - '# ' → Title (large, bold)
        - '## ' → Section heading
        - '### ' → Subsection heading
        - '- ' → Bullet list item
        - '1. ' → Numbered list item
        - '| col1 | col2 |' → Table (first row = header)
        - '---' → Page break
        - Other lines → Normal paragraphs

        IMPORTANT: Never use Unicode subscript/superscript characters in content.
        Use <sub>text</sub> or <super>text</super> markup instead.

        :param content: Document content in Markdown-like format
        :param filename: Output filename (default: document.pdf)
        :param page_size: "A4", "Letter", or "Legal"
        :param orientation: "portrait" or "landscape"
        :return: Status message with download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Creating PDF...")

        try:
            temp_dir = self._ensure_temp_dir()
            output_path = os.path.join(temp_dir, filename)

            self._create_with_reportlab(content, output_path, page_size, orientation)

            await emitter.send_file_link(output_path, filename)
            await emitter.success(f"Created {filename}")

            file_size = os.path.getsize(output_path)
            return f"Created '{filename}' ({file_size:,} bytes). Page: {page_size} {orientation}. Download link above."

        except Exception as e:
            await emitter.error(f"Creation error: {str(e)}")
            return f"Error creating PDF: {str(e)}"

    async def merge_pdfs(
        self,
        output_filename: str = "merged.pdf",
        __files__: list = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Merge multiple uploaded PDF files into one.
        Upload all PDFs to merge, then call this method.

        :param output_filename: Output filename for the merged PDF
        :return: Status message with download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Merging PDFs...")

        if not __files__:
            await emitter.error("No files uploaded")
            return "Error: No files uploaded. Upload multiple PDFs to merge."

        try:
            from pypdf import PdfMerger

            pdf_files = self._resolve_all_pdf_files(__files__)
            if len(pdf_files) < 2:
                return "Error: Need at least 2 PDF files to merge."

            merger = PdfMerger()
            for fp in pdf_files:
                merger.append(fp)

            temp_dir = self._ensure_temp_dir()
            output_path = os.path.join(temp_dir, output_filename)
            merger.write(output_path)
            merger.close()

            await emitter.send_file_link(output_path, output_filename)
            await emitter.success(f"Merged {len(pdf_files)} PDFs")

            file_size = os.path.getsize(output_path)
            return f"Merged {len(pdf_files)} PDFs into '{output_filename}' ({file_size:,} bytes)."

        except Exception as e:
            await emitter.error(f"Merge error: {str(e)}")
            return f"Error merging PDFs: {str(e)}"

    async def split_pdf(
        self,
        pages: str,
        output_filename: str = "",
        __files__: list = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Extract specific pages from a PDF.

        :param pages: Page range (e.g. "1-3", "1,3,5", "2-5,8,10-12"). 1-indexed.
        :param output_filename: Output filename (auto-generated if empty)
        :return: Status message with download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Splitting PDF...")

        if not __files__:
            await emitter.error("No file uploaded")
            return "Error: No file uploaded."

        file_path = self._resolve_pdf_file(__files__)
        if not file_path:
            return "Error: No PDF file found."

        try:
            from pypdf import PdfReader, PdfWriter

            reader = PdfReader(file_path)
            page_set = self._parse_page_range(pages)
            if not page_set:
                return f"Error: Invalid page range '{pages}'."

            writer = PdfWriter()
            for p in sorted(page_set):
                idx = p - 1  # 1-indexed to 0-indexed
                if 0 <= idx < len(reader.pages):
                    writer.add_page(reader.pages[idx])

            if len(writer.pages) == 0:
                return f"Error: No valid pages in range '{pages}'. PDF has {len(reader.pages)} pages."

            if not output_filename:
                output_filename = f"{Path(file_path).stem}_pages_{pages.replace(',', '_')}.pdf"

            temp_dir = self._ensure_temp_dir()
            output_path = os.path.join(temp_dir, output_filename)
            with open(output_path, "wb") as f:
                writer.write(f)

            await emitter.send_file_link(output_path, output_filename)
            await emitter.success(f"Extracted {len(writer.pages)} pages")
            return f"Extracted {len(writer.pages)} pages into '{output_filename}'."

        except Exception as e:
            await emitter.error(f"Split error: {str(e)}")
            return f"Error: {str(e)}"

    async def convert_pdf(
        self,
        target_format: str = "txt",
        __files__: list = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Convert an uploaded PDF to another format.
        Supported: txt, html, docx, png, jpg.
        - txt: pdftotext extraction
        - html/docx: LibreOffice conversion
        - png/jpg: pdf2image conversion (first page or all)

        :param target_format: Target format - "txt", "html", "docx", "png", "jpg"
        :return: Converted content or download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress(f"Converting PDF to {target_format}...")

        if not __files__:
            await emitter.error("No file uploaded")
            return "Error: No file uploaded."

        file_path = self._resolve_pdf_file(__files__)
        if not file_path:
            return "Error: No PDF file found."

        try:
            temp_dir = self._ensure_temp_dir()
            fmt = target_format.lower().strip(".")

            if fmt == "txt":
                return await self._convert_pdftotext(file_path, temp_dir, emitter)
            elif fmt in ("html", "docx"):
                return await self._convert_libreoffice(file_path, temp_dir, fmt, emitter)
            elif fmt in ("png", "jpg", "jpeg"):
                return await self._convert_to_images(file_path, temp_dir, fmt, emitter)
            else:
                return f"Error: Unsupported format '{fmt}'. Supported: txt, html, docx, png, jpg"

        except Exception as e:
            await emitter.error(f"Conversion error: {str(e)}")
            return f"Error: {str(e)}"

    async def ocr_pdf(
        self,
        language: str = "",
        pages: str = "",
        __files__: list = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Perform OCR on a scanned/image-based PDF using Tesseract.

        :param language: OCR language (default from Valve: eng+kor). Examples: "eng", "kor", "eng+kor+jpn"
        :param pages: Page range (e.g. "1-3"). Empty = all pages.
        :return: Extracted text
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Running OCR...")

        if not __files__:
            await emitter.error("No file uploaded")
            return "Error: No file uploaded."

        file_path = self._resolve_pdf_file(__files__)
        if not file_path:
            return "Error: No PDF file found."

        try:
            from pdf2image import convert_from_path
            import pytesseract

            lang = language or self.valves.TESSERACT_LANG
            page_set = self._parse_page_range(pages) if pages else None

            poppler_path = self.valves.POPPLER_PATH or None
            kwargs = {"pdf_path": file_path, "dpi": 300}
            if poppler_path:
                kwargs["poppler_path"] = poppler_path

            if page_set:
                first_page = min(page_set)
                last_page = max(page_set)
                kwargs["first_page"] = first_page
                kwargs["last_page"] = last_page

            await emitter.progress("Converting PDF pages to images...")
            images = convert_from_path(**kwargs)

            results = []
            for i, img in enumerate(images):
                page_num = (kwargs.get("first_page", 1)) + i
                if page_set and page_num not in page_set:
                    continue
                await emitter.progress(f"OCR page {page_num}...")
                text = pytesseract.image_to_string(img, lang=lang)
                results.append(f"--- Page {page_num} ---\n{text.strip()}")

            await emitter.success(f"OCR complete ({len(results)} pages)")
            return "\n\n".join(results) if results else "No text found via OCR."

        except Exception as e:
            await emitter.error(f"OCR error: {str(e)}")
            return f"Error: {str(e)}"

    async def protect_pdf(
        self,
        user_password: str = "",
        owner_password: str = "",
        __files__: list = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Add password protection (encryption) to a PDF.

        :param user_password: Password required to open the PDF. Leave empty for no open password.
        :param owner_password: Owner password for full permissions. Defaults to user_password if empty.
        :return: Protected PDF download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Encrypting PDF...")

        if not __files__:
            await emitter.error("No file uploaded")
            return "Error: No file uploaded."

        file_path = self._resolve_pdf_file(__files__)
        if not file_path:
            return "Error: No PDF file found."

        if not user_password and not owner_password:
            return "Error: Provide at least one password (user_password or owner_password)."

        try:
            from pypdf import PdfReader, PdfWriter

            reader = PdfReader(file_path)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            owner = owner_password or user_password
            writer.encrypt(user_password=user_password, owner_password=owner)

            temp_dir = self._ensure_temp_dir()
            output_filename = f"{Path(file_path).stem}_protected.pdf"
            output_path = os.path.join(temp_dir, output_filename)
            with open(output_path, "wb") as f:
                writer.write(f)

            await emitter.send_file_link(output_path, output_filename)
            await emitter.success("PDF encrypted")
            return f"Encrypted '{output_filename}' ({os.path.getsize(output_path):,} bytes)."

        except Exception as e:
            await emitter.error(f"Encryption error: {str(e)}")
            return f"Error: {str(e)}"

    async def add_watermark(
        self,
        text: str = "CONFIDENTIAL",
        opacity: float = 0.15,
        __files__: list = None,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Add a diagonal text watermark to every page of a PDF.

        :param text: Watermark text (e.g. "CONFIDENTIAL", "DRAFT")
        :param opacity: Watermark opacity from 0.0 (invisible) to 1.0 (fully opaque). Default 0.15.
        :return: Watermarked PDF download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Adding watermark...")

        if not __files__:
            await emitter.error("No file uploaded")
            return "Error: No file uploaded."

        file_path = self._resolve_pdf_file(__files__)
        if not file_path:
            return "Error: No PDF file found."

        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.colors import Color

            reader = PdfReader(file_path)
            first_page = reader.pages[0]
            page_w = float(first_page.mediabox.width)
            page_h = float(first_page.mediabox.height)

            # Create watermark PDF
            wm_buf = io.BytesIO()
            c = rl_canvas.Canvas(wm_buf, pagesize=(page_w, page_h))
            c.setFillColor(Color(0.5, 0.5, 0.5, alpha=opacity))
            c.setFont("Helvetica-Bold", 60)
            c.translate(page_w / 2, page_h / 2)
            c.rotate(45)
            c.drawCentredString(0, 0, text)
            c.save()
            wm_buf.seek(0)

            wm_reader = PdfReader(wm_buf)
            wm_page = wm_reader.pages[0]

            writer = PdfWriter()
            for page in reader.pages:
                page.merge_page(wm_page)
                writer.add_page(page)

            temp_dir = self._ensure_temp_dir()
            output_filename = f"{Path(file_path).stem}_watermarked.pdf"
            output_path = os.path.join(temp_dir, output_filename)
            with open(output_path, "wb") as f:
                writer.write(f)

            await emitter.send_file_link(output_path, output_filename)
            await emitter.success("Watermark added")
            return f"Added watermark '{text}' to {len(reader.pages)} pages."

        except Exception as e:
            await emitter.error(f"Watermark error: {str(e)}")
            return f"Error: {str(e)}"

    # =========================================================================
    # Internal: File Resolution
    # =========================================================================

    def _resolve_pdf_file(self, files: list) -> Optional[str]:
        if not files:
            return None
        for f in files:
            info = f if isinstance(f, dict) else {"path": f}
            name = info.get("filename", info.get("name", str(info.get("path", ""))))
            if not name.lower().endswith(".pdf"):
                continue
            for key in ("path", "file_path", "url", "id"):
                path = info.get(key)
                if path and isinstance(path, str):
                    for c in [path, f"/app/backend/data/uploads/{path}", f"/app/backend/data/cache/{path}"]:
                        if os.path.exists(c):
                            return c
                    return path
        # Fallback: first file
        if files:
            f = files[0]
            if isinstance(f, dict):
                for key in ("path", "file_path"):
                    if key in f:
                        return f[key]
            elif isinstance(f, str):
                return f
        return None

    def _resolve_all_pdf_files(self, files: list) -> list:
        result = []
        for f in files:
            info = f if isinstance(f, dict) else {"path": f}
            name = info.get("filename", info.get("name", str(info.get("path", ""))))
            if not name.lower().endswith(".pdf"):
                continue
            for key in ("path", "file_path"):
                path = info.get(key)
                if path and isinstance(path, str):
                    for c in [path, f"/app/backend/data/uploads/{path}", f"/app/backend/data/cache/{path}"]:
                        if os.path.exists(c):
                            result.append(c)
                            break
                    else:
                        result.append(path)
                    break
        return result

    def _ensure_temp_dir(self) -> str:
        os.makedirs(self.valves.TEMP_DIR, exist_ok=True)
        return self.valves.TEMP_DIR

    def _parse_page_range(self, pages_str: str) -> set:
        result = set()
        for part in pages_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    result.update(range(int(start), int(end) + 1))
                except ValueError:
                    pass
            elif part.isdigit():
                result.add(int(part))
        return result

    # =========================================================================
    # Internal: Reading
    # =========================================================================

    def _read_text(self, file_path: str, page_set: set = None) -> str:
        import pdfplumber

        parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                if page_set and page_num not in page_set:
                    continue
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(f"--- Page {page_num} ---\n{text}")

        if not parts:
            return "No text content found. The PDF may be image-based — try `ocr_pdf()` instead."
        return "\n\n".join(parts)

    def _read_tables(self, file_path: str, page_set: set = None) -> str:
        import pdfplumber

        parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                if page_set and page_num not in page_set:
                    continue
                tables = page.extract_tables()
                for t_idx, table in enumerate(tables):
                    if not table:
                        continue
                    parts.append(f"### Page {page_num}, Table {t_idx + 1}")
                    for r_idx, row in enumerate(table):
                        cells = [str(c or "").strip() for c in row]
                        parts.append("| " + " | ".join(cells) + " |")
                        if r_idx == 0:
                            parts.append("| " + " | ".join(["---"] * len(cells)) + " |")
                    parts.append("")

        if not parts:
            return "No tables found in the PDF."
        return "\n".join(parts)

    def _read_metadata(self, file_path: str) -> str:
        from pypdf import PdfReader

        reader = PdfReader(file_path)
        meta = reader.metadata
        parts = ["## PDF Metadata\n"]

        if meta:
            for key in ["/Title", "/Author", "/Subject", "/Creator", "/Producer", "/CreationDate", "/ModDate"]:
                val = meta.get(key)
                if val:
                    parts.append(f"- **{key[1:]}**: {val}")

        parts.append(f"\n**Pages**: {len(reader.pages)}")
        if reader.pages:
            p = reader.pages[0]
            w, h = float(p.mediabox.width), float(p.mediabox.height)
            parts.append(f"**Page size**: {w:.0f} x {h:.0f} pts ({w/72:.1f}\" x {h/72:.1f}\")")

        parts.append(f"**Encrypted**: {reader.is_encrypted}")
        return "\n".join(parts)

    def _read_structured(self, file_path: str, page_set: set = None) -> str:
        from pypdf import PdfReader
        import pdfplumber

        reader = PdfReader(file_path)
        parts = [f"## PDF Structure\n\n**Pages**: {len(reader.pages)}\n"]

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                if page_set and page_num not in page_set:
                    continue
                text = page.extract_text() or ""
                tables = page.extract_tables()
                w, h = page.width, page.height
                parts.append(f"### Page {page_num} ({w:.0f}x{h:.0f})")
                parts.append(f"Tables: {len(tables)}, Chars: {len(text)}")
                if text.strip():
                    preview = text[:500]
                    parts.append(f"```\n{preview}\n```")
                parts.append("")

        return "\n".join(parts)

    # =========================================================================
    # Internal: Creating
    # =========================================================================

    def _create_with_reportlab(self, content: str, output_path: str, page_size: str, orientation: str):
        from reportlab.lib.pagesizes import A4, LETTER, LEGAL, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors

        sizes = {"A4": A4, "Letter": LETTER, "Legal": LEGAL}
        ps = sizes.get(page_size, A4)
        if orientation.lower() == "landscape":
            ps = landscape(ps)

        doc = SimpleDocTemplate(output_path, pagesize=ps, leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch)
        styles = getSampleStyleSheet()

        story = []
        table_buf = []

        for line in content.split("\n"):
            s = line.strip()

            # Table accumulation
            if s.startswith("|") and s.endswith("|"):
                inner = s[1:-1].strip()
                if all(c in "-| :" for c in inner):
                    continue
                table_buf.append(s)
                continue
            elif table_buf:
                story.append(self._build_table(table_buf, styles))
                table_buf = []

            if s == "---":
                story.append(PageBreak())
            elif not s:
                story.append(Spacer(1, 6))
            elif s.startswith("### "):
                story.append(Paragraph(s[4:], styles["Heading3"]))
            elif s.startswith("## "):
                story.append(Paragraph(s[3:], styles["Heading2"]))
            elif s.startswith("# "):
                story.append(Paragraph(s[2:], styles["Heading1"]))
            elif s.startswith("- ") or s.startswith("* "):
                story.append(Paragraph(f"• {s[2:]}", styles["BodyText"]))
            elif len(s) > 2 and s[0].isdigit() and (s[1] == "." or (s[1].isdigit() and s[2] == ".")):
                story.append(Paragraph(s, styles["BodyText"]))
            else:
                story.append(Paragraph(s, styles["BodyText"]))

        if table_buf:
            story.append(self._build_table(table_buf, styles))

        doc.build(story)

    def _build_table(self, buf: list, styles):
        from reportlab.platypus import Table, TableStyle, Paragraph
        from reportlab.lib import colors

        rows_data = [[c.strip() for c in row.strip("|").split("|")] for row in buf]
        if not rows_data:
            return Paragraph("", styles["BodyText"])

        table_data = []
        for row in rows_data:
            table_data.append([Paragraph(cell, styles["BodyText"]) for cell in row])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.85, 0.85, 0.85)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # =========================================================================
    # Internal: Conversion
    # =========================================================================

    async def _convert_pdftotext(self, file_path, temp_dir, emitter) -> str:
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", file_path, "-"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                await emitter.success("Converted to text")
                text = result.stdout
                if len(text) > 20000:
                    return text[:20000] + "\n\n... (truncated at 20000 chars)"
                return text
            return f"Error: pdftotext failed. {result.stderr}"
        except FileNotFoundError:
            # Fallback to pdfplumber
            return self._read_text(file_path)

    async def _convert_libreoffice(self, file_path, temp_dir, fmt, emitter) -> str:
        soffice = self.valves.LIBREOFFICE_PATH
        input_copy = os.path.join(temp_dir, Path(file_path).name)
        shutil.copy2(file_path, input_copy)
        env = os.environ.copy()
        env["SAL_USE_VCLPLUGIN"] = "svp"
        try:
            result = subprocess.run(
                [soffice, "--headless", "--convert-to", fmt, "--outdir", temp_dir, input_copy],
                capture_output=True, text=True, timeout=120, env=env,
            )
        except FileNotFoundError:
            return f"Error: LibreOffice not found at '{soffice}'."
        except subprocess.TimeoutExpired:
            return "Error: Conversion timed out."

        output_path = os.path.join(temp_dir, f"{Path(file_path).stem}.{fmt}")
        if os.path.exists(output_path):
            await emitter.send_file_link(output_path, Path(output_path).name)
            await emitter.success(f"Converted to {fmt}")
            return f"Converted to {fmt} ({os.path.getsize(output_path):,} bytes)."
        return f"Error: Conversion failed. {result.stderr}"

    async def _convert_to_images(self, file_path, temp_dir, fmt, emitter) -> str:
        from pdf2image import convert_from_path

        poppler_path = self.valves.POPPLER_PATH or None
        kwargs = {"pdf_path": file_path, "dpi": 150, "fmt": fmt.replace("jpg", "jpeg")}
        if poppler_path:
            kwargs["poppler_path"] = poppler_path

        images = convert_from_path(**kwargs)
        saved = []
        for i, img in enumerate(images):
            fname = f"{Path(file_path).stem}_page{i+1}.{fmt}"
            fpath = os.path.join(temp_dir, fname)
            img.save(fpath)
            saved.append((fpath, fname))

        for fpath, fname in saved:
            await emitter.send_file_link(fpath, fname)

        await emitter.success(f"Converted {len(saved)} pages to {fmt}")
        return f"Converted {len(saved)} pages to {fmt} images."
