#!/usr/bin/env python3
"""
Section Detection Module
========================
Détection intelligente des sections dans les documents PDF
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
import fitz

class Section:
    """Représente une section détectée"""
    def __init__(self, number: str, title: str, page: int, position_y: float):
        self.number = number
        self.title = title  
        self.page = page
        self.position_y = position_y
        
    def __repr__(self):
        return f"Section({self.number}, '{self.title[:30]}...', page={self.page})"

class SectionDetector:
    """Détecteur de sections dans les PDFs"""
    
    def __init__(self, config: dict = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        
    def _default_config(self) -> dict:
        """Configuration par défaut"""
        return {
            'font_size_range': [12.0, 16.0],  # Au lieu de 14.0 fixe
            'bold_required': True,
            'title_min_length': 5,
            'section_patterns': [
                r'^\d+(?:\.\d+)*$',          # 1.2.3
                r'^[A-Z]+\d+(?:\.\d+)*$',    # A1.2  
            ]
        }
    
    def detect_sections(self, doc: fitz.Document) -> List[Section]:
        """Détecte toutes les sections du document"""
        sections = []
        
        for page_num in range(len(doc)):
            page_sections = self._detect_page_sections(doc[page_num], page_num)
            sections.extend(page_sections)
            
        # Trier par page puis position Y
        sections.sort(key=lambda s: (s.page, s.position_y))
        
        self.logger.info(f"Détecté {len(sections)} sections")
        return sections
    
    def _detect_page_sections(self, page: fitz.Page, page_num: int) -> List[Section]:
        """Détecte les sections d'une page"""
        sections = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
                
            lines = block["lines"]
            i = 0
            
            while i < len(lines) - 1:
                current_line = lines[i]
                next_line = lines[i + 1]
                
                current_text = self._extract_line_text(current_line)
                current_format = self._analyze_line_formatting(current_line)
                
                next_text = self._extract_line_text(next_line)
                next_format = self._analyze_line_formatting(next_line)
                
                if self._is_valid_section_pattern(current_text, current_format, 
                                                 next_text, next_format):
                    section = Section(
                        number=current_text.strip(),
                        title=next_text.strip(),
                        page=page_num,
                        position_y=current_line["bbox"][1]
                    )
                    sections.append(section)
                    
                    self.logger.debug(f"Section détectée: {section}")
                    i += 1  # Skip next line
                i += 1
        
        return sections
    
    def _extract_line_text(self, line: dict) -> str:
        """Extrait le texte d'une ligne"""
        text = ""
        for span in line["spans"]:
            text += span["text"]
        return text.strip()
    
    def _analyze_line_formatting(self, line: dict) -> dict:
        """Analyse le formatage d'une ligne"""
        if not line["spans"]:
            return {}
        
        span = line["spans"][0]
        return {
            'size': round(span["size"], 1),
            'font': span["font"],
            'flags': span["flags"],
            'is_bold': bool(span["flags"] & 16)
        }
    
    def _is_valid_section_pattern(self, text1: str, format1: dict, 
                                 text2: str, format2: dict) -> bool:
        """Vérifie si deux lignes forment un titre de section"""
        # Ligne 1 doit être un numéro de section
        is_section_number = any(
            re.match(pattern, text1) 
            for pattern in self.config['section_patterns']
        )
        if not is_section_number:
            return False
        
        # Ligne 2 doit être un titre
        if len(text2) < self.config['title_min_length']:
            return False
        
        # Vérification formatage (assouplir les règles)
        if self.config['bold_required']:
            if not (format1.get('is_bold', False) and format2.get('is_bold', False)):
                return False
        
        # Taille dans la plage configurée au lieu de 14.0 exactement
        size1, size2 = format1.get('size', 0), format2.get('size', 0)
        min_size, max_size = self.config['font_size_range']
        
        if not (min_size <= size1 <= max_size and min_size <= size2 <= max_size):
            return False
        
        # Le titre doit contenir des lettres
        if not re.search(r'[A-Za-zÀ-ÿ]{3,}', text2):
            return False
        
        return True

    def find_section_for_position(self, page_num: int, position_y: float, 
                                 sections: List[Section]) -> Optional[Section]:
        """Trouve la section correspondant à une position"""
        # Sections sur la même page
        same_page_sections = [s for s in sections if s.page == page_num]
        
        if same_page_sections:
            # Trouve la dernière section qui précède la position
            for section in reversed(same_page_sections):
                if section.position_y < position_y:
                    return section
        
        # Sinon, dernière section des pages précédentes
        previous_sections = [s for s in sections if s.page < page_num]
        if previous_sections:
            return max(previous_sections, key=lambda s: (s.page, s.position_y))
        
        return None 