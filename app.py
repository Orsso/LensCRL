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

# Configuration de la page
st.set_page_config(
    page_title="LensCRL Simple",
    page_icon="🔍",
    layout="wide",
)

# Styles CSS personnalisés
st.markdown("""
<style>
    /* Import de Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Import Feather Icons */
    @import url('https://cdn.jsdelivr.net/npm/feather-icons@4.29.0/dist/feather.min.css');
    
    /* Reset et base */
    .main {
        padding: 1.5rem 2rem;
        max-width: 1200px;
        margin: 0 auto;
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
        width: 40px;
        height: 40px;
        filter: drop-shadow(0 2px 8px rgba(76, 155, 232, 0.3));
    }
    
    .app-title {
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
        font-size: 2.25rem;
        font-weight: 600;
        margin: 0;
        letter-spacing: -0.025em;
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
    
    /* Sections */
    .section-header {
        color: #4C9BE8;
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        font-weight: 600;
        margin: 2.5rem 0 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding-left: 0.5rem;
        border-left: 3px solid #4C9BE8;
        background: linear-gradient(90deg, rgba(76, 155, 232, 0.1) 0%, transparent 100%);
        padding: 0.75rem 0 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        position: relative;
    }
    
    /* Icônes pour les sections avec Feather Icons */
    .section-header .icon {
        width: 20px;
        height: 20px;
        stroke: #4C9BE8;
        stroke-width: 2;
        margin-right: 0.5rem;
    }
    
    /* Fix hover rouge sur tous les éléments */
    .stButton > button, .stButton > button:hover, .stButton > button:focus, .stButton > button:active {
        color: white !important;
    }
    
    .stDownloadButton > button, .stDownloadButton > button:hover, .stDownloadButton > button:focus, .stDownloadButton > button:active {
        color: white !important;
    }
    
    /* Expander fix */
    .streamlit-expanderHeader, .streamlit-expanderHeader:hover, .streamlit-expanderHeader:focus {
        color: #E6EDF3 !important;
    }
    
    .streamlit-expanderContent {
        color: #E6EDF3 !important;
    }
    
    /* Text content color fixes */
    .main, .main p, .main div, .main span {
        color: #E6EDF3 !important;
    }
    
    /* Metrics text */
    .stMetric .metric-label, .stMetric .metric-value {
        color: inherit !important;
    }
    
    /* Expanders styles modernes et compacts */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #1F2937 0%, #374151 100%);
        border: 1px solid rgba(76, 155, 232, 0.3);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        margin-bottom: 0.5rem;
        color: #E6EDF3 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }
    .streamlit-expanderHeader:hover {
        border-color: rgba(76, 155, 232, 0.6);
        background: linear-gradient(135deg, #374151 0%, #4B5563 100%);
        color: #E6EDF3 !important;
        box-shadow: 0 2px 6px rgba(76, 155, 232, 0.15);
        transform: translateY(-1px);
    }
    
    /* Force expander text color on all states */
    .streamlit-expanderHeader, 
    .streamlit-expanderHeader:hover, 
    .streamlit-expanderHeader:focus,
    .streamlit-expanderHeader * {
        color: #E6EDF3 !important;
    }
    
    /* Expander arrow color */
    .streamlit-expanderHeader svg {
        stroke: #4C9BE8 !important;
        width: 16px;
        height: 16px;
    }
    
    .streamlit-expanderContent {
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-top: none;
        border-radius: 0 0 8px 8px;
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.4) 0%, rgba(55, 65, 81, 0.2) 100%);
        padding: 1rem;
        margin-top: -0.5rem;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Boutons */
    .stButton > button {
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%);
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 0.875rem 2rem;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(76, 155, 232, 0.25);
        text-transform: none;
        letter-spacing: 0.025em;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        box-shadow: 0 6px 20px rgba(76, 155, 232, 0.4);
        transform: translateY(-2px);
        color: white !important;
    }
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 8px rgba(76, 155, 232, 0.3);
        color: white !important;
    }
    .stButton > button:focus {
        outline: none;
        color: white !important;
        box-shadow: 0 0 0 2px rgba(76, 155, 232, 0.5);
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
    
    /* Section download button special styling */
    .section-download-btn .stDownloadButton > button {
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%);
        color: white !important;
        font-size: 0.85rem;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        min-height: 32px;
    }
    .section-download-btn .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white !important;
    }
    
    /* Individual image download buttons */
    .image-download-btn .stDownloadButton > button {
        background: linear-gradient(135deg, #6B7280 0%, #4B5563 100%);
        color: white !important;
        font-size: 0.8rem;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        width: 100%;
        min-height: 28px;
    }
    .image-download-btn .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #4B5563 0%, #374151 100%);
        color: white !important;
    }
    
    /* Bouton reset spécial */
    .stButton > button[data-testid*="reset"] {
        background: linear-gradient(135deg, #6B7280 0%, #4B5563 100%);
        color: white !important;
    }
    .stButton > button[data-testid*="reset"]:hover {
        background: linear-gradient(135deg, #4B5563 0%, #374151 100%);
        color: white !important;
    }
    
    /* Remove default Streamlit button styles that cause red text */
    .stButton > button, .stDownloadButton > button {
        background-color: transparent !important;
        border-color: transparent !important;
    }
    
    /* Force white text on all button states */
    .stButton > button *, .stDownloadButton > button * {
        color: white !important;
    }
    
    /* Bouton désactivé */
    .stButton > button:disabled {
        background: linear-gradient(135deg, #6B7280 0%, #4B5563 100%);
        color: #9CA3AF !important;
        cursor: not-allowed;
        box-shadow: none;
        transform: none;
        opacity: 0.7;
    }
    .stButton > button:disabled:hover {
        background: linear-gradient(135deg, #6B7280 0%, #4B5563 100%);
        color: #9CA3AF !important;
        transform: none;
        box-shadow: none;
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
    
    /* Checkbox */
    .stCheckbox > label {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: #E6EDF3;
    }
    
    /* Checkbox custom styling */
    .stCheckbox > label > span:first-child {
        background-color: transparent;
        border: 2px solid #4C9BE8;
        border-radius: 4px;
        width: 18px;
        height: 18px;
    }
    
    .stCheckbox > label > span:first-child[data-checked="true"] {
        background-color: #4C9BE8;
        border-color: #4C9BE8;
    }
    
    .stCheckbox > label > span:first-child[data-checked="true"]::after {
        content: "✓";
        color: white;
        font-size: 12px;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
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
    
    /* Checkbox label text color fix */
    .stCheckbox > label, .stCheckbox > label * {
        color: #E6EDF3 !important;
    }
    
    /* Text input labels */
    .stTextInput > label, .stTextInput > label * {
        color: #E6EDF3 !important;
    }
    
    /* File uploader labels and help text */
    .stFileUploader > label, .stFileUploader > label *,
    .stFileUploader > div, .stFileUploader > div * {
        color: #E6EDF3 !important;
    }
    
    /* Spinner text */
    .stSpinner > div {
        color: #E6EDF3 !important;
    }
    
    /* All paragraph and div text */
    p, div, span, label {
        color: #E6EDF3 !important;
    }
    
    /* Force all Streamlit widget text to be visible */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] div,
    [data-testid="stMarkdownContainer"] span {
        color: #E6EDF3 !important;
    }
    
    /* Images dans les sections - style moderne et compact */
    .section-image-container {
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.6) 0%, rgba(55, 65, 81, 0.4) 100%);
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.75rem;
        border: 1px solid rgba(76, 155, 232, 0.15);
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .section-image-container:hover {
        border-color: rgba(76, 155, 232, 0.3);
        background: linear-gradient(135deg, rgba(55, 65, 81, 0.7) 0%, rgba(75, 85, 99, 0.5) 100%);
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(76, 155, 232, 0.1);
    }
    
    /* Filename styling moderne */
    .image-filename {
        font-size: 0.75rem;
        color: #D1D5DB;
        font-family: 'Inter', sans-serif;
        background: rgba(17, 24, 39, 0.8);
        padding: 0.4rem 0.6rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        border-left: 2px solid #4C9BE8;
        word-break: break-all;
        font-weight: 500;
    }
    
    /* Footer */
    .app-footer {
        text-align: center;
        padding: 2rem 0;
        margin-top: 3rem;
        border-top: 1px solid rgba(76, 155, 232, 0.15);
        color: #8B949E;
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
    }
    .app-footer a {
        color: #4C9BE8;
        text-decoration: none;
        font-weight: 500;
        transition: color 0.3s ease;
    }
    .app-footer a:hover {
        color: #58A6FF;
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
        .section-header {
            font-size: 1.1rem;
        }
    }
    
    /* Sections détectées */
    .sections-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin: 1.5rem 0;
    }
    
    .section-card {
        background: linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    .section-card:hover {
        border-color: rgba(76, 155, 232, 0.4);
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    
    .section-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid rgba(76, 155, 232, 0.15);
    }
    
    .section-title {
        color: #4C9BE8;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.1rem;
        margin: 0;
    }
    
    .section-count {
        background: linear-gradient(135deg, #4C9BE8 0%, #3B82F6 100%);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        box-shadow: 0 2px 6px rgba(76, 155, 232, 0.3);
    }
    
    .section-preview {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.5rem;
        margin-top: 0.75rem;
    }
    
    .section-preview img {
        width: 100%;
        height: 60px;
        object-fit: cover;
        border-radius: 6px;
        border: 1px solid rgba(76, 155, 232, 0.2);
        transition: all 0.2s ease;
    }
    
    .section-preview img:hover {
        border-color: rgba(76, 155, 232, 0.5);
        transform: scale(1.05);
    }
    
    .section-more {
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(76, 155, 232, 0.1);
        border: 1px dashed rgba(76, 155, 232, 0.3);
        border-radius: 6px;
        height: 60px;
        color: #4C9BE8;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Stats cards */
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 1.5rem 0;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%);
        border: 1px solid rgba(76, 155, 232, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    .stat-card:hover {
        border-color: rgba(76, 155, 232, 0.4);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #4C9BE8;
        font-family: 'Inter', sans-serif;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        color: #8B949E;
        font-size: 0.9rem;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
    }
    
    /* Override any default Streamlit red colors on expanders */
    [data-testid="stExpander"] * {
        color: #E6EDF3 !important;
    }
    
    [data-testid="stExpander"] summary:hover {
        color: #E6EDF3 !important;
        background-color: rgba(76, 155, 232, 0.1) !important;
    }
    
    [data-testid="stExpander"] summary:hover * {
        color: #E6EDF3 !important;
    }
    
    /* Remove any red text decoration */
    [data-testid="stExpander"] a,
    [data-testid="stExpander"] a:hover,
    [data-testid="stExpander"] a:visited,
    [data-testid="stExpander"] a:active {
        color: #4C9BE8 !important;
        text-decoration: none !important;
    }
    
    /* Boutons d'action principaux - style carré et imposant */
    .action-buttons-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin: 2.5rem 0;
        padding: 1.5rem;
    }
    
    /* Download button - GROS BOUTON CARRÉ VERT */
    .main-download-btn .stDownloadButton > button {
        background: linear-gradient(135deg, #16A085 0%, #27AE60 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        box-shadow: 0 12px 24px rgba(22, 160, 133, 0.4) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        width: 100% !important;
        height: 100px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 1rem !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .main-download-btn .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #27AE60 0%, #2ECC71 100%) !important;
        box-shadow: 0 16px 32px rgba(22, 160, 133, 0.6) !important;
        transform: translateY(-6px) scale(1.02) !important;
        color: white !important;
    }
    
    .main-download-btn .stDownloadButton > button:active {
        transform: translateY(-3px) scale(1.01) !important;
        box-shadow: 0 8px 16px rgba(22, 160, 133, 0.4) !important;
        color: white !important;
    }
    
    /* Reset button - GROS BOUTON CARRÉ ROUGE */
    .main-reset-btn .stButton > button {
        background: linear-gradient(135deg, #E74C3C 0%, #C0392B 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        box-shadow: 0 12px 24px rgba(231, 76, 60, 0.4) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        width: 100% !important;
        height: 100px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 1rem !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .main-reset-btn .stButton > button:hover {
        background: linear-gradient(135deg, #C0392B 0%, #A93226 100%) !important;
        box-shadow: 0 16px 32px rgba(231, 76, 60, 0.6) !important;
        transform: translateY(-6px) scale(1.02) !important;
        color: white !important;
    }
    
    .main-reset-btn .stButton > button:active {
        transform: translateY(-3px) scale(1.01) !important;
        box-shadow: 0 8px 16px rgba(231, 76, 60, 0.4) !important;
        color: white !important;
    }
    
    /* Force la même hauteur pour tous les boutons d'action */
    .main-download-btn .stDownloadButton > button,
    .main-reset-btn .stButton > button {
        min-height: 100px !important;
        max-height: 100px !important;
    }
    
    /* Ajout d'effets de brillance */
    .main-download-btn .stDownloadButton > button::after,
    .main-reset-btn .stButton > button::after {
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .main-download-btn .stDownloadButton > button:hover::after,
    .main-reset-btn .stButton > button:hover::after {
        left: 100%;
    }
    
    /* Note: Icônes ajoutées directement dans les labels des boutons via emojis */
</style>
""", unsafe_allow_html=True)

