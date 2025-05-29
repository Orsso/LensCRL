#!/usr/bin/env python3
"""
LensCRL Simple CLI
==================
Interface ligne de commande épurée pour extraction d'images PDF.
"""

import argparse
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.lenscrl_simple import LensCRLSimple


def main():
    parser = argparse.ArgumentParser(
        description="LensCRL Simple - Extraction d'images PDF avec nomenclature CRL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python lenscrl_simple_cli.py extract document.pdf output/
  python lenscrl_simple_cli.py extract document.pdf output/ --manual PROCSG02
  python lenscrl_simple_cli.py extract document.pdf output/ --debug
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande extract
    extract_parser = subparsers.add_parser('extract', help='Extraire les images')
    extract_parser.add_argument('pdf_path', help='Chemin vers le fichier PDF')
    extract_parser.add_argument('output_dir', help='Répertoire de sortie')
    extract_parser.add_argument('--manual', help='Nom du manuel (auto-détecté si non spécifié)')
    extract_parser.add_argument('--debug', action='store_true', help='Mode debug verbeux')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'extract':
        return extract_command(args)
    
    return 0


def extract_command(args):
    """Commande d'extraction"""
    
    # Vérifier que le PDF existe
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"❌ Erreur: Fichier PDF introuvable: {pdf_path}")
        return 1
    
    # Créer l'API
    api = LensCRLSimple(debug=args.debug)
    
    print(f"📄 PDF: {pdf_path}")
    print(f"📁 Sortie: {args.output_dir}")
    if args.manual:
        print(f"📚 Manuel: {args.manual}")
    print()
    
    try:
        # Extraction
        result = api.extract_images(
            pdf_path=str(pdf_path),
            output_dir=args.output_dir,
            manual_name=args.manual
        )
        
        if result.success:
            print("🎉 EXTRACTION RÉUSSIE!")
            print()
            print("📊 RÉSULTATS:")
            print(f"  • Images extraites: {len(result.images_extracted)}")
            print(f"  • Images filtrées: {len(result.images_filtered)}")  
            print(f"  • Sections détectées: {len(result.sections_detected)}")
            print(f"  • Temps de traitement: {result.stats['processing_time']:.2f}s")
            print()
            
            # Détail par section
            if result.stats['images_by_section']:
                print("📋 RÉPARTITION PAR SECTION:")
                for section, count in sorted(result.stats['images_by_section'].items()):
                    section_obj = next((s for s in result.sections_detected if s.number == section), None)
                    title = section_obj.title if section_obj else "Sans titre"
                    print(f"  • Section {section}: {count} image(s) - {title}")
                print()
            
            # Lister les fichiers créés
            if result.images_extracted:
                print("📂 FICHIERS CRÉÉS:")
                for img in result.images_extracted[:10]:  # Limiter à 10 pour lisibilité
                    print(f"  • {img['filename']} ({img['dimensions']}, {img['size_bytes']} bytes)")
                
                if len(result.images_extracted) > 10:
                    print(f"  ... et {len(result.images_extracted) - 10} autres fichiers")
                print()
            
            print(f"✅ Extraction terminée dans: {args.output_dir}")
            return 0
            
        else:
            print("❌ ÉCHEC DE L'EXTRACTION!")
            print()
            print("🔍 ERREURS:")
            for error in result.errors:
                print(f"  • {error}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Extraction interrompue par l'utilisateur")
        return 1
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 