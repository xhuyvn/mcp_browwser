"""
PDF to Markdown Converter
=========================
Converts PDF files to clean Markdown using:
- PyMuPDF for text extraction and table detection
- LLM (via OpenAI-compatible API) for formatting text and reading scanned pages
- Optional watermark detection and removal
- Post-processing to clean artifacts

Supports 3 page types automatically:
1. Text pages with tables â†’ extracted locally (no LLM needed)
2. Text pages without tables â†’ sent to LLM for Markdown formatting
3. Scanned/image pages â†’ sent to LLM vision for OCR + formatting
"""

import fitz
import asyncio
import os
import sys
import re
import base64
from openai import AsyncOpenAI
from pathlib import Path

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIGURATION
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

BASE_URL = os.getenv("VLLM_BASE_URL", "http://192.168.58.137:3080/v1")
API_KEY = os.getenv("VLLM_API_KEY", "a8ac2daddce33ae9fc512c900d1eb173a6cead1cbe5848f45200f7c2fbccb588")
MODEL_NAME = os.getenv("VLLM_MODEL", "qwen36A3")


client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)

SYSTEM_PROMPT = """You are a document conversion expert.
Convert the following content into clean Markdown (.md) format.
Rules:
- Use #/##/### for headings.
- Markdown tables provided are already formatted â€” preserve them exactly.
- Do not add explanations, only return Markdown.
- Do not wrap output in code blocks."""

VISION_PROMPT = """Extract all PRINTED text from this document image and convert to clean Markdown.
- Ignore handwritten text, signatures, stamps, watermarks, annotations.
- Use Markdown table syntax for tabular data.
- Use #/##/### for headings.
- IMPORTANT: Return ONLY raw Markdown text. Do NOT use code fences. Do NOT write ```markdown."""

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# WATERMARK DETECTION & CLEANING
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def detect_watermark(pdf_path: str) -> str | None:
    """Send a sample page to LLM to identify watermark text patterns."""
    with fitz.open(pdf_path) as doc:
        sample = ""
        for i in range(min(2, len(doc))):
            sample += doc[i].get_text("text").strip() + "\n\n"

    if not sample.strip():
        return None

    sample = sample[:3000]

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a text analysis expert."},
                {"role": "user", "content": f"""Analyze this text extracted from a PDF document.
Identify any WATERMARK text â€” repeated patterns that appear multiple times and are NOT part of the actual document content.

Watermarks are typically:
- Email addresses with timestamps repeated many times
- Company names repeated diagonally
- "CONFIDENTIAL", "DRAFT", "COPY" etc.
- Any text pattern that repeats 3+ times and is clearly not document content

Text sample:
---
{sample}
---

If you find watermark pattern(s), respond with ONLY the core repeating text, one per line.
Keep it short â€” just the unique part that repeats.
If NO watermark found, respond with exactly: NONE"""},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        result = response.choices[0].message.content.strip()

        if not result or result.upper() == "NONE":
            return None

        print(f"  ðŸ” Detected watermark pattern(s):\n     {result}")
        return result

    except Exception as e:
        print(f"  [warn] Watermark detection failed: {e}")
        return None


