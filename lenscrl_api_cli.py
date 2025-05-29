#!/usr/bin/env python3
"""
LensCRL v3.0 - CLI avec API Backend
==================================

Interface en ligne de commande utilisant l'API Backend Phase 3.
Découplage complet entre interface et logique métier.
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Imports API
sys.path.insert(0, str(Path(__file__).parent / "src"))
from src.api.lenscrl_api import LensCRLAPI
from src.callbacks.progress_callbacks import ConsoleCallback, LoggingCallback, CompositeCallback
from src.models.api_models import OperationMode


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure le logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def cmd_analyze(args) -> int:
    """Commande d'analyse de document"""
    logger = setup_logging(args.verbose)
    
    # Callbacks
    callbacks = [ConsoleCallback(verbose=args.verbose)]
    if args.log_file:
        log_callback = LoggingCallback(logger)
        callbacks.append(log_callback)
    
    callback = CompositeCallback(callbacks)
    api = LensCRLAPI(callback=callback)
    
    # Analyse
    result = api.analyze_document(args.pdf, options=vars(args))
    
    # Affichage résultats
    if result.success:
        print(f"\n📊 ANALYSE COMPLÈTE")
        print(f"📄 Document: {result.document_info.file_path}")
        print(f"📋 Pages: {result.document_info.page_count}")
        print(f"📍 Sections: {len(result.sections_detected)}")
        print(f"🖼️ Images: {len(result.images_detected)}")
        print(f"⏱️ Temps: {result.processing_time:.2f}s")
        
        # Sauvegarde JSON si demandée
        if args.output_json:
            json_path = Path(args.output_json)
            json_path.write_text(result.to_json(), encoding='utf-8')
            print(f"💾 Analyse sauvée: {json_path}")
        
        return 0
    else:
        print(f"❌ Échec de l'analyse: {', '.join(result.errors)}")
        return 1


def cmd_preview(args) -> int:
    """Commande de preview d'extraction"""
    logger = setup_logging(args.verbose)
    
    callback = ConsoleCallback(verbose=args.verbose)
    api = LensCRLAPI(callback=callback)
    
    # Preview
    result = api.preview_extraction(
        args.pdf, 
        args.output,
        manual_name=args.manual,
        options=vars(args)
    )
    
    # Affichage résultats
    if result.analysis.success:
        print(f"\n🔍 PREVIEW D'EXTRACTION")
        print(f"📖 Manuel: {result.extraction_plan['manual_name']}")
        print(f"🖼️ Images à extraire: {len(result.preview_images)}")
        print(f"❌ Images rejetées: {len(result.rejected_images)}")
        print(f"📂 Taille estimée: {result.estimated_output_size / 1024:.1f} KB")
        print(f"⏱️ Durée estimée: {result.estimated_duration:.1f}s")
        
        # Détails par section
        plan = result.extraction_plan
        if plan['sections_with_images'] > 0:
            print(f"\n📋 RÉPARTITION PAR SECTION:")
            for section, count in plan['images_by_section'].items():
                print(f"  Section {section}: {count} image(s)")
        
        # Sauvegarde JSON si demandée
        if args.output_json:
            json_path = Path(args.output_json)
            json_path.write_text(result.to_json(), encoding='utf-8')
            print(f"💾 Preview sauvé: {json_path}")
        
        return 0
    else:
        print(f"❌ Échec du preview: {', '.join(result.analysis.errors)}")
        return 1


