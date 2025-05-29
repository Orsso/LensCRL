# 🚀 QUICKSTART - Refactoring Immédiat

## Actions à réaliser dans les 7 prochains jours

### ✅ JOUR 1-2 : Structure modulaire

#### 1. Créer la nouvelle architecture

```bash
# Créer l'arborescence
mkdir -p src/{core,config,utils,tests}
mkdir -p src/config
mkdir -p src/utils  
mkdir -p tests/{unit,integration,fixtures}

# Fichiers d'initialisation
touch src/__init__.py
touch src/core/__init__.py
touch src/config/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py
```

#### 2. Extraire SectionDetector (PRIORITÉ 1)

**Créer** `src/core/section_detector.py` :
```python
#!/usr/bin/env python3
"""
Section Detection Module
========================
Détection intelligente des sections dans les documents PDF
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
import fitz

class Section:
    """Représente une section détectée"""
    def __init__(self, number: str, title: str, page: int, position_y: float):
        self.number = number
        self.title = title  
        self.page = page
        self.position_y = position_y
        
    def __repr__(self):
        return f"Section({self.number}, '{self.title[:30]}...', page={self.page})"

class SectionDetector:
    """Détecteur de sections dans les PDFs"""
    
    def __init__(self, config: dict = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        
    def _default_config(self) -> dict:
        """Configuration par défaut"""
        return {
            'font_size_range': [12.0, 16.0],  # Au lieu de 14.0 fixe
            'bold_required': True,
            'title_min_length': 5,
            'section_patterns': [
                r'^\d+(?:\.\d+)*$',          # 1.2.3
                r'^[A-Z]+\d+(?:\.\d+)*$',    # A1.2  
            ]
        }
    
    def detect_sections(self, doc: fitz.Document) -> List[Section]:
        """Détecte toutes les sections du document"""
        sections = []
        
        for page_num in range(len(doc)):
            page_sections = self._detect_page_sections(doc[page_num], page_num)
            sections.extend(page_sections)
            
        # Trier par page puis position Y
        sections.sort(key=lambda s: (s.page, s.position_y))
        
        self.logger.info(f"Détecté {len(sections)} sections")
        return sections
    
    def _detect_page_sections(self, page: fitz.Page, page_num: int) -> List[Section]:
        """Détecte les sections d'une page"""
        sections = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
                
            lines = block["lines"]
            i = 0
            
            while i < len(lines) - 1:
                current_line = lines[i]
                next_line = lines[i + 1]
                
                current_text = self._extract_line_text(current_line)
                current_format = self._analyze_line_formatting(current_line)
                
                next_text = self._extract_line_text(next_line)
                next_format = self._analyze_line_formatting(next_line)
                
                if self._is_valid_section_pattern(current_text, current_format, 
                                                 next_text, next_format):
                    section = Section(
                        number=current_text.strip(),
                        title=next_text.strip(),
                        page=page_num,
                        position_y=current_line["bbox"][1]
                    )
                    sections.append(section)
                    
                    self.logger.debug(f"Section détectée: {section}")
                    i += 1  # Skip next line
                i += 1
        
        return sections
    
    def _extract_line_text(self, line: dict) -> str:
        """Extrait le texte d'une ligne"""
        text = ""
        for span in line["spans"]:
            text += span["text"]
        return text.strip()
    
    def _analyze_line_formatting(self, line: dict) -> dict:
        """Analyse le formatage d'une ligne"""
        if not line["spans"]:
            return {}
        
        span = line["spans"][0]
        return {
            'size': round(span["size"], 1),
            'font': span["font"],
            'flags': span["flags"],
            'is_bold': bool(span["flags"] & 16)
        }
    
    def _is_valid_section_pattern(self, text1: str, format1: dict, 
                                 text2: str, format2: dict) -> bool:
        """Vérifie si deux lignes forment un titre de section"""
        # Ligne 1 doit être un numéro de section
        is_section_number = any(
            re.match(pattern, text1) 
            for pattern in self.config['section_patterns']
        )
        if not is_section_number:
            return False
        
        # Ligne 2 doit être un titre
        if len(text2) < self.config['title_min_length']:
            return False
        
        # Vérification formatage (assouplir les règles)
        if self.config['bold_required']:
            if not (format1.get('is_bold', False) and format2.get('is_bold', False)):
                return False
        
        # Taille dans la plage configurée au lieu de 14.0 exactement
        size1, size2 = format1.get('size', 0), format2.get('size', 0)
        min_size, max_size = self.config['font_size_range']
        
        if not (min_size <= size1 <= max_size and min_size <= size2 <= max_size):
            return False
        
        # Le titre doit contenir des lettres
        if not re.search(r'[A-Za-zÀ-ÿ]{3,}', text2):
            return False
        
        return True

    def find_section_for_position(self, page_num: int, position_y: float, 
                                 sections: List[Section]) -> Optional[Section]:
        """Trouve la section correspondant à une position"""
        # Sections sur la même page
        same_page_sections = [s for s in sections if s.page == page_num]
        
        if same_page_sections:
            # Trouve la dernière section qui précède la position
            for section in reversed(same_page_sections):
                if section.position_y < position_y:
                    return section
        
        # Sinon, dernière section des pages précédentes
        previous_sections = [s for s in sections if s.page < page_num]
        if previous_sections:
            return max(previous_sections, key=lambda s: (s.page, s.position_y))
        
        return None
```

