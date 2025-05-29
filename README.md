# LensCRL - PDF Image Extractor

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A practical tool for automatically extracting images from PDF files and naming them according to CRL nomenclature.

## 🎯 What it does

- Extracts images from PDF files
- Automatically names them according to CRL format
- Detects document sections
- Filters duplicates (logos, headers)
- Cross-platform support (Windows, Linux, macOS)

## 📁 Project Structure

```
LensCRL/
├── lenscrl.py              # Main script
├── extract_images.sh       # Linux/macOS script
├── extract_images.bat      # Windows script
├── install.py              # Installation script
├── README.md               # This file
└── requirements.txt        # Dependencies
```

## 🔧 Installation

### Automatic installation
```bash
python3 install.py
```

### Manual installation
```bash
pip install PyMuPDF
chmod +x extract_images.sh  # Linux/macOS only
```

## 📖 Usage

### Simple mode (recommended)

**Windows:** Double-click `extract_images.bat`

**Linux/macOS:** Double-click `extract_images.sh`

### Command line

```bash
# Basic usage
./extract_images.sh -p "document.pdf" -o "./images"

# With options
./extract_images.sh -p "manual.pdf" -o "./output" -m "DOC01" -r

# Direct Python
python3 lenscrl.py --pdf "document.pdf" --output "./images" --report
```

## 📝 Nomenclature

The script names images as follows:

- **1 image per section:** `CRL-DOC01-2.1.png`
- **Multiple images:** `CRL-DOC01-2.1 n_1.png`, `CRL-DOC01-2.1 n_2.jpg`

## 🔧 Options

| Option | Description |
|--------|-------------|
| `-p`, `--pdf` | Source PDF file |
| `-o`, `--output` | Output directory |
| `-m`, `--manual` | Manual name (optional) |
| `-r`, `--report` | Generate report |
| `-h`, `--help` | Show help |

## 🐛 Common Issues

**PyMuPDF not installed:**
```bash
pip install PyMuPDF
```

**Permission denied (Linux/macOS):**
```bash
chmod +x extract_images.sh
```

**Python not found:**
- Windows: install from [python.org](https://python.org)
- Linux: `sudo apt install python3 python3-pip`
- macOS: `brew install python3`

## 📋 Requirements

- Python 3.7+
- PyMuPDF (installed automatically)
- ~100 MB free space

## 💡 How it works

1. Script analyzes PDF to find sections
2. Extracts images and determines which section they belong to
3. Names them according to CRL nomenclature
4. Filters duplicates using MD5 hash

## 🏗️ Usage Examples

```bash
# Technical manual
./extract_images.sh -p "DOC01-Manual.pdf" -o "./images_DOC01" -r

# Quick guide
./extract_images.sh -p "Guide.pdf" -o "./guide_images" -m "GUIDE"

# Batch processing
for pdf in *.pdf; do
    ./extract_images.sh -p "$pdf" -o "./$(basename "$pdf" .pdf)" -r
done
```

## 📄 License

MIT License - see `LICENSE` file

---

## 🚀 Quick Start

```bash
# 1. Install
python3 install.py

# 2. Test
./extract_images.sh -p "your_document.pdf" -o "./test" -r

# 3. Check results
ls ./test/CRL-*
```