def build_watermark_cleaner(patterns: str):
    """Build a cleaning function from LLM-detected watermark patterns."""
    pattern_lines = [p.strip() for p in patterns.split("\n") if p.strip()]

    def clean_watermark(text: str) -> str:
        lines = text.split("\n")
        cleaned = []

        for line in lines:
            original = line.strip()
            if not original:
                cleaned.append("")
                continue

            line_clean = original

            for pattern in pattern_lines:
                escaped = re.escape(pattern)

                # Match pattern with optional surrounding chars
                line_clean = re.sub(
                    r'[\w._-]*' + escaped + r'[\w._-]*',
                    '', line_clean, flags=re.IGNORECASE
                )

                # Match with timestamps attached
                line_clean = re.sub(
                    r'[\w._-]*' + escaped + r'[_\s]*\d{2}:\d{2}:\d{2}\s*\d{2}/\d{2}/\d{4}[\w@._]*',
                    '', line_clean, flags=re.IGNORECASE
                )

            # Standalone timestamp fragments
            line_clean = re.sub(
                r'^\s*[_\s]*\d{2}:\d{2}:\d{2}\s*\d{2}/\d{2}/\d{4}[\w@._]*\s*$',
                '', line_clean
            )

            line_clean = line_clean.strip()

            if not line_clean and original:
                continue

            if line_clean and len(re.sub(r'[^a-zA-Z0-9Ã€-á»¹]', '', line_clean)) < 2:
                continue

            cleaned.append(line_clean)

        result = re.sub(r'\n{3,}', '\n\n', "\n".join(cleaned))
        return result.strip()

    return clean_watermark


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# TABLE EXTRACTION
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def table_to_markdown(table, clean_fn=None) -> str:
    """Convert a PyMuPDF table object to a Markdown table string."""
    try:
        data = table.extract()
        if not data or len(data) < 1:
            return ""

        clean = []
        for row in data:
            cells = []
            for cell in row:
                val = str(cell).strip() if cell else ""
                if val and clean_fn:
                    val = clean_fn(val)
                cells.append(val)
            clean.append(cells)

        header = clean[0]
        col_count = len(header)
        lines = ["| " + " | ".join(header) + " |"]

        # Detect numeric columns for right-alignment
        separators = []
        for col in range(col_count):
            nums = sum(
                1 for row in clean[1:]
                if col < len(row) and row[col]
                and row[col].replace(",", "").replace(".", "").replace("-", "").replace(" ", "").isdigit()
            )
            total = sum(1 for row in clean[1:] if col < len(row) and row[col])
            separators.append("---:" if total > 0 and nums / total > 0.5 else "---")

        lines.append("| " + " | ".join(separators) + " |")

        for row in clean[1:]:
            padded = row[:col_count] + [""] * max(0, col_count - len(row))
            lines.append("| " + " | ".join(padded) + " |")

        return "\n".join(lines)
    except Exception as e:
        print(f"  [warn] Table extraction error: {e}")
        return ""


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# IMAGE CLEANING (for vision path)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def clean_page_image(page, zoom: float = 1.5) -> str:
    """Render page, remove colored ink (signatures/stamps), return base64."""
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    try:
        import numpy as np
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        arr = np.array(img)

        # Remove blue ink (signatures, stamps)
        blue_mask = (arr[:, :, 2] > 120) & (arr[:, :, 0] < 150) & (arr[:, :, 1] < 150)
        # Remove red/pink ink
        red_mask = (arr[:, :, 0] > 150) & (arr[:, :, 1] < 100) & (arr[:, :, 2] < 100)
        # Remove green ink
        green_mask = (arr[:, :, 1] > 150) & (arr[:, :, 0] < 100) & (arr[:, :, 2] < 100)

        arr[blue_mask | red_mask | green_mask] = [255, 255, 255]

        clean_img = Image.fromarray(arr)
        buffer = io.BytesIO()
        clean_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    except ImportError:
        # numpy/PIL not available, return raw image
        return base64.b64encode(pix.tobytes("png")).decode("utf-8")


