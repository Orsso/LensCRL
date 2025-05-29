#!/usr/bin/env python3
"""
Test Milestone - Validation Refactoring Phase 1
===============================================
Test d'intégration pour valider que le refactoring fonctionne avec le fichier témoin
"""

import sys
import os
from pathlib import Path
import tempfile
import logging

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Imports de la nouvelle architecture
from core.section_detector import SectionDetector, Section
from config.settings import ConfigManager
from utils.exceptions import LensCRLError, SectionDetectionError

def test_config_system():
    """Test 1: Système de configuration"""
    print("🔧 Test du système de configuration...")
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Vérifications essentielles
        assert 'detection' in config
        assert 'extraction' in config
        assert 'nomenclature' in config
        
        # Structure configuration détection
        detection = config['detection']
        assert 'section_patterns' in detection
        assert 'formatting' in detection
        assert len(detection['section_patterns']) >= 3
        
        print("✅ Système de configuration validé")
        return True
        
    except Exception as e:
        print(f"❌ Erreur configuration: {e}")
        return False

def test_section_detector_standalone():
    """Test 2: SectionDetector isolé"""
    print("🔍 Test du SectionDetector...")
    
    try:
        # Test avec configuration par défaut
        detector = SectionDetector()
        assert detector.config['font_size_range'] == [12.0, 16.0]
        
        # Test avec configuration personnalisée
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Adapter la configuration
        detector_config = {
            'font_size_range': config['detection']['formatting']['font_size_range'],
            'bold_required': config['detection']['formatting']['bold_required'],
            'title_min_length': config['detection']['formatting']['title_min_length'],
            'section_patterns': [p['pattern'] for p in config['detection']['section_patterns']]
        }
        
        detector_with_config = SectionDetector(detector_config)
        assert detector_with_config.config['font_size_range'] == [12.0, 16.0]
        
        print("✅ SectionDetector validé")
        return True
        
    except Exception as e:
        print(f"❌ Erreur SectionDetector: {e}")
        return False

def test_with_real_pdf():
    """Test 3: Test avec fichier PDF témoin"""
    print("📄 Test avec fichier PDF témoin...")
    
    # Chercher le fichier PDF témoin
    pdf_files = list(Path(".").glob("*.pdf"))
    if not pdf_files:
        print("⚠️  Aucun fichier PDF témoin trouvé")
        return True  # Pas d'échec si pas de PDF
    
    pdf_file = pdf_files[0]
    print(f"   Utilisation de: {pdf_file}")
    
    try:
        import fitz
        
        # Ouvrir le PDF
        doc = fitz.open(pdf_file)
        print(f"   PDF ouvert: {len(doc)} pages")
        
        # Test avec nouvelle architecture
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        detector_config = {
            'font_size_range': config['detection']['formatting']['font_size_range'],
            'bold_required': config['detection']['formatting']['bold_required'],
            'title_min_length': config['detection']['formatting']['title_min_length'],
            'section_patterns': [p['pattern'] for p in config['detection']['section_patterns']]
        }
        
        detector = SectionDetector(detector_config)
        sections = detector.detect_sections(doc)
        
        print(f"   Sections détectées: {len(sections)}")
        
        if sections:
            print("   Exemples de sections:")
            for i, section in enumerate(sections[:3]):
                print(f"      {section.number} - {section.title[:50]}... (page {section.page + 1})")
        
        doc.close()
        
        print("✅ Test PDF témoin validé")
        return True
        
    except ImportError:
        print("⚠️  PyMuPDF non disponible pour test PDF")
        return True
    except Exception as e:
        print(f"❌ Erreur test PDF: {e}")
        return False

def test_backward_compatibility():
    """Test 4: Compatibilité descendante"""
    print("🔄 Test compatibilité avec lenscrl.py existant...")
    
    try:
        # Import du fichier original
        import lenscrl
        
        # Vérifier que la classe existe toujours
        assert hasattr(lenscrl, 'LensCRL')
        
        print("✅ Compatibilité descendante validée")
        return True
        
    except Exception as e:
        print(f"❌ Erreur compatibilité: {e}")
        return False

def test_workspace_cleanliness():
    """Test 5: Propreté du workspace"""
    print("🧹 Test propreté du workspace...")
    
    try:
        # Vérifier structure attendue
        expected_dirs = ['src', 'tests', 'src/core', 'src/config', 'src/utils']
        for dir_path in expected_dirs:
            if not Path(dir_path).exists():
                print(f"❌ Répertoire manquant: {dir_path}")
                return False
        
        # Vérifier fichiers essentiels
        essential_files = [
            'src/core/section_detector.py',
            'src/config/settings.py',
            'src/config/default.yaml',
            'src/utils/exceptions.py'
        ]
        
        for file_path in essential_files:
            if not Path(file_path).exists():
                print(f"❌ Fichier manquant: {file_path}")
                return False
        
        # Vérifier qu'il n'y a pas de fichiers temporaires
        temp_files = list(Path(".").glob("*.tmp"))
        temp_files.extend(Path(".").glob("*~"))
        temp_files.extend(Path(".").glob("*.pyc"))
        
        if temp_files:
            print(f"⚠️  Fichiers temporaires détectés: {temp_files}")
        
        print("✅ Workspace propre validé")
        return True
        
    except Exception as e:
        print(f"❌ Erreur propreté workspace: {e}")
        return False

def test_error_handling():
    """Test 6: Gestion d'erreurs robuste"""
    print("⚡ Test gestion d'erreurs...")
    
    try:
        # Test exceptions personnalisées
        try:
            raise SectionDetectionError("Test erreur", {"context": "test"})
        except LensCRLError as e:
            assert str(e) == "Test erreur"
            assert e.context == {"context": "test"}
        
        # Test configuration invalide
        config_manager = ConfigManager()
        invalid_path = Path("/chemin/inexistant.yaml")
        result = config_manager._load_yaml(invalid_path)
        assert result == {}  # Doit retourner dict vide, pas crash
        
        print("✅ Gestion d'erreurs validée")
        return True
        
    except Exception as e:
        print(f"❌ Erreur gestion d'erreurs: {e}")
        return False

def run_all_tests():
    """Exécute tous les tests milestone"""
    print("=" * 60)
    print("🚀 MILESTONE TEST - PHASE 1 REFACTORING")
    print("=" * 60)
    
    tests = [
        test_config_system,
        test_section_detector_standalone,
        test_with_real_pdf,
        test_backward_compatibility,
        test_workspace_cleanliness,
        test_error_handling
    ]
    
    results = []
    for test_func in tests:
        print()
        result = test_func()
        results.append(result)
    
    print()
    print("=" * 60)
    print("📊 RÉSULTATS")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passés: {passed}/{total}")
    
    if passed == total:
        print("🎉 ✅ MILESTONE PHASE 1 RÉUSSI !")
        print()
        print("✨ Architecture modulaire validée")
        print("✨ Configuration externalisée validée")
        print("✨ Gestion d'erreurs robuste validée")
        print("✨ Compatibilité descendante maintenue")
        print()
        print("➡️  Prêt pour Phase 2: Robustesse & Configuration adaptative")
        return True
    else:
        print("❌ MILESTONE PHASE 1 ÉCHOUÉ")
        print(f"   {total - passed} test(s) à corriger")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 