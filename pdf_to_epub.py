#!/usr/bin/env python3
"""Convert a PDF file to EPUB format, with OCR support for scanned PDFs.

Usage: python3 pdf_to_epub.py input.pdf [output.epub] [--test [N]]

  --test      Procesează doar primele 5 pagini (sau N pagini) ca test
"""

import sys
import os
import re
import argparse
import fitz  # PyMuPDF
from ebooklib import epub


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF, return list of (page_num, text) tuples."""
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append((i + 1, text))
    doc.close()
    return pages


def ocr_pdf(pdf_path, max_pages=None, lang="eng"):
    """Extract text from scanned PDF using OCR."""
    try:
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        print("Eroare: pytesseract și Pillow nu sunt instalate.")
        print("Rulează: pip install pytesseract Pillow")
        sys.exit(2)

    doc = fitz.open(pdf_path)
    pages = []
    total = min(len(doc), max_pages) if max_pages else len(doc)

    for i in range(total):
        page = doc[i]
        print(f"  OCR pagina {i + 1}/{total}...", end="\r")
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang=lang)
        pages.append((i + 1, text))

    doc.close()
    print(f"  OCR finalizat: {total} pagini procesate.      ")
    return pages


def check_text_layer(pages):
    """Check if PDF has meaningful text content."""
    total_chars = sum(len(text.strip()) for _, text in pages)
    pages_with_text = sum(1 for _, text in pages if len(text.strip()) > 20)
    return total_chars, pages_with_text


def split_into_chapters(pages):
    """Try to detect chapter breaks based on common patterns."""
    chapter_patterns = [
        re.compile(r'^(capitolul|chapter)\s+\d+', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^(parte[a]?\s+\w+)', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^\d+\.\s+[A-Z]', re.MULTILINE),
    ]

    chapters = []
    current_title = "Introducere"
    current_text = []

    for page_num, text in pages:
        found_chapter = False
        for pattern in chapter_patterns:
            match = pattern.search(text)
            if match and current_text:
                chapters.append((current_title, "\n\n".join(current_text)))
                current_title = match.group(0).strip()
                current_text = [text]
                found_chapter = True
                break
        if not found_chapter:
            current_text.append(text)

    if current_text:
        chapters.append((current_title, "\n\n".join(current_text)))

    return chapters


def text_to_html(text):
    """Convert plain text to simple HTML with paragraphs."""
    paragraphs = text.split("\n\n")
    html_parts = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        p = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        p = p.replace("\n", "<br/>")
        html_parts.append(f"<p>{p}</p>")
    return "\n".join(html_parts)


def create_epub(chapters, output_path, title="Carte", author="Necunoscut", lang="ro"):
    """Create an EPUB file from chapters."""
    book = epub.EpubBook()
    book.set_identifier("id-" + os.path.basename(output_path))
    book.set_title(title)
    book.set_language(lang)
    book.add_author(author)

    epub_chapters = []
    spine = ["nav"]
    toc = []

    for i, (ch_title, ch_text) in enumerate(chapters):
        ch = epub.EpubHtml(
            title=ch_title,
            file_name=f"chapter_{i+1}.xhtml",
            lang=lang,
        )
        html_content = f"<h1>{ch_title}</h1>\n{text_to_html(ch_text)}"
        ch.content = html_content.encode("utf-8")
        book.add_item(ch)
        epub_chapters.append(ch)
        spine.append(ch)
        toc.append(ch)

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(output_path, book)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Convertește PDF în EPUB")
    parser.add_argument("pdf", help="Calea către fișierul PDF")
    parser.add_argument("output", nargs="?", help="Calea către fișierul EPUB (opțional)")
    parser.add_argument("--test", nargs="?", const=5, type=int, metavar="N",
                        help="Procesează doar primele N pagini ca test (implicit: 5)")
    parser.add_argument("--lang", default="eng",
                        help="Limba OCR tesseract (implicit: eng). Ex: ron, eng+ron")
    args = parser.parse_args()

    pdf_path = args.pdf
    if not os.path.exists(pdf_path):
        print(f"Eroare: Fișierul '{pdf_path}' nu există.")
        sys.exit(1)

    output_path = args.output or pdf_path.rsplit(".", 1)[0] + ".epub"
    test_pages = args.test

    if test_pages:
        print(f"*** MOD TEST: doar primele {test_pages} pagini ***\n")
        base, ext = os.path.splitext(output_path)
        output_path = f"{base}_test{ext}"

    print(f"Se procesează: {pdf_path}")
    pages = extract_text_from_pdf(pdf_path)
    total_pages = len(pages)
    print(f"Total pagini: {total_pages}")

    if test_pages:
        pages = pages[:test_pages]
        print(f"Se folosesc doar primele {test_pages} pagini.")

    total_chars, pages_with_text = check_text_layer(pages)
    print(f"Caractere text detectate: {total_chars}")
    print(f"Pagini cu text: {pages_with_text}/{len(pages)}")

    if pages_with_text < len(pages) * 0.3:
        print("\nPDF-ul este scanat. Se pornește OCR (poate dura câteva minute)...")
        pages = ocr_pdf(pdf_path, max_pages=test_pages, lang=args.lang)
    else:
        print(f"\nPDF-ul are text layer.")

    print("Se convertește în EPUB...")
    chapters = split_into_chapters(pages)
    print(f"Capitole detectate: {len(chapters)}")

    result = create_epub(chapters, output_path)
    print(f"\nEPUB creat cu succes: {result}")
    print(f"Dimensiune: {os.path.getsize(result) / 1024:.0f} KB")

    if test_pages:
        print(f"\n*** Acesta e doar un test cu {test_pages} pagini. ***")
        print(f"*** Dacă rezultatul e OK, rulează fără --test pentru toată cartea. ***")


if __name__ == "__main__":
    main()
