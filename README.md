# Passerelle USSD/SMS — API (prototype de laboratoire, Burundi)

Passerelle logicielle open source, auto-hébergeable, qui permet de prototyper des services de type **USSD** et **SMS** (menus interactifs, sessions, paiement de démonstration, notifications) **sans opérateur mobile ni argent réel**.

> **Important** : tout est simulé. Aucun débit, transfert ou conservation de fonds réels, aucun PIN réel, aucune connexion à un opérateur. Une simulation n'est pas un accès au réseau mobile ni une autorisation de fournir un service financier.

## Fonctionnalités

- API REST/JSON versionnée (`/api/v1`) avec documentation OpenAPI interactive (`/docs`)
- Sessions USSD : états ACTIVE, COMPLETED, CANCELLED, EXPIRED, expiration automatique
- Historique des interactions (menu, saisie, réponse, numéro d'étape)
- Transactions simulées : PENDING → SUCCESS / FAILED / CANCELLED, référence unique, **idempotence** par `idempotency_key`
- SMS simulés entrants/sortants avec suivi d'état, liés aux transactions
- Journal d'audit des actions sensibles
- Sécurité : JWT, mots de passe bcrypt, rôles, blocage anti brute-force, validation stricte des entrées

## Pile technique

| Élément | Choix |
|---|---|
| Langage | Python 3.12+ |
| API | FastAPI + Uvicorn |
| Base de données | PostgreSQL (SQLite pour les tests) |
| ORM / migrations | SQLAlchemy 2 + Alembic |
| Authentification | JWT (PyJWT) + bcrypt |
| Tests / qualité | pytest, Ruff, GitHub Actions |
| Conteneurs | Docker, Docker Compose (facultatif) |

## Installation rapide

```bash
git clone https://github.com/Jb-Tenaciou/ussd-gateway.git
cd ussd-gateway
python -m venv .venv
source .venv/Scripts/activate        # Linux/macOS : source .venv/bin/activate
pip install --only-binary=:all: -r requirements.txt
cp .env.example .env                 # puis renseigner DATABASE_URL et SECRET_KEY
alembic upgrade head                 # crée les tables
python seed.py +25779000000 'MotDePasseSolide123' "Admin Labo"
uvicorn app.main:app --reload
```

Documentation interactive : <http://localhost:8000/docs>

Générer une clé secrète (32 caractères minimum, sinon l'API refuse de démarrer) :

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Configuration (`.env`)

Le fichier `.env` ne doit **jamais** être commité (il est dans `.gitignore`). Modèle : `.env.example`.

| Variable | Rôle | Défaut |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://user:mdp@hote:port/base?sslmode=require` | SQLite locale |
| `SECRET_KEY` | Clé de signature JWT (32+ caractères) | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée du jeton | 60 |
| `SESSION_TIMEOUT_SECONDS` | Expiration d'une session USSD inactive | 120 |
| `CORS_ORIGINS` | Origines autorisées, séparées par des virgules | localhost:3000, localhost:5173 |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCK_MINUTES` | Blocage anti brute-force | 5 / 5 |

## Rôles et accès

| Rôle | Droits |
|---|---|
| `ADMIN` | Tout : comptes, sessions, transactions, SMS, journal d'audit |
| `OPERATOR` | Sessions, interactions, transactions, SMS (compte utilisé par les services métier) |
| `DEMO_USER` | Aucune route de gestion |

## Principales routes

| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | État de l'API et de la base |
| POST | `/api/v1/auth/login` | Connexion, renvoie un jeton |
| GET | `/api/v1/auth/me` | Profil connecté |
| POST | `/api/v1/auth/change-password` | Changer son mot de passe |
| POST/GET/PATCH | `/api/v1/users` | Gestion des comptes (ADMIN) |
| POST/GET/PATCH | `/api/v1/sessions` | Sessions USSD |
| POST/GET | `/api/v1/sessions/{id}/interactions` | Étapes d'une session |
| POST/GET | `/api/v1/transactions` | Transactions simulées (idempotentes) |
| PATCH | `/api/v1/transactions/{id}/status` | PENDING → SUCCESS / FAILED / CANCELLED |
| POST/GET | `/api/v1/sms` | SMS simulés |
| GET | `/api/v1/audit-logs` | Journal d'audit (ADMIN) |

Codes d'erreur : 401 non authentifié · 403 rôle insuffisant · 404 introuvable · 409 conflit (doublon, transition interdite, session terminée) · 422 validation · 429 trop de tentatives.

### Exemple

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone_number":"+25779222222","password":"..."}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST localhost:8000/api/v1/transactions \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"amount":"5000","idempotency_key":"CMD-0001-XYZ"}'
```

Un deuxième envoi avec la même `idempotency_key` renvoie la **même** transaction (pas de double paiement).

## Structure du projet

```
ussd-gateway/
├── app/
│   ├── main.py, config.py, database.py   # application, configuration, connexion
│   ├── models.py, schemas.py             # 6 tables, validation des données
│   ├── security.py, deps.py              # mots de passe, JWT, rôles, audit
│   ├── routers/                          # routes /api/v1
│   ├── services/                         # logique métier : moteur USSD, paiement, SMS
│   ├── menus/                            # définition des menus
│   └── simulator/                        # interface web du simulateur
├── alembic/                              # migrations de la base
├── tests/                                # tests pytest (+ perf/ pour la charge)
├── scripts/                              # sauvegarde et restauration
├── docs/                                 # architecture, installation, API, rapport de tests
├── examples/                             # clients d'exemple (Python, Java)
├── Dockerfile, docker-compose.yml
└── .github/workflows/ci.yml              # CI : Ruff + pytest
```

## Tests et qualité

```bash
python -m pytest -q       # tests de l'API (SQLite locale, ne touche pas à PostgreSQL)
ruff check .              # lint
```

Test de charge (locust) : voir l'en-tête de `tests/perf/locustfile.py`.

## Docker

```bash
SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))") docker compose up --build
```

Lance l'API et une base PostgreSQL locale, et applique les migrations au démarrage.

## Sauvegarde et restauration

```bash
DATABASE_URL_PG="postgres://user:mdp@hote:port/base?sslmode=require" ./scripts/backup.sh
DATABASE_URL_PG="postgres://..." ./scripts/restore.sh backups/fichier.sql   # base de TEST vide uniquement
```

Nécessite les outils clients PostgreSQL (`pg_dump`, `psql`).

## Migrations

```bash
alembic revision --autogenerate -m "description"   # générer
alembic upgrade head                                # appliquer
alembic current                                     # version actuelle
```

Règle d'équipe : une seule personne génère les migrations (Personne 1), pour éviter les conflits.

## Organisation de l'équipe

| Rôle | Responsabilités |
|---|---|
| **Personne 1** — API, base de données, sécurité | FastAPI, PostgreSQL, SQLAlchemy, Alembic, tables, routes, schémas, authentification, rôles, tests de l'API |
| **Personne 2** — Logique USSD, paiements simulés, SMS | Moteur de menus, sessions, simulation de paiement, idempotence, simulateur SMS, scénarios et tests des parcours |

Workflow Git : une branche par personne (`personne1-api`, `personne2-ussd`), Pull Request vers `main`, CI verte avant fusion.

## Sécurité

- Secrets uniquement dans `.env`, jamais dans Git ; refus de démarrer avec une `SECRET_KEY` faible
- Mots de passe hachés (bcrypt), jetons signés avec expiration
- Blocage de 5 minutes après 5 échecs de connexion
- Validation stricte des entrées, contrôle d'accès par rôle
- Journal d'audit sans mot de passe, PIN ni secret

## Limites connues

- Le blocage anti brute-force est en mémoire du processus (à déplacer vers Redis si plusieurs instances)
- Les jetons déjà émis restent valides jusqu'à leur expiration, même après un changement de mot de passe
- Aucune intégration opérateur réelle : un adaptateur externe serait un module isolé, dans une phase distincte (analyse juridique et réglementaire, accords opérateurs, audit de sécurité)

## Licence

Voir le fichier `LICENSE`.
