#!/usr/bin/env python3
"""
Tests unitaires pour le système de configuration
==============================================
"""

import pytest
import sys
import tempfile
import yaml
from pathlib import Path

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from config.settings import ConfigManager

class TestConfigManager:
    """Tests pour la classe ConfigManager"""
    
    def test_load_default_config(self):
        """Test chargement configuration par défaut"""
        manager = ConfigManager()
        config = manager.load_config()
        
        # Vérifications structure de base
        assert 'version' in config
        assert 'detection' in config
        assert 'extraction' in config
        assert 'nomenclature' in config
        assert 'logging' in config
        
        # Vérifications sections spécifiques
        assert 'section_patterns' in config['detection']
        assert 'formatting' in config['detection']
        assert 'image_filters' in config['extraction']
        assert 'prefix' in config['nomenclature']
        
    def test_config_structure(self):
        """Test structure détaillée de la configuration"""
        manager = ConfigManager()
        config = manager.load_config()
        
        # Test detection
        detection = config['detection']
        assert isinstance(detection['section_patterns'], list)
        assert len(detection['section_patterns']) >= 3
        assert isinstance(detection['formatting']['font_size_range'], list)
        assert len(detection['formatting']['font_size_range']) == 2
        
        # Test extraction
        extraction = config['extraction']
        assert extraction['image_filters']['min_width'] == 50
        assert extraction['image_filters']['min_height'] == 50
        assert isinstance(extraction['image_filters']['allowed_formats'], list)
        
        # Test nomenclature
        nomenclature = config['nomenclature']
        assert nomenclature['prefix'] == "CRL"
        assert nomenclature['separator'] == "-"
        
    def test_merge_configs(self):
        """Test fusion de configurations"""
        manager = ConfigManager()
        
        base_config = {
            'section1': {
                'key1': 'value1',
                'key2': 'value2'
            },
            'section2': 'value3'
        }
        
        override_config = {
            'section1': {
                'key2': 'new_value2',  # Override
                'key3': 'value3'       # Nouveau
            },
            'section3': 'value4'       # Nouvelle section
        }
        
        merged = manager._merge_configs(base_config, override_config)
        
        # Vérifications
        assert merged['section1']['key1'] == 'value1'  # Conservé
        assert merged['section1']['key2'] == 'new_value2'  # Overridé
        assert merged['section1']['key3'] == 'value3'  # Ajouté
        assert merged['section2'] == 'value3'  # Conservé
        assert merged['section3'] == 'value4'  # Ajouté
        
    def test_load_yaml_file(self):
        """Test chargement fichier YAML"""
        manager = ConfigManager()
        
        # Créer un fichier YAML temporaire
        test_config = {
            'test_section': {
                'test_key': 'test_value',
                'test_number': 42
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.safe_dump(test_config, f)
            temp_path = Path(f.name)
        
        try:
            loaded = manager._load_yaml(temp_path)
            assert loaded == test_config
        finally:
            temp_path.unlink()  # Nettoyer
            
    def test_load_yaml_error_handling(self):
        """Test gestion d'erreurs chargement YAML"""
        manager = ConfigManager()
        
        # Test fichier inexistant
        result = manager._load_yaml(Path("/fichier/inexistant.yaml"))
        assert result == {}
        
    def test_save_user_config(self):
        """Test sauvegarde configuration utilisateur"""
        manager = ConfigManager()
        
        test_config = {
            'detection': {
                'formatting': {
                    'font_size_range': [10.0, 18.0]
                }
            }
        }
        
        # Utiliser un répertoire temporaire pour le test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Modifier temporairement le chemin utilisateur
            original_path = manager.user_config_path
            manager.user_config_path = Path(temp_dir) / ".lenscrl" / "config.yaml"
            
            try:
                manager.save_user_config(test_config)
                
                # Vérifier que le fichier a été créé
                assert manager.user_config_path.exists()
                
                # Vérifier le contenu
                loaded = manager._load_yaml(manager.user_config_path)
                assert loaded == test_config
                
            finally:
                manager.user_config_path = original_path 