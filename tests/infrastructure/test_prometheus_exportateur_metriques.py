"""
Tests de l'adaptateur `PrometheusExportateurMetriques`, contre le texte
d'exposition réellement produit (pas contre l'implémentation interne), même
discipline que m14_ocr : un test vérifie un comportement observable.
"""

from __future__ import annotations

from chsa_triage_observabilite.infrastructure.adapters.prometheus_exportateur_metriques import (
    PrometheusExportateurMetriques,
)


def test_compteur_apparait_dans_le_texte_expose() -> None:
    exportateur = PrometheusExportateurMetriques()

    exportateur.incrementer_compteur("test_compteur_total", {"nom": "x"})

    texte = exportateur.exposer_texte().decode("utf-8")
    assert 'test_compteur_total{nom="x"} 1.0' in texte


def test_compteur_incremente_deux_fois_vaut_deux() -> None:
    exportateur = PrometheusExportateurMetriques()

    exportateur.incrementer_compteur("test_double_total", {"nom": "x"})
    exportateur.incrementer_compteur("test_double_total", {"nom": "x"})

    texte = exportateur.exposer_texte().decode("utf-8")
    assert 'test_double_total{nom="x"} 2.0' in texte


def test_duree_observee_apparait_dans_l_histogramme() -> None:
    exportateur = PrometheusExportateurMetriques()

    exportateur.observer_duree("test_duree_secondes", 0.25, {"nom": "x"})

    texte = exportateur.exposer_texte().decode("utf-8")
    assert "test_duree_secondes_bucket" in texte
    assert 'test_duree_secondes_sum{nom="x"} 0.25' in texte


def test_compteur_sans_etiquettes_fonctionne_aussi() -> None:
    exportateur = PrometheusExportateurMetriques()

    exportateur.incrementer_compteur("test_sans_etiquette_total")

    texte = exportateur.exposer_texte().decode("utf-8")
    assert "test_sans_etiquette_total 1.0" in texte
