# LensCRL

**Extraction d'images PDF avec nomenclature CRL - Interface Web Moderne**

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-latest-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

<!-- Force redeploy 2025-05-29 -->

## 🌐 Application

**🚀 [https://lenscrl.streamlit.app/](https://lenscrl.streamlit.app/)**

## ✨ Fonctionnalités

- **Détection automatique** des sections et images
- **Nomenclature CRL** standardisée (`CRL-MANUAL-X.X n_Y.ext`)
- **Filtrage intelligent** des doublons, logos et headers
- **Interface web moderne** avec téléchargements par section

## 🚀 Installation Locale

```bash
pip install -r requirements.txt
streamlit run app.py
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

1. **Détection** → Patterns regex + analyse typographique
2. **Extraction** → PyMuPDF/pypdfium2 pour compatibilité cloud
3. **Association** → Mapping intelligent image→section  
4. **Filtrage** → Hash doublons + règles de position
5. **Export** → Nomenclature CRL automatique

---


