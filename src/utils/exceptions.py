#!/usr/bin/env python3
"""
Custom Exceptions for LensCRL
=============================
"""

class LensCRLError(Exception):
    """Exception de base pour LensCRL"""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message)
        self.context = context or {}

class ConfigurationError(LensCRLError):
    """Erreur de configuration"""
    pass

class PDFAnalysisError(LensCRLError):
    """Erreur lors de l'analyse PDF"""
    pass

class SectionDetectionError(LensCRLError):
    """Erreur lors de la détection de sections"""
    pass

class ImageExtractionError(LensCRLError):
    """Erreur lors de l'extraction d'images"""
    pass

class ImageValidationError(LensCRLError):
    """Erreur lors de la validation d'images"""
    pass

class SpatialAnalysisError(LensCRLError):
    """Erreur lors de l'analyse spatiale"""
    pass

class ValidationError(LensCRLError):
    """Erreur de validation"""
    pass

class FileOperationError(LensCRLError):
    """Erreur opération fichier"""
    pass 