"""
Tests du cas d'usage `ServiceAnalyseConversations`, avec des doublures en
mémoire — même discipline que les autres cas d'usage de ce projet.
"""

from __future__ import annotations

from chsa_triage_observabilite.application.services.service_analyse_conversations import (
    ServiceAnalyseConversations,
)
from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)
from chsa_triage_observabilite.domain.model.etat_conversation_accumule import (
    EtatConversationAccumule,
)


class FauxLecteurJournalAudit:
    def __init__(self, entrees: list[EntreeJournalAudit]) -> None:
        self._entrees = entrees

    def lire_nouvelles_entrees(self) -> list[EntreeJournalAudit]:
        return self._entrees


class FauxAccumulateurConversations:
    """Doublure en mémoire, même contrat que `FichierAccumulateurConversations`."""

    def __init__(self) -> None:
        self._etats: dict[str, dict] = {}

    def enregistrer_tour(self, conversation_id: str, horodatage: str) -> None:
        conv = self._etats.setdefault(
            conversation_id,
            {"nombre_tours": 0, "horodatage_premier_tour": horodatage, "a_eu_un_echec": False},
        )
        conv["nombre_tours"] += 1

    def enregistrer_echec(self, conversation_id: str, horodatage: str) -> None:
        conv = self._etats.setdefault(
            conversation_id,
            {"nombre_tours": 0, "horodatage_premier_tour": horodatage, "a_eu_un_echec": False},
        )
        conv["a_eu_un_echec"] = True

    def cloturer_conversation(self, conversation_id: str) -> EtatConversationAccumule | None:
        conv = self._etats.pop(conversation_id, None)
        if conv is None:
            return None
        return EtatConversationAccumule(**conv)


class FauxExportateurMetriques:
    def __init__(self) -> None:
        self.compteurs_incrementes : list[tuple[str, dict]] = []
        self.durees_observees      : list[tuple[str, float, dict]] = []

    def incrementer_compteur(self, nom: str, etiquettes: dict | None = None) -> None:
        self.compteurs_incrementes.append((nom, etiquettes or {}))

    def observer_duree(
        self, nom: str, duree_secondes: float, etiquettes: dict | None = None
    ) -> None:
        self.durees_observees.append((nom, duree_secondes, etiquettes or {}))


def _entree(
    type_evenement: str, conversation_id: str = "conv-1", horodatage: str = "2026-10-21T10:00:00+00:00"
) -> EntreeJournalAudit:
    return EntreeJournalAudit(
        horodatage=horodatage,
        type_evenement=type_evenement,
        conversation_id=conversation_id,
        version_modele="mombasstic/chsa-triage-dpo-lora",
        metadonnees={},
    )


def test_tour_entretien_accumule_sans_emettre_de_metrique() -> None:
    accumulateur = FauxAccumulateurConversations()
    exportateur  = FauxExportateurMetriques()
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit([_entree("tour_entretien")]), accumulateur, exportateur
    )

    nombre_cloturees = service.executer()

    assert nombre_cloturees == 0
    assert exportateur.durees_observees == []
    assert exportateur.compteurs_incrementes == []


def test_diagnostic_cloture_et_emet_nombre_tours_et_temps() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [
        _entree("tour_entretien", horodatage="2026-10-21T10:00:00+00:00"),
        _entree("tour_entretien", horodatage="2026-10-21T10:01:00+00:00"),
        _entree("diagnostic", horodatage="2026-10-21T10:03:00+00:00"),
    ]
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit(entrees), FauxAccumulateurConversations(), exportateur
    )

    nombre_cloturees = service.executer()

    assert nombre_cloturees == 1
    noms_observes = [nom for nom, _, _ in exportateur.durees_observees]
    assert "chsa_conversation_nombre_tours" in noms_observes
    assert "chsa_conversation_temps_diagnostic_secondes" in noms_observes

    valeur_nombre_tours = next(
        v for nom, v, _ in exportateur.durees_observees if nom == "chsa_conversation_nombre_tours"
    )
    assert valeur_nombre_tours == 2.0

    valeur_temps = next(
        v for nom, v, _ in exportateur.durees_observees
        if nom == "chsa_conversation_temps_diagnostic_secondes"
    )
    assert valeur_temps == 180.0  # 10:00:00 -> 10:03:00


def test_diagnostic_sans_tour_connu_n_emet_rien() -> None:
    """Conversation commencée avant que ce service ne tourne : pas de
    donnée à agréger, jamais une valeur inventée."""
    exportateur = FauxExportateurMetriques()
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit([_entree("diagnostic")]),
        FauxAccumulateurConversations(),
        exportateur,
    )

    nombre_cloturees = service.executer()

    assert nombre_cloturees == 0
    assert exportateur.durees_observees == []


def test_diagnostic_reformule_incremente_un_compteur_dedie() -> None:
    exportateur = FauxExportateurMetriques()
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit([_entree("diagnostic_reformule")]),
        FauxAccumulateurConversations(),
        exportateur,
    )

    service.executer()

    noms = [nom for nom, _ in exportateur.compteurs_incrementes]
    assert "chsa_conversation_reformulation_total" in noms


def test_echec_inference_accumule_sans_emettre_de_metrique() -> None:
    accumulateur = FauxAccumulateurConversations()
    exportateur  = FauxExportateurMetriques()
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit([_entree("echec_inference")]), accumulateur, exportateur
    )

    nombre_cloturees = service.executer()

    assert nombre_cloturees == 0
    assert exportateur.compteurs_incrementes == []
    assert accumulateur._etats["conv-1"]["a_eu_un_echec"] is True


def test_diagnostic_apres_echec_emet_avec_echec_true() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [
        _entree("tour_entretien", horodatage="2026-10-21T10:00:00+00:00"),
        _entree("echec_inference", horodatage="2026-10-21T10:01:00+00:00"),
        _entree("diagnostic", horodatage="2026-10-21T10:02:00+00:00"),
    ]
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit(entrees), FauxAccumulateurConversations(), exportateur
    )

    service.executer()

    _, etiquettes_echec = next(
        (nom, etq)
        for nom, etq in exportateur.compteurs_incrementes
        if nom == "chsa_conversation_avec_echec_total"
    )
    assert etiquettes_echec["avec_echec"] == "True"


def test_diagnostic_sans_echec_emet_avec_echec_false() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [
        _entree("tour_entretien", horodatage="2026-10-21T10:00:00+00:00"),
        _entree("diagnostic", horodatage="2026-10-21T10:01:00+00:00"),
    ]
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit(entrees), FauxAccumulateurConversations(), exportateur
    )

    service.executer()

    _, etiquettes_echec = next(
        (nom, etq)
        for nom, etq in exportateur.compteurs_incrementes
        if nom == "chsa_conversation_avec_echec_total"
    )
    assert etiquettes_echec["avec_echec"] == "False"


def test_etiquettes_globales_fusionnees() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [
        _entree("tour_entretien", horodatage="2026-10-21T10:00:00+00:00"),
        _entree("diagnostic", horodatage="2026-10-21T10:01:00+00:00"),
    ]
    service = ServiceAnalyseConversations(
        FauxLecteurJournalAudit(entrees),
        FauxAccumulateurConversations(),
        exportateur,
        etiquettes_globales={"configuration": "staging1_local_gguf"},
    )

    service.executer()

    for _, _, etiquettes in exportateur.durees_observees:
        assert etiquettes["configuration"] == "staging1_local_gguf"
