#!/usr/bin/env python3
"""
Adaptive Detection Module
==========================
Détection adaptative de sections avec apprentissage de patterns
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
import fitz

from .section_detector import Section, SectionDetector
from ..utils.exceptions import SectionDetectionError

@dataclass
class DocumentPattern:
    """Pattern détecté dans le document"""
    font_sizes: List[float]
    font_names: Set[str]
    formatting_styles: Set[str]  # bold, italic, etc.
    numbering_patterns: List[str]
    section_gaps: List[float]  # Espaces entre sections
    confidence: float

@dataclass
class SectionCandidate:
    """Candidat pour être une section"""
    text: str
    font_size: float
    font_name: str
    is_bold: bool
    is_italic: bool
    position_x: float
    position_y: float
    page: int
    confidence_score: float
    detected_pattern: Optional[str] = None

class AdaptiveDetector:
    """Détecteur adaptatif qui apprend les patterns du document"""
    
    def __init__(self, config: dict = None):
        self.config = self._merge_config(config or {})
        self.logger = logging.getLogger(__name__)
        self.learned_patterns: Optional[DocumentPattern] = None
        self.section_detector = SectionDetector(config)
        
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
            'pattern_learning': {
                'min_samples': 3,           # Échantillons min pour apprendre
                'confidence_threshold': 0.7, # Seuil de confiance
                'adaptation_enabled': True,
            },
            'adaptive_thresholds': {
                'font_size_tolerance': 2.0,  # Tolérance adaptative
                'position_tolerance': 10.0,  # Tolérance position
                'frequency_threshold': 0.3,  # Seuil fréquence patterns
            },
            'candidate_filtering': {
                'min_confidence': 0.5,
                'max_candidates_per_page': 10,
                'text_length_range': [5, 200],
            }
        }
    
    def analyze_document_structure(self, pdf_doc: fitz.Document) -> DocumentPattern:
        """Analyse la structure globale du document pour détecter les patterns"""
        self.logger.info("Analyse de la structure du document...")
        
        # Collecter tous les candidats potentiels
        all_candidates = []
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            candidates = self._extract_section_candidates(page)
            all_candidates.extend(candidates)
        
        # Analyser les patterns
        pattern = self._learn_patterns_from_candidates(all_candidates)
        
        # Stocker les patterns appris
        self.learned_patterns = pattern
        
        self.logger.info(f"Patterns détectés - Tailles: {pattern.font_sizes}, "
                        f"Styles: {pattern.formatting_styles}, "
                        f"Confiance: {pattern.confidence:.2f}")
        
        return pattern
    
    def _extract_section_candidates(self, page: fitz.Page) -> List[SectionCandidate]:
        """Extrait les candidats sections d'une page"""
        candidates = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    
                    # Filtres de base
                    if not self._is_potential_section_text(text):
                        continue
                    
                    # Extraire propriétés typographiques
                    font_size = span.get("size", 0.0)
                    font_name = span.get("font", "")
                    flags = span.get("flags", 0)
                    
                    is_bold = bool(flags & 2**4)  # Flag bold
                    is_italic = bool(flags & 2**1)  # Flag italic
                    
                    bbox = span["bbox"]
                    position_x = bbox[0]
                    position_y = bbox[1]
                    
                    # Score de confiance initial
                    confidence = self._calculate_initial_confidence(
                        text, font_size, is_bold, position_x
                    )
                    
                    candidate = SectionCandidate(
                        text=text,
                        font_size=font_size,
                        font_name=font_name,
                        is_bold=is_bold,
                        is_italic=is_italic,
                        position_x=position_x,
                        position_y=position_y,
                        page=page.number,
                        confidence_score=confidence
                    )
                    
                    candidates.append(candidate)
        
        # Filtrer et trier les candidats
        valid_candidates = [
            c for c in candidates 
            if c.confidence_score >= self.config['candidate_filtering']['min_confidence']
        ]
        
        # Limiter le nombre par page
        max_candidates = self.config['candidate_filtering']['max_candidates_per_page']
        valid_candidates.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return valid_candidates[:max_candidates]
    
    def _is_potential_section_text(self, text: str) -> bool:
        """Vérifie si le texte peut être une section"""
        if not text:
            return False
        
        length_range = self.config['candidate_filtering']['text_length_range']
        if not (length_range[0] <= len(text) <= length_range[1]):
            return False
        
        # Patterns de sections typiques
        section_patterns = [
            r'^\d+\..*',              # "1. Titre"
            r'^\d+\.\d+.*',           # "1.1 Titre"
            r'^\d+\.\d+\.\d+.*',      # "1.1.1 Titre"
            r'^[A-Z][a-z]+.*',        # "Annexe", "Conclusion"
            r'^[IVX]+\..*',           # "I. Titre" (chiffres romains)
            r'^[A-Z]\..*',            # "A. Titre"
            r'.*ANNEXE.*',            # Annexes
            r'.*CONCLUSION.*',        # Conclusions
        ]
        
        text_upper = text.upper()
        
        # Vérifier contre les patterns
        for pattern in section_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Mots-clés de sections
        section_keywords = [
            'OBJECTIF', 'DOMAINE', 'INTRODUCTION', 'CONTEXTE',
            'ANNEXE', 'CONCLUSION', 'RÉSUMÉ', 'SOMMAIRE',
            'CHAPITRE', 'SECTION', 'PARTIE'
        ]
        
        for keyword in section_keywords:
            if keyword in text_upper:
                return True
        
        return False
    
    def _calculate_initial_confidence(self, text: str, font_size: float, 
                                    is_bold: bool, position_x: float) -> float:
        """Calcule la confiance initiale d'un candidat"""
        confidence = 0.0
        
        # Bonus pour la taille de police
        if font_size >= 12.0:
            confidence += 0.3
        if font_size >= 14.0:
            confidence += 0.2
        
        # Bonus pour le gras
        if is_bold:
            confidence += 0.3
        
        # Bonus pour la position (alignement gauche)
        if position_x < 100:  # Proche du bord gauche
            confidence += 0.2
        
        # Bonus pour les patterns de numérotation
        if re.match(r'^\d+\.', text):
            confidence += 0.3
        elif re.match(r'^\d+\.\d+', text):
            confidence += 0.4
        
        # Bonus pour les mots-clés
        text_upper = text.upper()
        if any(keyword in text_upper for keyword in ['ANNEXE', 'CONCLUSION', 'OBJECTIF']):
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def _learn_patterns_from_candidates(self, candidates: List[SectionCandidate]) -> DocumentPattern:
        """Apprend les patterns à partir des candidats"""
        if not candidates:
            return DocumentPattern(
                font_sizes=[], font_names=set(), formatting_styles=set(),
                numbering_patterns=[], section_gaps=[], confidence=0.0
            )
        
        # Analyser les tailles de police les plus fréquentes
        font_sizes = [c.font_size for c in candidates if c.confidence_score > 0.6]
        font_size_counter = Counter(font_sizes)
        
        # Garder les tailles les plus fréquentes
        common_sizes = [size for size, count in font_size_counter.most_common(3)]
        
        # Analyser les styles de formatage
        formatting_styles = set()
        for candidate in candidates:
            if candidate.is_bold:
                formatting_styles.add('bold')
            if candidate.is_italic:
                formatting_styles.add('italic')
        
        # Analyser les patterns de numérotation
        numbering_patterns = []
        for candidate in candidates:
            text = candidate.text
            if re.match(r'^\d+\.', text):
                numbering_patterns.append('numeric')
            elif re.match(r'^\d+\.\d+', text):
                numbering_patterns.append('hierarchical')
            elif re.match(r'^[IVX]+\.', text):
                numbering_patterns.append('roman')
            elif re.match(r'^[A-Z]\.', text):
                numbering_patterns.append('alphabetic')
        
        # Calculer la confiance globale
        confidence = self._calculate_pattern_confidence(candidates, common_sizes, formatting_styles)
        
        return DocumentPattern(
            font_sizes=common_sizes,
            font_names=set(c.font_name for c in candidates),
            formatting_styles=formatting_styles,
            numbering_patterns=list(set(numbering_patterns)),
            section_gaps=[],  # À implémenter si nécessaire
            confidence=confidence
        )
    
    def _calculate_pattern_confidence(self, candidates: List[SectionCandidate], 
                                    common_sizes: List[float], 
                                    formatting_styles: Set[str]) -> float:
        """Calcule la confiance des patterns détectés"""
        if not candidates:
            return 0.0
        
        confidence = 0.0
        
        # Confiance basée sur la cohérence des tailles
        if common_sizes:
            size_consistency = len(common_sizes) / len(set(c.font_size for c in candidates))
            confidence += size_consistency * 0.4
        
        # Confiance basée sur le formatage cohérent
        if 'bold' in formatting_styles:
            bold_ratio = sum(1 for c in candidates if c.is_bold) / len(candidates)
            confidence += bold_ratio * 0.3
        
        # Confiance basée sur la qualité moyenne des candidats
        avg_candidate_confidence = sum(c.confidence_score for c in candidates) / len(candidates)
        confidence += avg_candidate_confidence * 0.3
        
        return min(1.0, confidence)
    
    def detect_sections_adaptive(self, pdf_doc: fitz.Document) -> List[Section]:
        """Détection adaptative de sections"""
        # Première passe : analyse de structure
        if self.config['pattern_learning']['adaptation_enabled']:
            document_pattern = self.analyze_document_structure(pdf_doc)
        else:
            document_pattern = None
        
        # Adapter la configuration du détecteur de base
        if document_pattern and document_pattern.confidence > self.config['pattern_learning']['confidence_threshold']:
            self._adapt_detector_config(document_pattern)
        
        # Deuxième passe : détection avec configuration adaptée
        sections = self.section_detector.detect_sections(pdf_doc)
        
        # Troisième passe : raffinement avec les candidats adaptatifs
        if document_pattern:
            additional_sections = self._detect_additional_sections(pdf_doc, sections, document_pattern)
            sections.extend(additional_sections)
        
        # Tri et déduplication
        sections = self._deduplicate_and_sort_sections(sections)
        
        self.logger.info(f"Détection adaptative terminée: {len(sections)} sections trouvées")
        return sections
    
    def _adapt_detector_config(self, pattern: DocumentPattern):
        """Adapte la configuration du détecteur basée sur les patterns appris"""
        if not pattern.font_sizes:
            return
        
        # Adapter les plages de taille de police
        min_size = min(pattern.font_sizes) - self.config['adaptive_thresholds']['font_size_tolerance']
        max_size = max(pattern.font_sizes) + self.config['adaptive_thresholds']['font_size_tolerance']
        
        # Mettre à jour la configuration du détecteur
        if hasattr(self.section_detector, 'config'):
            self.section_detector.config['font_size_range'] = [max(8.0, min_size), min(20.0, max_size)]
        
        # Adapter les exigences de formatage
        if 'bold' in pattern.formatting_styles:
            if hasattr(self.section_detector, 'config'):
                self.section_detector.config['require_bold'] = True
        
        self.logger.debug(f"Configuration adaptée: taille [{min_size:.1f}, {max_size:.1f}], "
                         f"gras requis: {'bold' in pattern.formatting_styles}")
    
    def _detect_additional_sections(self, pdf_doc: fitz.Document, 
                                  existing_sections: List[Section], 
                                  pattern: DocumentPattern) -> List[Section]:
        """Détecte des sections additionnelles basées sur les patterns appris"""
        additional_sections = []
        existing_positions = set((s.page, s.position_y) for s in existing_sections)
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            candidates = self._extract_section_candidates(page)
            
            for candidate in candidates:
                # Skip si déjà détecté
                candidate_pos = (candidate.page, candidate.position_y)
                if any(abs(candidate.position_y - pos[1]) < 10 
                      for pos in existing_positions if pos[0] == candidate.page):
                    continue
                
                # Vérifier contre les patterns appris
                if self._matches_learned_pattern(candidate, pattern):
                    section = Section(
                        number=f"adaptive_{len(additional_sections)}",
                        title=candidate.text,
                        page=candidate.page,
                        position_y=candidate.position_y,
                        font_size=candidate.font_size,
                        is_bold=candidate.is_bold
                    )
                    additional_sections.append(section)
                    existing_positions.add(candidate_pos)
        
        return additional_sections
    
    def _matches_learned_pattern(self, candidate: SectionCandidate, 
                               pattern: DocumentPattern) -> bool:
        """Vérifie si un candidat correspond aux patterns appris"""
        score = 0.0
        
        # Vérifier la taille de police
        if pattern.font_sizes:
            tolerance = self.config['adaptive_thresholds']['font_size_tolerance']
            if any(abs(candidate.font_size - size) <= tolerance for size in pattern.font_sizes):
                score += 0.4
        
        # Vérifier le formatage
        if 'bold' in pattern.formatting_styles and candidate.is_bold:
            score += 0.3
        
        if 'italic' in pattern.formatting_styles and candidate.is_italic:
            score += 0.1
        
        # Vérifier les patterns de numérotation
        for numbering_pattern in pattern.numbering_patterns:
            if numbering_pattern == 'numeric' and re.match(r'^\d+\.', candidate.text):
                score += 0.2
            elif numbering_pattern == 'hierarchical' and re.match(r'^\d+\.\d+', candidate.text):
                score += 0.2
        
        # Seuil de correspondance
        threshold = self.config['adaptive_thresholds']['frequency_threshold']
        return score >= threshold
    
    def _deduplicate_and_sort_sections(self, sections: List[Section]) -> List[Section]:
        """Déduplique et trie les sections"""
        # Déduplication basée sur position approximative
        unique_sections = []
        
        for section in sections:
            is_duplicate = any(
                s.page == section.page and 
                abs(s.position_y - section.position_y) < 10
                for s in unique_sections
            )
            
            if not is_duplicate:
                unique_sections.append(section)
        
        # Tri par page puis position Y
        unique_sections.sort(key=lambda s: (s.page, s.position_y))
        
        return unique_sections
    
    def get_detection_statistics(self) -> Dict:
        """Retourne les statistiques de détection"""
        stats = {
            'learned_patterns': None,
            'adaptation_enabled': self.config['pattern_learning']['adaptation_enabled'],
            'detector_config': getattr(self.section_detector, 'config', {})
        }
        
        if self.learned_patterns:
            stats['learned_patterns'] = {
                'font_sizes': self.learned_patterns.font_sizes,
                'formatting_styles': list(self.learned_patterns.formatting_styles),
                'numbering_patterns': self.learned_patterns.numbering_patterns,
                'confidence': self.learned_patterns.confidence
            }
        
        return stats 