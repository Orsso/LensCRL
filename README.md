# 🔍 LensCRL Simple

**Extraction d'images PDF avec nomenclature CRL - Version épurée et robuste**

## ✨ Fonctionnalités

### 🎯 **Noyau Robuste**
- **Détection fiable des sections** (patterns X.X en gras, ≥12pt)
- **Détection fiable des images** (PyMuPDF natif)
- **Attribution robuste** image→section (dernière section précédente)
- **Filtrage intelligent** (doublons hash, logos, headers/footers)

### 📋 **Nomenclature CRL**
Format automatique : `CRL-XXXX-X.X n_Y.ext`
- `XXXX` = Nom manuel (ex: PROCSG02)
- `X.X` = Numéro section (ex: 1.1, 2.3)
- `n_Y` = Compteur image (n_1, n_2...)

## 🚀 Usage

### Installation
```bash
pip install PyMuPDF
```

### Extraction Simple
```bash
python lenscrl_simple_cli.py extract document.pdf output/
```

### Avec Options
```bash
python lenscrl_simple_cli.py extract document.pdf output/ --manual PROCSG02 --debug
```

## 📊 Exemple de Sortie

```
🎉 EXTRACTION RÉUSSIE!

📊 RÉSULTATS:
  • Images extraites: 47
  • Images filtrées: 41
  • Sections détectées: 3
  • Temps de traitement: 3.45s

📋 RÉPARTITION PAR SECTION:
  • Section 1: 1 image(s) - CONTROLE DU DOCUMENT
  • Section 3: 46 image(s) - REGLAGES STANDARDS

📂 FICHIERS CRÉÉS:
  • CRL-PROCSG02-1 n_104_190.png (640x480, 45KB)
  • CRL-PROCSG02-3 n_56_295.png (800x600, 67KB)
  ...
```

## 🏗️ Architecture Simple

```
LensCRL Simple/
├── src/api/lenscrl_simple.py    # API complète (400 lignes)
├── lenscrl_simple_cli.py        # CLI épuré
└── README_SIMPLE.md            # Documentation
```

### Logique de Base

1. **Sections** : Pattern regex + gras + taille ≥12pt
2. **Images** : PyMuPDF `get_images()` + extraction bbox
3. **Association** : Géographique simple (dernière section précédente)
4. **Filtrage** : Hash doublons + taille + position headers/footers

## ⚙️ Principes de Design

### 🎯 **Simplicité**
- **1 fichier principal** (lenscrl_simple.py)
- **Logique linéaire** : détection → filtrage → association → sauvegarde
- **Patterns simples** : regex basiques, pas d'IA complexe

### 🔒 **Robustesse**
- **Fallbacks clairs** : si pas de section → première section
- **Gestion d'erreurs** : try/catch sur chaque image
- **Logs détaillés** : debug complet du processus

### 📈 **Performance**
- **Pas de dépendances lourdes** : seulement PyMuPDF
- **Traitement streaming** : image par image
- **Cache doublons** : hash MD5 des images

## 🔧 Personnalisation

### Filtres Images
```python
# Dans _filter_images_simple()
if img.width < 50 or img.height < 50:    # Taille min
if img.size_bytes < 1000:                # Poids min (1KB)
if y_ratio < 0.1 or y_ratio > 0.9:       # Headers/footers
```

### Patterns Sections
```python
# Dans _is_section_pattern()
patterns = [
    r'^\d+\.\d+(\.\d+)?\s+',    # 1.1, 2.3.4
    r'^[A-Z]\.\d+\s+',          # A.1, B.2
    r'^\d+\s+[A-Z]',            # 1 Introduction
]
```

## 📈 Stats de Nettoyage

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| **Fichiers core** | 8 | 1 | -87% |
| **Lignes de code** | ~2000 | 400 | -80% |
| **Dépendances** | 15+ | 1 | -93% |
| **Complexité** | Élevée | Simple | ✅ |

## 🎯 Objectifs Atteints

- ✅ **Détection fiable** des images et sections
- ✅ **Attribution robuste** image→section
- ✅ **Filtrage efficace** (logos, headers, doublons)
- ✅ **Nomenclature CRL** automatique
- ✅ **Code épuré** et maintenable
- ✅ **Workspace propre** et organisé

---

**LensCRL Simple** : L'essentiel, sans le superflu. 🎯 