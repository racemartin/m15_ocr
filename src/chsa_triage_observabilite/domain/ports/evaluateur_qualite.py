"""
Port (F4, garde-fous) : demander à un juge l'évaluation de sécurité/forme
d'un diagnostic, sans savoir quel modèle ni quel moteur répond derrière
(`llama-server` local aujourd'hui, potentiellement un autre backend demain).
Même discipline que `ExportateurMetriques` : un seul contrat, plusieurs
adaptateurs possibles.
"""

from __future__ import annotations

from typing import Protocol

from chsa_triage_observabilite.domain.model.resultat_evaluation_qualite import (
    ResultatEvaluationQualite,
)


class EvaluateurQualite(Protocol):
    """Port F4 : évaluer un texte de diagnostic."""

    def evaluer(self, texte_diagnostic: str) -> ResultatEvaluationQualite | None:
        """Retourne un résultat, ou `None` si le juge est injoignable ou a
        répondu dans un format inexploitable — jamais une exception : un
        juge indisponible ne doit jamais interrompre le sondage des autres
        métriques (même discipline que `VerificateurConnectivite`)."""
        ...
