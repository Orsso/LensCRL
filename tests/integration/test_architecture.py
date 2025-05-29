#!/usr/bin/env python3
"""
Test d'intégration architecture modulaire
=========================================
"""

import pytest
import sys
from pathlib import Path

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.section_detector import SectionDetector, Section
from config.settings import ConfigManager
from utils.exceptions import LensCRLError, SectionDetectionError

class TestArchitectureIntegration:
    """Tests d'intégration pour l'architecture modulaire"""
    
    def test_section_detector_with_config_manager(self):
        """Test intégration SectionDetector + ConfigManager"""
        # Charger la configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Adapter la configuration pour le SectionDetector
        detector_config = {
            'font_size_range': config['detection']['formatting']['font_size_range'],
            'bold_required': config['detection']['formatting']['bold_required'],
            'title_min_length': config['detection']['formatting']['title_min_length'],
            'section_patterns': [p['pattern'] for p in config['detection']['section_patterns']]
        }
        
        # Créer le détecteur avec la configuration adaptée
        detector = SectionDetector(detector_config)
        
        # Vérifier que la configuration est bien appliquée
        assert detector.config['font_size_range'] == config['detection']['formatting']['font_size_range']
        assert detector.config['bold_required'] == config['detection']['formatting']['bold_required']
        
        # Vérifier les patterns de section
        patterns_from_config = [p['pattern'] for p in config['detection']['section_patterns']]
        assert detector.config['section_patterns'] == patterns_from_config
        
    def test_exception_hierarchy(self):
        """Test hiérarchie d'exceptions"""
        # Test que toutes les exceptions héritent de LensCRLError
        with pytest.raises(LensCRLError):
            raise SectionDetectionError("Test erreur détection")
            
        # Test avec contexte
        try:
            raise SectionDetectionError("Erreur avec contexte", {"page": 1, "section": "1.2"})
        except SectionDetectionError as e:
            assert str(e) == "Erreur avec contexte"
            assert e.context == {"page": 1, "section": "1.2"}
            
    def test_config_override_in_detector(self):
        """Test override de configuration dans le détecteur"""
        # Configuration personnalisée
        custom_config = {
            'font_size_range': [10.0, 20.0],
            'bold_required': False,
            'title_min_length': 3,
            'section_patterns': [r'^\d+$', r'^[A-Z]\d+$']
        }
        
        detector = SectionDetector(custom_config)
        
        # Test validation avec nouvelles règles
        format1 = {'is_bold': False, 'size': 15.0}  # bold_required = False
        format2 = {'is_bold': False, 'size': 15.0}
        
        # Doit accepter sans bold
        assert detector._is_valid_section_pattern("1", format1, "Test", format2)
        
        # Doit accepter titre court
        assert detector._is_valid_section_pattern("1", format1, "ABC", format2)
        
    def test_workspace_cleanliness(self):
        """Test que le workspace reste propre"""
        # Vérifier qu'aucun fichier temporaire n'est créé
        current_dir = Path(".")
        temp_files_before = list(current_dir.glob("*.tmp"))
        temp_files_before.extend(current_dir.glob("*~"))
        
        # Effectuer des opérations
        config_manager = ConfigManager()
        config = config_manager.load_config()
        detector = SectionDetector()
        
        # Vérifier qu'aucun nouveau fichier temporaire
        temp_files_after = list(current_dir.glob("*.tmp"))
        temp_files_after.extend(current_dir.glob("*~"))
        
        assert len(temp_files_after) == len(temp_files_before)
        
    def test_module_imports(self):
        """Test que tous les modules s'importent correctement"""
        # Test imports relatifs
        from core import section_detector
        from config import settings
        from utils import exceptions
        
        # Test classes disponibles
        assert hasattr(section_detector, 'SectionDetector')
        assert hasattr(section_detector, 'Section')
        assert hasattr(settings, 'ConfigManager')
        assert hasattr(exceptions, 'LensCRLError')
        
    def test_logging_integration(self):
        """Test intégration du logging"""
        import logging
        
        # Configurer logging selon config
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        logging_config = config['logging']
        
        # Créer détecteur avec logging
        detector = SectionDetector()
        
        # Vérifier que le logger est configuré
        assert detector.logger is not None
        assert detector.logger.name == "core.section_detector" 