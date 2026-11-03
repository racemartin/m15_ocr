"""
Tests de l'adaptateur `JsonlLecteurJournalAudit`, contre un vrai fichier
temporaire (pas de double ici : c'est justement le comportement fichier,
curseur compris, qu'on veut prouver).
"""

from __future__ import annotations

import json
from pathlib import Path

from chsa_triage_observabilite.infrastructure.adapters.jsonl_lecteur_journal_audit import (
    JsonlLecteurJournalAudit,
)

ENTREE_EXEMPLE = {
    "horodatage": "2026-10-21T00:00:00+00:00",
    "type_evenement": "tour_entretien",
    "conversation_id": "conv-1",
    "entree": "...",
    "sortie": "...",
    "version_modele": "mombasstic/chsa-triage-dpo-lora",
    "metadonnees": {"latence_ms": 531.0},
}


def _ecrire_lignes(chemin: Path, *entrees: dict) -> None:
    with chemin.open("a", encoding="utf-8") as f:
        for entree in entrees:
            f.write(json.dumps(entree) + "\n")


def test_fichier_absent_retourne_liste_vide(tmp_path: Path) -> None:
    lecteur = JsonlLecteurJournalAudit(tmp_path / "absent.jsonl")

    assert lecteur.lire_nouvelles_entrees() == []


def test_lit_les_entrees_ecrites(tmp_path: Path) -> None:
    chemin = tmp_path / "journal.jsonl"
    _ecrire_lignes(chemin, ENTREE_EXEMPLE)
    lecteur = JsonlLecteurJournalAudit(chemin)

    entrees = lecteur.lire_nouvelles_entrees()

    assert len(entrees) == 1
    assert entrees[0].type_evenement == "tour_entretien"
    assert entrees[0].metadonnees["latence_ms"] == 531.0
    assert entrees[0].sortie == "..."


def test_ne_relit_jamais_les_memes_lignes_deux_fois(tmp_path: Path) -> None:
    chemin = tmp_path / "journal.jsonl"
    _ecrire_lignes(chemin, ENTREE_EXEMPLE)
    lecteur = JsonlLecteurJournalAudit(chemin)

    premiere_lecture = lecteur.lire_nouvelles_entrees()
    deuxieme_lecture_sans_nouvelle_ligne = lecteur.lire_nouvelles_entrees()

    assert len(premiere_lecture) == 1
    assert deuxieme_lecture_sans_nouvelle_ligne == []


def test_curseur_survit_a_une_nouvelle_instance(tmp_path: Path) -> None:
    """Le curseur est sur disque, pas en mémoire : une nouvelle instance
    (ex. un nouveau processus CLI) reprend où la précédente s'est arrêtée."""
    chemin = tmp_path / "journal.jsonl"
    _ecrire_lignes(chemin, ENTREE_EXEMPLE)
    JsonlLecteurJournalAudit(chemin).lire_nouvelles_entrees()

    _ecrire_lignes(chemin, {**ENTREE_EXEMPLE, "conversation_id": "conv-2"})
    nouvelle_instance = JsonlLecteurJournalAudit(chemin)
    entrees = nouvelle_instance.lire_nouvelles_entrees()

    assert len(entrees) == 1
    assert entrees[0].conversation_id == "conv-2"


def test_ligne_malformee_ignoree_sans_lever_d_exception(tmp_path: Path) -> None:
    chemin = tmp_path / "journal.jsonl"
    with chemin.open("w", encoding="utf-8") as f:
        f.write("{ceci n'est pas du JSON valide\n")
        f.write(json.dumps(ENTREE_EXEMPLE) + "\n")
    lecteur = JsonlLecteurJournalAudit(chemin)

    entrees = lecteur.lire_nouvelles_entrees()

    assert len(entrees) == 1  # la ligne valide est quand même lue
