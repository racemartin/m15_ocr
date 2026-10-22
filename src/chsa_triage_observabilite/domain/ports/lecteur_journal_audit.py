"""
Port générique (F2, instrumentation du trafic réel) : lire les entrées du
journal d'audit de m14_ocr ajoutées depuis la dernière lecture. Un seul
contrat, indépendant de l'endroit où vit réellement le journal (fichier
JSONL local aujourd'hui, potentiellement un dataset Hugging Face demain,
cf. `CHSA_JOURNAL_AUDIT=hf_dataset` déjà supporté par m14_ocr) — même
discipline que `VerificateurConnectivite`.
"""

from __future__ import annotations

from typing import Protocol

from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)


class LecteurJournalAudit(Protocol):
    """Port générique : lire les nouvelles entrées, sans savoir où elles vivent."""

    def lire_nouvelles_entrees(self) -> list[EntreeJournalAudit]:
        """Retourne les entrées ajoutées depuis le dernier appel, jamais les
        mêmes deux fois. Une ligne malformée est ignorée (avec un
        avertissement journalisé), jamais une levée d'exception : une
        source externe imparfaite ne doit jamais interrompre
        l'instrumentation du reste du lot."""
        ...
