#!/usr/bin/env python3
"""
Système de callbacks pour le suivi de progression
===============================================

Callbacks pour suivre l'avancement des opérations en temps réel.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import logging
from ..models.api_models import ProcessingProgress, ProcessingStatus


class ProgressCallback(ABC):
    """Interface base pour les callbacks de progression"""
    
    @abstractmethod
    def on_start(self, total_steps: int, description: str = ""):
        """Appelé au début du traitement"""
        pass
    
    @abstractmethod
    def on_progress(self, progress: ProcessingProgress):
        """Appelé à chaque étape de progression"""
        pass
    
    @abstractmethod
    def on_step_complete(self, step_name: str, result: Any = None):
        """Appelé quand une étape est terminée"""
        pass
    
    @abstractmethod
    def on_complete(self, final_result: Any):
        """Appelé à la fin du traitement"""
        pass
    
    @abstractmethod
    def on_error(self, error: Exception, step_name: str = ""):
        """Appelé en cas d'erreur"""
        pass
    
    @abstractmethod
    def on_warning(self, warning: str, step_name: str = ""):
        """Appelé en cas d'avertissement"""
        pass


class LoggingCallback(ProgressCallback):
    """Callback qui log la progression"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def on_start(self, total_steps: int, description: str = ""):
        self.logger.info(f"🚀 Début: {description} ({total_steps} étapes)")
    
    def on_progress(self, progress: ProcessingProgress):
        self.logger.info(
            f"⏳ {progress.current_step} - "
            f"{progress.progress_percent:.1f}% "
            f"({progress.pages_processed}/{progress.total_pages} pages)"
        )
    
    def on_step_complete(self, step_name: str, result: Any = None):
        self.logger.info(f"✅ {step_name} terminé")
    
    def on_complete(self, final_result: Any):
        self.logger.info("🎉 Traitement terminé avec succès")
    
    def on_error(self, error: Exception, step_name: str = ""):
        self.logger.error(f"❌ Erreur {step_name}: {error}")
    
    def on_warning(self, warning: str, step_name: str = ""):
        self.logger.warning(f"⚠️ Avertissement {step_name}: {warning}")


class ConsoleCallback(ProgressCallback):
    """Callback avec affichage console coloré"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.current_progress = 0.0
    
    def on_start(self, total_steps: int, description: str = ""):
        print(f"\n🚀 {description}")
        print("=" * 60)
    
    def on_progress(self, progress: ProcessingProgress):
        self.current_progress = progress.progress_percent
        if self.verbose:
            # Barre de progression simple
            bar_length = 40
            filled_length = int(bar_length * progress.progress_percent / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            print(f"\r⏳ {progress.current_step}: [{bar}] {progress.progress_percent:.1f}%", end='', flush=True)
    
    def on_step_complete(self, step_name: str, result: Any = None):
        print(f"\n✅ {step_name}")
    
    def on_complete(self, final_result: Any):
        print(f"\n🎉 Traitement terminé !")
        print("=" * 60)
    
    def on_error(self, error: Exception, step_name: str = ""):
        print(f"\n❌ Erreur {step_name}: {error}")
    
    def on_warning(self, warning: str, step_name: str = ""):
        print(f"\n⚠️ {warning}")


class FunctionCallback(ProgressCallback):
    """Callback qui appelle des fonctions personnalisées"""
    
    def __init__(self, 
                 on_start_fn: Optional[Callable] = None,
                 on_progress_fn: Optional[Callable] = None,
                 on_step_complete_fn: Optional[Callable] = None,
                 on_complete_fn: Optional[Callable] = None,
                 on_error_fn: Optional[Callable] = None,
                 on_warning_fn: Optional[Callable] = None):
        self.on_start_fn = on_start_fn
        self.on_progress_fn = on_progress_fn
        self.on_step_complete_fn = on_step_complete_fn
        self.on_complete_fn = on_complete_fn
        self.on_error_fn = on_error_fn
        self.on_warning_fn = on_warning_fn
    
    def on_start(self, total_steps: int, description: str = ""):
        if self.on_start_fn:
            self.on_start_fn(total_steps, description)
    
    def on_progress(self, progress: ProcessingProgress):
        if self.on_progress_fn:
            self.on_progress_fn(progress)
    
    def on_step_complete(self, step_name: str, result: Any = None):
        if self.on_step_complete_fn:
            self.on_step_complete_fn(step_name, result)
    
    def on_complete(self, final_result: Any):
        if self.on_complete_fn:
            self.on_complete_fn(final_result)
    
    def on_error(self, error: Exception, step_name: str = ""):
        if self.on_error_fn:
            self.on_error_fn(error, step_name)
    
    def on_warning(self, warning: str, step_name: str = ""):
        if self.on_warning_fn:
            self.on_warning_fn(warning, step_name)


class CompositeCallback(ProgressCallback):
    """Callback qui combine plusieurs callbacks"""
    
    def __init__(self, callbacks: list[ProgressCallback]):
        self.callbacks = callbacks
    
    def on_start(self, total_steps: int, description: str = ""):
        for callback in self.callbacks:
            try:
                callback.on_start(total_steps, description)
            except Exception as e:
                logging.warning(f"Erreur callback on_start: {e}")
    
    def on_progress(self, progress: ProcessingProgress):
        for callback in self.callbacks:
            try:
                callback.on_progress(progress)
            except Exception as e:
                logging.warning(f"Erreur callback on_progress: {e}")
    
    def on_step_complete(self, step_name: str, result: Any = None):
        for callback in self.callbacks:
            try:
                callback.on_step_complete(step_name, result)
            except Exception as e:
                logging.warning(f"Erreur callback on_step_complete: {e}")
    
    def on_complete(self, final_result: Any):
        for callback in self.callbacks:
            try:
                callback.on_complete(final_result)
            except Exception as e:
                logging.warning(f"Erreur callback on_complete: {e}")
    
    def on_error(self, error: Exception, step_name: str = ""):
        for callback in self.callbacks:
            try:
                callback.on_error(error, step_name)
            except Exception as e:
                logging.warning(f"Erreur callback on_error: {e}")
    
    def on_warning(self, warning: str, step_name: str = ""):
        for callback in self.callbacks:
            try:
                callback.on_warning(warning, step_name)
            except Exception as e:
                logging.warning(f"Erreur callback on_warning: {e}")


class ProgressTracker:
    """Gestionnaire de progression avec callbacks"""
    
    def __init__(self, callback: Optional[ProgressCallback] = None):
        self.callback = callback or LoggingCallback()
        self.total_steps = 0
        self.current_step = 0
        self.status = ProcessingStatus.PENDING
        self.start_time = 0
        self.errors = []
        self.warnings = []
    
    def start(self, total_steps: int, description: str = ""):
        """Démarre le suivi de progression"""
        import time
        self.total_steps = total_steps
        self.current_step = 0
        self.status = ProcessingStatus.ANALYZING
        self.start_time = time.time()
        self.errors = []
        self.warnings = []
        
        self.callback.on_start(total_steps, description)
    
    def update(self, step_name: str, pages_processed: int = 0, 
               total_pages: int = 0, sections_found: int = 0,
               images_found: int = 0, images_validated: int = 0,
               images_extracted: int = 0):
        """Met à jour la progression"""
        import time
        
        self.current_step += 1
        progress_percent = (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
        elapsed_time = time.time() - self.start_time
        
        progress = ProcessingProgress(
            status=self.status,
            current_step=step_name,
            progress_percent=progress_percent,
            pages_processed=pages_processed,
            total_pages=total_pages,
            sections_found=sections_found,
            images_found=images_found,
            images_validated=images_validated,
            images_extracted=images_extracted,
            errors=self.errors.copy(),
            warnings=self.warnings.copy(),
            elapsed_time=elapsed_time
        )
        
        self.callback.on_progress(progress)
    
    def complete_step(self, step_name: str, result: Any = None):
        """Marque une étape comme terminée"""
        self.callback.on_step_complete(step_name, result)
    
    def complete(self, final_result: Any):
        """Termine le suivi"""
        self.status = ProcessingStatus.COMPLETED
        self.callback.on_complete(final_result)
    
    def error(self, error: Exception, step_name: str = ""):
        """Signale une erreur"""
        self.status = ProcessingStatus.ERROR
        self.errors.append(str(error))
        self.callback.on_error(error, step_name)
    
    def warning(self, warning: str, step_name: str = ""):
        """Signale un avertissement"""
        self.warnings.append(warning)
        self.callback.on_warning(warning, step_name)
    
    def set_status(self, status: ProcessingStatus):
        """Change le statut"""
        self.status = status 