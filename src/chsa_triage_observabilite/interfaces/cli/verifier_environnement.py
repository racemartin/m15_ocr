"""
Point d'entrée CLI (F0, pré-requis) : vérifie que toutes les dépendances
externes configurées sont accessibles AVANT de lancer quoi que ce soit
d'autre (instrumentation, génération de trafic, dashboard). Lit `.env`
(jamais de clé en dur, même règle que `interfaces/api/main.py` dans
m14_ocr), construit les adaptateurs concrets, et affiche un rapport.

Usage :
    uv run verifier-environnement
"""

from __future__ import annotations

# Bibliothèques standard
import sys
from pathlib import Path

# Lecture du .env
from dotenv import load_dotenv

# Cas d'usage
from chsa_triage_observabilite.application.services.service_verification_environnement import (
    ServiceVerificationEnvironnement,
)

# Modèle de domaine
from chsa_triage_observabilite.domain.model.resultat_verification import (
    ResultatVerification,
)

# Adaptateur concret
from chsa_triage_observabilite.infrastructure.adapters.prometheus_exportateur_metriques import (
    PrometheusExportateurMetriques,
)

# Fabrique commune (composition root partagée entre points d'entrée)
from chsa_triage_observabilite.interfaces.cli.fabrique_adaptateurs import (
    construire_etiquettes_globales,
    construire_verificateurs,
)

LARGEUR_SEPARATEUR = 80
DOSSIER_METRIQUES  = Path("data")


def _chemin_metriques(configuration: str | None) -> Path:
    """Un fichier `.prom` par configuration auditée (pas un seul fichier
    partagé) : sinon, exécuter `verifier-environnement` contre deux
    configurations différentes (ex. comparer `staging1_local_gguf` et
    `staging2_local_transformers_peft`) écraserait silencieusement le
    résultat précédent, cassant exactement la comparaison qu'on cherche
    à faire dans Grafana."""
    if configuration:
        return DOSSIER_METRIQUES / f"metriques_verification__{configuration}.prom"
    return DOSSIER_METRIQUES / "metriques_verification.prom"


def _afficher_rapport(resultats: list[ResultatVerification]) -> None:
    ligne = "=" * LARGEUR_SEPARATEUR
    print(ligne)
    print("VÉRIFICATION DE L'ENVIRONNEMENT")
    print(ligne)

    if not resultats:
        print("  Aucune dépendance externe configurée dans .env pour l'instant.")
        print(ligne)
        return

    for resultat in resultats:
        symbole = "OK " if resultat.disponible else "KO "
        label   = resultat.nom.ljust(28, ".")
        print(f"  [{symbole}] {label}: {resultat.detail} ({resultat.duree_ms:.0f} ms)")

    print(ligne)


def main() -> None:
    load_dotenv()

    verificateurs         = construire_verificateurs()
    exportateur_metriques = PrometheusExportateurMetriques()
    etiquettes_globales    = construire_etiquettes_globales()
    rapport = ServiceVerificationEnvironnement(
        verificateurs,
        exportateur_metriques,
        etiquettes_globales=etiquettes_globales,
    ).executer()
    _afficher_rapport(rapport.resultats)

    # --- Métriques Prometheus de cette exécution, écrites sur disque --------
    chemin_metriques = _chemin_metriques(etiquettes_globales.get("configuration"))
    chemin_metriques.parent.mkdir(parents=True, exist_ok=True)
    chemin_metriques.write_bytes(exportateur_metriques.exposer_texte())
    print(f"Métriques Prometheus écrites dans {chemin_metriques}")

    if not rapport.tout_dispo:
        print("Au moins une dépendance est indisponible, voir le détail ci-dessus.")
        sys.exit(1)

    print("Toutes les dépendances configurées sont accessibles.")


if __name__ == "__main__":
    main()
