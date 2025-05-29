#!/usr/bin/env python3
"""
Tests unitaires pour SectionDetector
====================================
"""

import pytest
import sys
from pathlib import Path

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.section_detector import SectionDetector, Section

class TestSectionDetector:
    """Tests pour la classe SectionDetector"""
    
    def test_default_config(self):
        """Test configuration par défaut"""
        detector = SectionDetector()
        config = detector.config
        
        assert config['font_size_range'] == [12.0, 16.0]
        assert config['bold_required'] is True
        assert config['title_min_length'] == 5
        assert len(config['section_patterns']) >= 2
        
    def test_custom_config(self):
        """Test configuration personnalisée"""
        custom_config = {
            'font_size_range': [10.0, 18.0],
            'bold_required': False,
            'title_min_length': 3,
            'section_patterns': [r'^\d+$']
        }
        
        detector = SectionDetector(custom_config)
        assert detector.config == custom_config
        
    def test_section_creation(self):
        """Test création d'une section"""
        section = Section("1.2", "Introduction", 0, 100.5)
        
        assert section.number == "1.2"
        assert section.title == "Introduction"
        assert section.page == 0
        assert section.position_y == 100.5
        
    def test_section_repr(self):
        """Test représentation d'une section"""
        section = Section("1", "Un titre très long pour tester la troncature", 1, 200.0)
        repr_str = repr(section)
        
        assert "Section(1" in repr_str
        assert "Un titre très long pour tester..." in repr_str
        assert "page=1" in repr_str
        
    def test_is_valid_section_pattern(self):
        """Test validation des patterns de section"""
        detector = SectionDetector()
        
        # Test pattern numérique valide
        format1 = {'is_bold': True, 'size': 14.0}
        format2 = {'is_bold': True, 'size': 14.0}
        
        # Cas valide
        assert detector._is_valid_section_pattern("1.2", format1, "Introduction", format2)
        
        # Cas invalides
        assert not detector._is_valid_section_pattern("invalid", format1, "Introduction", format2)
        assert not detector._is_valid_section_pattern("1.2", format1, "A", format2)  # titre trop court
        
    def test_extract_line_text(self):
        """Test extraction de texte d'une ligne"""
        detector = SectionDetector()
        
        # Mock d'une ligne PyMuPDF
        line = {
            "spans": [
                {"text": "Partie 1"},
                {"text": " - "},
                {"text": "Introduction"}
            ]
        }
        
        text = detector._extract_line_text(line)
        assert text == "Partie 1 - Introduction"
        
    def test_analyze_line_formatting(self):
        """Test analyse du formatage d'une ligne"""
        detector = SectionDetector()
        
        # Mock d'une ligne avec formatage
        line = {
            "spans": [
                {
                    "size": 14.5,
                    "font": "Arial-Bold",
                    "flags": 16,  # Bold flag
                    "text": "1.2"
                }
            ]
        }
        
        format_info = detector._analyze_line_formatting(line)
        
        assert format_info['size'] == 14.5
        assert format_info['font'] == "Arial-Bold"
        assert format_info['flags'] == 16
        assert format_info['is_bold'] is True
        
    def test_find_section_for_position(self):
        """Test recherche de section pour une position"""
        detector = SectionDetector()
        
        sections = [
            Section("1", "Intro", 0, 50.0),
            Section("2", "Methode", 0, 150.0),
            Section("3", "Resultats", 1, 50.0)
        ]
        
        # Test position sur même page
        section = detector.find_section_for_position(0, 100.0, sections)
        assert section.number == "1"
        
        section = detector.find_section_for_position(0, 200.0, sections)
        assert section.number == "2"
        
        # Test position sur page suivante
        section = detector.find_section_for_position(1, 100.0, sections)
        assert section.number == "3"
        
        # Test page après toutes les sections
        section = detector.find_section_for_position(2, 50.0, sections)
        assert section.number == "3"  # Dernière section connue 