def page_to_base64(page, zoom: float = 1.5) -> str:
    """Render a PDF page to a base64-encoded PNG string."""
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return base64.b64encode(pix.tobytes("png")).decode("utf-8")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PER-PAGE EXTRACTION (auto-detect strategy)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def extract_page(page, page_num: int, clean_fn=None) -> dict:
    """
    Auto-detect page type:
    - image-only â†’ return cleaned image for LLM vision
    - has tables  â†’ extract tables locally + remaining text
    - text-only   â†’ return text for LLM formatting
    """
    native_text = page.get_text("text").strip()

    if native_text and clean_fn:
        native_text = clean_fn(native_text)

    # Case 1: Scanned / image-only page
    if not native_text:
        print(f"\n  [page {page_num}] image-only â†’ LLM vision")
        return {
            "page_num": page_num,
            "strategy": "vision",
            "image_b64": clean_page_image(page),
            "content": None,
        }

    # Check for tables
    tables_md = []
    table_rects = []
    try:
        finder = page.find_tables()
        for table in finder.tables:
            md = table_to_markdown(table, clean_fn)
            if md:
                tables_md.append({"md": md, "y_pos": table.bbox[1]})
                table_rects.append(fitz.Rect(table.bbox))
    except Exception:
        pass

    # Case 2: Has tables â†’ extract locally
    if tables_md:
        print(f"\n  [page {page_num}] {len(tables_md)} table(s) â†’ local extraction")

        text_blocks = []
        for block in page.get_text("blocks"):
            if block[6] != 0:
                continue
            block_rect = fitz.Rect(block[:4])
            if not any(block_rect.intersects(tr) for tr in table_rects):
                text = block[4].strip()
                if text and clean_fn:
                    text = clean_fn(text)
                if text:
                    text_blocks.append({"text": text, "y_pos": block[1]})

        all_parts = []
        for tb in text_blocks:
            all_parts.append({"content": tb["text"], "y_pos": tb["y_pos"], "is_table": False})
        for tm in tables_md:
            all_parts.append({"content": tm["md"], "y_pos": tm["y_pos"], "is_table": True})
        all_parts.sort(key=lambda x: x["y_pos"])

        lines = []
        for part in all_parts:
            if part["is_table"]:
                lines.append("\n" + part["content"] + "\n")
            else:
                lines.append(part["content"])

        return {
            "page_num": page_num,
            "strategy": "local",
            "content": "\n\n".join(lines).strip(),
            "image_b64": None,
        }

    # Case 3: Text only â†’ LLM formatting
    print(f"\n  [page {page_num}] text-only â†’ LLM")
    return {
        "page_num": page_num,
        "strategy": "text_llm",
        "content": native_text,
        "image_b64": None,
    }


def extract_all_pages(pdf_path: str, clean_fn=None) -> list[dict]:
    """Extract all pages with auto-detection."""
    pages = []
    with fitz.open(pdf_path) as doc:
        total = len(doc)
        for i, page in enumerate(doc):
            print(f"\r  Processing page: {i+1}/{total}", end="", flush=True)
            page_data = extract_page(page, i + 1, clean_fn)
            pages.append(page_data)
    print()
    return pages


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# LLM PROCESSING (per page, strategy-aware)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def process_page_with_llm(
    page_data: dict,
    semaphore: asyncio.Semaphore,
    completed: list,
    total: int,
) -> str:
    """Process a single page. Local pages skip LLM entirely."""
    page_num = page_data["page_num"]
    strategy = page_data["strategy"]

    # Local extraction â€” already done
    if strategy == "local":
        completed.append(1)
        print(f"\r  Progress: {len(completed)}/{total} pages done", end="", flush=True)
        return page_data["content"]

    # Build message based on strategy
    if strategy == "vision":
        user_content = [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{page_data['image_b64']}"}},
            {"type": "text", "text": VISION_PROMPT},
        ]
    else:  # text_llm
        user_content = page_data["content"]

    async with semaphore:
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                ),
                timeout=300,
            )
            result = response.choices[0].message.content
            if result and result.strip():
                # Strip code fences immediately
                result = re.sub(r'```(?:markdown|md)?\s*\n', '', result)
                result = re.sub(r'\n```\s*$', '', result.strip())
                completed.append(1)
                print(f"\r  Progress: {len(completed)}/{total} pages done", end="", flush=True)
                return result.strip()
        except Exception as e:
            print(f"\n  [warn] Page {page_num} ({strategy}) failed: {type(e).__name__}: {e}")

        # Fallback
        completed.append(1)
        print(f"\r  Progress: {len(completed)}/{total} pages done (fallback)", end="", flush=True)
        if page_data["content"]:
            return page_data["content"]
        return f"<!-- Page {page_num}: extraction failed -->"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# POST-PROCESSING
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def clean_markdown(text: str) -> str:
    """Remove PDF artifacts: headers, footers, page numbers, URLs, separators."""

    # Strip ```markdown ... ``` code fences that LLM sometimes wraps output in
    text = re.sub(r'```(?:markdown|md)?\s*\n', '', text)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'```(?:markdown|md)?\s*\n(.*?)```', r'\1', text, flags=re.DOTALL)

    lines = text.split("\n")
    cleaned = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            cleaned.append("")
            continue

        # Skip standalone page numbers
        if re.match(r'^\d{1,3}$', stripped):
            continue

        # Skip standalone URLs
        if re.match(r'^https?://\S+$', stripped):
            continue

        # Skip page indicators (1/4, 2/4)
        if re.match(r'^\d+/\d+$', stripped):
            continue

        # Skip date+time headers
        if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}\s*(AM|PM|am|pm)?$', stripped):
            continue

        # Skip common artifact names
        if stripped.lower() in ('printableservlet', 'page', 'printed'):
            continue

        # Remove inline footer URLs with page numbers
        stripped = re.sub(r'https?://\S+\s*\d*/\d*\s*$', '', stripped).strip()

        # Remove markdown links to footer URLs
        stripped = re.sub(r'\[(?:https?://|tps://)\S*\]\(https?://\S*\)', '', stripped).strip()

        # Remove trailing page numbers
        stripped = re.sub(r'\s+\d{1,2}/\d{1,2}\s*$', '', stripped).strip()

        if not stripped:
            continue

        cleaned.append(stripped if not line.startswith(" ") else line.rstrip())

    result = re.sub(r'\n{3,}', '\n\n', "\n".join(cleaned))
    return result.strip()

