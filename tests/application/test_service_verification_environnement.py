"""
Tests du cas d'usage `ServiceVerificationEnvironnement`, avec des doublures en
mémoire (pas de réseau), même discipline que m14_ocr : un cas d'usage se
teste contre le port, jamais contre un adaptateur réel.
"""

from __future__ import annotations

from chsa_triage_observabilite.application.services.service_verification_environnement import (
    ServiceVerificationEnvironnement,
)
from chsa_triage_observabilite.domain.model.resultat_verification import (
    ResultatVerification,
)


class FauxVerificateur:
    """Doublure de `VerificateurConnectivite` : résultat fixé à l'avance."""

    def __init__(self, resultat: ResultatVerification) -> None:
        self._resultat = resultat

    def verifier(self) -> ResultatVerification:
        return self._resultat


def _resultat(disponible: bool, nom: str = "Dépendance test") -> ResultatVerification:
    return ResultatVerification(
        nom=nom, disponible=disponible, detail="détail test", duree_ms=1.0
    )


def test_tout_dispo_vrai_quand_toutes_les_dependances_sont_disponibles() -> None:
    service = ServiceVerificationEnvironnement(
        [FauxVerificateur(_resultat(True)), FauxVerificateur(_resultat(True))]
    )

    rapport = service.executer()

    assert rapport.tout_dispo is True
    assert len(rapport.resultats) == 2


def test_tout_dispo_faux_des_qu_une_seule_dependance_echoue() -> None:
    service = ServiceVerificationEnvironnement(
        [FauxVerificateur(_resultat(True)), FauxVerificateur(_resultat(False))]
    )

    rapport = service.executer()

    assert rapport.tout_dispo is False


def test_rapport_vide_quand_aucun_verificateur_enregistre() -> None:
    service = ServiceVerificationEnvironnement([])

    rapport = service.executer()

    assert rapport.resultats == []
    assert rapport.tout_dispo is True  # all([]) est vrai, aucune dépendance à casser


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


def test_sans_exportateur_metriques_le_comportement_reste_identique() -> None:
    """Rétrocompatibilité : le CLI F0 existant n'a jamais besoin de fournir
    un exportateur, et ce cas d'usage doit continuer à fonctionner sans."""
    service = ServiceVerificationEnvironnement([FauxVerificateur(_resultat(True))])

    rapport = service.executer()

    assert rapport.tout_dispo is True


def test_avec_exportateur_metriques_chaque_resultat_est_enregistre() -> None:
    exportateur = FauxExportateurMetriques()
    service = ServiceVerificationEnvironnement(
        [FauxVerificateur(_resultat(True, nom="A")), FauxVerificateur(_resultat(False, nom="B"))],
        exportateur,
    )

    service.executer()

    assert len(exportateur.compteurs_incrementes) == 2
    assert len(exportateur.durees_observees) == 2
    noms_enregistres = {etiquettes["nom"] for _, etiquettes in exportateur.compteurs_incrementes}
    assert noms_enregistres == {"A", "B"}


def test_etiquettes_globales_fusionnees_dans_chaque_metrique() -> None:
    """La configuration auditée (ex. staging1_local_gguf) doit apparaître
    sur CHAQUE métrique de l'exécution, pas seulement sur certaines."""
    exportateur = FauxExportateurMetriques()
    service = ServiceVerificationEnvironnement(
        [FauxVerificateur(_resultat(True, nom="A")), FauxVerificateur(_resultat(True, nom="B"))],
        exportateur,
        etiquettes_globales={"configuration": "staging1_local_gguf"},
    )

    service.executer()

    for _, etiquettes in exportateur.compteurs_incrementes:
        assert etiquettes["configuration"] == "staging1_local_gguf"
    for _, _, etiquettes in exportateur.durees_observees:
        assert etiquettes["configuration"] == "staging1_local_gguf"
