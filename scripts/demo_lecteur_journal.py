"""
Script de démonstration manuelle (F2) : lit le journal d'audit réel via
`JsonlLecteurJournalAudit` et journalise CHAQUE champ de CHAQUE entrée lue,
un par un — contrairement à `instrumenter-journal`, qui agrège directement
en métriques sans rien afficher d'intermédiaire. Utile pour vérifier à
l'œil ce que le lecteur voit vraiment, avant de faire confiance aux
métriques qui en sortent.

N'appartient PAS au paquet installable (`src/`) : un outil d'inspection
manuelle, jamais appelé par le CLI réel, même distinction que
`scripts/` dans m14_ocr.

Usage :
    uv run python scripts/demo_lecteur_journal.py <chemin_vers_le_jsonl>
    # ou, en reprenant CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT du .env :
    uv run python scripts/demo_lecteur_journal.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from chsa_triage_observabilite.infrastructure.adapters.jsonl_lecteur_journal_audit import (
    JsonlLecteurJournalAudit,
)
from tools.rafael.log_tool import LogTool

log = LogTool(origin="demo")


def _resoudre_chemin_journal() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    load_dotenv()
    chemin = os.environ.get("CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT")
    if not chemin:
        print(
            "Donne le chemin en argument, ou définis "
            "CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT dans .env."
        )
        sys.exit(1)
    return Path(chemin)


def main() -> None:
    chemin_journal = _resoudre_chemin_journal()
    log.STEP(1, "Lecture du journal d'audit", str(chemin_journal))

    lecteur = JsonlLecteurJournalAudit(chemin_journal)
    entrees = lecteur.lire_nouvelles_entrees()

    if not entrees:
        log.LEVEL_6_NOTICE("demo", "Aucune nouvelle entrée depuis le dernier curseur.")
        return

    for index, entree in enumerate(entrees, start=1):
        log.STEP(2, f"Entrée {index}/{len(entrees)}")
        log.PARAMETER_VALUE("horodatage",      entree.horodatage)
        log.PARAMETER_VALUE("type_evenement",  entree.type_evenement)
        log.PARAMETER_VALUE("conversation_id", entree.conversation_id)
        log.PARAMETER_VALUE("version_modele",  entree.version_modele)
        log.LOG_DICT(entree.metadonnees, "metadonnees")

    log.LEVEL_6_NOTICE("demo", f"{len(entrees)} entrée(s) affichée(s) au total.")


if __name__ == "__main__":
    main()
