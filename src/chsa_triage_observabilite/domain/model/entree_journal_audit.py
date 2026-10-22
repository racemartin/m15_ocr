"""
Une entrée du journal d'audit de m14_ocr, telle que consommée par m15 — un
sous-ensemble volontairement minimal des champs réels (`entree_audit.py`
dans m14_ocr), jamais le dataclass d'origine importé directement : m15
consomme un artefact externe (un fichier), jamais le code interne de
m14_ocr, même à travers une frontière locale.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EntreeJournalAudit:
    """Une ligne JSONL déjà parsée, prête à devenir des métriques."""

    horodatage      : str
    type_evenement  : str   # "tour_entretien" | "diagnostic" | "echec_inference" | ...
    conversation_id : str
    version_modele  : str
    metadonnees     : dict = field(default_factory=dict)
