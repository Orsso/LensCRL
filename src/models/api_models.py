#!/usr/bin/env python3
"""
Modèles de données pour l'API LensCRL
===================================

Classes de données pour standardiser les échanges avec l'API backend.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import json
from datetime import datetime


class ProcessingStatus(Enum):
    """Statuts de traitement"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    DETECTING_SECTIONS = "detecting_sections"
    VALIDATING_IMAGES = "validating_images"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class OperationMode(Enum):
    """Modes d'opération de l'API"""
    ANALYZE = "analyze"          # Analyse sans extraction
    PREVIEW = "preview"          # Preview avec validation
    EXTRACT = "extract"          # Extraction complète
    VALIDATE_CONFIG = "validate_config"  # Validation config


@dataclass
class DocumentInfo:
    """Informations sur le document PDF"""
    file_path: str
    file_size: int
    page_count: int
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SectionInfo:
    """Information sur une section détectée"""
    number: str
    title: str
    page: int
    bbox: tuple
    confidence: float
    font_size: float
    is_bold: bool
    position_y: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageInfo:
    """Information sur une image détectée/extraite"""
    page: int
    bbox: tuple
    format: str
    size_bytes: int
    dimensions: tuple  # (width, height)
    quality_score: float
    image_type: str
    section_association: Optional[str] = None
    confidence: float = 0.0
    validation_status: str = "unknown"
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessingProgress:
    """Progression du traitement"""
    status: ProcessingStatus
    current_step: str
    progress_percent: float
    pages_processed: int
    total_pages: int
    sections_found: int
    images_found: int
    images_validated: int
    images_extracted: int
    errors: List[str] = None
    warnings: List[str] = None
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'status': self.status.value
        }


@dataclass
class AnalysisResult:
    """Résultat d'analyse PDF (sans extraction)"""
    document_info: DocumentInfo
    sections_detected: List[SectionInfo]
    images_detected: List[ImageInfo]
    statistics: Dict[str, Any]
    processing_time: float
    timestamp: str
    success: bool = True
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'document_info': self.document_info.to_dict(),
            'sections_detected': [s.to_dict() for s in self.sections_detected],
            'images_detected': [i.to_dict() for i in self.images_detected],
            'statistics': self.statistics,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp,
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings
        }
        # Convertir les objets bbox (tuple/Rect) en listes pour JSON
        if 'bbox' in result and isinstance(result['bbox'], (tuple, list)):
            result['bbox'] = list(result['bbox'])
        return result
    
    def to_json(self) -> str:
        return json.dumps(clean_for_json(self.to_dict()), indent=2, ensure_ascii=False)


@dataclass
class PreviewResult:
    """Résultat de preview (analyse + validation sans extraction)"""
    analysis: AnalysisResult
    preview_images: List[ImageInfo]  # Images qui seraient extraites
    rejected_images: List[ImageInfo]  # Images qui seraient rejetées
    extraction_plan: Dict[str, Any]  # Plan d'extraction
    estimated_output_size: int  # Taille estimée en bytes
    estimated_duration: float  # Durée estimée en secondes
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'analysis': self.analysis.to_dict(),
            'preview_images': [i.to_dict() for i in self.preview_images],
            'rejected_images': [i.to_dict() for i in self.rejected_images],
            'extraction_plan': self.extraction_plan,
            'estimated_output_size': self.estimated_output_size,
            'estimated_duration': self.estimated_duration
        }
    
    def to_json(self) -> str:
        return json.dumps(clean_for_json(self.to_dict()), indent=2, ensure_ascii=False)


@dataclass
class ExtractionResult:
    """Résultat d'extraction complète"""
    preview: PreviewResult
    extracted_files: List[Dict[str, Any]]  # Fichiers créés
    output_directory: str
    statistics: Dict[str, Any]
    processing_time: float
    timestamp: str
    success: bool = True
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'preview': self.preview.to_dict(),
            'extracted_files': self.extracted_files,
            'output_directory': self.output_directory,
            'statistics': self.statistics,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp,
            'success': self.success,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def to_json(self) -> str:
        return json.dumps(clean_for_json(self.to_dict()), indent=2, ensure_ascii=False)


@dataclass
class ConfigValidationResult:
    """Résultat de validation de configuration"""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    suggestions: List[str] = None
    corrected_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(clean_for_json(self.to_dict()), indent=2, ensure_ascii=False)


@dataclass
class APIRequest:
    """Requête API standardisée"""
    operation: OperationMode
    pdf_path: str
    config: Dict[str, Any] = None
    output_dir: Optional[str] = None
    manual_name: Optional[str] = None
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.options is None:
            self.options = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'operation': self.operation.value
        }


@dataclass
class APIResponse:
    """Réponse API standardisée"""
    success: bool
    operation: OperationMode
    result: Union[AnalysisResult, PreviewResult, ExtractionResult, ConfigValidationResult]
    request_id: Optional[str] = None
    processing_time: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        result_dict = self.result.to_dict() if hasattr(self.result, 'to_dict') else self.result
        return {
            'success': self.success,
            'operation': self.operation.value,
            'result': result_dict,
            'request_id': self.request_id,
            'processing_time': self.processing_time,
            'timestamp': self.timestamp
        }
    
    def to_json(self) -> str:
        return json.dumps(clean_for_json(self.to_dict()), indent=2, ensure_ascii=False)


def clean_for_json(obj):
    """Nettoie un objet pour le rendre JSON-serializable"""
    if isinstance(obj, (tuple, list)):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: clean_for_json(value) for key, value in obj.items()}
    elif hasattr(obj, '__dict__'):
        # Objet custom, essayer de le convertir
        try:
            return obj.__dict__
        except:
            return str(obj)
    elif str(type(obj)) == "<class 'fitz.Rect'>":
        # Objet fitz.Rect spécifique
        return [obj.x0, obj.y0, obj.x1, obj.y1]
    else:
        return obj 