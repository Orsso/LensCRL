#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LensCRL - PDF Image Extractor
=============================

A practical tool for automatically extracting images from PDF files
and naming them according to CRL nomenclature.

Author: Arien Reibel
Version: 1.0
"""

import os
import re
import sys
import argparse
import logging
import platform
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("❌ ERROR: PyMuPDF is not installed.")
    print("   Install it with: pip install PyMuPDF")
    sys.exit(1)

import unicodedata

class LensCRL:
    """PDF image extractor with CRL nomenclature."""
    
    def __init__(self, pdf_path: str, output_dir: str, manual_name: Optional[str] = None):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.manual_name = manual_name
        self.detected_sections = []
        self.extracted_images = []
        
        # Logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('lenscrl_extraction.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def detect_document_sections(self, doc: fitz.Document) -> List[Dict]:
        """Detects document sections."""
        self.logger.info("Detecting sections...")
        
        sections = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                lines = block["lines"]
                i = 0
                
                while i < len(lines) - 1:
                    current_line = lines[i]
                    next_line = lines[i + 1]
                    
                    current_text = self.extract_line_text(current_line)
                    current_format = self.analyze_line_formatting(current_line)
                    
                    next_text = self.extract_line_text(next_line)
                    next_format = self.analyze_line_formatting(next_line)
                    
                    if self.is_valid_section_pattern(current_text, current_format, next_text, next_format):
                        section = {
                            'number': current_text.strip(),
                            'title': next_text.strip(),
                            'page': page_num,
                            'position_y': current_line["bbox"][1]
                        }
                        sections.append(section)
                        
                        self.logger.info(f"Section detected: {section['number']} - {section['title']} (page {page_num + 1}, Y={section['position_y']:.1f})")
                        i += 1  # Skip next line
                    i += 1
        
        # Sort by page then by Y position
        sections.sort(key=lambda x: (x['page'], x['position_y']))
        
        self.detected_sections = sections
        return sections
    
    def find_section_for_image(self, page_num: int, image_bbox: Tuple) -> Optional[str]:
        """Finds the corresponding section for an image."""
        image_y = image_bbox[1]  # Image Y position
        
        # 1. Look for sections on the same page as the image
        same_page_sections = [s for s in self.detected_sections if s['page'] == page_num]
        
        if same_page_sections:
            # Sort by Y position
            same_page_sections.sort(key=lambda x: x['position_y'])
            
            # Find the last section that precedes the image (section Y < image Y)
            current_section = None
            for section in same_page_sections:
                if section['position_y'] < image_y:
                    current_section = section['number']
                    self.logger.debug(f"Image page {page_num + 1} Y={image_y:.1f} → section {current_section} (Y={section['position_y']:.1f})")
                else:
                    break  # Stop when we find a section after the image
            
            if current_section:
                return current_section
        
        # 2. If no section on the same page, look for the last previous section
        previous_sections = [s for s in self.detected_sections if s['page'] < page_num]
        if previous_sections:
            # Take the last previous section
            last_section = max(previous_sections, key=lambda x: (x['page'], x['position_y']))
            self.logger.debug(f"Image page {page_num + 1} → previous section {last_section['number']} (page {last_section['page'] + 1})")
            return last_section['number']
        
        return None
    
    def extract_line_text(self, line: dict) -> str:
        """Extracts text from a line."""
        text = ""
        for span in line["spans"]:
            text += span["text"]
        return text.strip()
    
    def analyze_line_formatting(self, line: dict) -> dict:
        """Analyzes line formatting."""
        if not line["spans"]:
            return {}
        
        span = line["spans"][0]
        return {
            'size': round(span["size"], 1),
            'font': span["font"],
            'flags': span["flags"],
            'is_bold': bool(span["flags"] & 16)
        }
    
    def is_valid_section_pattern(self, text1: str, format1: dict, text2: str, format2: dict) -> bool:
        """Checks if two consecutive lines form a section title."""
        # Line 1 must be a section number
        if not re.match(r'^\d+(?:\.\d+)*$', text1):
            return False
        
        # Line 2 must be a title
        if len(text2) < 5:
            return False
        
        # Both must be bold 14pt
        if not (format1.get('is_bold', False) and format2.get('is_bold', False)):
            return False
        
        if not (format1.get('size', 0) == 14.0 and format2.get('size', 0) == 14.0):
            return False
        
        # Title must contain letters
        if not re.search(r'[A-Za-zÀ-ÿ]{3,}', text2):
            return False
        
        return True
    
    def extract_images(self) -> List[Dict]:
        """Extracts images from PDF and names them according to CRL nomenclature."""
        self.logger.info(f"Opening PDF: {self.pdf_path}")
        
        try:
            doc = fitz.open(self.pdf_path)
        except Exception as e:
            self.logger.error(f"Error opening PDF: {e}")
            return []
        
        # Detect all sections
        self.detect_document_sections(doc)
        
        # Deduce manual name
        manual_name = self.deduce_manual_name()
        self.logger.info(f"Manual name: {manual_name}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_images = []
        counter_by_section = {}
        seen_image_hashes = set()
        duplicate_images = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            if image_list:
                self.logger.info(f"Page {page_num + 1}: {len(image_list)} image(s)")
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Extract image
                        xref = img[0]
                        image_doc = doc.extract_image(xref)
                        image_data = image_doc["image"]
                        extension = image_doc["ext"]
                        
                        # Detect duplicates
                        image_hash = hashlib.md5(image_data).hexdigest()
                        if image_hash in seen_image_hashes:
                            duplicate_images += 1
                            self.logger.debug(f"Duplicate image ignored on page {page_num + 1}")
                            continue
                        seen_image_hashes.add(image_hash)
                        
                        # Get image position
                        try:
                            image_rects = page.get_image_rects(xref)
                            if image_rects:
                                image_bbox = image_rects[0]
                            else:
                                image_bbox = (0, 100 + img_index * 50, 100, 150 + img_index * 50)
                        except:
                            image_bbox = (0, 100 + img_index * 50, 100, 150 + img_index * 50)
                        
                        # Find section
                        section_number = self.find_section_for_image(page_num, image_bbox)
                        if not section_number:
                            section_number = "0"
                        
                        # Count images per section
                        if section_number not in counter_by_section:
                            counter_by_section[section_number] = 0
                        counter_by_section[section_number] += 1
                        position_in_section = counter_by_section[section_number]
                        
                        # Build temporary filename
                        temp_filename = f"CRL-{manual_name}-{section_number} n_{position_in_section}.{extension}"
                        temp_path = self.output_dir / temp_filename
                        
                        # Save image
                        with open(temp_path, "wb") as image_file:
                            image_file.write(image_data)
                        
                        image_info = {
                            'temp_filename': temp_filename,
                            'temp_path': temp_path,
                            'page': page_num + 1,
                            'section': section_number,
                            'position': position_in_section,
                            'extension': extension,
                            'manual_name': manual_name,
                            'hash': image_hash,
                            'bbox': image_bbox
                        }
                        
                        extracted_images.append(image_info)
                        self.logger.info(f"Image extracted: {temp_filename} (page {page_num + 1}, section {section_number}, Y={image_bbox[1]:.1f})")
                        
                    except Exception as e:
                        self.logger.error(f"Error extracting image {img_index} on page {page_num + 1}: {e}")
                        continue
        
        doc.close()
        
        # Final renaming phase according to CRL rules
        self.logger.info("Applying CRL nomenclature...")
        for img in extracted_images:
            section = img['section']
            total_images_in_section = counter_by_section[section]
            
            if total_images_in_section == 1:
                final_name = f"CRL-{img['manual_name']}-{section}.{img['extension']}"
            else:
                final_name = f"CRL-{img['manual_name']}-{section} n_{img['position']}.{img['extension']}"
            
            final_path = self.output_dir / final_name
            img['temp_path'].rename(final_path)
            
            img['filename'] = final_name
            img['path'] = final_path
            
            self.logger.info(f"Final file: {final_name}")
        
        # Log statistics
        self.logger.info(f"Duplicate images filtered: {duplicate_images}")
        self.logger.info("Summary by section:")
        for section, count in sorted(counter_by_section.items()):
            self.logger.info(f"  Section {section}: {count} image(s)")
        
        self.extracted_images = extracted_images
        return extracted_images
    
    def deduce_manual_name(self) -> str:
        """Deduces manual name from PDF filename."""
        if self.manual_name:
            return self.manual_name
            
        filename = self.pdf_path.stem
        
        # Extraction patterns
        patterns = [
            r'^([A-Z]+\d+)',  # Ex: PROCSG02
            r'^([A-Z]{2,})',  # Ex: OMA, STC
            r'^(\w+?)[-_]',   # First segment before - or _
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                return match.group(1)
        
        return input(f"Manual name for '{filename}': ").strip().upper()
    
    def generate_report(self) -> str:
        """Generates an extraction report."""
        report = []
        report.append("=" * 60)
        report.append("LENSCRL v1.0 EXTRACTION REPORT")
        report.append("=" * 60)
        report.append(f"PDF file: {self.pdf_path}")
        report.append(f"Output directory: {self.output_dir}")
        report.append(f"Sections detected: {len(self.detected_sections)}")
        report.append(f"Images extracted: {len(self.extracted_images)}")
        report.append("")
        
        report.append("DETECTED SECTIONS:")
        report.append("-" * 30)
        for section in self.detected_sections:
            report.append(f"  {section['number']} - {section['title']}")
            report.append(f"    Page {section['page'] + 1}, Y={section['position_y']:.1f}")
        report.append("")
        
        # Summary by section
        counter_by_section = {}
        for img in self.extracted_images:
            section = img['section']
            counter_by_section[section] = counter_by_section.get(section, 0) + 1
        
        report.append("IMAGES BY SECTION:")
        report.append("-" * 30)
        for section, count in sorted(counter_by_section.items()):
            report.append(f"  Section {section}: {count} image(s)")
        
        report.append("")
        report.append("CREATED FILES:")
        report.append("-" * 30)
        for img in self.extracted_images:
            report.append(f"  {img['filename']} (page {img['page']})")
        
        return "\n".join(report)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="LensCRL v1.0 - PDF Image Extractor"
    )
    
    parser.add_argument('--pdf', '-p', required=True, help="Source PDF file")
    parser.add_argument('--output', '-o', required=True, help="Output directory")
    parser.add_argument('--manual', '-m', help="Manual name (optional)")
    parser.add_argument('--report', '-r', action='store_true', help="Generate report")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf):
        print(f"Error: PDF file '{args.pdf}' does not exist.")
        sys.exit(1)
    
    print("=" * 50)
    print("LENSCRL v1.0 - PDF IMAGE EXTRACTOR")
    print("=" * 50)
    print(f"PDF: {args.pdf}")
    print(f"Output: {args.output}")
    print()
    
    extractor = LensCRL(
        pdf_path=args.pdf,
        output_dir=args.output,
        manual_name=args.manual
    )
    
    try:
        images = extractor.extract_images()
        
        print(f"\n✅ Extraction completed!")
        print(f"   Images extracted: {len(images)}")
        print(f"   Saved to: {args.output}")
        
        if args.report:
            report = extractor.generate_report()
            report_path = Path(args.output) / "lenscrl_report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"   Report: {report_path}")
            print("\n" + report)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 