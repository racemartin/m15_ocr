"""
Tests de l'adaptateur `FichierAccumulateurConversations`, contre un vrai
fichier temporaire — même esprit que `test_jsonl_lecteur_journal_audit.py`.
"""

from __future__ import annotations

from pathlib import Path

from chsa_triage_observabilite.infrastructure.adapters.fichier_accumulateur_conversations import (
    FichierAccumulateurConversations,
)


def test_cloturer_conversation_jamais_enregistree_retourne_none(tmp_path: Path) -> None:
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")

    assert accumulateur.cloturer_conversation("inconnue") is None


def test_un_seul_tour_puis_cloture(tmp_path: Path) -> None:
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")

    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:00:00+00:00")
    etat = accumulateur.cloturer_conversation("conv-1")

    assert etat is not None
    assert etat.nombre_tours == 1
    assert etat.horodatage_premier_tour == "2026-10-21T10:00:00+00:00"


def test_trois_tours_comptes_correctement(tmp_path: Path) -> None:
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")

    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:00:00+00:00")
    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:01:00+00:00")
    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:02:00+00:00")
    etat = accumulateur.cloturer_conversation("conv-1")

    assert etat is not None
    assert etat.nombre_tours == 3
    # L'horodatage retenu est celui du PREMIER tour, jamais le dernier.
    assert etat.horodatage_premier_tour == "2026-10-21T10:00:00+00:00"


def test_cloturer_retire_l_etat_pas_de_double_comptage(tmp_path: Path) -> None:
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")
    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:00:00+00:00")
    accumulateur.cloturer_conversation("conv-1")

    deuxieme_cloture = accumulateur.cloturer_conversation("conv-1")

    assert deuxieme_cloture is None


def test_etat_survit_a_une_nouvelle_instance(tmp_path: Path) -> None:
    """Le fichier JSON est sur disque, pas en mémoire : une nouvelle
    instance (nouveau processus CLI) reprend l'état déjà accumulé."""
    chemin = tmp_path / "etat.json"
    FichierAccumulateurConversations(chemin).enregistrer_tour(
        "conv-1", "2026-10-21T10:00:00+00:00"
    )

    nouvelle_instance = FichierAccumulateurConversations(chemin)
    etat = nouvelle_instance.cloturer_conversation("conv-1")

    assert etat is not None
    assert etat.nombre_tours == 1


def test_echec_puis_cloture_restitue_a_eu_un_echec(tmp_path: Path) -> None:
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")

    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:00:00+00:00")
    accumulateur.enregistrer_echec("conv-1", "2026-10-21T10:01:00+00:00")
    etat = accumulateur.cloturer_conversation("conv-1")

    assert etat is not None
    assert etat.a_eu_un_echec is True


def test_sans_echec_cloture_restitue_a_eu_un_echec_false(tmp_path: Path) -> None:
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")

    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:00:00+00:00")
    etat = accumulateur.cloturer_conversation("conv-1")

    assert etat is not None
    assert etat.a_eu_un_echec is False


def test_echec_en_tout_premier_evenement_cree_la_conversation(tmp_path: Path) -> None:
    """Le tout premier message échoue avant tout tour réussi : l'horodatage
    de l'échec sert de repli pour `horodatage_premier_tour`."""
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")

    accumulateur.enregistrer_echec("conv-1", "2026-10-21T10:00:00+00:00")
    etat = accumulateur.cloturer_conversation("conv-1")

    assert etat is not None
    assert etat.nombre_tours == 0
    assert etat.horodatage_premier_tour == "2026-10-21T10:00:00+00:00"
    assert etat.a_eu_un_echec is True


def test_deux_conversations_independantes(tmp_path: Path) -> None:
    accumulateur = FichierAccumulateurConversations(tmp_path / "etat.json")

    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:00:00+00:00")
    accumulateur.enregistrer_tour("conv-2", "2026-10-21T11:00:00+00:00")
    accumulateur.enregistrer_tour("conv-1", "2026-10-21T10:01:00+00:00")

    etat_1 = accumulateur.cloturer_conversation("conv-1")
    etat_2 = accumulateur.cloturer_conversation("conv-2")

    assert etat_1 is not None and etat_1.nombre_tours == 2
    assert etat_2 is not None and etat_2.nombre_tours == 1
