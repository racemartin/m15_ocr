"""
État accumulé d'une conversation en cours, entre le premier tour
d'entretien reçu et sa clôture (le diagnostic). Permet de compter les
tours et de mesurer le temps écoulé SANS connaître d'avance combien de
cycles de sondage séparent le premier tour du diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EtatConversationAccumule:
    """Ce qu'on sait d'une conversation pas encore close.

    `a_eu_un_echec` (C6) : True si au moins un `echec_inference` a été vu
    pour cette conversation AVANT sa clôture. Limite connue et assumée :
    une conversation qui échoue et n'est JAMAIS relancée jusqu'à un
    diagnostic ne se clôture jamais, donc ce drapeau n'est jamais
    restitué pour elle — C6 ne mesure le taux d'échec que parmi les
    conversations qui aboutissent."""

    nombre_tours            : int
    horodatage_premier_tour : str
    a_eu_un_echec           : bool = False