#### 3. Modifier lenscrl.py pour utiliser SectionDetector

**Dans `lenscrl.py`**, remplacer les méthodes de détection :

```python
# Ajouter en haut du fichier
from src.core.section_detector import SectionDetector, Section

# Dans la classe LensCRL, remplacer detect_document_sections():
def detect_document_sections(self, doc: fitz.Document) -> List[Dict]:
    """Détecte les sections du document (compatible ancien format)"""
    detector = SectionDetector()
    sections = detector.detect_sections(doc)
    
    # Convertir en ancien format pour compatibilité
    return [
        {
            'number': s.number,
            'title': s.title,
            'page': s.page,
            'position_y': s.position_y
        }
        for s in sections
    ]
```

### ✅ JOUR 3 : Configuration externalisée

#### 4. Créer système de configuration

**Installer PyYAML** :
```bash
pip install pyyaml
echo "pyyaml>=6.0" >> requirements.txt
```

**Créer** `src/config/default.yaml` :
```yaml
# Configuration par défaut LensCRL v2.0
version: "2.0"

detection:
  section_patterns:
    - pattern: '^\d+(?:\.\d+)*$'
      description: "Numérotation classique (1.2.3)"
    - pattern: '^[A-Z]+\d+(?:\.\d+)*$'
      description: "Préfixe lettres (A1.2)"
    - pattern: '^[A-Z]+[-_]\d+(?:\.\d+)*$'
      description: "Préfixe avec séparateur (DOC-1.2)"
  
  formatting:
    font_size_range: [12.0, 16.0]    # Remplace 14.0 fixe
    bold_required: true
    title_min_length: 5
    
  positioning:
    max_distance_pixels: 100
    column_detection: false          # Pour plus tard
    
extraction:
  image_filters:
    min_width: 50
    min_height: 50 
    max_file_size_mb: 50
    allowed_formats: ["png", "jpg", "jpeg", "bmp", "gif", "tiff"]
    
  duplicate_detection:
    hash_algorithm: "md5"
    similarity_threshold: 0.95
    filter_logos: true
    
nomenclature:
  prefix: "CRL"
  separator: "-"
  numbering_format: "n_{position}"
  
logging:
  level: "INFO"
  file: "lenscrl_extraction.log"
  format: "%(asctime)s - %(levelname)s - %(message)s"
```

**Créer** `src/config/settings.py` :
```python
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
```

### ✅ JOUR 4 : Gestion d'erreurs robuste  

#### 5. Créer hiérarchie d'exceptions

**Créer** `src/utils/exceptions.py` :
```python
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

class ValidationError(LensCRLError):
    """Erreur de validation"""
    pass

class FileOperationError(LensCRLError):
    """Erreur opération fichier"""
    pass
```

#### 6. Mise à jour requirements.txt

```bash
echo "# LensCRL v2.0 - Dependencies
PyMuPDF>=1.23.0
pyyaml>=6.0

# Development dependencies (optional)
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0" > requirements.txt
```

### ✅ JOUR 5-7 : Commencer refactoring lenscrl.py

#### 7. Remplacer les except: génériques

**Chercher et remplacer dans `lenscrl.py`** :

```python
# AVANT (ligne ~227):
except:
    image_bbox = (0, 100 + img_index * 50, 100, 150 + img_index * 50)

# APRÈS:
except (AttributeError, KeyError, IndexError) as e:
    self.logger.warning(f"Impossible de déterminer position image {img_index}: {e}")
    # Position par défaut basée sur l'index
    image_bbox = (0, 100 + img_index * 50, 100, 150 + img_index * 50)
```

#### 8. Test de l'architecture modulaire

**Créer** `test_refactoring.py` dans la racine :
```python
#!/usr/bin/env python3
"""
Test basique de la nouvelle architecture
"""

def test_section_detector():
    """Test du SectionDetector séparé"""
    from src.core.section_detector import SectionDetector
    from src.config.settings import ConfigManager
    
    # Test configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    print(f"Configuration chargée: {len(config)} sections")
    
    # Test détecteur
    detector = SectionDetector(config['detection'])
    print(f"SectionDetector créé avec config: {detector.config}")
    
    print("✅ Architecture modulaire OK")

if __name__ == "__main__":
    test_refactoring()
```

**Tester** :
```bash
python test_refactoring.py
```

### ✅ Actions de validation

À la fin de la semaine 1, vous devriez avoir :

1. **Structure modulaire** ✅
   ```
   src/
   ├── core/section_detector.py
   ├── config/settings.py + default.yaml  
   └── utils/exceptions.py
   ```

2. **SectionDetector séparé** ✅ avec config flexible

3. **Configuration externalisée** ✅ YAML + gestionnaire

4. **Exceptions spécialisées** ✅ remplaçant `except:`

5. **Tests basiques** ✅ pour valider l'architecture

### 🎯 Critères de succès Semaine 1

- [ ] `python test_refactoring.py` fonctionne
- [ ] Votre doc témoin se traite toujours correctement
- [ ] Configuration modifiable dans `default.yaml`
- [ ] Zero `except:` générique dans le code
- [ ] Logging plus précis avec contexte

**Après ça**, votre prototype sera déjà beaucoup plus robuste et vous pourrez attaquer la Phase 2 (détection adaptative) en toute confiance !

Voulez-vous que je commence par créer un de ces fichiers pour vous donner l'élan ? 