# Cache pour stocker les résultats du traitement
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
    
if 'processing_results' not in st.session_state:
    st.session_state.processing_results = None

if 'reset_app' not in st.session_state:
    st.session_state.reset_app = False

def reset_application():
    st.session_state.reset_app = True
    st.session_state.is_processing = False
    # Incrémenter la clé du file uploader pour le forcer à se reset
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
    st.session_state.file_uploader_key += 1

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

    # Initialisation et exécution de LensCRL - DEBUG ACTIVÉ PAR DÉFAUT
    processor = LensCRLSimple(debug=True)
    st.write("🔍 **Mode debug activé** - Vérifiez la console pour les détails")
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
        st.session_state.is_processing = False
        st.session_state.reset_app = False
        st.rerun()
    
    # Initialiser la clé du file uploader si elle n'existe pas
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0
    
    try:
        # En-tête avec logo
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

        # Zone de dépôt du fichier PDF
        st.markdown('''
            <p class="section-header">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                Sélection du fichier
            </p>
        ''', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Choisissez un fichier PDF",
            type="pdf",
            help="Déposez votre fichier PDF ici",
            key=f'file_uploader_{st.session_state.file_uploader_key}'
        )

        if uploaded_file:
            # Configuration de la nomenclature
            st.markdown('''
                <p class="section-header">
                    <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a.997.997 0 01-1.414 0l-7-7A1.997 1.997 0 014 12V7a4 4 0 014-4z"></path>
                    </svg>
                    Configuration de la nomenclature
                </p>
            ''', unsafe_allow_html=True)
            
            # Configuration du préfixe
            prefix = st.text_input(
                "Préfixe",
                value="CRL",
                help="Préfixe utilisé pour tous les fichiers (par défaut: CRL)"
            )

            # Détection automatique améliorée du nom du manuel
            with st.spinner("Détection du nom du manuel..."):
                # Sauvegarder temporairement le PDF pour la détection
                temp_pdf_path = Path(st.session_state.temp_dir) / uploaded_file.name
                with open(temp_pdf_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                # Utiliser la nouvelle fonction de détection
                processor = LensCRLSimple(debug=False)
                detected_name = processor._deduce_manual_name(str(temp_pdf_path))
                
                # Nettoyer le fichier temporaire
                temp_pdf_path.unlink()

            # Configuration du nom avec affichage du type de détection
            st.markdown('''
                <div style="background: linear-gradient(90deg, rgba(46, 125, 50, 0.15), rgba(76, 155, 232, 0.15)); 
                     border-left: 4px solid #4C9BE8; padding: 1rem; margin: 1rem 0; border-radius: 0.5rem;
                     border: 1px solid rgba(76, 155, 232, 0.3);">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <svg style="width: 16px; height: 16px; color: #4C9BE8;" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/>
                        </svg>
                        <strong style="color: #E6EDF3;">Nom détecté automatiquement</strong>
                    </div>
                    <div style="font-family: 'Courier New', monospace; font-size: 1.1em; color: #4C9BE8; 
                         background: rgba(13, 17, 23, 0.8); padding: 0.5rem; border-radius: 4px; border-left: 2px solid #4C9BE8;">''' + detected_name + '''</div>
                </div>
            ''', unsafe_allow_html=True)

            # Checkbox pour utiliser le nom détecté ou personnalisé
            use_detected = st.checkbox(
                f"Utiliser le nom détecté : **{detected_name}**", 
                value=True,
                help="Nom détecté depuis les footers, métadonnées ou nom de fichier"
            )
            
            # Champ de saisie personnalisé (affiché seulement si pas de détection automatique)
            manual_name = detected_name
            if not use_detected:
                manual_name = st.text_input(
                    "Nom personnalisé",
                    value=detected_name,
                    help="Ex: PROCSG02, OMA, STC, etc."
                )
                st.info(f"Nom utilisé : **{manual_name}**")
            else:
                st.success(f"Nom utilisé : **{detected_name}**")

            # Aperçu de la nomenclature
            st.markdown(
                f'''
                <div class="preview-container">
                    <div class="preview-title">Aperçu de la nomenclature</div>
                    <div class="preview-code">{prefix}-{manual_name}-1.1 n_1.png</div>
                </div>
                ''',
                unsafe_allow_html=True
            )

            # Bouton pour lancer le traitement
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                # État de traitement
                if 'is_processing' not in st.session_state:
                    st.session_state.is_processing = False
                
                process_button = st.button(
                    "Lancer le traitement", 
                    use_container_width=True
                )

            if process_button:
                # Création du dossier de sortie
                output_dir = Path(st.session_state.temp_dir) / "output"
                output_dir.mkdir(exist_ok=True)

                # Si nouveau fichier ou changement d'options, retraiter
                current_file_hash = hash(uploaded_file.getvalue())
                cache_key = (current_file_hash, prefix, manual_name)
                
                if 'last_process_key' not in st.session_state or st.session_state.last_process_key != cache_key:
                    with st.spinner("Traitement en cours..."):
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

            # Afficher les résultats s'ils existent
            if 'processing_results' in st.session_state and st.session_state.processing_results:
                results = st.session_state.processing_results
                
                if results.success:
                    # Affichage des résultats
                    st.markdown('''
                        <p class="section-header">
                            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                            </svg>
                            Résultats
                        </p>
                    ''', unsafe_allow_html=True)
                    
                    # Stats principales
                    st.markdown(
                        f'''
                        <div class="stats-container">
                            <div class="stat-card">
                                <div class="stat-value">{len(results.images_extracted)}</div>
                                <div class="stat-label">Images extraites</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{len(results.images_filtered)}</div>
                                <div class="stat-label">Images filtrées</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">{len(results.sections_detected)}</div>
                                <div class="stat-label">Sections détectées</div>
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )

                    # Boutons d'action directement après les résultats
                    if results.images_extracted:
                        st.markdown('''
                            <p class="section-header">
                                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                                </svg>
                                Actions
                            </p>
                        ''', unsafe_allow_html=True)
                        
                        # Container pour boutons d'action uniformes
                        st.markdown('<div class="action-buttons-container">', unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2, gap="large")
                        with col1:
                            st.markdown('<div class="main-download-btn">', unsafe_allow_html=True)
                            zip_data = create_zip_from_images(results.images_extracted, manual_name)
                            
                            # Bouton avec icône SVG intégrée
                            download_label = '''
                            <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem;">
                                <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                                </svg>
                                <span>Télécharger</span>
                            </div>
                            '''
                            st.markdown(download_label, unsafe_allow_html=True)
                            
                            st.download_button(
                                label="TÉLÉCHARGER TOUT",
                                data=zip_data,
                                file_name=f"{manual_name}_images_completes.zip",
                                mime="application/zip",
                                use_container_width=True,
                                help=f"Télécharger {len(results.images_extracted)} images en ZIP"
                            )
                            st.markdown('</div>', unsafe_allow_html=True)
                            
                        with col2:
                            st.markdown('<div class="main-reset-btn">', unsafe_allow_html=True)
                            
                            # Bouton avec icône SVG intégrée  
                            reset_label = '''
                            <div style="display: flex; align-items: center; justify-content: center; gap: 0.75rem;">
                                <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                </svg>
                                <span>Nouveau scan</span>
                            </div>
                            '''
                            st.markdown(reset_label, unsafe_allow_html=True)
                            
                            st.button(
                                "NOUVEAU DOCUMENT", 
                                on_click=reset_application, 
                                use_container_width=True,
                                help="Recommencer avec un nouveau PDF"
                            )
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Affichage des sections avec images dans des expanders
                    if results.stats.get('images_by_section'):
                        st.markdown('''
                            <p class="section-header">
                                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 011-1h1m-1 1v1m0 0H9m10 0V5a2 2 0 00-1-1h-1m1 1v1m0 0H15"></path>
                                </svg>
                                Images par section
                            </p>
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
                                        st.markdown('<div class="section-download-btn">', unsafe_allow_html=True)
                                        section_zip = create_zip_from_images(section_images, f"{manual_name}_section_{section}")
                                        st.download_button(
                                            label="↓ ZIP",
                                            data=section_zip,
                                            file_name=f"{manual_name}_section_{section}.zip",
                                            mime="application/zip",
                                            use_container_width=True,
                                            key=f"section_dl_{section}"
                                        )
                                        st.markdown('</div>', unsafe_allow_html=True)
                                
                                # Grille d'images sans séparateur
                                cols = st.columns(3)
                                for idx, img_info in enumerate(section_images):
                                    with cols[idx % 3]:
                                        img_path = img_info['path']
                                        if os.path.exists(img_path):
                                            # Container moderne pour l'image
                                            st.markdown('<div class="section-image-container">', unsafe_allow_html=True)
                                            
                                            # Image avec un style moderne
                                            st.image(
                                                img_path,
                                                caption=None,
                                                use_container_width=True
                                            )
                                            
                                            # Filename compact avec icône moderne
                                            st.markdown(
                                                f'''<div class="image-filename">
                                                    <span style="color: #4C9BE8;">◦</span> {img_info["filename"]}
                                                </div>''',
                                                unsafe_allow_html=True
                                            )
                                            
                                            # Bouton de téléchargement compact
                                            st.markdown('<div class="image-download-btn">', unsafe_allow_html=True)
                                            with open(img_path, 'rb') as f:
                                                st.download_button(
                                                    label="↓",
                                                    data=f.read(),
                                                    file_name=img_info['filename'],
                                                    mime=f"image/{img_info['filename'].split('.')[-1]}",
                                                    use_container_width=True,
                                                    key=f"img_dl_{section}_{idx}"
                                                )
                                            st.markdown('</div>', unsafe_allow_html=True)
                                            
                                            st.markdown('</div>', unsafe_allow_html=True)
                
                else:
                    if st.session_state.processing_results:
                        st.error(f"Erreur lors du traitement: {', '.join(st.session_state.processing_results.errors if st.session_state.processing_results.errors else ['Erreur inconnue'])}")
                    else:
                        st.error("Erreur lors du traitement du PDF")

        # Footer
        st.markdown(
            '''
            <div class="app-footer">
                Made with <a href="https://github.com/Orsso/LensCRL" target="_blank">LensCRL</a>
            </div>
            ''',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"Erreur inattendue: {str(e)}")

if __name__ == "__main__":
    main() 