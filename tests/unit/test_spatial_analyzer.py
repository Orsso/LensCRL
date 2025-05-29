#!/usr/bin/env python3
"""
Tests unitaires pour le module SpatialAnalyzer
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import fitz

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.spatial_analyzer import SpatialAnalyzer, PageLayout, ImageContext
from src.core.section_detector import Section

class TestSpatialAnalyzer:
    
    def setup_method(self):
        """Configuration pour chaque test"""
        self.analyzer = SpatialAnalyzer()
        
        # Mock page
        self.mock_page = Mock(spec=fitz.Page)
        self.mock_page.number = 0
        self.mock_page.rect = fitz.Rect(0, 0, 595, 842)  # A4
    
    def test_default_config(self):
        """Test configuration par défaut"""
        config = self.analyzer._default_config()
        
        assert 'column_detection' in config
        assert 'image_association' in config
        assert 'layout_analysis' in config
        
        assert config['column_detection']['min_gap_width'] == 20.0
        assert config['image_association']['max_distance_pixels'] == 200.0
    
    def test_extract_text_zones_empty(self):
        """Test extraction zones de texte - page vide"""
        # Mock page vide
        self.mock_page.get_text.return_value = {"blocks": []}
        
        zones = self.analyzer._extract_text_zones(self.mock_page)
        
        assert zones == []
    
    def test_extract_text_zones_with_content(self):
        """Test extraction zones de texte - avec contenu"""
        # Mock page avec contenu
        mock_text_dict = {
            "blocks": [
                {
                    "lines": [{"spans": [{"text": "Test"}]}],
                    "bbox": (50, 50, 200, 100)
                },
                {
                    "lines": [{"spans": [{"text": "Another"}]}],
                    "bbox": (50, 150, 200, 200)
                }
            ]
        }
        self.mock_page.get_text.return_value = mock_text_dict
        
        zones = self.analyzer._extract_text_zones(self.mock_page)
        
        assert len(zones) == 2
        assert zones[0] == (50, 50, 200, 100)
        assert zones[1] == (50, 150, 200, 200)
    
    def test_detect_columns_no_zones(self):
        """Test détection colonnes - pas de zones"""
        columns = self.analyzer._detect_columns([])
        
        assert columns == []
    
    def test_detect_columns_single_column(self):
        """Test détection colonnes - une seule colonne"""
        zones = [
            (50, 50, 200, 100),
            (50, 150, 200, 200),
            (60, 250, 210, 300)
        ]
        
        columns = self.analyzer._detect_columns(zones)
        
        assert len(columns) == 1
        assert columns[0][0] == 50  # Start de la colonne
        assert columns[0][1] == 210  # End de la colonne
    
    def test_detect_columns_multiple_columns(self):
        """Test détection colonnes - plusieurs colonnes"""
        zones = [
            (50, 50, 200, 100),    # Colonne 1
            (250, 50, 400, 100),   # Colonne 2 (gap > 20)
            (50, 150, 200, 200),   # Colonne 1
            (250, 150, 400, 200)   # Colonne 2
        ]
        
        columns = self.analyzer._detect_columns(zones)
        
        assert len(columns) == 2
        assert columns[0] == (50, 200)
        assert columns[1] == (250, 400)
    
    def test_calculate_margins(self):
        """Test calcul des marges"""
        zones = [
            (50, 80, 300, 120),
            (50, 200, 300, 240)
        ]
        
        margins = self.analyzer._calculate_margins(self.mock_page, zones)
        
        assert margins['left'] == 50
        assert margins['top'] == 80
        assert margins['right'] == 295  # 595 - 300
        assert margins['bottom'] == 602  # 842 - 240
    
    def test_analyze_page_layout(self):
        """Test analyse complète de la mise en page"""
        # Mock données
        mock_text_dict = {
            "blocks": [
                {
                    "lines": [{"spans": [{"text": "Test"}]}],
                    "bbox": (50, 50, 200, 100)
                }
            ]
        }
        self.mock_page.get_text.return_value = mock_text_dict
        
        layout = self.analyzer.analyze_page_layout(self.mock_page)
        
        assert isinstance(layout, PageLayout)
        assert layout.page_num == 0
        assert len(layout.text_zones) == 1
        assert 'left' in layout.margins
    
    def test_find_image_column_no_columns(self):
        """Test recherche colonne image - pas de colonnes"""
        image_bbox = (100, 100, 200, 200)
        
        column = self.analyzer._find_image_column(image_bbox, [])
        
        assert column is None
    
    def test_find_image_column_found(self):
        """Test recherche colonne image - trouvée"""
        image_bbox = (120, 100, 180, 200)  # Centre X = 150
        columns = [(50, 200), (250, 400)]  # Image dans première colonne
        
        column = self.analyzer._find_image_column(image_bbox, columns)
        
        assert column == 0
    
    def test_find_image_column_second_column(self):
        """Test recherche colonne image - deuxième colonne"""
        image_bbox = (320, 100, 380, 200)  # Centre X = 350
        columns = [(50, 200), (250, 400)]  # Image dans deuxième colonne
        
        column = self.analyzer._find_image_column(image_bbox, columns)
        
        assert column == 1
    
    def test_create_image_context(self):
        """Test création contexte image"""
        image_bbox = (100, 100, 200, 200)
        layout = PageLayout(
            page_num=0,
            columns=[(50, 300)],
            margins={'left': 50, 'top': 50, 'right': 295, 'bottom': 600},
            text_zones=[]
        )
        
        # Mock extraction texte autour
        with patch.object(self.analyzer, '_extract_nearby_text', return_value=['texte proche']):
            context = self.analyzer.create_image_context(image_bbox, self.mock_page, layout)
        
        assert isinstance(context, ImageContext)
        assert context.bbox == image_bbox
        assert context.page == 0
        assert context.area == 10000  # 100 * 100
        assert context.aspect_ratio == 1.0  # 100/100
        assert context.column == 0
        assert context.nearby_text == ['texte proche']
    
    def test_calculate_spatial_distance_same_page(self):
        """Test calcul distance spatiale - même page"""
        image_context = ImageContext(
            bbox=(100, 200, 200, 300),
            page=0, area=10000, aspect_ratio=1.0,
            column=0, nearby_text=[], distance_to_sections={}
        )
        section = Section("1", "Test", 0, 150)
        
        distance = self.analyzer._calculate_spatial_distance(image_context, section)
        
        assert distance == 50  # |200 - 150|
    
    def test_calculate_spatial_distance_different_page(self):
        """Test calcul distance spatiale - pages différentes"""
        image_context = ImageContext(
            bbox=(100, 200, 200, 300),
            page=2, area=10000, aspect_ratio=1.0,
            column=0, nearby_text=[], distance_to_sections={}
        )
        section = Section("1", "Test", 0, 150)
        
        distance = self.analyzer._calculate_spatial_distance(image_context, section)
        
        assert distance == 2000.0  # 1000 * |2 - 0|
    
    def test_calculate_association_score(self):
        """Test calcul score d'association"""
        image_context = ImageContext(
            bbox=(100, 200, 200, 300),
            page=0, area=10000, aspect_ratio=1.0,
            column=0, nearby_text=['section', 'test'], distance_to_sections={}
        )
        section = Section("1", "Section Test", 0, 180)
        layout = PageLayout(0, [(50, 300)], {}, [])
        
        with patch.object(self.analyzer, '_calculate_text_context_score', return_value=0.1):
            score = self.analyzer._calculate_association_score(image_context, section, layout)
        
        # Score devrait être > 0 avec bonus même page et distance proche
        assert score > 0.1
        assert score <= 1.0
    
    def test_calculate_text_context_score(self):
        """Test calcul score contexte textuel"""
        image_context = ImageContext(
            bbox=(100, 200, 200, 300),
            page=0, area=10000, aspect_ratio=1.0,
            column=0, nearby_text=['section test titre'], distance_to_sections={}
        )
        section = Section("1", "Section Test", 0, 180)
        
        score = self.analyzer._calculate_text_context_score(image_context, section)
        
        # Devrait détecter "section" et "test" dans le texte autour
        assert score > 0.5  # 2 mots sur 2 trouvés
    
    def test_associate_image_to_section_best_match(self):
        """Test association image-section - meilleure correspondance"""
        image_context = ImageContext(
            bbox=(100, 200, 200, 300),
            page=0, area=10000, aspect_ratio=1.0,
            column=0, nearby_text=['test'], distance_to_sections={}
        )
        
        sections = [
            Section("1", "Section A", 0, 100),
            Section("2", "Section B", 0, 180),  # Plus proche
            Section("3", "Section C", 0, 300)
        ]
        
        layout = PageLayout(0, [], {}, [])
        
        with patch.object(self.analyzer, '_calculate_association_score') as mock_score:
            # Scores simulés
            mock_score.side_effect = [0.2, 0.8, 0.3]
            
            result = self.analyzer.associate_image_to_section(image_context, sections, layout)
        
        assert result is not None
        assert result.number == "2"  # Section avec le meilleur score
    
    def test_associate_image_to_section_fallback(self):
        """Test association image-section - fallback"""
        image_context = ImageContext(
            bbox=(100, 200, 200, 300),
            page=0, area=10000, aspect_ratio=1.0,
            column=0, nearby_text=[], distance_to_sections={}
        )
        
        sections = [
            Section("1", "Section A", 0, 100),
            Section("2", "Section B", 0, 180)
        ]
        
        layout = PageLayout(0, [], {}, [])
        
        with patch.object(self.analyzer, '_calculate_association_score', return_value=0.1):
            # Tous les scores trop bas, utilise fallback
            with patch.object(self.analyzer, '_find_fallback_section', return_value=sections[1]):
                result = self.analyzer.associate_image_to_section(image_context, sections, layout)
        
        assert result is not None
        assert result.number == "2" 