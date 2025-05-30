#!/usr/bin/env python3
"""
LensCRL Web Interface
=====================
Interface web Streamlit pour l'extraction d'images PDF avec nomenclature CRL.
"""

import streamlit as st
import os
from pathlib import Path
import tempfile
import zipfile
import io
import shutil
import base64
from assets.logo import LOGO_SVG
import sys
import streamlit.components.v1 as components

# Try to import PyMuPDF first, fallback to pypdfium2 for Streamlit Cloud compatibility
PDF_LIBRARY = None
try:
    import fitz
    PDF_LIBRARY = "pymupdf"
except ImportError:
    try:
        import pypdfium2 as pdfium
        PDF_LIBRARY = "pypdfium2"
    except ImportError:
        st.error("❌ Aucune bibliothèque PDF disponible (PyMuPDF ou pypdfium2)")
        st.stop()

# Ajouter src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import de l'API LensCRL
if PDF_LIBRARY == "pymupdf":
    from src.api.lenscrl_simple import LensCRLSimple
else:
    # For cloud deployment, we'll need a pypdfium2 adapter
    st.info("ℹ️ Mode compatibilité cloud (pypdfium2) - Certaines fonctionnalités peuvent être limitées")
    try:
        from src.api.lenscrl_simple import LensCRLSimple
    except ImportError:
        st.error("❌ Impossible de charger l'API LensCRL")
        st.stop()

# Créer un favicon basé sur le logo SVG de l'app
FAVICON_SVG = """
<svg width="32" height="32" viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="25" cy="25" r="20" fill="#0E1117" stroke="#4C9BE8" stroke-width="3"/>
    <circle cx="25" cy="25" r="12" fill="#4C9BE8" opacity="0.4"/>
    <path d="M18 25 L32 25 M25 18 L25 32" stroke="#4C9BE8" stroke-width="3" stroke-linecap="round"/>
    <path d="M20 20 L30 30 M30 20 L20 30" stroke="#4C9BE8" stroke-width="2" stroke-linecap="round" opacity="0.6"/>
</svg>
"""

# Encoder le SVG en base64 pour l'utiliser comme favicon
favicon_b64 = base64.b64encode(FAVICON_SVG.encode()).decode()
favicon_url = f"data:image/svg+xml;base64,{favicon_b64}"

# Configuration de la page
st.set_page_config(
    page_title="LensCRL",
    page_icon=favicon_url,  # Utilise le logo SVG de l'app comme favicon
    layout="centered",
)

