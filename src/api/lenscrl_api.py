#!/usr/bin/env python3
"""
API Backend LensCRL v2.0
========================

API principale pour découpler l'extraction d'images PDF de l'interface utilisateur.
Permet d'utiliser LensCRL depuis CLI, GUI, web ou autres interfaces.
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import fitz

# Imports des modules existants
from ..core.adaptive_detector import AdaptiveDetector
from ..core.image_validator import ImageValidator, ValidationResult
from ..core.spatial_analyzer import SpatialAnalyzer
from ..core.section_detector import Section
from ..config.settings import ConfigManager

# Imports API Phase 3
from ..models.api_models import (
    DocumentInfo, SectionInfo, ImageInfo, AnalysisResult, 
    PreviewResult, ExtractionResult, ConfigValidationResult,
    APIRequest, APIResponse, OperationMode, ProcessingStatus
)
from ..callbacks.progress_callbacks import ProgressCallback, ProgressTracker, LoggingCallback


class LensCRLAPI:
    """
    API Backend LensCRL
    =================
    
    Interface principale pour toutes les opérations LensCRL.
    Découplé des interfaces utilisateur pour maximum de flexibilité.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                 callback: Optional[ProgressCallback] = None):
        """
        Initialise l'API LensCRL
        
        Args:
            config: Configuration personnalisée (optionnel)
            callback: Callback pour suivi progression (optionnel)
        """
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config_manager = ConfigManager()
        if config:
            self.config_manager.update_config(config)
        
        # Chargement configuration Phase 2
        try:
            self.phase2_config = self.config_manager.load_yaml_config("src/config/phase2.yaml")
        except Exception as e:
            self.logger.warning(f"Impossible de charger config Phase 2: {e}")
            self.phase2_config = {}
        
        # Initialisation modules Phase 2
        self.adaptive_detector = AdaptiveDetector(self.phase2_config.get('adaptive_detection', {}))
        self.image_validator = ImageValidator(self.phase2_config.get('image_validation', {}))
        self.spatial_analyzer = SpatialAnalyzer(self.phase2_config.get('spatial_analysis', {}))
        
        # Callback système
        self.progress_callback = callback or LoggingCallback()
        self.progress_tracker = ProgressTracker(self.progress_callback)
        
        self.logger.info("LensCRL API v2.0 initialisée")
    
    def analyze_document(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Analyse un document PDF sans extraction
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            options: Options d'analyse (optionnel)
            
        Returns:
            AnalysisResult: Résultat de l'analyse complète
        """
        start_time = time.time()
        options = options or {}
        
        try:
            self.progress_tracker.start(4, f"Analyse du document {Path(pdf_path).name}")
            
            # 1. Vérification et ouverture du PDF
            self.progress_tracker.update("Ouverture du PDF", 0, 1)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"Fichier PDF non trouvé: {pdf_path}")
            
            doc = fitz.open(pdf_path)
            doc_info = self._extract_document_info(doc, pdf_path)
            self.progress_tracker.complete_step("Ouverture du PDF")
            
            # 2. Détection des sections
            self.progress_tracker.set_status(ProcessingStatus.DETECTING_SECTIONS)
            self.progress_tracker.update("Détection des sections", 0, doc_info.page_count)
            
            detected_sections = self._detect_sections(doc)
            sections_info = [self._section_to_info(s) for s in detected_sections]
            
            self.progress_tracker.update("Détection des sections", doc_info.page_count, doc_info.page_count, 
                                       sections_found=len(sections_info))
            self.progress_tracker.complete_step("Détection des sections")
            
            # 3. Détection des images
            self.progress_tracker.set_status(ProcessingStatus.VALIDATING_IMAGES)
            self.progress_tracker.update("Détection des images", 0, doc_info.page_count)
            
            detected_images = self._detect_images(doc)
            images_info = [self._image_to_info(img) for img in detected_images]
            
            self.progress_tracker.update("Détection des images", doc_info.page_count, doc_info.page_count,
                                       sections_found=len(sections_info), images_found=len(images_info))
            self.progress_tracker.complete_step("Détection des images")
            
            # 4. Calcul des statistiques
            self.progress_tracker.update("Calcul des statistiques")
            
            statistics = self._calculate_statistics(doc_info, sections_info, images_info)
            
            doc.close()
            processing_time = time.time() - start_time
            
            result = AnalysisResult(
                document_info=doc_info,
                sections_detected=sections_info,
                images_detected=images_info,
                statistics=statistics,
                processing_time=processing_time,
                timestamp="",  # Sera rempli automatiquement
                success=True
            )
            
            self.progress_tracker.complete_step("Calcul des statistiques")
            self.progress_tracker.complete(result)
            
            return result
            
        except Exception as e:
            self.progress_tracker.error(e, "Analyse du document")
            self.logger.error(f"Erreur lors de l'analyse: {e}")
            
            # Retourner un résultat d'erreur
            processing_time = time.time() - start_time
            return AnalysisResult(
                document_info=DocumentInfo(pdf_path, 0, 0),
                sections_detected=[],
                images_detected=[],
                statistics={},
                processing_time=processing_time,
                timestamp="",
                success=False,
                errors=[str(e)]
            )
    
    def preview_extraction(self, pdf_path: str, output_dir: str,
                          manual_name: Optional[str] = None,
                          options: Optional[Dict[str, Any]] = None) -> PreviewResult:
        """
        Preview d'extraction (analyse + validation sans extraction réelle)
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            output_dir: Répertoire de sortie prévu
            manual_name: Nom manuel (optionnel)
            options: Options de preview (optionnel)
            
        Returns:
            PreviewResult: Résultat du preview avec plan d'extraction
        """
        options = options or {}
        
        try:
            # 1. Analyse complète du document
            analysis = self.analyze_document(pdf_path, options)
            if not analysis.success:
                raise Exception(f"Échec de l'analyse: {', '.join(analysis.errors)}")
            
            # 2. Validation des images avec ImageValidator
            doc = fitz.open(pdf_path)
            
            preview_images = []
            rejected_images = []
            
            for image_info in analysis.images_detected:
                # Simuler la validation
                page = doc[image_info.page]
                validation_result = self.image_validator.validate_image(image_info.bbox, page)
                
                # Mettre à jour ImageInfo avec résultats validation
                updated_image = ImageInfo(
                    page=image_info.page,
                    bbox=image_info.bbox,
                    format=image_info.format,
                    size_bytes=image_info.size_bytes,
                    dimensions=image_info.dimensions,
                    quality_score=validation_result.quality_score,
                    image_type=validation_result.image_type.value,
                    validation_status=validation_result.validation_result.value,
                    issues=validation_result.issues
                )
                
                # Trier entre acceptées et rejetées
                if validation_result.validation_result in [
                    ValidationResult.INVALID_SIZE, ValidationResult.INVALID_ASPECT,
                    ValidationResult.INVALID_CONTENT, ValidationResult.DECORATION
                ]:
                    rejected_images.append(updated_image)
                elif validation_result.validation_result == ValidationResult.DUPLICATE:
                    rejected_images.append(updated_image)
                else:
                    preview_images.append(updated_image)
            
            doc.close()
            
            # 3. Créer le plan d'extraction
            extraction_plan = self._create_extraction_plan(
                preview_images, analysis.sections_detected, manual_name or self._deduce_manual_name(pdf_path)
            )
            
            # 4. Estimations
            estimated_output_size = sum(img.size_bytes for img in preview_images)
            estimated_duration = len(preview_images) * 0.1  # 0.1s par image estimée
            
            return PreviewResult(
                analysis=analysis,
                preview_images=preview_images,
                rejected_images=rejected_images,
                extraction_plan=extraction_plan,
                estimated_output_size=estimated_output_size,
                estimated_duration=estimated_duration
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors du preview: {e}")
            # Retourner un preview d'erreur
            error_analysis = AnalysisResult(
                document_info=DocumentInfo(pdf_path, 0, 0),
                sections_detected=[],
                images_detected=[],
                statistics={},
                processing_time=0.0,
                timestamp="",
                success=False,
                errors=[str(e)]
            )
            return PreviewResult(
                analysis=error_analysis,
                preview_images=[],
                rejected_images=[],
                extraction_plan={},
                estimated_output_size=0,
                estimated_duration=0.0
            )
    
    def extract_images(self, pdf_path: str, output_dir: str,
                      manual_name: Optional[str] = None,
                      options: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        """
        Extraction complète des images
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            output_dir: Répertoire de sortie
            manual_name: Nom manuel (optionnel)
            options: Options d'extraction (optionnel)
            
        Returns:
            ExtractionResult: Résultat de l'extraction complète
        """
        start_time = time.time()
        options = options or {}
        
        try:
            # 1. Preview pour valider
            preview = self.preview_extraction(pdf_path, output_dir, manual_name, options)
            if not preview.analysis.success:
                raise Exception("Échec du preview d'extraction")
            
            # 2. Créer le répertoire de sortie
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 3. Extraire les images réellement
            self.progress_tracker.start(len(preview.preview_images), "Extraction des images")
            self.progress_tracker.set_status(ProcessingStatus.EXTRACTING)
            
            extracted_files = []
            doc = fitz.open(pdf_path)
            
            counter_by_section = {}
            
            for i, image_info in enumerate(preview.preview_images):
                try:
                    # Extraire l'image
                    page = doc[image_info.page]
                    image_list = page.get_images()
                    
                    if i < len(image_list):
                        img = image_list[i]
                        xref = img[0]
                        image_doc = doc.extract_image(xref)
                        image_data = image_doc["image"]
                        extension = image_doc["ext"]
                        
                        # Déterminer la section
                        section_number = self._find_section_for_image(
                            image_info, preview.analysis.sections_detected
                        )
                        
                        # Compteur par section
                        if section_number not in counter_by_section:
                            counter_by_section[section_number] = 0
                        counter_by_section[section_number] += 1
                        
                        # Nom du fichier
                        manual = manual_name or self._deduce_manual_name(pdf_path)
                        if counter_by_section[section_number] == 1:
                            filename = f"CRL-{manual}-{section_number}.{extension}"
                        else:
                            filename = f"CRL-{manual}-{section_number} n_{counter_by_section[section_number]}.{extension}"
                        
                        # Sauvegarder
                        file_path = output_path / filename
                        with open(file_path, "wb") as f:
                            f.write(image_data)
                        
                        extracted_files.append({
                            'filename': filename,
                            'path': str(file_path),
                            'page': image_info.page + 1,
                            'section': section_number,
                            'size_bytes': len(image_data),
                            'quality_score': image_info.quality_score,
                            'image_type': image_info.image_type
                        })
                        
                        self.progress_tracker.update(
                            f"Extraction image {i+1}/{len(preview.preview_images)}",
                            pages_processed=i+1,
                            total_pages=len(preview.preview_images),
                            images_extracted=len(extracted_files)
                        )
                        
                except Exception as e:
                    self.progress_tracker.warning(f"Erreur extraction image {i}: {e}")
                    continue
            
            doc.close()
            
            # 4. Finaliser la nomenclature CRL
            self._finalize_crl_nomenclature(extracted_files, output_path)
            
            # 5. Statistiques finales
            processing_time = time.time() - start_time
            
            statistics = {
                'total_images_extracted': len(extracted_files),
                'total_images_rejected': len(preview.rejected_images),
                'sections_with_images': len(counter_by_section),
                'output_size_bytes': sum(f['size_bytes'] for f in extracted_files),
                'processing_time': processing_time,
                'images_by_section': counter_by_section
            }
            
            result = ExtractionResult(
                preview=preview,
                extracted_files=extracted_files,
                output_directory=str(output_path),
                statistics=statistics,
                processing_time=processing_time,
                timestamp="",
                success=True
            )
            
            self.progress_tracker.complete(result)
            return result
            
        except Exception as e:
            self.progress_tracker.error(e, "Extraction des images")
            self.logger.error(f"Erreur lors de l'extraction: {e}")
            
            # Retourner un résultat d'erreur
            processing_time = time.time() - start_time
            error_preview = PreviewResult(
                analysis=AnalysisResult(
                    document_info=DocumentInfo(pdf_path, 0, 0),
                    sections_detected=[],
                    images_detected=[],
                    statistics={},
                    processing_time=0.0,
                    timestamp="",
                    success=False,
                    errors=[str(e)]
                ),
                preview_images=[],
                rejected_images=[],
                extraction_plan={},
                estimated_output_size=0,
                estimated_duration=0.0
            )
            
            return ExtractionResult(
                preview=error_preview,
                extracted_files=[],
                output_directory=output_dir,
                statistics={},
                processing_time=processing_time,
                timestamp="",
                success=False,
                errors=[str(e)]
            )
    
    def validate_configuration(self, config: Dict[str, Any]) -> ConfigValidationResult:
        """
        Valide une configuration utilisateur
        
        Args:
            config: Configuration à valider
            
        Returns:
            ConfigValidationResult: Résultat de la validation
        """
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Validation de base
            if not isinstance(config, dict):
                errors.append("La configuration doit être un dictionnaire")
                return ConfigValidationResult(False, errors)
            
            # Validation des sections connues
            known_sections = ['adaptive_detection', 'image_validation', 'spatial_analysis', 'global']
            for section in config:
                if section not in known_sections:
                    warnings.append(f"Section inconnue dans la configuration: {section}")
                    suggestions.append(f"Sections valides: {', '.join(known_sections)}")
            
            # Validation spécifique par section
            if 'image_validation' in config:
                iv_config = config['image_validation']
                if 'size_constraints' in iv_config:
                    size_config = iv_config['size_constraints']
                    if 'min_width' in size_config and size_config['min_width'] < 10:
                        warnings.append("min_width très petit, risque d'inclure des artifacts")
                    if 'min_height' in size_config and size_config['min_height'] < 10:
                        warnings.append("min_height très petit, risque d'inclure des artifacts")
            
            # Configuration corrigée si nécessaire
            corrected_config = config.copy()
            
            return ConfigValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                corrected_config=corrected_config if warnings else None
            )
            
        except Exception as e:
            return ConfigValidationResult(
                is_valid=False,
                errors=[f"Erreur lors de la validation: {e}"]
            )
    
    # Méthodes utilitaires privées
    
    def _extract_document_info(self, doc: fitz.Document, pdf_path: str) -> DocumentInfo:
        """Extrait les informations du document PDF"""
        file_stat = os.stat(pdf_path)
        metadata = doc.metadata
        
        return DocumentInfo(
            file_path=pdf_path,
            file_size=file_stat.st_size,
            page_count=len(doc),
            creation_date=metadata.get('creationDate'),
            modification_date=metadata.get('modDate'),
            title=metadata.get('title'),
            author=metadata.get('author')
        )
    
    def _detect_sections(self, doc: fitz.Document) -> List[Section]:
        """Détecte les sections avec AdaptiveDetector"""
        try:
            return self.adaptive_detector.detect_sections_adaptive(doc)
        except Exception as e:
            self.logger.warning(f"Échec détection adaptative: {e}, fallback vers détection classique")
            # Fallback vers le détecteur classique
            try:
                from ..core.section_detector import SectionDetector
                classic_detector = SectionDetector()
                return classic_detector.detect_sections(doc)
            except Exception as e2:
                self.logger.error(f"Échec détection classique aussi: {e2}")
                return []
    
    def _detect_images(self, doc: fitz.Document) -> List[Dict]:
        """Détecte toutes les images du document"""
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    image_doc = doc.extract_image(xref)
                    
                    # Position de l'image
                    try:
                        image_rects = page.get_image_rects(xref)
                        bbox = image_rects[0] if image_rects else (0, 0, 100, 100)
                    except:
                        bbox = (0, img_index * 50, 100, 100 + img_index * 50)
                    
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    
                    images.append({
                        'page': page_num,
                        'bbox': bbox,
                        'format': image_doc["ext"],
                        'size_bytes': len(image_doc["image"]),
                        'dimensions': (width, height),
                        'xref': xref
                    })
                    
                except Exception as e:
                    self.logger.debug(f"Erreur détection image page {page_num}: {e}")
                    continue
        
        return images
    
    def _section_to_info(self, section: Section) -> SectionInfo:
        """Convertit Section vers SectionInfo"""
        # Créer une bbox approximative basée sur la position
        bbox = (0, section.position_y, 100, section.position_y + 20)
        
        return SectionInfo(
            number=section.number,
            title=section.title,
            page=section.page,
            bbox=bbox,
            confidence=0.9,  # Valeur par défaut
            font_size=14.0,  # Valeur par défaut
            is_bold=True,    # Valeur par défaut
            position_y=section.position_y
        )
    
    def _image_to_info(self, image_dict: Dict) -> ImageInfo:
        """Convertit dict image vers ImageInfo"""
        return ImageInfo(
            page=image_dict['page'],
            bbox=image_dict['bbox'],
            format=image_dict['format'],
            size_bytes=image_dict['size_bytes'],
            dimensions=image_dict['dimensions'],
            quality_score=0.7,  # Score par défaut, sera calculé lors de la validation
            image_type="unknown"
        )
    
    def _calculate_statistics(self, doc_info: DocumentInfo, 
                            sections: List[SectionInfo], 
                            images: List[ImageInfo]) -> Dict[str, Any]:
        """Calcule les statistiques d'analyse"""
        return {
            'document': {
                'pages': doc_info.page_count,
                'size_mb': doc_info.file_size / (1024 * 1024),
                'title': doc_info.title
            },
            'sections': {
                'total_detected': len(sections),
                'pages_with_sections': len(set(s.page for s in sections))
            },
            'images': {
                'total_detected': len(images),
                'pages_with_images': len(set(i.page for i in images)),
                'total_size_mb': sum(i.size_bytes for i in images) / (1024 * 1024),
                'formats': list(set(i.format for i in images))
            }
        }
    
    def _create_extraction_plan(self, images: List[ImageInfo], 
                              sections: List[SectionInfo], 
                              manual_name: str) -> Dict[str, Any]:
        """Crée un plan d'extraction détaillé"""
        sections_with_images = {}
        
        for image in images:
            section = self._find_section_for_image(image, sections)
            if section not in sections_with_images:
                sections_with_images[section] = []
            sections_with_images[section].append(image)
        
        return {
            'manual_name': manual_name,
            'total_images': len(images),
            'sections_with_images': len(sections_with_images),
            'images_by_section': {
                section: len(imgs) for section, imgs in sections_with_images.items()
            },
            'filename_preview': [
                f"CRL-{manual_name}-{section}-n_{i+1}.{img.format}"
                for section, imgs in sections_with_images.items()
                for i, img in enumerate(imgs)
            ][:10]  # Preview des 10 premiers noms
        }
    
    def _find_section_for_image(self, image: ImageInfo, sections: List[SectionInfo]) -> str:
        """Trouve la section correspondante à une image"""
        # Logique simplifiée - à améliorer avec SpatialAnalyzer
        image_y = image.bbox[1]
        
        # Chercher la section la plus proche avant l'image
        best_section = "0"  # Section par défaut
        for section in sections:
            if section.page <= image.page and section.position_y <= image_y:
                best_section = section.number
        
        return best_section
    
    def _deduce_manual_name(self, pdf_path: str) -> str:
        """Déduit le nom du manuel depuis le nom de fichier"""
        filename = Path(pdf_path).stem
        
        # Patterns d'extraction
        import re
        patterns = [
            r'^([A-Z]+\d+)',  # Ex: PROCSG02
            r'^([A-Z]{2,})',  # Ex: OMA, STC
            r'^(\w+?)[-_]',   # Premier segment avant - ou _
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                return match.group(1)
        
        return filename[:10].upper()  # Fallback
    
    def _finalize_crl_nomenclature(self, extracted_files: List[Dict], output_path: Path):
        """Finalise la nomenclature CRL selon les règles"""
        # Grouper par section
        sections = {}
        for file_info in extracted_files:
            section = file_info['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(file_info)
        
        # Renommer selon les règles CRL
        for section, files in sections.items():
            if len(files) == 1:
                # Une seule image : CRL-MANUAL-SECTION.ext
                file_info = files[0]
                old_path = Path(file_info['path'])
                new_name = f"CRL-{file_info['filename'].split('-')[1]}-{section}.{old_path.suffix[1:]}"
                new_path = output_path / new_name
                
                if old_path.exists() and old_path != new_path:
                    old_path.rename(new_path)
                    file_info['filename'] = new_name
                    file_info['path'] = str(new_path) 