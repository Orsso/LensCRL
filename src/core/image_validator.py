#!/usr/bin/env python3
"""
Image Validation Module
========================
Validation et filtrage d'images extraites
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import fitz

from ..utils.exceptions import ImageValidationError

class ImageType(Enum):
    """Types d'images détectés"""
    DIAGRAM = "diagram"
    CHART = "chart"
    PHOTO = "photo"
    LOGO = "logo"
    DECORATION = "decoration"
    TEXT_IMAGE = "text_image"
    UNKNOWN = "unknown"

class ValidationResult(Enum):
    """Résultats de validation"""
    VALID = "valid"
    INVALID_SIZE = "invalid_size"
    INVALID_ASPECT = "invalid_aspect"
    INVALID_CONTENT = "invalid_content"
    DUPLICATE = "duplicate"
    DECORATION = "decoration"

@dataclass
class ImageAnalysis:
    """Analyse d'une image"""
    image_type: ImageType
    confidence: float
    quality_score: float
    content_relevance: float
    validation_result: ValidationResult
    issues: List[str]

class ImageValidator:
    """Validateur pour filtrer et analyser les images extraites"""
    
    def __init__(self, config: dict = None):
        self.config = self._merge_config(config or {})
        self.logger = logging.getLogger(__name__)
        self._processed_hashes: set = set()  # Cache pour détecter doublons
        
    def _merge_config(self, user_config: dict) -> dict:
        """Fusionne la configuration utilisateur avec la configuration par défaut"""
        default_config = self._default_config()
        
        # Fusion récursive des dictionnaires
        def deep_merge(default: dict, user: dict) -> dict:
            result = default.copy()
            for key, value in user.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        return deep_merge(default_config, user_config)
    
    def _default_config(self) -> dict:
        """Configuration par défaut"""
        return {
            'size_constraints': {
                'min_width': 50,      # Largeur minimale en pixels
                'min_height': 50,     # Hauteur minimale en pixels
                'max_width': 2000,    # Largeur maximale en pixels
                'max_height': 2000,   # Hauteur maximale en pixels
                'min_area': 5000,     # Surface minimale
            },
            'aspect_ratio': {
                'min_ratio': 0.1,     # Ratio largeur/hauteur minimal
                'max_ratio': 10.0,    # Ratio largeur/hauteur maximal
            },
            'content_analysis': {
                'enable_duplicate_detection': True,
                'enable_decoration_filter': True,
                'min_complexity_score': 0.3,  # Score minimal de complexité
            },
            'quality_thresholds': {
                'min_quality_score': 0.5,
                'min_relevance_score': 0.4,
            }
        }
    
    def validate_image(self, image_bbox: Tuple[float, float, float, float], 
                      page: fitz.Page, context: dict = None) -> ImageAnalysis:
        """Valide une image et retourne l'analyse complète"""
        x0, y0, x1, y1 = image_bbox
        width = x1 - x0
        height = y1 - y0
        
        analysis = ImageAnalysis(
            image_type=ImageType.UNKNOWN,
            confidence=0.0,
            quality_score=0.0,
            content_relevance=0.0,
            validation_result=ValidationResult.VALID,
            issues=[]
        )
        
        # 1. Validation des dimensions
        size_valid, size_issues = self._validate_size(width, height)
        if not size_valid:
            analysis.validation_result = ValidationResult.INVALID_SIZE
            analysis.issues.extend(size_issues)
            return analysis
        
        # 2. Validation du ratio d'aspect
        aspect_ratio = width / height if height > 0 else float('inf')
        aspect_valid, aspect_issues = self._validate_aspect_ratio(aspect_ratio)
        if not aspect_valid:
            analysis.validation_result = ValidationResult.INVALID_ASPECT
            analysis.issues.extend(aspect_issues)
            return analysis
        
        # 3. Analyse du contenu
        content_analysis = self._analyze_image_content(image_bbox, page)
        analysis.image_type = content_analysis.get('type', ImageType.UNKNOWN)
        analysis.confidence = content_analysis.get('confidence', 0.0)
        analysis.quality_score = content_analysis.get('quality', 0.0)
        
        # 4. Détection de décorations/éléments non pertinents
        if self.config['content_analysis']['enable_decoration_filter']:
            if self._is_decoration(image_bbox, page, content_analysis):
                analysis.validation_result = ValidationResult.DECORATION
                analysis.issues.append("Image détectée comme élément décoratif")
                return analysis
        
        # 5. Détection de doublons
        if self.config['content_analysis']['enable_duplicate_detection']:
            image_hash = self._calculate_image_hash(image_bbox, page)
            if image_hash in self._processed_hashes:
                analysis.validation_result = ValidationResult.DUPLICATE
                analysis.issues.append("Image dupliquée détectée")
                return analysis
            self._processed_hashes.add(image_hash)
        
        # 6. Calcul de la pertinence du contenu
        analysis.content_relevance = self._calculate_content_relevance(
            image_bbox, page, context or {}
        )
        
        # 7. Validation finale basée sur les scores
        if analysis.quality_score < self.config['quality_thresholds']['min_quality_score']:
            analysis.validation_result = ValidationResult.INVALID_CONTENT
            analysis.issues.append(f"Score qualité trop bas: {analysis.quality_score:.2f}")
        
        if analysis.content_relevance < self.config['quality_thresholds']['min_relevance_score']:
            analysis.validation_result = ValidationResult.INVALID_CONTENT
            analysis.issues.append(f"Pertinence trop faible: {analysis.content_relevance:.2f}")
        
        self.logger.debug(f"Image validée: {analysis.validation_result.value}, "
                         f"type={analysis.image_type.value}, "
                         f"qualité={analysis.quality_score:.2f}")
        
        return analysis
    
    def _validate_size(self, width: float, height: float) -> Tuple[bool, List[str]]:
        """Valide les dimensions de l'image"""
        issues = []
        constraints = self.config['size_constraints']
        
        if width < constraints['min_width']:
            issues.append(f"Largeur trop petite: {width} < {constraints['min_width']}")
        
        if height < constraints['min_height']:
            issues.append(f"Hauteur trop petite: {height} < {constraints['min_height']}")
        
        if width > constraints['max_width']:
            issues.append(f"Largeur trop grande: {width} > {constraints['max_width']}")
        
        if height > constraints['max_height']:
            issues.append(f"Hauteur trop grande: {height} > {constraints['max_height']}")
        
        area = width * height
        if area < constraints['min_area']:
            issues.append(f"Surface trop petite: {area} < {constraints['min_area']}")
        
        return len(issues) == 0, issues
    
    def _validate_aspect_ratio(self, aspect_ratio: float) -> Tuple[bool, List[str]]:
        """Valide le ratio d'aspect de l'image"""
        issues = []
        constraints = self.config['aspect_ratio']
        
        if aspect_ratio < constraints['min_ratio']:
            issues.append(f"Ratio trop étroit: {aspect_ratio:.2f} < {constraints['min_ratio']}")
        
        if aspect_ratio > constraints['max_ratio']:
            issues.append(f"Ratio trop large: {aspect_ratio:.2f} > {constraints['max_ratio']}")
        
        return len(issues) == 0, issues
    
    def _analyze_image_content(self, image_bbox: Tuple[float, float, float, float], 
                              page: fitz.Page) -> Dict:
        """Analyse heuristique du contenu de l'image"""
        x0, y0, x1, y1 = image_bbox
        width = x1 - x0
        height = y1 - y0
        area = width * height
        aspect_ratio = width / height if height > 0 else 1.0
        
        # Heuristiques basées sur les propriétés géométriques
        confidence = 0.0
        image_type = ImageType.UNKNOWN
        quality_score = 0.5  # Score de base
        
        # Détecter d'abord les ratios extrêmes (probable décoration)
        if aspect_ratio > 4.0 or aspect_ratio < 0.25:
            image_type = ImageType.DECORATION
            confidence = 0.7
            quality_score = 0.2
        # Analyse par taille et ratio pour les autres cas
        elif area > 50000:  # Grande image
            if 0.5 <= aspect_ratio <= 2.0:
                image_type = ImageType.DIAGRAM
                confidence = 0.7
                quality_score = 0.8
            elif aspect_ratio > 2.0:
                image_type = ImageType.CHART
                confidence = 0.6
                quality_score = 0.7
        elif area > 10000:  # Image moyenne
            if 0.8 <= aspect_ratio <= 1.5:
                image_type = ImageType.PHOTO
                confidence = 0.6
                quality_score = 0.6
            else:
                image_type = ImageType.DIAGRAM
                confidence = 0.5
                quality_score = 0.6
        else:  # Petite image
            if aspect_ratio > 3.0 or aspect_ratio < 0.3:
                image_type = ImageType.DECORATION
                confidence = 0.7
                quality_score = 0.2
            else:
                image_type = ImageType.LOGO
                confidence = 0.4
                quality_score = 0.5
        
        # Ajustement basé sur la position
        page_height = page.rect.height
        relative_y = y0 / page_height
        
        # En-tête ou pied de page = probable logo/décoration
        if relative_y < 0.1 or relative_y > 0.9:
            if image_type not in [ImageType.DECORATION, ImageType.LOGO]:
                quality_score *= 0.7  # Pénalité
        
        return {
            'type': image_type,
            'confidence': confidence,
            'quality': quality_score,
            'area': area,
            'aspect_ratio': aspect_ratio
        }
    
    def _is_decoration(self, image_bbox: Tuple[float, float, float, float], 
                      page: fitz.Page, content_analysis: Dict) -> bool:
        """Détermine si l'image est décorative"""
        # Critères de décoration
        if content_analysis.get('type') == ImageType.DECORATION:
            return True
        
        # Très petites images avec ratio extrême
        area = content_analysis.get('area', 0)
        aspect_ratio = content_analysis.get('aspect_ratio', 1.0)
        
        if area < 5000 and (aspect_ratio > 5.0 or aspect_ratio < 0.2):
            return True
        
        # Position en marge
        x0, y0, x1, y1 = image_bbox
        page_width = page.rect.width
        page_height = page.rect.height
        
        margin_threshold = 0.05  # 5% de la page
        
        if (x0 < page_width * margin_threshold or 
            x1 > page_width * (1 - margin_threshold) or
            y0 < page_height * margin_threshold or 
            y1 > page_height * (1 - margin_threshold)):
            
            # Si en marge ET petite, probablement décoratif
            if area < 10000:
                return True
        
        return False
    
    def _calculate_image_hash(self, image_bbox: Tuple[float, float, float, float], 
                             page: fitz.Page) -> str:
        """Calcule un hash simple pour détecter les doublons"""
        # Hash basé sur taille et position relative
        x0, y0, x1, y1 = image_bbox
        width = x1 - x0
        height = y1 - y0
        
        # Position relative dans la page
        page_width = page.rect.width
        page_height = page.rect.height
        rel_x = x0 / page_width if page_width > 0 else 0
        rel_y = y0 / page_height if page_height > 0 else 0
        
        # Hash simple
        hash_str = f"{width:.0f}x{height:.0f}@{rel_x:.2f},{rel_y:.2f}"
        return hash_str
    
    def _calculate_content_relevance(self, image_bbox: Tuple[float, float, float, float], 
                                   page: fitz.Page, context: Dict) -> float:
        """Calcule la pertinence du contenu de l'image"""
        relevance = 0.5  # Score de base
        
        # Bonus si associée à une section
        if context.get('section'):
            relevance += 0.3
        
        # Bonus si proche de texte technique
        nearby_text = context.get('nearby_text', [])
        technical_keywords = [
            'figure', 'schéma', 'diagramme', 'graphique', 'tableau',
            'image', 'photo', 'illustration', 'annexe', 'exemple'
        ]
        
        for text in nearby_text:
            text_lower = text.lower()
            for keyword in technical_keywords:
                if keyword in text_lower:
                    relevance += 0.1
                    break
        
        # Pénalité si en zone de marge
        x0, y0, x1, y1 = image_bbox
        page_width = page.rect.width
        page_height = page.rect.height
        
        center_x = (x0 + x1) / 2
        center_y = (y0 + y1) / 2
        
        # Distance du centre de la page (normalisée)
        distance_from_center = abs(center_x - page_width/2) / (page_width/2)
        distance_from_center += abs(center_y - page_height/2) / (page_height/2)
        distance_from_center /= 2  # Moyenne
        
        # Pénalité progressive selon distance du centre
        relevance -= distance_from_center * 0.2
        
        return max(0.0, min(1.0, relevance))
    
    def filter_valid_images(self, image_bboxes: List[Tuple[float, float, float, float]], 
                           page: fitz.Page, context: dict = None) -> List[Tuple[Tuple[float, float, float, float], ImageAnalysis]]:
        """Filtre et retourne les images valides avec leur analyse"""
        valid_images = []
        
        for bbox in image_bboxes:
            analysis = self.validate_image(bbox, page, context)
            
            if analysis.validation_result == ValidationResult.VALID:
                valid_images.append((bbox, analysis))
            else:
                self.logger.debug(f"Image rejetée: {analysis.validation_result.value} - {analysis.issues}")
        
        self.logger.info(f"Images filtrées: {len(valid_images)}/{len(image_bboxes)} valides")
        return valid_images
    
    def reset_duplicate_cache(self):
        """Remet à zéro le cache de détection de doublons"""
        self._processed_hashes.clear()
        self.logger.debug("Cache de doublons réinitialisé") 