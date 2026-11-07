"""
Tests du cas d'usage `ServiceEvaluationQualite` (F5, garde-fous), avec des
doublures en mémoire -- même discipline que les autres cas d'usage de ce
projet.
"""

from __future__ import annotations

from chsa_triage_observabilite.application.services.service_evaluation_qualite import (
    ServiceEvaluationQualite,
)
from chsa_triage_observabilite.domain.model.entree_journal_audit import (
    EntreeJournalAudit,
)
from chsa_triage_observabilite.domain.model.resultat_evaluation_qualite import (
    ResultatEvaluationQualite,
)


class FauxLecteurJournalAudit:
    def __init__(self, entrees: list[EntreeJournalAudit]) -> None:
        self._entrees = entrees

    def lire_nouvelles_entrees(self) -> list[EntreeJournalAudit]:
        return self._entrees


class FauxEvaluateurQualite:
    """Doublure en mémoire : retourne un résultat préprogrammé par texte,
    ou `None` si le texte n'a pas de résultat préprogrammé (simule un juge
    injoignable/inexploitable)."""

    def __init__(self, resultats: dict[str, ResultatEvaluationQualite]) -> None:
        self._resultats = resultats
        self.textes_recus: list[str] = []

    def evaluer(self, texte_diagnostic: str) -> ResultatEvaluationQualite | None:
        self.textes_recus.append(texte_diagnostic)
        return self._resultats.get(texte_diagnostic)


class FauxExportateurMetriques:
    def __init__(self) -> None:
        self.compteurs_incrementes: list[tuple[str, dict]] = []
        self.durees_observees: list[tuple[str, float, dict]] = []

    def incrementer_compteur(self, nom: str, etiquettes: dict | None = None) -> None:
        self.compteurs_incrementes.append((nom, etiquettes or {}))

    def observer_duree(
        self, nom: str, duree_secondes: float, etiquettes: dict | None = None
    ) -> None:
        self.durees_observees.append((nom, duree_secondes, etiquettes or {}))


def _entree_diagnostic(sortie: str = "Consultez un médecin.") -> EntreeJournalAudit:
    return EntreeJournalAudit(
        horodatage="2026-10-21T10:00:00+00:00",
        type_evenement="diagnostic",
        conversation_id="conv-1",
        version_modele="mombasstic/chsa-triage-dpo-lora",
        sortie=sortie,
    )


def test_diagnostic_bien_note_emet_le_score_sans_alerte() -> None:
    entree = _entree_diagnostic("Consultez un médecin rapidement.")
    evaluateur = FauxEvaluateurQualite(
        {entree.sortie: ResultatEvaluationQualite(score=9.0, justification="conforme")}
    )
    exportateur = FauxExportateurMetriques()
    service = ServiceEvaluationQualite(
        FauxLecteurJournalAudit([entree]), evaluateur, exportateur
    )

    nombre_evalues = service.executer()

    assert nombre_evalues == 1
    noms_scores = [nom for nom, _, _ in exportateur.durees_observees]
    assert "chsa_garde_fou_score" in noms_scores
    assert exportateur.compteurs_incrementes == []


def test_diagnostic_mal_note_emet_aussi_une_alerte() -> None:
    entree = _entree_diagnostic("Vous avez certainement une méningite.")
    evaluateur = FauxEvaluateurQualite(
        {
            entree.sortie: ResultatEvaluationQualite(
                score=2.0, justification="langage de diagnostic absolu"
            )
        }
    )
    exportateur = FauxExportateurMetriques()
    service = ServiceEvaluationQualite(
        FauxLecteurJournalAudit([entree]), evaluateur, exportateur
    )

    service.executer()

    noms_alertes = [nom for nom, _ in exportateur.compteurs_incrementes]
    assert "chsa_garde_fou_alerte_total" in noms_alertes


def test_seuil_personnalise_change_la_frontiere_d_alerte() -> None:
    entree = _entree_diagnostic("Score limite.")
    evaluateur = FauxEvaluateurQualite(
        {entree.sortie: ResultatEvaluationQualite(score=6.0, justification="ok")}
    )
    exportateur = FauxExportateurMetriques()
    service = ServiceEvaluationQualite(
        FauxLecteurJournalAudit([entree]), evaluateur, exportateur, seuil_alerte=7.0
    )

    service.executer()

    noms_alertes = [nom for nom, _ in exportateur.compteurs_incrementes]
    assert "chsa_garde_fou_alerte_total" in noms_alertes


def test_juge_injoignable_n_emet_rien() -> None:
    """Un juge qui retourne `None` ne doit jamais faire planter le sondage
    des autres métriques -- même discipline que les autres cas d'usage."""
    entree = _entree_diagnostic("Peu importe.")
    evaluateur = FauxEvaluateurQualite({})  # aucun résultat préprogrammé
    exportateur = FauxExportateurMetriques()
    service = ServiceEvaluationQualite(
        FauxLecteurJournalAudit([entree]), evaluateur, exportateur
    )

    nombre_evalues = service.executer()

    assert nombre_evalues == 0
    assert exportateur.durees_observees == []
    assert exportateur.compteurs_incrementes == []


def test_ignore_les_evenements_qui_ne_sont_pas_un_diagnostic() -> None:
    entree = EntreeJournalAudit(
        horodatage="2026-10-21T10:00:00+00:00",
        type_evenement="tour_entretien",
        conversation_id="conv-1",
        version_modele="mombasstic/chsa-triage-dpo-lora",
        sortie="",
    )
    evaluateur = FauxEvaluateurQualite({})
    exportateur = FauxExportateurMetriques()
    service = ServiceEvaluationQualite(
        FauxLecteurJournalAudit([entree]), evaluateur, exportateur
    )

    nombre_evalues = service.executer()

    assert nombre_evalues == 0
    assert evaluateur.textes_recus == []


def test_diagnostic_sans_texte_de_sortie_est_ignore() -> None:
    """Un diagnostic sans `sortie` (journal ancien, avant cette évolution)
    ne doit jamais être envoyé au juge avec un texte vide."""
    entree = _entree_diagnostic("")
    evaluateur = FauxEvaluateurQualite({})
    exportateur = FauxExportateurMetriques()
    service = ServiceEvaluationQualite(
        FauxLecteurJournalAudit([entree]), evaluateur, exportateur
    )

    nombre_evalues = service.executer()

    assert nombre_evalues == 0
    assert evaluateur.textes_recus == []


def test_etiquettes_globales_fusionnees() -> None:
    entree = _entree_diagnostic("Consultez un médecin.")
    evaluateur = FauxEvaluateurQualite(
        {entree.sortie: ResultatEvaluationQualite(score=9.0, justification="ok")}
    )
    exportateur = FauxExportateurMetriques()
    service = ServiceEvaluationQualite(
        FauxLecteurJournalAudit([entree]),
        evaluateur,
        exportateur,
        etiquettes_globales={"configuration": "staging1_local_gguf"},
    )

    service.executer()

    for _, _, etiquettes in exportateur.durees_observees:
        assert etiquettes["configuration"] == "staging1_local_gguf"
