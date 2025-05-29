# LensCRL

**Extraction d'images PDF avec nomenclature CRL - Interface Web Moderne**

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-latest-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🌐 Application en Ligne

**🚀 Accès Direct : [https://lenscrl.streamlit.app/](https://lenscrl.streamlit.app/)**

Utilisez l'application directement dans votre navigateur sans installation !

## 🚀 Démarrage Rapide

### Option 1 : Application Web (Recommandé)
- **En ligne** : [https://lenscrl.streamlit.app/](https://lenscrl.streamlit.app/)
- **Local** : `streamlit run app.py`

### Option 2 : Installation Locale
```bash
# Installation
pip install -r requirements.txt

# Lancement interface web
streamlit run app.py

# Ou utilisation CLI
python lenscrl_simple_cli.py extract document.pdf output/
```

## ✨ Fonctionnalités

- **Interface Web Moderne** - Upload, configuration et téléchargement intuitifs
- **Détection Automatique** - Sections et images extraites intelligemment  
- **Nomenclature CRL** - Format `CRL-MANUAL-X.X n_Y.ext` automatique
- **Filtrage Avancé** - Suppression des doublons, logos et headers
- **Téléchargements Flexibles** - Par section ou images individuelles

## 🎯 Usage

### Option 1 : Application en Ligne (Le plus simple)
1. Visitez [https://lenscrl.streamlit.app/](https://lenscrl.streamlit.app/)
2. Glissez votre PDF dans la zone de dépôt
3. Configurez le préfixe et nom du manuel
4. Cliquez "Lancer le traitement"
5. Téléchargez vos images organisées

### Option 2 : Interface Web Locale
1. Lancez `streamlit run app.py`
2. Glissez votre PDF dans la zone de dépôt
3. Configurez le préfixe et nom du manuel
4. Cliquez "Lancer le traitement"
5. Téléchargez vos images organisées

### Option 3 : Ligne de Commande
```bash
python lenscrl_simple_cli.py extract document.pdf output/ --manual PROCSG02
```

## 📂 Structure

```
LensCRL/
├── app.py                       # Interface Streamlit
├── lenscrl_simple_cli.py        # CLI
├── src/api/lenscrl_simple.py    # Logique core
├── .streamlit/config.toml       # Configuration thème
└── assets/logo.py               # Logo SVG
```

## 🛠️ Architecture

**Simple et Efficace** - Un seul fichier core, logique linéaire, pas de complexité inutile.

1. **Détection** → Patterns regex + analyse typographique
2. **Extraction** → PyMuPDF natif pour les images
3. **Association** → Mapping intelligent image→section  
4. **Filtrage** → Hash doublons + règles de taille/position
5. **Export** → Nomenclature CRL automatique

## 📊 Exemple de Sortie

```
CRL-PROCSG02-1.1 n_1.png
CRL-PROCSG02-1.1 n_2.png
CRL-PROCSG02-2.3 n_1.png
...
```

---


