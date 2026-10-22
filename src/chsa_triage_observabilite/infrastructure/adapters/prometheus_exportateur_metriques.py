"""
Adaptateur du port `ExportateurMetriques` : expose des compteurs et des
histogrammes au format d'exposition Prometheus. Un `CollectorRegistry`
dédié (jamais le registre global `prometheus_client`) : plusieurs
instances de cet adaptateur, par exemple une par test, ne se marchent
jamais dessus.
"""

from __future__ import annotations

# Client Prometheus
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

# Journalisation
from tools.rafael.log_tool import LogTool


class PrometheusExportateurMetriques:
    """Implémente `ExportateurMetriques` pour Prometheus.

    Chaque métrique (compteur ou histogramme) est créée paresseusement, à
    la première utilisation, parce que `prometheus_client` exige de
    déclarer les noms d'étiquettes (`labelnames`) à la création — on ne
    les connaît qu'au premier appel réel."""

    def __init__(self) -> None:
        self._registre    = CollectorRegistry()
        self._compteurs   : dict[str, Counter]   = {}
        self._histogrammes: dict[str, Histogram] = {}
        self._log          = LogTool(origin="infrastructure")

    @property
    def registre(self) -> CollectorRegistry:
        """Expose le `CollectorRegistry` réel, pour `prometheus_client.start_http_server`
        (serveur HTTP continu, F3) : celui-ci exige le registre natif, pas
        notre enveloppe — jamais utilisé par `exposer_texte()` lui-même."""
        return self._registre

    # #########################################################################
    # Incrémente de 1 le compteur `nom`. Crée le compteur au premier appel,
    # avec les noms d'étiquettes observés à ce moment-là.
    # #########################################################################
    def incrementer_compteur(
        self, nom: str, etiquettes: dict[str, str] | None = None
    ) -> None:
        etiquettes = etiquettes or {}
        self._log.START_CALL_MANAGER_FUNCTION(
            "PrometheusExportateurMetriques", "incrementer_compteur", f"nom={nom}"
        )

        if nom not in self._compteurs:
            self._compteurs[nom] = Counter(
                nom,
                f"Compteur {nom}",
                labelnames=list(etiquettes.keys()),
                registry=self._registre,
            )

        compteur = self._compteurs[nom]
        (compteur.labels(**etiquettes) if etiquettes else compteur).inc()

        self._log.FINISH_CALL_MANAGER_FUNCTION(
            "PrometheusExportateurMetriques", "incrementer_compteur", "fait"
        )

    # #########################################################################
    # Enregistre une durée observée pour l'histogramme `nom`. Même logique
    # de création paresseuse que `incrementer_compteur`.
    # #########################################################################
    def observer_duree(
        self,
        nom: str,
        duree_secondes: float,
        etiquettes: dict[str, str] | None = None,
    ) -> None:
        etiquettes = etiquettes or {}
        self._log.START_CALL_MANAGER_FUNCTION(
            "PrometheusExportateurMetriques", "observer_duree", f"nom={nom}"
        )
        self._log.PARAMETER_VALUE("duree_secondes", f"{duree_secondes:.6f}")

        if nom not in self._histogrammes:
            self._histogrammes[nom] = Histogram(
                nom,
                f"Histogramme {nom}",
                labelnames=list(etiquettes.keys()),
                registry=self._registre,
            )

        histogramme = self._histogrammes[nom]
        (
            histogramme.labels(**etiquettes) if etiquettes else histogramme
        ).observe(duree_secondes)

        self._log.FINISH_CALL_MANAGER_FUNCTION(
            "PrometheusExportateurMetriques", "observer_duree", "fait"
        )

    # #########################################################################
    # Sérialise toutes les métriques courantes au format d'exposition
    # Prometheus (texte brut), prêt à être servi par un endpoint `/metrics`.
    # #########################################################################
    def exposer_texte(self) -> bytes:
        return generate_latest(self._registre)
