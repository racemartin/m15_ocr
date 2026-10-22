# CHSA Triage — Observabilité

> **Projet M15 (OpenClassrooms, AI Engineer)**
> Audit et instrumentation (Prometheus/Grafana) de l'agent de triage
> médical [CHSA (m14_ocr)](https://github.com/racemartin/m14_ocr),
> **sans modifier** le système audité.
> Architecture hexagonale (ports et adaptateurs), même discipline que
> m14_ocr.

---

## Démarrage rapide

```bash
git clone <url-du-depot> m15_ocr
cd m15_ocr

uv sync --group dev
cp .env.example .env
# Renseigner HF_TOKEN et, si disponibles, CHSA_TRIAGE_URL_SANTE / MLFLOW_TRACKING_URI

uv run verifier-environnement
```

Sortie attendue (si `.env` est vide, les vérifications sont simplement
ignorées, pas en échec) :

```
================================================================================
VÉRIFICATION DE L'ENVIRONNEMENT
================================================================================
  Aucune dépendance externe configurée dans .env pour l'instant.
================================================================================
Toutes les dépendances configurées sont accessibles.
```

Installation détaillée, variables d'environnement une par une, et
discipline de sécurité : [`docs/01_installation.md`](docs/01_installation.md).

## Tableau de bord (Prometheus + Grafana)

```bash
uv run servir-metriques &          # expose /metrics en continu sur l'hôte
docker compose up -d               # Prometheus (scrape) + Grafana (dashboard)
```

Grafana : [http://localhost:3000](http://localhost:3000) (`admin` /
`GRAFANA_ADMIN_PASSWORD`, `admin` par défaut). Détails de la pile et des
premiers panneaux : [`docs/00_architecture.md`](docs/00_architecture.md)
"Pile d'observabilité".

## Pourquoi ce projet

Le code de m14_ocr documente lui-même, dans son propre port
`JournalAudit`, une décision de périmètre : *« jamais une stack
d'observabilité lourde »*. m15_ocr comble précisément ce manque, de
façon non invasive : le système audité ne change pas une seule ligne.

## Architecture

Schéma complet (ports, adaptateurs, et relation avec m14_ocr) :
[`docs/00_architecture.md`](docs/00_architecture.md).

## Tests et lint

```bash
uv run pytest -q
uv run ruff check src/
```

## Auteur

**Rafael Cerezo Martín**

- GitHub : [@racemartin](https://github.com/racemartin)

## Licence

MIT License, voir [LICENSE](LICENSE).