# RESUME: DETECT AND REPROCESS FAILED PAGES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def find_failed_pages(md_path: Path) -> list[int]:
    """Scan existing markdown file for failed page placeholders."""
    text = md_path.read_text(encoding="utf-8")
    matches = re.findall(r'<!-- Page (\d+): (?:extraction failed|empty) -->', text)
    return [int(n) for n in matches]


def patch_markdown(md_path: Path, patches: dict[int, str]) -> str:
    """Replace failed page placeholders with new content."""
    text = md_path.read_text(encoding="utf-8")
    for page_num, new_content in patches.items():
        pattern = rf'<!-- Page {page_num}: (?:extraction failed|empty) -->'
        text = re.sub(pattern, new_content.strip(), text)
    return text


async def resume(
    pdf_path: str,
    concurrency: int = 5,
    has_watermark: bool = False,
):
    path = Path(pdf_path)
    output_path = path.with_suffix(".md")

    if not output_path.exists():
        print(f"[!] No existing output found: {output_path}")
        print("    Run normally first to generate the initial file.")
        sys.exit(1)

    failed_pages = find_failed_pages(output_path)
    if not failed_pages:
        print("âœ… No failed pages found in existing output.")
        return

    print(f"\nðŸ“„ PDF:    {pdf_path}")
    print(f"ðŸ“ Output: {output_path}")
    print(f"ðŸ” Failed pages to retry: {failed_pages}\n")

    # Watermark cleaner
    clean_fn = None
    if has_watermark:
        print("ðŸ” Detecting watermark pattern...")
        patterns = await detect_watermark(pdf_path)
        if patterns:
            clean_fn = build_watermark_cleaner(patterns)
            print(f"  âœ“ Watermark cleaner ready\n")

    # Extract only failed pages
    pages_data = []
    with fitz.open(pdf_path) as doc:
        for page_num in failed_pages:
            idx = page_num - 1  # 0-based
            if idx >= len(doc):
                print(f"  [warn] Page {page_num} out of range, skipping")
                continue
            print(f"  Re-extracting page {page_num}...", end="", flush=True)
            page_data = extract_page(doc[idx], page_num, clean_fn)
            pages_data.append(page_data)
            print(" done")

    if not pages_data:
        print("[!] No pages to reprocess.")
        return

    # Reprocess with LLM
    print(f"\nðŸ¤– Reprocessing {len(pages_data)} page(s)...\n")
    semaphore = asyncio.Semaphore(concurrency)
    completed: list = []
    tasks = [
        process_page_with_llm(p, semaphore, completed, len(pages_data))
        for p in pages_data
    ]
    results = await asyncio.gather(*tasks)
    print()

    # Build patch map
    patches = {}
    for page_data, result in zip(pages_data, results):
        page_num = page_data["page_num"]
        if isinstance(result, str) and result.strip() and "extraction failed" not in result:
            patches[page_num] = result
            print(f"  âœ“ Page {page_num}: recovered ({len(result)} chars)")
        else:
            print(f"  âœ— Page {page_num}: still failed, keeping placeholder")

    if not patches:
        print("\n[!] No pages recovered.")
        return

    # Patch and clean
    patched = patch_markdown(output_path, patches)
    patched = clean_markdown(patched)
    output_path.write_text(patched, encoding="utf-8")
    print(f"\nâœ… Patched {len(patches)}/{len(pages_data)} pages â†’ {output_path}")