# Styles CSS avec technique moderne des sections encapsulées
st.markdown("""
<style>
    /* Import de Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
    
    /* Reset et base */
    .main {
        padding: 1.5rem 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Éviter l'encapsulation globale du container principal */
    .main > .block-container > div:first-child {
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Header et logo */
    .app-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 3rem;
        padding-bottom: 2rem;
        border-bottom: 1px solid rgba(76, 155, 232, 0.15);
    }
    
    .app-logo svg {
        width: 75px;
        height: 75px;
        filter: drop-shadow(0 2px 8px rgba(76, 155, 232, 0.3));
    }
    
    .app-title {
        color: #FFFFFF;
        font-family: 'Orbitron', sans-serif;
        font-size: 2.25rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.025em;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .app-subtitle {
        color: #8B949E;
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        font-weight: 400;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }

    /* Technique moderne pour les sections encapsulées */
    /* Section de sélection de fichier */
    div[data-testid='stVerticalBlock']:has(.file-selection-marker) {
        background: linear-gradient(135deg, rgba(14, 17, 23, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
    }

    div[data-testid='stVerticalBlock']:has(.file-selection-marker):before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #4C9BE8 0%, rgba(76, 155, 232, 0.2) 100%);
    }

    /* Section de configuration (collapsable) */
    div[data-testid='stVerticalBlock']:has(.config-marker) {
        background: linear-gradient(135deg, rgba(14, 17, 23, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
        cursor: pointer;
    }

    div[data-testid='stVerticalBlock']:has(.config-marker):before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #4C9BE8 0%, rgba(76, 155, 232, 0.2) 100%);
    }

    /* Section des résultats */
    div[data-testid='stVerticalBlock']:has(.results-marker) {
        background: linear-gradient(135deg, rgba(14, 17, 23, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
    }

    div[data-testid='stVerticalBlock']:has(.results-marker):before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #4C9BE8 0%, rgba(76, 155, 232, 0.2) 100%);
    }

    /* Section des actions */
    div[data-testid='stVerticalBlock']:has(.actions-marker) {
        background: linear-gradient(135deg, rgba(14, 17, 23, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
    }

    div[data-testid='stVerticalBlock']:has(.actions-marker):before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #4C9BE8 0%, rgba(76, 155, 232, 0.2) 100%);
    }

    /* Section des images par section */
    div[data-testid='stVerticalBlock']:has(.images-sections-marker) {
        background: linear-gradient(135deg, rgba(14, 17, 23, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
    }

    div[data-testid='stVerticalBlock']:has(.images-sections-marker):before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #4C9BE8 0%, rgba(76, 155, 232, 0.2) 100%);
    }

    /* Titres des sections avec icônes */
    .section-title {
        color: #4C9BE8;
        font-family: 'Inter', sans-serif;
        font-size: 1.15rem;
        font-weight: 600;
        margin: 0 0 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid rgba(76, 155, 232, 0.1);
    }

    .section-title svg {
        width: 20px;
        height: 20px;
        stroke: #4C9BE8;
    }

    /* Gestion du collapse pour la configuration */
    .config-collapsed {
        height: 80px !important;
        overflow: hidden;
        transition: all 0.3s ease;
    }

    .config-expanded {
        height: auto !important;
        transition: all 0.3s ease;
    }

    /* Indicateur de collapse */
    .collapse-indicator {
        float: right;
        transition: transform 0.3s ease;
        font-size: 0.8rem;
        color: #4C9BE8;
    }

    .collapse-indicator.collapsed {
        transform: rotate(-90deg);
    }

    /* Masquer les marqueurs visuellement */
    .file-selection-marker,
    .config-marker,
    .results-marker,
    .actions-marker,
    .images-sections-marker {
        display: none;
    }

    /* Fix hover rouge sur tous les éléments */
    .stButton > button, .stButton > button:hover, .stButton > button:focus, .stButton > button:active {
        color: white !important;
        border: none !important;
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%) !important;
    }
    
    .stDownloadButton > button, .stDownloadButton > button:hover, .stDownloadButton > button:focus, .stDownloadButton > button:active {
        color: white !important;
        border: none !important;
    }

    /* Text content color fixes */
    .main, .main p, .main div, .main span {
        color: #E6EDF3 !important;
    }

    /* Autres styles conservés... */
    /* [Le reste des styles CSS existants] */
    
    /* Animation de loading */
    .lds-dual-ring {
        display: inline-block;
        width: 32px;
        height: 32px;
        vertical-align: middle;
    }
    .lds-dual-ring:after {
        content: " ";
        display: block;
        width: 32px;
        height: 32px;
        margin: 0 auto;
        border-radius: 50%;
        border: 4px solid #4C9BE8;
        border-color: #4C9BE8 transparent #4C9BE8 transparent;
        animation: lds-dual-ring 1.1s linear infinite;
    }
    @keyframes lds-dual-ring {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Boutons */
    .stButton > button {
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.875rem 2rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(76, 155, 232, 0.25) !important;
        text-transform: none !important;
        letter-spacing: 0.025em !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        box-shadow: 0 6px 20px rgba(76, 155, 232, 0.4) !important;
        transform: translateY(-2px) !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
        box-shadow: 0 2px 8px rgba(76, 155, 232, 0.3) !important;
        color: white !important;
        border: none !important;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    }
    .stButton > button:focus {
        outline: none !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 0 0 2px rgba(76, 155, 232, 0.5) !important;
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%) !important;
    }
    
    /* Download buttons */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(46, 125, 50, 0.3);
        padding: 0.5rem 1rem;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #2E7D32 0%, #388E3C 100%);
        box-shadow: 0 4px 12px rgba(46, 125, 50, 0.4);
        transform: translateY(-1px);
        color: white !important;
    }
    .stDownloadButton > button:active {
        transform: translateY(0);
        color: white !important;
    }
    .stDownloadButton > button:focus {
        outline: none;
        color: white !important;
    }

    /* Métriques */
    .stMetric {
        background: linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid rgba(76, 155, 232, 0.15);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    .stMetric:hover {
        border-color: rgba(76, 155, 232, 0.3);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
        transform: translateY(-2px);
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        background-color: #262730;
        border: 2px solid #363746;
        border-radius: 12px;
        color: white;
        font-family: 'Inter', sans-serif;
        padding: 0.75rem 1rem;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4C9BE8;
        box-shadow: 0 0 0 3px rgba(76, 155, 232, 0.15);
    }
    
    /* Checkboxes - les vraies cases à cocher, pas le texte */
    .stCheckbox input[type="checkbox"]:checked {
        background-color: #4C9BE8 !important;
        border-color: #4C9BE8 !important;
        accent-color: #4C9BE8 !important;
    }
    
    .stCheckbox input[type="checkbox"] {
        accent-color: #4C9BE8 !important;
        border-color: #363746 !important;
    }
    
    .stCheckbox input[type="checkbox"]:hover {
        border-color: #4C9BE8 !important;
    }
    
    /* Empêcher SEULEMENT le surlignage du texte - PAS la checkbox */
    .stCheckbox label [data-testid="stMarkdownContainer"],
    .stCheckbox label [data-testid="stMarkdownContainer"] p,
    .stCheckbox label > div:last-child {
        color: #E6EDF3 !important;
        background: none !important;
    }
    
    .stCheckbox label:hover [data-testid="stMarkdownContainer"],
    .stCheckbox label:hover [data-testid="stMarkdownContainer"] p,
    .stCheckbox label:hover > div:last-child {
        color: #E6EDF3 !important;
        background: none !important;
    }
    
    /* File uploader */
    .stFileUploader {
        border: 2px dashed rgba(76, 155, 232, 0.3);
        border-radius: 16px;
        padding: 2rem;
        background: linear-gradient(135deg, rgba(30, 30, 30, 0.6) 0%, rgba(42, 42, 42, 0.6) 100%);
        transition: all 0.3s ease;
    }
    .stFileUploader:hover {
        border-color: rgba(76, 155, 232, 0.5);
        background: linear-gradient(135deg, rgba(30, 30, 30, 0.8) 0%, rgba(42, 42, 42, 0.8) 100%);
    }
    
    /* Preview */
    .preview-container {
        background: linear-gradient(135deg, #1A1A1A 0%, #2D2D2D 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    .preview-title {
        color: #4C9BE8;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .preview-code {
        font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
        background: #0D1117;
        color: #58A6FF;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        border-left: 3px solid #4C9BE8;
        font-size: 0.9rem;
        letter-spacing: 0.025em;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
    }

    /* Success/Info messages */
    .element-container .stAlert {
        border-radius: 12px;
        border: 1px solid rgba(76, 155, 232, 0.3);
        box-shadow: 0 4px 16px rgba(76, 155, 232, 0.15);
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.8) 0%, rgba(55, 65, 81, 0.6) 100%);
    }
    
    /* Force dark theme on all alert content */
    .stAlert, .stAlert * {
        color: #E6EDF3 !important;
        background-color: transparent !important;
    }

    /* Success messages with green accent */
    .stSuccess {
        border-color: rgba(46, 125, 50, 0.5) !important;
        background: linear-gradient(135deg, rgba(46, 125, 50, 0.15) 0%, rgba(76, 155, 232, 0.1) 100%) !important;
    }
    
    /* Info messages with blue accent */
    .stInfo {
        border-color: rgba(76, 155, 232, 0.5) !important;
        background: linear-gradient(135deg, rgba(76, 155, 232, 0.15) 0%, rgba(59, 130, 246, 0.1) 100%) !important;
    }
    
    /* Warning/Error messages */
    .stWarning {
        border-color: rgba(245, 158, 11, 0.5) !important;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(251, 191, 36, 0.1) 100%) !important;
    }
    
    .stError {
        border-color: rgba(239, 68, 68, 0.5) !important;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(248, 113, 113, 0.1) 100%) !important;
    }

    /* Force all text elements to be visible */
    p, div, span, label {
        color: #E6EDF3 !important;
    }
    
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] div,
    [data-testid="stMarkdownContainer"] span {
        color: #E6EDF3 !important;
    }

    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .main > div {
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }
        .app-title {
            font-size: 1.75rem;
        }
        .section-title {
            font-size: 1rem;
        }
    }
    
    /* ====== STYLES PERSONNALISÉS - PRIORITÉ ABSOLUE (À LA FIN) ====== */
    
    /* Réinitialiser tous les boutons à leur style natif d'abord */
    .stButton > button {
        background: transparent !important;
        color: #E6EDF3 !important;
        border: 1px solid #363746 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
    }
    
    .stButton > button:hover {
        background: rgba(76, 155, 232, 0.1) !important;
        color: #4C9BE8 !important;
        border: 1px solid #4C9BE8 !important;
        transform: none !important;
        box-shadow: none !important;
    }
    
    /* Boutons de téléchargement VERTS - même couleur que l'icône de succès */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #27AE60 0%, #2ECC71 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        box-shadow: 0 2px 8px rgba(39, 174, 96, 0.3) !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #2ECC71 0%, #27D177 100%) !important;
        box-shadow: 0 4px 12px rgba(39, 174, 96, 0.4) !important;
        transform: translateY(-1px) !important;
        color: white !important;
        border: none !important;
    }
    
    /* Boutons personnalisés BLEUS - PRIORITÉ ABSOLUE FINALE */
    button:contains("Lancer le traitement"),
    button:contains("NOUVEAU DOC"),
    .stButton > button[data-testid="baseButton-primary"],
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.875rem 2rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 4px 12px rgba(76, 155, 232, 0.25) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-transform: none !important;
        letter-spacing: 0.025em !important;
    }
    
    button:contains("Lancer le traitement"):hover,
    button:contains("NOUVEAU DOC"):hover,
    .stButton > button[data-testid="baseButton-primary"]:hover,
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        box-shadow: 0 6px 20px rgba(76, 155, 232, 0.4) !important;
        transform: translateY(-2px) !important;
        color: white !important;
        border: none !important;
    }
    
    button:contains("Lancer le traitement"):active,
    button:contains("NOUVEAU DOC"):active,
    .stButton > button[data-testid="baseButton-primary"]:active,
    .stButton button[kind="primary"]:active {
        transform: translateY(0) !important;
        box-shadow: 0 2px 8px rgba(76, 155, 232, 0.3) !important;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    }
    
    button:contains("Lancer le traitement"):focus,
    button:contains("NOUVEAU DOC"):focus,
    .stButton > button[data-testid="baseButton-primary"]:focus,
    .stButton button[kind="primary"]:focus {
        outline: none !important;
        box-shadow: 0 0 0 2px rgba(76, 155, 232, 0.5) !important;
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%) !important;
    }

    /* Override global hover colors */
    * {
        --primary-color: #4C9BE8 !important;
    }
    
    /* Force Streamlit app variables */
    .stApp, [data-testid="stAppViewContainer"] {
        --primary-color: #4C9BE8 !important;
        --background-color: #0E1117 !important;
        --secondary-background-color: #1F2937 !important;
        --text-color: #E6EDF3 !important;
    }
</style>
""", unsafe_allow_html=True)

