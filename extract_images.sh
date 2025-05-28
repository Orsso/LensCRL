#!/bin/bash
# PDF Image Extraction Script - LensCRL
# Compatible with Linux/macOS
# Version: 1.0

set -e  # Stop on error

# Colors for display
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display functions with colors
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Help function
show_help() {
    echo "================================================"
    echo "LENSCRL v1.0 - PDF IMAGE EXTRACTOR"
    echo "================================================"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -p, --pdf FILE        Source PDF file (required)"
    echo "  -o, --output DIR      Output directory (required)"
    echo "  -m, --manual NAME     Manual name (optional)"
    echo "  -r, --report          Generate report"
    echo "  -h, --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 -p \"document.pdf\" -o \"./images\" -r"
    echo "  $0 --pdf \"manual.pdf\" --output \"./output\" --manual \"DOC01\""
    echo ""
    echo "Nomenclature:"
    echo "  • CRL-[MANUALNAME]-[SECTION#].{ext}          (1 image)"
    echo "  • CRL-[MANUALNAME]-[SECTION#] n_[POS].{ext}  (multiple images)"
    echo ""
}

# Default variables
PDF_FILE=""
OUTPUT_DIR=""
MANUAL_NAME=""
GENERATE_REPORT=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACTOR_SCRIPT="$SCRIPT_DIR/lenscrl.py"

# Argument parsing
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--pdf)
            PDF_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -m|--manual)
            MANUAL_NAME="$2"
            shift 2
            ;;
        -r|--report)
            GENERATE_REPORT=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$PDF_FILE" ]]; then
    print_error "Source PDF file is required (-p/--pdf)"
    show_help
    exit 1
fi

if [[ -z "$OUTPUT_DIR" ]]; then
    print_error "Output directory is required (-o/--output)"
    show_help
    exit 1
fi

# Preliminary checks
print_info "Checking environment..."

# Check if PDF file exists
if [[ ! -f "$PDF_FILE" ]]; then
    print_error "PDF file '$PDF_FILE' does not exist"
    exit 1
fi

# Check if Python script exists
if [[ ! -f "$EXTRACTOR_SCRIPT" ]]; then
    print_error "Extractor script not found: $EXTRACTOR_SCRIPT"
    exit 1
fi

# Detect Python
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')
    if [[ "${PYTHON_VERSION%%.*}" -ge 3 ]]; then
        PYTHON_CMD="python"
    fi
fi

if [[ -z "$PYTHON_CMD" ]]; then
    print_error "Python 3 is not installed or accessible"
    print_info "Install Python 3:"
    print_info "  • Ubuntu/Debian: sudo apt install python3 python3-pip"
    print_info "  • CentOS/RHEL: sudo yum install python3 python3-pip"
    print_info "  • macOS: brew install python3"
    exit 1
fi

print_success "Python found: $($PYTHON_CMD --version)"

# Check PyMuPDF
print_info "Checking PyMuPDF..."
if ! $PYTHON_CMD -c "import fitz" 2>/dev/null; then
    print_warning "PyMuPDF is not installed"
    print_info "Installing PyMuPDF..."
    
    if ! $PYTHON_CMD -m pip install PyMuPDF; then
        print_error "Failed to install PyMuPDF"
        print_info "Try manually:"
        print_info "  $PYTHON_CMD -m pip install --user PyMuPDF"
        exit 1
    fi
    
    print_success "PyMuPDF installed successfully"
else
    print_success "PyMuPDF is available"
fi

# Build command
print_info "Preparing extraction..."

CMD_ARGS=("--pdf" "$PDF_FILE" "--output" "$OUTPUT_DIR")

if [[ -n "$MANUAL_NAME" ]]; then
    CMD_ARGS+=("--manual" "$MANUAL_NAME")
fi

if [[ "$GENERATE_REPORT" == true ]]; then
    CMD_ARGS+=("--report")
fi

# Display information
echo ""
echo "================================================"
echo "STARTING EXTRACTION"
echo "================================================"
print_info "PDF file: $PDF_FILE"
print_info "Output directory: $OUTPUT_DIR"
if [[ -n "$MANUAL_NAME" ]]; then
    print_info "Manual name: $MANUAL_NAME"
fi
print_info "Report: $([ "$GENERATE_REPORT" == true ] && echo "Yes" || echo "No")"
echo ""

# Execute extraction
print_info "Running LensCRL..."

if $PYTHON_CMD "$EXTRACTOR_SCRIPT" "${CMD_ARGS[@]}"; then
    echo ""
    print_success "Extraction completed!"
    print_info "Images have been saved to: $OUTPUT_DIR"
    
    if [[ "$GENERATE_REPORT" == true ]]; then
        REPORT_FILE="$OUTPUT_DIR/lenscrl_report.txt"
        if [[ -f "$REPORT_FILE" ]]; then
            print_info "Report available: $REPORT_FILE"
        fi
    fi
    
    # Count extracted files
    if [[ -d "$OUTPUT_DIR" ]]; then
        NB_IMAGES=$(find "$OUTPUT_DIR" -name "CRL-*.png" -o -name "CRL-*.jpg" -o -name "CRL-*.jpeg" | wc -l)
        print_success "$NB_IMAGES image(s) extracted with CRL nomenclature"
    fi
    
else
    echo ""
    print_error "Extraction failed"
    exit 1
fi

echo ""
print_success "🎉 Done!" 