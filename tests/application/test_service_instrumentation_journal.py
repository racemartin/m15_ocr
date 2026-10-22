"""
Tests du cas d'usage `ServiceInstrumentationJournal`, avec des doublures en
mémoire (pas de fichier réel), même discipline que les autres cas d'usage
de ce projet.
"""

from __future__ import annotations

from chsa_triage_observabilite.application.services.service_instrumentation_journal import (
    ServiceInstrumentationJournal,
)
from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)


class FauxLecteurJournalAudit:
    """Doublure de `LecteurJournalAudit` : retourne une liste fixée à l'avance."""

    def __init__(self, entrees: list[EntreeJournalAudit]) -> None:
        self._entrees = entrees

    def lire_nouvelles_entrees(self) -> list[EntreeJournalAudit]:
        return self._entrees


class FauxExportateurMetriques:
    """Doublure de `ExportateurMetriques` : enregistre les appels reçus."""

    def __init__(self) -> None:
        self.compteurs_incrementes : list[tuple[str, dict]] = []
        self.durees_observees      : list[tuple[str, float, dict]] = []

    def incrementer_compteur(self, nom: str, etiquettes: dict | None = None) -> None:
        self.compteurs_incrementes.append((nom, etiquettes or {}))

    def observer_duree(
        self, nom: str, duree_secondes: float, etiquettes: dict | None = None
    ) -> None:
        self.durees_observees.append((nom, duree_secondes, etiquettes or {}))


def _entree(type_evenement: str, metadonnees: dict | None = None) -> EntreeJournalAudit:
    return EntreeJournalAudit(
        horodatage="2026-10-21T00:00:00+00:00",
        type_evenement=type_evenement,
        conversation_id="test-conv",
        version_modele="mombasstic/chsa-triage-dpo-lora",
        metadonnees=metadonnees or {},
    )


def test_rapport_vide_quand_aucune_entree_nouvelle() -> None:
    service = ServiceInstrumentationJournal(
        FauxLecteurJournalAudit([]), FauxExportateurMetriques()
    )

    rapport = service.executer()

    assert rapport.nombre_entrees == 0


def test_tour_entretien_enregistre_un_compteur_et_une_duree() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [_entree("tour_entretien", {"latence_ms": 531.0})]
    service = ServiceInstrumentationJournal(
        FauxLecteurJournalAudit(entrees), exportateur
    )

    rapport = service.executer()

    assert rapport.nombre_entrees == 1
    assert len(exportateur.compteurs_incrementes) == 1
    nom_duree, duree_secondes, _ = exportateur.durees_observees[0]
    assert nom_duree == "chsa_journal_latence_secondes"
    assert duree_secondes == 0.531


def test_diagnostic_avec_format_non_respecte_enregistre_la_metrique() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [
        _entree("diagnostic", {"format_respecte": False, "latence_ms": 1200.0})
    ]
    service = ServiceInstrumentationJournal(
        FauxLecteurJournalAudit(entrees), exportateur
    )

    service.executer()

    noms_compteurs = [nom for nom, _ in exportateur.compteurs_incrementes]
    assert "chsa_diagnostic_format_respecte_total" in noms_compteurs
    _, etiquettes_format = next(
        (nom, etq)
        for nom, etq in exportateur.compteurs_incrementes
        if nom == "chsa_diagnostic_format_respecte_total"
    )
    assert etiquettes_format["format_respecte"] == "False"


def test_echec_inference_enregistre_une_erreur_jamais_une_duree() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [_entree("echec_inference", {"type_erreur": "ReadTimeout"})]
    service = ServiceInstrumentationJournal(
        FauxLecteurJournalAudit(entrees), exportateur
    )

    service.executer()

    noms_compteurs = [nom for nom, _ in exportateur.compteurs_incrementes]
    assert "chsa_journal_erreurs_total" in noms_compteurs
    assert exportateur.durees_observees == []  # pas de latence pour un échec


def test_etiquettes_globales_fusionnees_sur_chaque_metrique() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [_entree("tour_entretien", {"latence_ms": 100.0})]
    service = ServiceInstrumentationJournal(
        FauxLecteurJournalAudit(entrees),
        exportateur,
        etiquettes_globales={"configuration": "staging1_local_gguf"},
    )

    service.executer()

    for _, etiquettes in exportateur.compteurs_incrementes:
        assert etiquettes["configuration"] == "staging1_local_gguf"
    for _, _, etiquettes in exportateur.durees_observees:
        assert etiquettes["configuration"] == "staging1_local_gguf"


def test_nombre_tokens_sortie_enregistre_pour_tour_entretien_et_diagnostic() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [
        _entree("tour_entretien", {"nombre_tokens_sortie": 48}),
        _entree("diagnostic", {"nombre_tokens_sortie": 120, "format_respecte": True}),
    ]
    service = ServiceInstrumentationJournal(FauxLecteurJournalAudit(entrees), exportateur)

    service.executer()

    valeurs_tokens = [
        valeur for nom, valeur, _ in exportateur.durees_observees
        if nom == "chsa_journal_tokens_sortie"
    ]
    assert sorted(valeurs_tokens) == [48.0, 120.0]


def test_nombre_tokens_sortie_absente_n_emet_rien() -> None:
    exportateur = FauxExportateurMetriques()
    entrees = [_entree("tour_entretien", {"latence_ms": 100.0})]
    service = ServiceInstrumentationJournal(FauxLecteurJournalAudit(entrees), exportateur)

    service.executer()

    noms = [nom for nom, _, _ in exportateur.durees_observees]
    assert "chsa_journal_tokens_sortie" not in noms
