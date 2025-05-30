#!/usr/bin/env python3
"""
LensCRL Simple API
==================
API épurée et robuste pour extraction d'images PDF avec nomenclature CRL.

Fonctionnalités essentielles :
1. Détection fiable des sections (sans sommaire)
2. Détection fiable des images
3. Attribution robuste image→section (dernière section précédente)
4. Filtrage simple mais efficace (logos, headers, doublons)
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import hashlib

# Try PyMuPDF first, fallback to pypdfium2 for cloud compatibility
PDF_BACKEND = None
try:
    import fitz
    PDF_BACKEND = "pymupdf"
except ImportError:
    try:
        import pypdfium2 as pdfium
        PDF_BACKEND = "pypdfium2"
    except ImportError:
        raise ImportError("Aucune bibliothèque PDF disponible. Installez PyMuPDF ou pypdfium2.")


@dataclass
class SimpleSection:
    """Section détectée - version simplifiée"""
    number: str
    title: str
    page: int
    position_y: float
    

@dataclass
class SimpleImage:
    """Image détectée - version simplifiée"""
    page: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    size_bytes: int
    width: int
    height: int
    format: str
    hash: str  # Pour détecter doublons


@dataclass
class ExtractionResult:
    """Résultat d'extraction simplifié"""
    images_extracted: List[Dict]
    images_filtered: List[Dict]
    sections_detected: List[SimpleSection]
    stats: Dict
    success: bool
    errors: List[str]