# MAIN
async def main(
    pdf_path: str,
    concurrency: int = 5,
    has_watermark: bool = False,
    overwrite: bool = False,
):
    path = Path(pdf_path)

    if not path.exists():
        print(f"[!] File not found: {pdf_path}")
        sys.exit(1)
    if path.suffix.lower() != ".pdf":
        print(f"[!] Not a PDF file: {pdf_path}")
        sys.exit(1)

    output_path = path.with_suffix(".md")
    if output_path.exists() and not overwrite:
        print(f"[!] Output already exists: {output_path}")
        print("    Use overwrite=y to replace.")
        sys.exit(1)

    print(f"\nðŸ“„ Input:  {pdf_path}")
    print(f"ðŸ“ Output: {output_path}")
    print(f"âš™ï¸  Concurrency: {concurrency} | Watermark: {'on' if has_watermark else 'off'}\n")

    # Step 0: Detect watermark if requested
    clean_fn = None
    if has_watermark:
        print("ðŸ” Detecting watermark pattern...")
        patterns = await detect_watermark(pdf_path)
        if patterns:
            clean_fn = build_watermark_cleaner(patterns)
            print(f"  âœ“ Watermark cleaner ready\n")
        else:
            print("  âœ— No watermark detected, proceeding normally\n")

    # Step 1: Extract all pages (auto-detect per page)
    pages = extract_all_pages(pdf_path, clean_fn)

    local_count = sum(1 for p in pages if p["strategy"] == "local")
    vision_count = sum(1 for p in pages if p["strategy"] == "vision")
    text_count = sum(1 for p in pages if p["strategy"] == "text_llm")
    print(f"  Summary: {local_count} local (tables), {text_count} textâ†’LLM, {vision_count} imageâ†’LLM vision\n")

    # Step 2: Process all pages (local ones skip LLM)
    semaphore = asyncio.Semaphore(concurrency)
    completed: list = []
    tasks = [
        process_page_with_llm(p, semaphore, completed, len(pages))
        for p in pages
    ]
    results = await asyncio.gather(*tasks)
    print()

    # Step 3: Assemble output
    parts = []
    for i, result in enumerate(results):
        content = result if isinstance(result, str) and result.strip() else f"<!-- Page {pages[i]['page_num']}: empty -->"
        parts.append(content)

    final = "\n\n".join(parts)

    # Step 4: Clean markdown
    final = clean_markdown(final)

    output_path.write_text(final, encoding="utf-8")
    print(f"\nâœ… Done â†’ {output_path}")


if __name__ == "__main__":
    print("=== PDF to Markdown Converter ===\n")

    pdf = input("ðŸ“„ PDF file path: ").strip()

    mode_raw = input("â–¶ï¸  Mode â€” (1) Fresh run  (2) Resume failed pages [default: 1]: ").strip()
    mode = mode_raw if mode_raw in ("1", "2") else "1"

    watermark_raw = input("ðŸ” Does the PDF have watermarks? (y/N): ").strip().lower()
    has_watermark = watermark_raw == "y"

    concurrency_raw = input("âš¡ Max concurrent requests [default: 5]: ").strip()
    concurrency = int(concurrency_raw) if concurrency_raw else 5

    if mode == "2":
        asyncio.run(resume(pdf, concurrency, has_watermark))
    else:
        overwrite_raw = input("â™»ï¸  Overwrite existing output? (y/N): ").strip().lower()
        overwrite = overwrite_raw == "y"
        asyncio.run(main(pdf, concurrency, has_watermark, overwrite))
