#!/usr/bin/env python3
"""
Test API Phase 3 - LensCRL Backend
=================================

Test simple pour valider l'API backend nouvellement créée.
"""

import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.lenscrl_api import LensCRLAPI
from src.callbacks.progress_callbacks import ConsoleCallback
from src.models.api_models import OperationMode

def test_api_analyze():
    """Test de la fonction analyze_document"""
    print("\n🧪 TEST 1: Analyse de document")
    print("=" * 50)
    
    # Initialiser l'API avec callback console
    callback = ConsoleCallback(verbose=True)
    api = LensCRLAPI(callback=callback)
    
    # Test avec le PDF témoin
    pdf_path = "PROCSG02-SVC-SG_2025-04-15_17-00 (1).pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF témoin non trouvé: {pdf_path}")
        return False
    
    try:
        # Analyser le document
        result = api.analyze_document(pdf_path)
        
        print(f"\n📊 RÉSULTATS ANALYSE:")
        print(f"✅ Succès: {result.success}")
        print(f"📄 Pages: {result.document_info.page_count}")
        print(f"📋 Sections détectées: {len(result.sections_detected)}")
        print(f"🖼️ Images détectées: {len(result.images_detected)}")
        print(f"⏱️ Temps de traitement: {result.processing_time:.2f}s")
        
        if result.errors:
            print(f"❌ Erreurs: {result.errors}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        return False

def test_api_preview():
    """Test de la fonction preview_extraction"""
    print("\n🧪 TEST 2: Preview d'extraction")
    print("=" * 50)
    
    # Initialiser l'API
    api = LensCRLAPI()
    
    pdf_path = "PROCSG02-SVC-SG_2025-04-15_17-00 (1).pdf"
    output_dir = "test_api_output"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF témoin non trouvé: {pdf_path}")
        return False
    
    try:
        # Preview d'extraction
        result = api.preview_extraction(pdf_path, output_dir)
        
        print(f"\n📊 RÉSULTATS PREVIEW:")
        print(f"✅ Succès analyse: {result.analysis.success}")
        print(f"🖼️ Images à extraire: {len(result.preview_images)}")
        print(f"❌ Images rejetées: {len(result.rejected_images)}")
        print(f"📂 Taille estimée: {result.estimated_output_size / 1024:.1f} KB")
        print(f"⏱️ Durée estimée: {result.estimated_duration:.1f}s")
        
        # Afficher plan d'extraction
        plan = result.extraction_plan
        print(f"\n📋 PLAN D'EXTRACTION:")
        print(f"📖 Manuel: {plan['manual_name']}")
        print(f"📁 Sections avec images: {plan['sections_with_images']}")
        
        return result.analysis.success
        
    except Exception as e:
        print(f"❌ Erreur lors du preview: {e}")
        return False

def test_api_config_validation():
    """Test de validation de configuration"""
    print("\n🧪 TEST 3: Validation de configuration")
    print("=" * 50)
    
    api = LensCRLAPI()
    
    # Test avec configuration valide
    valid_config = {
        'image_validation': {
            'size_constraints': {
                'min_width': 50,
                'min_height': 50
            }
        },
        'adaptive_detection': {
            'enable_adaptive_thresholds': True
        }
    }
    
    result = api.validate_configuration(valid_config)
    
    print(f"📊 VALIDATION CONFIG VALIDE:")
    print(f"✅ Valide: {result.is_valid}")
    print(f"❌ Erreurs: {len(result.errors)}")
    print(f"⚠️ Avertissements: {len(result.warnings)}")
    
    # Test avec configuration invalide
    invalid_config = {
        'unknown_section': {},
        'image_validation': {
            'size_constraints': {
                'min_width': 5  # Très petit
            }
        }
    }
    
    result2 = api.validate_configuration(invalid_config)
    
    print(f"\n📊 VALIDATION CONFIG INVALIDE:")
    print(f"✅ Valide: {result2.is_valid}")
    print(f"❌ Erreurs: {len(result2.errors)}")
    print(f"⚠️ Avertissements: {len(result2.warnings)}")
    if result2.warnings:
        print(f"   {result2.warnings[0]}")
    
    return True

def test_api_json_serialization():
    """Test de sérialisation JSON"""
    print("\n🧪 TEST 4: Sérialisation JSON")
    print("=" * 50)
    
    api = LensCRLAPI()
    pdf_path = "PROCSG02-SVC-SG_2025-04-15_17-00 (1).pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF témoin non trouvé: {pdf_path}")
        return False
    
    try:
        # Analyser et sérialiser
        result = api.analyze_document(pdf_path)
        json_str = result.to_json()
        
        print(f"📊 SÉRIALISATION JSON:")
        print(f"✅ JSON généré: {len(json_str)} caractères")
        print(f"📄 Début JSON: {json_str[:200]}...")
        
        # Vérifier que c'est du JSON valide
        import json
        parsed = json.loads(json_str)
        print(f"✅ JSON valide parsé avec {len(parsed)} clés")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur sérialisation: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 TESTS API PHASE 3 - LENSCRL BACKEND")
    print("=" * 60)
    
    tests = [
        test_api_analyze,
        test_api_preview,
        test_api_config_validation,
        test_api_json_serialization
    ]
    
    results = []
    
    for test_func in tests:
        try:
            success = test_func()
            results.append(success)
        except Exception as e:
            print(f"❌ Erreur test {test_func.__name__}: {e}")
            results.append(False)
    
    # Résumé
    print("\n🎯 RÉSUMÉ DES TESTS")
    print("=" * 30)
    print(f"✅ Tests réussis: {sum(results)}/{len(results)}")
    print(f"❌ Tests échoués: {len(results) - sum(results)}/{len(results)}")
    
    if all(results):
        print("\n🎉 TOUS LES TESTS PASSENT ! API Phase 3 fonctionnelle !")
    else:
        print("\n⚠️ Certains tests ont échoué. Vérification nécessaire.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 