#!/usr/bin/env python3
"""
API Package - LensCRL Backend
=============================

API Backend pour découpler l'extraction d'images PDF de l'interface utilisateur.
"""

# API LensCRL Simple
from .lenscrl_simple import LensCRLSimple

__all__ = ['LensCRLSimple'] 