def cmd_extract(args) -> int:
    """Commande d'extraction complète"""
    logger = setup_logging(args.verbose)
    
    callback = ConsoleCallback(verbose=args.verbose)
    api = LensCRLAPI(callback=callback)
    
    # Extraction
    result = api.extract_images(
        args.pdf,
        args.output,
        manual_name=args.manual,
        options=vars(args)
    )
    
    # Affichage résultats
    if result.success:
        print(f"\n🎉 EXTRACTION TERMINÉE")
        print(f"📁 Répertoire: {result.output_directory}")
        print(f"🖼️ Images extraites: {len(result.extracted_files)}")
        print(f"📊 Sections avec images: {result.statistics['sections_with_images']}")
        print(f"💽 Taille totale: {result.statistics['output_size_bytes'] / 1024:.1f} KB")
        print(f"⏱️ Temps total: {result.processing_time:.2f}s")
        
        # Liste des fichiers créés
        if args.verbose:
            print(f"\n📄 FICHIERS CRÉÉS:")
            for file_info in result.extracted_files[:10]:  # Limiter à 10
                print(f"  • {file_info['filename']} (page {file_info['page']})")
            
            if len(result.extracted_files) > 10:
                print(f"  ... et {len(result.extracted_files) - 10} autres")
        
        # Sauvegarde JSON si demandée
        if args.output_json:
            json_path = Path(args.output_json)
            json_path.write_text(result.to_json(), encoding='utf-8')
            print(f"💾 Résultats sauvés: {json_path}")
        
        return 0
    else:
        print(f"❌ Échec de l'extraction: {', '.join(result.errors)}")
        return 1


def cmd_validate_config(args) -> int:
    """Commande de validation de configuration"""
    api = LensCRLAPI()
    
    # Charger la configuration
    try:
        if args.config.endswith('.json'):
            import json
            with open(args.config, 'r') as f:
                config = json.load(f)
        elif args.config.endswith('.yaml') or args.config.endswith('.yml'):
            import yaml
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)
        else:
            print(f"❌ Format de fichier non supporté: {args.config}")
            return 1
    except Exception as e:
        print(f"❌ Erreur lecture configuration: {e}")
        return 1
    
    # Validation
    result = api.validate_configuration(config)
    
    print(f"🔧 VALIDATION CONFIGURATION")
    print(f"✅ Valide: {result.is_valid}")
    
    if result.errors:
        print(f"\n❌ ERREURS ({len(result.errors)}):")
        for error in result.errors:
            print(f"  • {error}")
    
    if result.warnings:
        print(f"\n⚠️ AVERTISSEMENTS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  • {warning}")
    
    if result.suggestions:
        print(f"\n💡 SUGGESTIONS ({len(result.suggestions)}):")
        for suggestion in result.suggestions:
            print(f"  • {suggestion}")
    
    return 0 if result.is_valid else 1


def main():
    """Fonction principale CLI"""
    parser = argparse.ArgumentParser(
        description="LensCRL v3.0 - Extracteur d'images PDF avec API Backend",
        epilog="Utilise l'API Backend Phase 3 pour un découplage complet."
    )
    
    parser.add_argument('--version', action='version', version='LensCRL 3.0 (Phase 3)')
    parser.add_argument('--verbose', '-v', action='store_true', help="Mode verbeux")
    parser.add_argument('--log-file', help="Fichier de log")
    parser.add_argument('--output-json', help="Sauvegarder résultats en JSON")
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande analyze
    analyze_parser = subparsers.add_parser('analyze', help='Analyser un PDF sans extraction')
    analyze_parser.add_argument('pdf', help='Fichier PDF à analyser')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # Commande preview
    preview_parser = subparsers.add_parser('preview', help='Preview d\'extraction')
    preview_parser.add_argument('pdf', help='Fichier PDF')
    preview_parser.add_argument('output', help='Répertoire de sortie prévu')
    preview_parser.add_argument('--manual', '-m', help='Nom du manuel')
    preview_parser.set_defaults(func=cmd_preview)
    
    # Commande extract
    extract_parser = subparsers.add_parser('extract', help='Extraire les images')
    extract_parser.add_argument('pdf', help='Fichier PDF')
    extract_parser.add_argument('output', help='Répertoire de sortie')
    extract_parser.add_argument('--manual', '-m', help='Nom du manuel')
    extract_parser.set_defaults(func=cmd_extract)
    
    # Commande validate-config
    config_parser = subparsers.add_parser('validate-config', help='Valider une configuration')
    config_parser.add_argument('config', help='Fichier de configuration (.json ou .yaml)')
    config_parser.set_defaults(func=cmd_validate_config)
    
    # Parse et exécution
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n⏹️ Opération annulée par l'utilisateur")
        return 130
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 