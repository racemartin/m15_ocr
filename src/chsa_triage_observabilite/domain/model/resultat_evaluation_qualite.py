"""
Résultat d'une évaluation par le juge-LLM (F5, garde-fous) : un score de
sécurité/forme (PAS d'exactitude clinique, voir `docs/00_architecture.md`
"Juge-LLM (F5)") et une justification courte, pour un seul diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultatEvaluationQualite:
    """Ce que le juge-LLM renvoie pour un diagnostic donné.

    `score` : 0 (viole gravement les garde-fous) à 10 (conforme), jamais une
    note d'exactitude médicale — le juge n'a aucune compétence clinique
    validée, seulement un jugement sur la forme et la sécurité du texte
    (recommandation de consulter, absence de langage diagnostique absolu,
    absence de fuite de données personnelles)."""

    score         : float
    justification : str