# Styles CSS pour corriger l'encapsulation globale
st.markdown("""
<style>
    /* SOLUTION DIRECTE : Neutraliser le premier conteneur vertical qui englobe tout */
    .main div[data-testid='stVerticalBlock']:first-child {
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    .main div[data-testid='stVerticalBlock']:first-child:before {
        display: none !important;
    }
    
    /* Cibler le conteneur principal Streamlit */
    [data-testid="stAppViewContainer"] > .main .block-container > div:first-child {
        background: none !important;
        border: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
    }
    
    /* CORRECTION FINALE : Boutons système (⚙, ✕) et checkboxes */
    
    /* Petits boutons système SEULEMENT (⚙, ✕) - excluant spécifiquement les téléchargements */
    .stButton > button:not([data-testid="stDownloadButton"]):not([class*="download"]) {
        background: transparent !important;
        color: #E6EDF3 !important;
        border: 1px solid #363746 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
    }
    
    .stButton > button:hover:not([data-testid="stDownloadButton"]):not([class*="download"]) {
        background: rgba(76, 155, 232, 0.1) !important;
        color: #4C9BE8 !important;
        border: 1px solid #4C9BE8 !important;
        transform: none !important;
    }
    
    /* RÉAFFIRMER les boutons TÉLÉCHARGER VERTS */
    .stDownloadButton > button,
    button[data-testid="stDownloadButton"],
    button[class*="download"] {
        background: linear-gradient(135deg, #27AE60 0%, #2ECC71 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        box-shadow: 0 2px 8px rgba(39, 174, 96, 0.3) !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .stDownloadButton > button:hover,
    button[data-testid="stDownloadButton"]:hover,
    button[class*="download"]:hover {
        background: linear-gradient(135deg, #2ECC71 0%, #27D177 100%) !important;
        box-shadow: 0 4px 12px rgba(39, 174, 96, 0.4) !important;
        transform: translateY(-1px) !important;
        color: white !important;
        border: none !important;
    }
    
    /* Checkboxes - les vraies cases à cocher, pas le texte */
    .stCheckbox input[type="checkbox"]:checked {
        background-color: #4C9BE8 !important;
        border-color: #4C9BE8 !important;
        accent-color: #4C9BE8 !important;
    }
    
    .stCheckbox input[type="checkbox"] {
        accent-color: #4C9BE8 !important;
        border-color: #363746 !important;
    }
    
    .stCheckbox input[type="checkbox"]:hover {
        border-color: #4C9BE8 !important;
    }
    
    /* Empêcher SEULEMENT le surlignage du texte - PAS la checkbox */
    .stCheckbox label [data-testid="stMarkdownContainer"],
    .stCheckbox label [data-testid="stMarkdownContainer"] p,
    .stCheckbox label > div:last-child {
        color: #E6EDF3 !important;
        background: none !important;
    }
    
    .stCheckbox label:hover [data-testid="stMarkdownContainer"],
    .stCheckbox label:hover [data-testid="stMarkdownContainer"] p,
    .stCheckbox label:hover > div:last-child {
        color: #E6EDF3 !important;
        background: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Cache pour stocker les résultats du traitement
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
    
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = None

if 'reset_app' not in st.session_state:
    st.session_state.reset_app = False

if 'config_collapsed' not in st.session_state:
    st.session_state.config_collapsed = True

def reset_application():
    """Reset complet de l'application : session state + cache Streamlit"""
    # Nettoyer l'ancien dossier temporaire s'il existe
    if 'temp_dir' in st.session_state:
        old_temp_dir = Path(st.session_state.temp_dir)
        if old_temp_dir.exists():
            shutil.rmtree(old_temp_dir, ignore_errors=True)
    
    # Créer un nouveau dossier temporaire
    st.session_state.temp_dir = tempfile.mkdtemp()
    
    # Reset des variables de session
    st.session_state.reset_app = True
    st.session_state.treatment_state = 'button'  # Remettre à l'état initial
    st.session_state.processing_results = None
    st.session_state.last_process_key = None
    
    # Incrémenter la clé du file uploader pour le forcer à se reset
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
    st.session_state.file_uploader_key += 1
    
    # IMPORTANT: Vider le cache Streamlit pour forcer le retraitement
    st.cache_data.clear()

def create_zip_from_images(image_paths, manual_name="images"):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for img_info in image_paths:
            if os.path.exists(img_info['path']):
                zip_file.write(img_info['path'], img_info['filename'])
    return zip_buffer.getvalue()

@st.cache_data(show_spinner=False)
def process_pdf(pdf_content, output_dir, manual_name, debug_mode, original_filename, prefix):
    # Sauvegarde temporaire du PDF avec le nom original
    pdf_path = Path(output_dir) / original_filename
    with open(pdf_path, "wb") as f:
        f.write(pdf_content)

    # Initialisation et exécution de LensCRL avec debug console seulement
    processor = LensCRLSimple(debug=True)
    return processor.extract_images(
        str(pdf_path),
        str(output_dir),
        manual_name if manual_name else None,
        prefix
    )

def main():
    # Vérifier si on doit reset l'application
    if st.session_state.get('reset_app', False):
        st.session_state.processing_results = None
        st.session_state.last_process_key = None
        st.session_state.treatment_state = 'button'  # Reset à l'état initial
        st.session_state.reset_app = False
        st.rerun()
    
    # Initialiser la clé du file uploader si elle n'existe pas
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
    
    try:
        # En-tête avec logo (en dehors de toute encapsulation)
        st.markdown(
            f'''
            <div class="app-header">
                <div class="app-logo">{LOGO_SVG}</div>
                <div>
                    <h1 class="app-title">LensCRL</h1>
                    <p class="app-subtitle">Extraction d'images PDF avec nomenclature CRL</p>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # SECTION 1: Sélection du fichier PDF
        with st.container():
            st.markdown('<span class="file-selection-marker"></span>', unsafe_allow_html=True)
            st.markdown('''
                <div style="color: #8B949E; 
                     font-family: 'Inter', sans-serif; 
                     font-size: 1rem; 
                     font-weight: 500; 
                     margin: 0 0 1.5rem 0; 
                     display: flex; 
                     align-items: center; 
                     gap: 0.5rem;">
                    <svg style="width: 16px; height: 16px; stroke: #8B949E;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    Sélection du fichier
                </div>
            ''', unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader(
                "Choisissez un fichier PDF",
                type="pdf",
                help="Déposez votre fichier PDF ici",
                key=f'file_uploader_{st.session_state.file_uploader_key}'
            )

        if uploaded_file:
            # Détection du nom du manuel pour le preview
            temp_pdf_path = Path(st.session_state.temp_dir) / uploaded_file.name
            with open(temp_pdf_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            processor = LensCRLSimple(debug=False)
            detected_name = processor._deduce_manual_name(str(temp_pdf_path))
            temp_pdf_path.unlink()
            
            # SECTION 2: Configuration avec preview par défaut
            with st.container():
                st.markdown('<span class="config-marker"></span>', unsafe_allow_html=True)
                
                if st.session_state.config_collapsed:
                    # État collapsed : Preview discret + bouton settings bien proportionné
                    st.markdown('''
                        <div style="color: #8B949E; 
                             font-family: 'Inter', sans-serif; 
                             font-size: 0.9rem; 
                             font-weight: 400; 
                             margin: 0 0 1rem 0; 
                             opacity: 0.8;">
                            Preview
                        </div>
                    ''', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        # Preview élégant de la nomenclature
                        st.markdown(
                            f'''
                            <div style="background: rgba(13, 17, 23, 0.8); 
                                 border: 1px solid rgba(76, 155, 232, 0.3);
                                 border-radius: 8px; 
                                 padding: 1rem; 
                                 margin: 0;">
                                <div style="font-family: 'Courier New', monospace; 
                                     font-size: 1.1rem; 
                                     color: #4C9BE8; 
                                     text-align: center;
                                     letter-spacing: 0.5px;">CRL-{detected_name}-1.1 n_1.png</div>
                            </div>
                            ''',
                            unsafe_allow_html=True
                        )
                    with col2:
                        # Bouton settings mieux proportionné
                        if st.button(
                            "⚙",
                            key="config_expand",
                            help="Modifier la configuration",
                            use_container_width=True
                        ):
                            st.session_state.config_collapsed = False
                            st.rerun()
                else:
                    # État expanded : Configuration plus discrète
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown('''
                            <div style="color: #8B949E; 
                                 font-family: 'Inter', sans-serif; 
                                 font-size: 1rem; 
                                 font-weight: 500; 
                                 margin: 0 0 1.5rem 0; 
                                 display: flex; 
                                 align-items: center; 
                                 gap: 0.5rem;">
                                <svg style="width: 16px; height: 16px; stroke: #8B949E;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                </svg>
                                Configuration
                            </div>
                        ''', unsafe_allow_html=True)
                    with col2:
                        # Bouton pour collapse avec même proportion
                        if st.button(
                            "✕",
                            key="config_collapse", 
                            help="Masquer la configuration",
                            use_container_width=True
                        ):
                            st.session_state.config_collapsed = True
                            st.rerun()
                    
                    # Configuration du préfixe
                    prefix = st.text_input(
                        "Préfixe",
                        value="CRL",
                        help="Préfixe utilisé pour tous les fichiers (par défaut: CRL)"
                    )

                    # Nom du manuel - simplifié
                    use_detected = st.checkbox(
                        f"Utiliser le nom détecté : **{detected_name}**", 
                        value=True,
                        help="Nom détecté depuis les footers, métadonnées ou nom de fichier"
                    )
                    
                    manual_name = detected_name
                    if not use_detected:
                        manual_name = st.text_input(
                            "Nom personnalisé",
                            value=detected_name,
                            help="Ex: PROCSG02, OMA, STC, etc."
                        )

                    # Preview final simplifié
                    st.markdown(
                        f'''
                        <div style="background: rgba(13, 17, 23, 0.8); 
                             border: 1px solid rgba(76, 155, 232, 0.3);
                             border-radius: 8px; 
                             padding: 1rem; 
                             margin: 1rem 0;">
                            <div style="color: #8B949E; font-size: 0.85rem; margin-bottom: 0.5rem;">Aperçu</div>
                            <div style="font-family: 'Courier New', monospace; 
                                 font-size: 1.1rem; 
                                 color: #4C9BE8; 
                                 text-align: center;
                                 letter-spacing: 0.5px;">{prefix}-{manual_name}-1.1 n_1.png</div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
                
                # Définir les valeurs par défaut pour la suite (que la config soit ouverte ou fermée)
                if st.session_state.config_collapsed:
                    prefix = "CRL"
                    manual_name = detected_name

            # Bouton pour lancer le traitement (sans box)
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                # États du traitement : 'button', 'processing', 'completed'
                if 'treatment_state' not in st.session_state:
                    st.session_state.treatment_state = 'button'
                
                # Détecter les changements de configuration pour réactiver le bouton
                current_config = (uploaded_file.name if uploaded_file else None, prefix, manual_name)
                if 'last_config' not in st.session_state:
                    st.session_state.last_config = current_config
                elif st.session_state.last_config != current_config:
                    st.session_state.treatment_state = 'button'
                    st.session_state.last_config = current_config

                # Spinner CSS pour l'animation personnalisée
                spinner_html = '''<div class="lds-dual-ring"></div>'''
                
                # Icône de succès
                success_icon = '''
                <div style="display:flex;justify-content:center;align-items:center;height:56px;">
                    <div style="background: linear-gradient(135deg, #27AE60 0%, #2ECC71 100%); 
                         border-radius: 50%; width: 56px; height: 56px; 
                         display: flex; align-items: center; justify-content: center;
                         box-shadow: 0 4px 12px rgba(39, 174, 96, 0.3);
                         animation: successPulse 0.6s ease-out;">
                        <svg width="24" height="24" fill="white" viewBox="0 0 24 24">
                            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                        </svg>
                    </div>
                </div>
                <style>
                @keyframes successPulse {
                    0% { transform: scale(0.8); opacity: 0; }
                    50% { transform: scale(1.1); }
                    100% { transform: scale(1); opacity: 1; }
                }
                </style>
                '''
                
                # Initialiser process_button par défaut
                process_button = False
                
                # Affichage selon l'état
                if st.session_state.treatment_state == 'processing':
                    st.markdown(f'<div style="display:flex;justify-content:center;align-items:center;height:56px;">{spinner_html}</div>', unsafe_allow_html=True)
                elif st.session_state.treatment_state == 'completed':
                    st.markdown(success_icon, unsafe_allow_html=True)
                else:  # state == 'button'
                    process_button = st.button(
                        "Lancer le traitement", 
                        use_container_width=True
                    )

            if process_button:
                # Passer à l'état processing
                st.session_state.treatment_state = 'processing'
                st.rerun()

            # Traitement effectif (seulement si en état processing et pas encore traité)
            if st.session_state.treatment_state == 'processing':
                # Création du dossier de sortie
                output_dir = Path(st.session_state.temp_dir) / "output"
                output_dir.mkdir(exist_ok=True)

                # Si nouveau fichier ou changement d'options, retraiter
                current_file_hash = hash(uploaded_file.getvalue())
                cache_key = (current_file_hash, prefix, manual_name)
                
                if 'last_process_key' not in st.session_state or st.session_state.last_process_key != cache_key:
                    # Nettoyer le dossier de sortie
                    if output_dir.exists():
                        shutil.rmtree(output_dir)
                    output_dir.mkdir(exist_ok=True)
                    
                    # Traiter le PDF
                    results = process_pdf(
                        uploaded_file.getvalue(),
                        output_dir,
                        manual_name,
                        False,  # debug mode désactivé
                        uploaded_file.name,
                        prefix
                    )
                    st.session_state.processing_results = results
                    st.session_state.last_process_key = cache_key
                
                # Passer à l'état completed après le traitement
                st.session_state.treatment_state = 'completed'
                st.rerun()

        # SECTION 3: Résultats (si disponibles)
        if 'processing_results' in st.session_state and st.session_state.processing_results:
            results = st.session_state.processing_results
            
            if results.success:
                # Section des résultats
                with st.container():
                    st.markdown('<span class="results-marker"></span>', unsafe_allow_html=True)
                    st.markdown('''
                        <div style="color: #8B949E; 
                             font-family: 'Inter', sans-serif; 
                             font-size: 1rem; 
                             font-weight: 500; 
                             margin: 0 0 1.5rem 0; 
                             display: flex; 
                             align-items: center; 
                             gap: 0.5rem;">
                            <svg style="width: 16px; height: 16px; stroke: #8B949E;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                            </svg>
                            Résultats
                        </div>
                    ''', unsafe_allow_html=True)
                    
                    # Stats principales
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Images extraites", len(results.images_extracted))
                    with col2:
                        st.metric("Images filtrées", len(results.images_filtered))
                    with col3:
                        st.metric("Sections détectées", len(results.sections_detected))

                # Section des actions
                if results.images_extracted:
                    with st.container():
                        st.markdown('<span class="actions-marker"></span>', unsafe_allow_html=True)
                        st.markdown('''
                            <div style="color: #8B949E; 
                                 font-family: 'Inter', sans-serif; 
                                 font-size: 1rem; 
                                 font-weight: 500; 
                                 margin: 0 0 1.5rem 0; 
                                 display: flex; 
                                 align-items: center; 
                                 gap: 0.5rem;">
                                <svg style="width: 16px; height: 16px; stroke: #8B949E;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                                </svg>
                                Actions
                            </div>
                        ''', unsafe_allow_html=True)
                        
                        # Préparer les données du ZIP
                        zip_data = create_zip_from_images(results.images_extracted, manual_name)
                        
                        # Boutons d'action
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.download_button(
                                label=f"TÉLÉCHARGER {len(results.images_extracted)} IMAGES",
                                data=zip_data,
                                file_name=f"{manual_name}_images_completes.zip",
                                mime="application/zip",
                                use_container_width=True,
                                key="download_all_btn"
                            ):
                                st.success(f"✅ Téléchargement de {len(results.images_extracted)} images lancé !")
                        
                        with col2:
                            if st.button(
                                "NOUVEAU DOC",
                                use_container_width=True,
                                key="reset_btn"
                            ):
                                reset_application()
                                st.rerun()

                # Section des images par section
                if results.stats.get('images_by_section'):
                    with st.container():
                        st.markdown('<span class="images-sections-marker"></span>', unsafe_allow_html=True)
                        st.markdown('''
                            <div style="color: #8B949E; 
                                 font-family: 'Inter', sans-serif; 
                                 font-size: 1rem; 
                                 font-weight: 500; 
                                 margin: 0 0 1.5rem 0; 
                                 display: flex; 
                                 align-items: center; 
                                 gap: 0.5rem;">
                                <svg style="width: 16px; height: 16px; stroke: #8B949E;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 011-1h1m-1 1v1m0 0H9m10 0V5a2 2 0 00-1-1h-1m1 1v1m0 0H15"></path>
                                </svg>
                                Images par section
                            </div>
                        ''', unsafe_allow_html=True)
                        
                        # Organiser les images par section
                        images_by_section = {}
                        for img_info in results.images_extracted:
                            section = img_info.get('section', '0')
                            if section not in images_by_section:
                                images_by_section[section] = []
                            images_by_section[section].append(img_info)
                        
                        # Afficher chaque section dans un expander
                        for section in sorted(images_by_section.keys()):
                            section_images = images_by_section[section]
                            count = len(section_images)
                            
                            # Expander moderne avec icône flat
                            with st.expander(f"▸ Section {section} • {count} image{('s' if count > 1 else '')}", expanded=False):
                                
                                # Header compact de la section
                                col_info, col_dl_section = st.columns([2, 1])
                                with col_info:
                                    st.markdown(f"<span style='color: #9CA3AF; font-size: 0.85rem;'>{count} image{('s' if count > 1 else '')} • Section {section}</span>", unsafe_allow_html=True)
                                
                                with col_dl_section:
                                    # Bouton pour télécharger toutes les images de cette section
                                    if count > 1:
                                        section_zip = create_zip_from_images(section_images, f"{manual_name}_section_{section}")
                                        st.download_button(
                                            label="↓ ZIP",
                                            data=section_zip,
                                            file_name=f"{manual_name}_section_{section}.zip",
                                            mime="application/zip",
                                            use_container_width=True,
                                            key=f"section_dl_{section}"
                                        )
                                
                                # Grille d'images sans séparateur
                                cols = st.columns(3)
                                for idx, img_info in enumerate(section_images):
                                    with cols[idx % 3]:
                                        img_path = img_info['path']
                                        if os.path.exists(img_path):
                                            st.image(
                                                img_path,
                                                caption=img_info["filename"],
                                                use_container_width=True
                                            )
                                                
                                            # Bouton de téléchargement compact
                                            with open(img_path, 'rb') as f:
                                                st.download_button(
                                                    label="↓",
                                                    data=f.read(),
                                                    file_name=img_info['filename'],
                                                    mime=f"image/{img_info['filename'].split('.')[-1]}",
                                                    use_container_width=True,
                                                    key=f"img_dl_{section}_{idx}"
                                                )
                                        else:
                                            # Fichier manquant - afficher un message informatif
                                            st.warning(f"⚠️ Fichier manquant: {img_info['filename']}")
                                            st.info("💡 Cliquez sur **NOUVEAU DOC** pour relancer l'extraction")
            else:
                st.error(f"Erreur lors du traitement: {', '.join(results.errors if results.errors else ['Erreur inconnue'])}")

        # Footer avec le nouveau style
        st.markdown(
            '''
            <div style="margin-top: 3rem; padding: 1rem; text-align: center; color: #4C9BE8; opacity: 0.8;">
                Run local : <a href="https://github.com/Orsso/LensCRL" target="_blank" style="color: #4C9BE8; text-decoration: none;">LensCRL</a>
            </div>
            ''',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"Erreur inattendue: {str(e)}")

if __name__ == "__main__":
    main() 