"""
Port générique (F1, instrumentation) : exposer des métriques, sans savoir
vers quel système de monitoring elles partent (Prometheus aujourd'hui,
potentiellement un autre backend demain). Même discipline que
`VerificateurConnectivite` : un seul contrat, plusieurs adaptateurs
possibles.
"""

from __future__ import annotations

from typing import Protocol


class ExportateurMetriques(Protocol):
    """Port générique : enregistrer un compteur ou une durée observée."""

    def incrementer_compteur(
        self, nom: str, etiquettes: dict[str, str] | None = None
    ) -> None:
        """Incrémente de 1 le compteur `nom`, optionnellement étiqueté
        (ex. `{"niveau_esi": "2"}`)."""
        ...

    def observer_duree(
        self,
        nom: str,
        duree_secondes: float,
        etiquettes: dict[str, str] | None = None,
    ) -> None:
        """Enregistre une durée observée pour l'histogramme `nom`, pour en
        tirer ensuite des percentiles (P50/P95/P99) côté dashboard."""
        ...
