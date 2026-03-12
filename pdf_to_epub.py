#!/usr/bin/env python3
"""Convert a PDF file to EPUB format.

Usage: python3 pdf_to_epub.py input.pdf [output.epub]

Detects if the PDF has a text layer. If not, reports that OCR is needed.
"""

import sys
import os
import re
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
        # Escape HTML
        p = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Keep single newlines as line breaks
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
    if len(sys.argv) < 2:
        print("Utilizare: python3 pdf_to_epub.py input.pdf [output.epub]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Eroare: Fișierul '{pdf_path}' nu există.")
        sys.exit(1)

    output_path = sys.argv[2] if len(sys.argv) > 2 else pdf_path.rsplit(".", 1)[0] + ".epub"

    print(f"Se procesează: {pdf_path}")
    pages = extract_text_from_pdf(pdf_path)
    total_pages = len(pages)
    print(f"Total pagini: {total_pages}")

    total_chars, pages_with_text = check_text_layer(pages)
    print(f"Caractere text detectate: {total_chars}")
    print(f"Pagini cu text: {pages_with_text}/{total_pages}")

    if pages_with_text < total_pages * 0.3:
        print("\n⚠ PDF-ul pare să fie scanat (fără text layer).")
        print("  Este nevoie de OCR pentru a extrage textul.")
        print("  Rulează: apt-get install tesseract-ocr tesseract-ocr-ron")
        print("  Apoi: pip install pytesseract Pillow")
        print("  Și reîncearcă conversia.")
        sys.exit(2)

    print(f"\nPDF-ul are text layer. Se convertește...")
    chapters = split_into_chapters(pages)
    print(f"Capitole detectate: {len(chapters)}")

    result = create_epub(chapters, output_path)
    print(f"\nEPUB creat cu succes: {result}")
    print(f"Dimensiune: {os.path.getsize(result) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
