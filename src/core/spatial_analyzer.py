#!/usr/bin/env python3
"""
Spatial Analysis Module
========================
Analyse spatiale avancée pour l'association intelligente image-section
"""

import logging
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass
import fitz

from .section_detector import Section
from ..utils.exceptions import SectionDetectionError

@dataclass
class PageLayout:
    """Représente la mise en page d'une page"""
    page_num: int
    columns: List[Tuple[float, float]]  # (x_start, x_end) pour chaque colonne
    margins: Dict[str, float]  # top, bottom, left, right
    text_zones: List[Tuple[float, float, float, float]]  # (x0, y0, x1, y1)
    
@dataclass 
class ImageContext:
    """Contexte d'une image avec informations spatiales"""
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    page: int
    area: float
    aspect_ratio: float
    column: Optional[int]  # Colonne dans laquelle se trouve l'image
    nearby_text: List[str]  # Texte autour de l'image
    distance_to_sections: Dict[str, float]  # Distance aux sections

class SpatialAnalyzer:
    """Analyseur spatial pour association intelligente image-section"""
    
    def __init__(self, config: dict = None):
        self.config = self._merge_config(config or {})
        self.logger = logging.getLogger(__name__)
        
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
            'column_detection': {
                'min_gap_width': 20.0,  # Largeur minimale entre colonnes
                'text_threshold': 5,    # Minimum de lignes pour détecter colonne
            },
            'image_association': {
                'max_distance_pixels': 200.0,  # Distance max pour association
                'same_column_bonus': 0.5,      # Bonus si même colonne
                'text_context_radius': 50.0,   # Rayon pour chercher texte
            },
            'layout_analysis': {
                'margin_detection': True,
                'multi_column_support': True,
            }
        }
    
    def analyze_page_layout(self, page: fitz.Page) -> PageLayout:
        """Analyse la mise en page d'une page"""
        page_num = page.number
        
        # Analyser les zones de texte
        text_zones = self._extract_text_zones(page)
        
        # Détecter les colonnes
        columns = self._detect_columns(text_zones) if self.config['layout_analysis']['multi_column_support'] else []
        
        # Calculer les marges
        margins = self._calculate_margins(page, text_zones)
        
        layout = PageLayout(
            page_num=page_num,
            columns=columns,
            margins=margins,
            text_zones=text_zones
        )
        
        self.logger.debug(f"Layout page {page_num}: {len(columns)} colonnes, marges={margins}")
        return layout
    
    def _extract_text_zones(self, page: fitz.Page) -> List[Tuple[float, float, float, float]]:
        """Extrait les zones de texte de la page"""
        text_zones = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" in block and block["lines"]:
                bbox = block["bbox"]
                text_zones.append(bbox)
                
        return text_zones
    
    def _detect_columns(self, text_zones: List[Tuple[float, float, float, float]]) -> List[Tuple[float, float]]:
        """Détecte les colonnes dans la page"""
        if not text_zones:
            return []
        
        # Trier les zones par position X
        sorted_zones = sorted(text_zones, key=lambda z: z[0])
        
        # Grouper les zones par colonnes
        columns = []
        current_column_start = sorted_zones[0][0]
        current_column_end = sorted_zones[0][2]
        
        gap_threshold = self.config['column_detection']['min_gap_width']
        
        for zone in sorted_zones[1:]:
            zone_start, zone_end = zone[0], zone[2]
            
            # Si gap important, nouvelle colonne
            if zone_start - current_column_end > gap_threshold:
                columns.append((current_column_start, current_column_end))
                current_column_start = zone_start
                current_column_end = zone_end
            else:
                # Étendre la colonne courante
                current_column_end = max(current_column_end, zone_end)
        
        # Ajouter la dernière colonne
        columns.append((current_column_start, current_column_end))
        
        return columns
    
    def _calculate_margins(self, page: fitz.Page, text_zones: List[Tuple[float, float, float, float]]) -> Dict[str, float]:
        """Calcule les marges de la page"""
        if not text_zones:
            return {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
        
        page_rect = page.rect
        
        # Trouver les limites du contenu
        min_x = min(zone[0] for zone in text_zones)
        min_y = min(zone[1] for zone in text_zones)
        max_x = max(zone[2] for zone in text_zones)
        max_y = max(zone[3] for zone in text_zones)
        
        return {
            'left': min_x - page_rect.x0,
            'top': min_y - page_rect.y0,
            'right': page_rect.x1 - max_x,
            'bottom': page_rect.y1 - max_y
        }
    
    def create_image_context(self, image_bbox: Tuple[float, float, float, float], 
                           page: fitz.Page, layout: PageLayout) -> ImageContext:
        """Crée le contexte spatial d'une image"""
        x0, y0, x1, y1 = image_bbox
        
        # Calculer propriétés de l'image
        area = (x1 - x0) * (y1 - y0)
        aspect_ratio = (x1 - x0) / (y1 - y0) if y1 > y0 else 1.0
        
        # Déterminer la colonne
        column = self._find_image_column(image_bbox, layout.columns)
        
        # Extraire texte autour
        nearby_text = self._extract_nearby_text(page, image_bbox)
        
        return ImageContext(
            bbox=image_bbox,
            page=page.number,
            area=area,
            aspect_ratio=aspect_ratio,
            column=column,
            nearby_text=nearby_text,
            distance_to_sections={}
        )
    
    def _find_image_column(self, image_bbox: Tuple[float, float, float, float], 
                          columns: List[Tuple[float, float]]) -> Optional[int]:
        """Trouve dans quelle colonne se trouve l'image"""
        if not columns:
            return None
            
        image_center_x = (image_bbox[0] + image_bbox[2]) / 2
        
        for i, (col_start, col_end) in enumerate(columns):
            if col_start <= image_center_x <= col_end:
                return i
                
        return None
    
    def _extract_nearby_text(self, page: fitz.Page, image_bbox: Tuple[float, float, float, float]) -> List[str]:
        """Extrait le texte autour de l'image"""
        x0, y0, x1, y1 = image_bbox
        radius = self.config['image_association']['text_context_radius']
        
        # Zone élargie autour de l'image
        search_rect = fitz.Rect(x0 - radius, y0 - radius, x1 + radius, y1 + radius)
        
        try:
            # Extraire texte dans la zone
            text_dict = page.get_text("dict", clip=search_rect)
            nearby_text = []
            
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text and len(text) > 2:
                                nearby_text.append(text)
            
            return nearby_text[:10]  # Limiter à 10 éléments
            
        except Exception as e:
            self.logger.warning(f"Erreur extraction texte autour image: {e}")
            return []
    
    def associate_image_to_section(self, image_context: ImageContext, 
                                 sections: List[Section], 
                                 layout: PageLayout) -> Optional[Section]:
        """Association intelligente image-section avec analyse spatiale"""
        if not sections:
            return None
        
        # Calculer scores pour chaque section
        scores = {}
        
        for section in sections:
            score = self._calculate_association_score(image_context, section, layout)
            scores[section.number] = (score, section)
        
        # Prendre la section avec le meilleur score
        if scores:
            best_score, best_section = max(scores.values(), key=lambda x: x[0])
            
            # Seuil minimum pour association
            if best_score > 0.3:  # Ajustable
                self.logger.debug(f"Image associée à section {best_section.number} (score: {best_score:.2f})")
                return best_section
        
        # Fallback : dernière section précédente
        return self._find_fallback_section(image_context, sections)
    
    def _calculate_association_score(self, image_context: ImageContext, 
                                   section: Section, layout: PageLayout) -> float:
        """Calcule le score d'association entre une image et une section"""
        score = 0.0
        
        # 1. Distance spatiale (plus proche = meilleur)
        distance = self._calculate_spatial_distance(image_context, section)
        distance_score = max(0, 1.0 - distance / self.config['image_association']['max_distance_pixels'])
        score += distance_score * 0.4
        
        # 2. Même page bonus
        if image_context.page == section.page:
            score += 0.3
        
        # 3. Même colonne bonus
        if layout.columns and image_context.column is not None:
            section_column = self._find_section_column(section, layout.columns)
            if section_column == image_context.column:
                score += self.config['image_association']['same_column_bonus']
        
        # 4. Contexte textuel
        text_score = self._calculate_text_context_score(image_context, section)
        score += text_score * 0.2
        
        # Assurer que le score reste dans [0.0, 1.0]
        return min(1.0, max(0.0, score))
    
    def _calculate_spatial_distance(self, image_context: ImageContext, section: Section) -> float:
        """Calcule la distance spatiale entre image et section"""
        # Distance simple Y si même page
        if image_context.page == section.page:
            image_y = image_context.bbox[1]  # Top de l'image
            return abs(image_y - section.position_y)
        else:
            # Pénalité importante pour pages différentes
            page_diff = abs(image_context.page - section.page)
            return 1000.0 * page_diff
    
    def _find_section_column(self, section: Section, columns: List[Tuple[float, float]]) -> Optional[int]:
        """Trouve dans quelle colonne se trouve une section"""
        # Pour l'instant, suppose que les sections sont en colonne 0
        # Peut être amélioré en analysant la position X de la section
        return 0 if columns else None
    
    def _calculate_text_context_score(self, image_context: ImageContext, section: Section) -> float:
        """Calcule le score basé sur le contexte textuel"""
        # Rechercher mots-clés de la section dans le texte autour de l'image
        section_keywords = section.title.lower().split()
        nearby_text = " ".join(image_context.nearby_text).lower()
        
        matches = sum(1 for keyword in section_keywords if keyword in nearby_text)
        return matches / len(section_keywords) if section_keywords else 0.0
    
    def _find_fallback_section(self, image_context: ImageContext, sections: List[Section]) -> Optional[Section]:
        """Trouve une section de fallback (dernière section précédente)"""
        # Sections sur la même page ou précédentes
        candidate_sections = [
            s for s in sections 
            if s.page <= image_context.page
        ]
        
        if not candidate_sections:
            return None
        
        # Trier par page puis position Y
        candidate_sections.sort(key=lambda s: (s.page, s.position_y))
        
        # Sur la même page : dernière section avant l'image
        same_page = [s for s in candidate_sections if s.page == image_context.page]
        if same_page:
            image_y = image_context.bbox[1]
            valid_sections = [s for s in same_page if s.position_y <= image_y]
            if valid_sections:
                return valid_sections[-1]
        
        # Sinon, dernière section des pages précédentes
        return candidate_sections[-1] 