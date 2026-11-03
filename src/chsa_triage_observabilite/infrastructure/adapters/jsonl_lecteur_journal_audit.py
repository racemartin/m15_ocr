"""
Adaptateur du port `LecteurJournalAudit` : lit un fichier JSONL local écrit
par m14_ocr (`CHSA_CHEMIN_JOURNAL_AUDIT`), en mémorisant un curseur d'octets
entre deux appels — y compris entre deux exécutions du processus, puisque
`instrumenter-journal` est un CLI ponctuel, pas un service qui tourne en
continu. Fonctionne SEULEMENT si m15 tourne sur la même machine que m14_ocr
(frontière locale, voir `docs/00_architecture.md` "Accès au journal
d'audit"), contrairement à `UrlVerificateurConnectivite`, qui lui
fonctionne même à distance.
"""

from __future__ import annotations

import json
from pathlib import Path

from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)
from tools.rafael.log_tool import LogTool


class JsonlLecteurJournalAudit:
    """Implémente `LecteurJournalAudit` pour un fichier JSONL local."""

    def __init__(self, chemin_journal: str | Path, chemin_curseur: str | Path | None = None) -> None:
        self._chemin_journal = Path(chemin_journal)
        self._chemin_curseur = (
            Path(chemin_curseur)
            if chemin_curseur
            else self._chemin_journal.with_name(self._chemin_journal.name + ".curseur")
        )
        self._log = LogTool(origin="infrastructure")

    # #########################################################################
    # Lit depuis le curseur mémorisé jusqu'à la fin du fichier, parse chaque
    # ligne JSON, et avance le curseur d'autant. Un fichier absent (m14_ocr
    # pas encore démarré, ou aucun tour encore enregistré) retourne une
    # liste vide, jamais une erreur.
    # #########################################################################
    def lire_nouvelles_entrees(self) -> list[EntreeJournalAudit]:
        self._log.START_CALL_MANAGER_FUNCTION(
            "JsonlLecteurJournalAudit", "lire_nouvelles_entrees", str(self._chemin_journal)
        )

        if not self._chemin_journal.exists():
            self._log.FINISH_CALL_MANAGER_FUNCTION(
                "JsonlLecteurJournalAudit", "lire_nouvelles_entrees", "fichier absent, 0 entrée"
            )
            return []

        offset_depart = self._lire_curseur()
        entrees: list[EntreeJournalAudit] = []
        lignes_malformees = 0

        with self._chemin_journal.open("rb") as f:
            f.seek(offset_depart)
            for ligne_brute in f:
                ligne = ligne_brute.decode("utf-8").strip()
                if not ligne:
                    continue
                try:
                    donnees = json.loads(ligne)
                except json.JSONDecodeError:
                    lignes_malformees += 1
                    continue
                entrees.append(
                    EntreeJournalAudit(
                        horodatage      = donnees.get("horodatage", ""),
                        type_evenement  = donnees.get("type_evenement", ""),
                        conversation_id = donnees.get("conversation_id", ""),
                        version_modele  = donnees.get("version_modele", ""),
                        metadonnees     = donnees.get("metadonnees", {}),
                        sortie          = donnees.get("sortie", ""),
                    )
                )
            nouvel_offset = f.tell()

        self._ecrire_curseur(nouvel_offset)

        if lignes_malformees:
            self._log.LEVEL_5_WARNING(
                "JsonlLecteurJournalAudit",
                f"{lignes_malformees} ligne(s) JSON malformée(s) ignorée(s)",
            )
        self._log.FINISH_CALL_MANAGER_FUNCTION(
            "JsonlLecteurJournalAudit",
            "lire_nouvelles_entrees",
            f"{len(entrees)} nouvelle(s) entrée(s)",
        )
        return entrees

    # -------------------------------------------------------------------------
    def _lire_curseur(self) -> int:
        if not self._chemin_curseur.exists():
            return 0
        try:
            return int(self._chemin_curseur.read_text(encoding="utf-8").strip())
        except ValueError:
            return 0

    def _ecrire_curseur(self, offset: int) -> None:
        self._chemin_curseur.write_text(str(offset), encoding="utf-8")