class LensCRLSimple:
    """API LensCRL simple et robuste"""
    
    def __init__(self, debug: bool = True):
        self.logger = logging.getLogger(__name__)
        
        # Configuration du logging spécifique à LensCRL seulement
        if debug:
            # Nettoyer les handlers existants pour éviter la duplication
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
            
            # Créer un handler console spécifique
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)  # INFO au lieu de DEBUG pour réduire le bruit
            
            # Format simplifié et propre
            formatter = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            
            # Configurer le logger LensCRL seulement
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)
            
            # Empêcher la propagation vers le logger racine
            self.logger.propagate = False
            
            # Réduire le niveau des autres loggers pour éviter le spam
            logging.getLogger("fitz").setLevel(logging.WARNING)
            logging.getLogger("pypdfium2").setLevel(logging.WARNING)
            logging.getLogger("PIL").setLevel(logging.WARNING)
            logging.getLogger("matplotlib").setLevel(logging.WARNING)
            
            # Supprimer les logs de système de fichiers/watchdog/etc
            for noisy_logger in ['watchdog', 'inotify', 'fsevents', 'polling', 'file_events']:
                logging.getLogger(noisy_logger).setLevel(logging.CRITICAL)
        else:
            self.logger.setLevel(logging.WARNING)
    
    def extract_images(self, pdf_path: str, output_dir: str, 
                      manual_name: Optional[str] = None,
                      prefix: str = "CRL") -> ExtractionResult:
        """
        Extraction complète : détection + filtrage + association + sauvegarde
        
        Args:
            pdf_path: Chemin vers le PDF
            output_dir: Répertoire de sortie  
            manual_name: Nom du manuel (auto-détecté si None)
            prefix: Préfixe pour la nomenclature (défaut: CRL)
            
        Returns:
            ExtractionResult: Résultat complet de l'extraction
        """
        start_time = time.time()
        
        try:
            # 1. Ouvrir le document
            doc = fitz.open(pdf_path)
            self.logger.info(f"Document ouvert: {len(doc)} pages")
            
            # 2. Détecter les sections
            sections = self._detect_sections_simple(doc)
            self.logger.info(f"Sections détectées: {len(sections)}")
            
            # 3. Détecter toutes les images
            all_images = self._detect_images_simple(doc)
            self.logger.info(f"Images brutes détectées: {len(all_images)}")
            
            # 4. Filtrer les images (logos, headers, doublons)
            filtered_images = self._filter_images_simple(all_images, doc)
            self.logger.info(f"Images après filtrage: {len(filtered_images)}")
            
            # 5. Associer images→sections
            associated_images = self._associate_images_simple(filtered_images, sections)
            
            # 6. Déduire nom du manuel
            if not manual_name:
                manual_name = self._deduce_manual_name(pdf_path)
            
            # 7. Extraire et sauvegarder avec compteur par section
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            extracted_files = []
            errors = []
            
            # Grouper images par section pour compteur séquentiel
            images_by_section = {}
            for img_info in associated_images:
                section = img_info['section']
                if section not in images_by_section:
                    images_by_section[section] = []
                images_by_section[section].append(img_info)
            
            # Traiter chaque section avec compteur
            for section, section_images in images_by_section.items():
                total_images_in_section = len(section_images)
                for counter, img_info in enumerate(section_images, 1):  # Commencer à 1
                    try:
                        file_info = self._save_image_simple(
                            doc, img_info, output_path, manual_name, 
                            counter, prefix, total_images_in_section
                        )
                        if file_info:
                            extracted_files.append(file_info)
                    except Exception as e:
                        error_msg = f"Erreur sauvegarde image page {img_info['page']}: {e}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
            
            # 8. Statistiques
            processing_time = time.time() - start_time
            stats = {
                'processing_time': processing_time,
                'pages_processed': len(doc),
                'sections_found': len(sections),
                'images_total': len(all_images),
                'images_filtered_out': len(all_images) - len(filtered_images),
                'images_extracted': len(extracted_files),
                'images_by_section': {}
            }
            
            # Grouper par section pour stats
            for img in extracted_files:
                section = img['section']
                stats['images_by_section'][section] = stats['images_by_section'].get(section, 0) + 1
            
            self.logger.info(f"Extraction terminée: {len(extracted_files)} images en {processing_time:.2f}s")
            
            # Fermer le document ici, après toutes les opérations
            doc.close()
            
            return ExtractionResult(
                images_extracted=extracted_files,
                images_filtered=[img for img in all_images if img not in filtered_images],
                sections_detected=sections,
                stats=stats,
                success=True,
                errors=errors
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction: {e}")
            return ExtractionResult(
                images_extracted=[],
                images_filtered=[],
                sections_detected=[],
                stats={'processing_time': time.time() - start_time},
                success=False,
                errors=[str(e)]
            )
    
    def _detect_sections_simple(self, doc: fitz.Document) -> List[SimpleSection]:
        """Détection simple et fiable des sections (ignore sommaire)"""
        sections = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Ignorer les premières pages (sommaire/table des matières)
            if page_num < 4:  # Pages 1-4 = couverture, blanc, sommaire, blanc
                continue
            
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        font_size = span["size"]
                        is_bold = "bold" in span["font"].lower()
                        
                        # Pattern de section : format X.Y.Z en gras, taille >= 11pt
                        if (is_bold and font_size >= 11.0 and 
                            self._is_real_section_pattern(text)):
                            
                            # Extraire le numéro de section
                            section_number = self._extract_section_number(text)
                            if section_number:
                                # Position Y du texte
                                bbox = span["bbox"]
                                position_y = bbox[1]
                                
                                # Chercher le titre sur la ligne suivante ou même ligne
                                title = self._find_section_title(text, line, block)
                                
                                section = SimpleSection(
                                    number=section_number,
                                    title=title,
                                    page=page_num,
                                    position_y=position_y
                                )
                                sections.append(section)
                                
                                self.logger.debug(f"Section trouvée: {section_number} '{title}' page {page_num + 1}")
        
        # Trier par page puis position Y
        sections.sort(key=lambda s: (s.page, s.position_y))
        
        # Filtrer les doublons proches
        filtered_sections = []
        for section in sections:
            duplicate = False
            for existing in filtered_sections:
                if (existing.page == section.page and 
                    abs(existing.position_y - section.position_y) < 10.0 and
                    existing.number == section.number):
                    duplicate = True
                    break
            
            if not duplicate:
                filtered_sections.append(section)
        
        return filtered_sections
    
    def _is_real_section_pattern(self, text: str) -> bool:
        """Vérifie si le texte correspond à un pattern de vraie section (pas sommaire)"""
        import re
        
        # Patterns de vraies sections (ignorant sommaire)
        real_patterns = [
            r'^\d+\.\d+\.\d+\s*$',      # 2.3.1, 2.4.3, etc. (seuls)
            r'^\d+\.\d+\.\d+\.\d+\s*$', # 2.4.3.1, etc. (seuls)
            r'^\d+\.\d+\s*$',           # 2.3, 2.4, etc. (seuls)
        ]
        
        for pattern in real_patterns:
            if re.match(pattern, text):
                return True
        return False
    
    def _extract_section_number(self, text: str) -> str:
        """Extrait le numéro de section du texte"""
        import re
        
        # Extraire le pattern numérique au début
        match = re.match(r'^(\d+(?:\.\d+)*)', text.strip())
        if match:
            return match.group(1)
        return ""
    
    def _find_section_title(self, section_text: str, current_line: dict, current_block: dict) -> str:
        """Trouve le titre associé à une section"""
        # Pour l'instant, retourner un titre générique
        # On pourrait améliorer en cherchant le texte en gras suivant
        section_num = self._extract_section_number(section_text)
        return f"Section {section_num}"
    
    def _detect_images_simple(self, doc: fitz.Document) -> List[SimpleImage]:
        """Détection simple et fiable des images"""
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img in image_list:
                try:
                    xref = img[0]
                    image_data = doc.extract_image(xref)
                    
                    # Obtenir bbox de l'image sur la page
                    image_rects = page.get_image_rects(xref)
                    if not image_rects:
                        continue
                    
                    bbox = image_rects[0]
                    width = int(bbox.width)
                    height = int(bbox.height)
                    
                    # Hash pour détecter doublons
                    image_hash = hashlib.md5(image_data["image"]).hexdigest()
                    
                    simple_image = SimpleImage(
                        page=page_num,
                        bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                        size_bytes=len(image_data["image"]),
                        width=width,
                        height=height,
                        format=image_data["ext"],
                        hash=image_hash
                    )
                    images.append(simple_image)
                    
                except Exception as e:
                    self.logger.warning(f"Erreur extraction image page {page_num + 1}: {e}")
                    continue
        
        return images
    
    def _filter_images_simple(self, images: List[SimpleImage], doc: fitz.Document) -> List[SimpleImage]:
        """Filtrage simple mais efficace"""
        filtered = []
        seen_hashes = set()
        
        for img in images:
            # 1. Filtrer doublons par hash
            if img.hash in seen_hashes:
                self.logger.debug(f"Doublon ignoré: hash {img.hash[:8]}")
                continue
            seen_hashes.add(img.hash)
            
            # 2. Filtrer par taille minimale
            if img.width < 50 or img.height < 50:
                self.logger.debug(f"Image trop petite ignorée: {img.width}x{img.height}")
                continue
            
            # 3. Filtrer les très petites en bytes (icônes)
            if img.size_bytes < 1000:  # < 1KB
                self.logger.debug(f"Image trop légère ignorée: {img.size_bytes} bytes")
                continue
            
            # 4. Filtrer headers/footers par position
            page_height = doc[img.page].rect.height
            y_ratio = img.bbox[1] / page_height  # Position Y relative
            
            if y_ratio < 0.1:  # 10% du haut (header)
                self.logger.debug(f"Header ignoré: position Y {y_ratio:.2%}")
                continue
                
            if y_ratio > 0.9:  # 10% du bas (footer)
                self.logger.debug(f"Footer ignoré: position Y {y_ratio:.2%}")
                continue
            
            # 5. Image garde
            filtered.append(img)
        
        return filtered
    
    def _associate_images_simple(self, images: List[SimpleImage], sections: List[SimpleSection]) -> List[Dict]:
        """Association simple et robuste image→section"""
        associated = []
        
        for img in images:
            # Trouver la dernière section précédente
            section = self._find_section_for_image(img, sections)
            
            img_info = {
                'image': img,
                'section': section.number if section else "0",
                'section_title': section.title if section else "Sans section",
                'page': img.page,
                'bbox': img.bbox
            }
            associated.append(img_info)
            
            self.logger.debug(f"Image page {img.page + 1} → Section {img_info['section']}")
        
        return associated
    
    def _find_section_for_image(self, image: SimpleImage, sections: List[SimpleSection]) -> Optional[SimpleSection]:
        """Trouve la section pour une image : dernière section précédente"""
        
        # 1. Sections sur la même page, avant l'image (position Y)
        same_page_sections = [s for s in sections 
                            if s.page == image.page and s.position_y < image.bbox[1]]
        if same_page_sections:
            # Prendre la dernière section qui est avant l'image sur la même page
            return max(same_page_sections, key=lambda s: s.position_y)
        
        # 2. Si aucune section sur la même page avant l'image,
        # chercher la dernière section des pages précédentes
        previous_pages = [s for s in sections if s.page < image.page]
        if previous_pages:
            return max(previous_pages, key=lambda s: (s.page, s.position_y))
        
        # 3. Fallback : première section du document
        # Si aucune section trouvée avant l'image
        return sections[0] if sections else None
    
    def _deduce_manual_name(self, pdf_path: str) -> str:
        """Déduit le nom du manuel depuis le footer, métadonnées puis nom de fichier"""
        
        # Tentative 1: Chercher dans les footers (priorité)
        try:
            if PDF_BACKEND == "pymupdf":
                doc = fitz.open(pdf_path)
                footer_name = self._extract_name_from_footer(doc)
                doc.close()
                if footer_name:
                    self.logger.info(f"Nom trouvé dans footer: {footer_name}")
                    return footer_name
        except Exception as e:
            self.logger.warning(f"Erreur extraction footer: {e}")
        
        # Tentative 2: Chercher dans les métadonnées PDF
        try:
            if PDF_BACKEND == "pymupdf":
                doc = fitz.open(pdf_path)
                metadata_name = self._extract_name_from_metadata(doc)
                doc.close()
                if metadata_name:
                    self.logger.info(f"Nom trouvé dans métadonnées: {metadata_name}")
                    return metadata_name
        except Exception as e:
            self.logger.warning(f"Erreur extraction métadonnées: {e}")
        
        # Tentative 3: Fallback - Nom de fichier (méthode actuelle)
        filename = Path(pdf_path).stem
        import re
        
        patterns = [
            r'^([A-Z]+\d+)',  # PROCSG02
            r'^([A-Z]{2,})',  # OMA, STC
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                filename_name = match.group(1)
                self.logger.info(f"Nom déduit du fichier: {filename_name}")
                return filename_name
        
        # Fallback final
        fallback_name = filename[:10].upper()
        self.logger.info(f"Nom fallback: {fallback_name}")
        return fallback_name
    
    def _extract_name_from_footer(self, doc: fitz.Document) -> Optional[str]:
        """Extrait le nom du manuel depuis les footers des pages"""
        import re
        
        # Analyser les 3 premières pages pour détecter les patterns de footer
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            page_height = page.rect.height
            
            # Zone footer : 10% du bas de la page
            footer_y_start = page_height * 0.9
            
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                
                # Vérifier si le block est dans la zone footer
                block_y = block["bbox"][1]
                if block_y < footer_y_start:
                    continue
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        
                        # Patterns pour les noms de manuels techniques
                        patterns = [
                            r'\b([A-Z]{2,}SG\d+)\b',      # PROCSG02, etc.
                            r'\b([A-Z]{3,}\d+)\b',        # General format
                            r'\b([A-Z]{2,}-[A-Z]{2,})\b', # Format avec tiret
                            r'\b([A-Z]{2,}/[A-Z]{2,})\b', # Format avec slash
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, text)
                            if match:
                                manual_name = match.group(1)
                                self.logger.debug(f"Nom candidat trouvé dans footer page {page_num + 1}: {manual_name}")
                                
                                # Valider que ce n'est pas un faux positif (dates, numéros de page, etc.)
                                if self._validate_manual_name(manual_name):
                                    return manual_name
        
        return None
    
    def _extract_name_from_metadata(self, doc: fitz.Document) -> Optional[str]:
        """Extrait le nom du manuel depuis les métadonnées PDF"""
        import re
        
        try:
            metadata = doc.metadata
            
            # Chercher dans le titre
            if metadata.get('title'):
                title = metadata['title'].strip()
                patterns = [
                    r'\b([A-Z]{2,}SG\d+)\b',
                    r'\b([A-Z]{3,}\d+)\b',
                    r'\b([A-Z]{2,}-[A-Z]{2,})\b',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, title)
                    if match:
                        manual_name = match.group(1)
                        if self._validate_manual_name(manual_name):
                            return manual_name
            
            # Chercher dans le sujet
            if metadata.get('subject'):
                subject = metadata['subject'].strip()
                patterns = [
                    r'\b([A-Z]{2,}SG\d+)\b',
                    r'\b([A-Z]{3,}\d+)\b',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, subject)
                    if match:
                        manual_name = match.group(1)
                        if self._validate_manual_name(manual_name):
                            return manual_name
        
        except Exception as e:
            self.logger.warning(f"Erreur lecture métadonnées: {e}")
        
        return None
    
    def _validate_manual_name(self, name: str) -> bool:
        """Valide qu'un nom candidat est vraiment un nom de manuel"""
        import re
        
        # Filtrer les faux positifs courants
        false_positives = [
            r'^\d{4}$',           # Années (2024, etc.)
            r'^PAGE\d*$',         # Numéros de page
            r'^REV\d*$',          # Révisions
            r'^VER\d*$',          # Versions
            r'^DOC\d*$',          # Documents génériques
            r'^\d{1,3}$',         # Numéros simples
        ]
        
        for fp_pattern in false_positives:
            if re.match(fp_pattern, name):
                return False
        
        # Critères de validation positifs
        if len(name) < 3 or len(name) > 15:
            return False
        
        # Doit contenir au moins une lettre et éventuellement des chiffres
        if not re.search(r'[A-Z]', name):
            return False
        
        return True
    
    def _save_image_simple(self, doc: fitz.Document, img_info: Dict, 
                          output_path: Path, manual_name: str, counter: int,
                          prefix: str = "CRL", total_images_in_section: int = 1) -> Optional[Dict]:
        """Sauvegarde simple d'une image avec nomenclature personnalisée"""
        try:
            img = img_info['image']
            page = doc[img.page]
            
            # Extraire l'image
            pix = page.get_pixmap(clip=fitz.Rect(img.bbox), dpi=300)
            
            if pix.width == 0 or pix.height == 0:
                return None
            
            # Nomenclature personnalisée: PREFIX-XXXX-X.X n_X.ext
            section = img_info['section']
            if total_images_in_section > 1:
                filename = f"{prefix}-{manual_name}-{section} n_{counter}.{img.format}"
            else:
                filename = f"{prefix}-{manual_name}-{section}.{img.format}"
            output_file = output_path / filename
            
            # Sauvegarder
            if img.format.lower() in ['jpg', 'jpeg']:
                pix.save(str(output_file), output="jpeg")
            else:
                pix.save(str(output_file), output="png")
            
            self.logger.debug(f"Image sauvée: {filename}")
            
            return {
                'filename': filename,
                'path': str(output_file),
                'section': section,
                'page': img.page + 1,
                'size_bytes': output_file.stat().st_size,
                'dimensions': f"{pix.width}x{pix.height}",
                'counter': counter
            }
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde image: {e}")
            return None


# Interface simple pour tests
if __name__ == "__main__":
    api = LensCRLSimple(debug=True)
    
    # Test simple
    import sys
    if len(sys.argv) >= 3:
        pdf_path = sys.argv[1] 
        output_dir = sys.argv[2]
        manual_name = sys.argv[3] if len(sys.argv) > 3 else None
        
        result = api.extract_images(pdf_path, output_dir, manual_name)
        
        if result.success:
            print(f"✅ Extraction réussie: {len(result.images_extracted)} images")
            print(f"📊 Stats: {result.stats}")
        else:
            print(f"❌ Échec: {result.errors}")
    else:
        print("Usage: python lenscrl_simple.py <pdf_path> <output_dir> [manual_name]") 