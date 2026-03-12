#!/bin/bash
# Setup pentru conversia PDF -> EPUB cu OCR
# Funcționează pe Windows (WSL/Git Bash), Linux și macOS

set -e

echo "=== Setup PDF to EPUB converter ==="

# Instalează tesseract OCR + limba română
if command -v apt-get &> /dev/null; then
    echo "Se instalează tesseract-ocr..."
    sudo apt-get update -qq
    sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
elif command -v brew &> /dev/null; then
    echo "Se instalează tesseract-ocr (macOS)..."
    brew install tesseract
    brew install tesseract-lang
else
    echo "⚠ Nu pot instala tesseract automat."
    echo "  Instalează manual: https://github.com/tesseract-ocr/tesseract"
fi

# Creează venv
echo "Se creează virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Instalează dependențe Python
echo "Se instalează dependențele Python..."
pip install PyMuPDF ebooklib pytesseract Pillow

echo ""
echo "=== Setup complet! ==="
echo ""
echo "Utilizare:"
echo "  source .venv/bin/activate"
echo "  python3 pdf_to_epub.py carte.pdf"
echo ""
