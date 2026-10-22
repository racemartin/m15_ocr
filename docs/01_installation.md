# Installation détaillée

Ce document couvre l'installation complète du projet, pas à pas. Pour un
démarrage rapide, voir la section « Démarrage rapide » du `README.md`.

## 1. Pré-requis

- Python 3.12 (voir `.python-version`).
- [`uv`](https://docs.astral.sh/uv/) comme gestionnaire de paquets et
  d'environnement, même outil que m14_ocr.
- Git.
- Un compte Hugging Face avec un jeton d'accès (`HF_TOKEN`), si l'on
  souhaite vérifier l'accès au dataset du journal d'audit ou relancer des
  jobs d'entraînement du projet audité (m14_ocr).

## 2. Cloner et installer les dépendances

```bash
git clone <url-du-depot> m15_ocr
cd m15_ocr
uv sync --group dev
```

`uv sync` lit `pyproject.toml` et `uv.lock`, crée `.venv/` et installe
exactement les versions verrouillées (reproductible, même mécanisme que
m14_ocr). Le groupe `dev` ajoute `ruff` (lint) et `pytest` (tests).

Sortie attendue au premier `uv sync` (téléchargement réel des paquets) :

```
Resolved 27 packages in ...
Installed 25 packages in ...
```

Et à un `uv sync` suivant, si rien n'a changé (comportement normal, pas
une erreur) :

```
Resolved 27 packages in 10ms
Audited 25 packages in 261ms
```

`Audited` signifie qu'uv a vérifié que `.venv/` correspond déjà
exactement à `uv.lock`, sans rien réinstaller.

### Pas d'activation manuelle nécessaire

Contrairement au flux classique `python -m venv` + `source
.venv/bin/activate`, **`uv run <commande>` exécute directement dans
`.venv/` sans activation préalable**. C'est pour ça que ce document
n'écrit jamais `source .venv/bin/activate` : chaque commande de ce
projet (`uv run verifier-environnement`, `uv run pytest`, `uv run
ruff`...) fonctionne déjà, qu'une session d'activation ait eu lieu ou
non. `.venv/` existe bien sur disque (`ls .venv`), mais y "entrer" à la
main n'est jamais nécessaire ici.

## 3. Configurer les secrets (`.env`)

```bash
cp .env.example .env
```

Puis renseigner dans `.env` (jamais commité, voir § Sécurité) :

| Variable | Obligatoire | Rôle |
|---|---|---|
| `HF_TOKEN` | Non, mais recommandé | Jeton Hugging Face (lecture suffit pour une simple vérification d'accès ; écriture nécessaire pour publier sur un dataset, ex. journal d'audit). |
| `CHSA_JOURNAL_AUDIT_REPO` | Non | Dépôt dataset HF du journal d'audit, repris de m14_ocr (ex. `mombasstic/chsa-triage-audit-journal`). |
| `CHSA_TRIAGE_URL_BASE` | Non | URL de **base** de l'API chsa-triage (m14_ocr) à auditer — locale ou distante (Space HF), même variable dans les deux cas, jamais un "mode" séparé. |
| `CHSA_TRIAGE_CLE_API` | Non | Clé `X-API-Key` pour les routes protégées de chsa-triage (toutes sauf `/sante`). |
| `CHSA_TRIAGE_CONFIGURATION` | Non | Étiquette de la configuration de déploiement auditée (`staging1_local_gguf`, etc. — voir `.env.example`), posée sur chaque métrique. Déclarative, jamais déduite. |
| `MLFLOW_TRACKING_URI` | Non | URL d'une instance MLflow, si réutilisée du m14_ocr. |
| `CHSA_TRIAGE_CHEMIN_JOURNAL_AUDIT` | Non | Chemin **local** vers le `.jsonl` écrit par chsa-triage (frontière locale, voir `docs/00_architecture.md`). Requis pour `instrumenter-journal` et pour que `servir-metriques` lise aussi le journal. |
| `CHSA_PORT_METRIQUES` | Non (défaut 9200) | Port HTTP du endpoint `/metrics` de `servir-metriques`. |
| `CHSA_INTERVALLE_SONDAGE_SECONDES` | Non (défaut 30) | Fréquence à laquelle `servir-metriques` relit lui-même ses sources. |

Une variable absente ne fait pas échouer le script de vérification :
cette dépendance est simplement ignorée (elle n'est pas encore
nécessaire à ce stade du projet). C'est volontaire : on ajoute une
vérification au moment où la dépendance correspondante devient réelle,
jamais avant.

## 4. Vérifier l'environnement avant d'aller plus loin

```bash
uv run verifier-environnement
```

Ce script est l'équivalent d'un `/sante` applicatif, mais exécuté une
seule fois en amont plutôt qu'exposé en continu : il vérifie chaque
dépendance externe **configurée** dans `.env` (authentification Hugging
Face, accès à un dataset précis, disponibilité d'un endpoint HTTP), sans
jamais lever d'exception — un échec de connectivité est un résultat
normal (`[KO]` dans le rapport), pas un bug du programme.

Sortie attendue si tout est accessible :

```
================================================================================
VÉRIFICATION DE L'ENVIRONNEMENT
================================================================================
  [OK ] Hugging Face Hub............: Connecté en tant que 'mombasstic' (475 ms)
================================================================================
Toutes les dépendances configurées sont accessibles.
```

Le script termine avec un code de sortie non nul (`exit 1`) si au moins
une dépendance configurée est indisponible — utilisable comme garde-fou
dans un script ou une CI, avant de lancer un travail plus coûteux.

## 5. Lancer les tests et le lint

```bash
uv run pytest -q
uv run ruff check src/
```

## 6. Sécurité : gestion des secrets

- `.env` est dans `.gitignore` : il ne doit **jamais** être commité.
- `.env.example` est le seul fichier tracké, avec des valeurs vides —
  c'est le contrat documenté de ce qui est attendu, sans jamais exposer
  une vraie clé.
- Chaque adaptateur de vérification (`infrastructure/adapters/`) reçoit
  son jeton par injection explicite (constructeur), jamais en lisant
  l'environnement lui-même — seul `interfaces/cli/verifier_environnement.py`
  lit `os.environ`, même discipline que `interfaces/api/main.py` dans
  m14_ocr (« la seule couche qui lit des variables d'environnement »).
- Un jeton invalide ou expiré produit un résultat `[KO]` explicite, avec
  le message d'erreur du fournisseur, jamais un plantage silencieux.

## 7. Suite : architecture

Voir [`00_architecture.md`](00_architecture.md) pour le schéma hexagonal
complet (ports, adaptateurs, et comment ce projet s'articule avec
m14_ocr sans le modifier).
