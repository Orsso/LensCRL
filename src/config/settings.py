#!/usr/bin/env python3
"""
Configuration Management
========================
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    """Gestionnaire de configuration"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent
        self.default_config_path = self.config_dir / "default.yaml"
        self.user_config_path = Path.home() / ".lenscrl" / "config.yaml"
        
    def load_config(self, custom_config_path: str = None) -> Dict[str, Any]:
        """Charge la configuration avec priorités"""
        # 1. Configuration par défaut
        config = self._load_yaml(self.default_config_path)
        
        # 2. Configuration utilisateur (override)
        if self.user_config_path.exists():
            user_config = self._load_yaml(self.user_config_path)
            config = self._merge_configs(config, user_config)
            
        # 3. Configuration personnalisée (override)
        if custom_config_path and Path(custom_config_path).exists():
            custom_config = self._load_yaml(custom_config_path)
            config = self._merge_configs(config, custom_config)
            
        return config
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Charge un fichier YAML"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Erreur lecture config {path}: {e}")
            return {}
    
    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """Fusionne deux configurations (override a priorité)"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def save_user_config(self, config: Dict[str, Any]):
        """Sauvegarde configuration utilisateur"""
        self.user_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.user_config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True) 