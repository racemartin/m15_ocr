"""
Résultat d'une vérification de connectivité (équivalent healthcheck pour
une dépendance externe : API, dataset HF, instance MLflow...). Zéro
dépendance externe, même discipline que le reste de `domain/`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultatVerification:
    """Un résultat de vérification, indépendant de la dépendance vérifiée."""

    nom             : str    # Nom lisible de la dépendance (ex. "Hugging Face Hub")
    disponible      : bool   # True si la dépendance est accessible et authentifiée
    detail          : str    # Message court, toujours rempli (succès ou raison d'échec)
    duree_ms        : float  # Temps de la vérification, pour détecter une dépendance lente
