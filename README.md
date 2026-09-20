# Enrichissement intelligent des métadonnées documentaires dans une GED

Ce dépôt contient le prototype développé dans le cadre d’un mémoire de Mastère portant sur l’amélioration des métadonnées documentaires grâce à l’intelligence artificielle. Il illustre une chaîne d’assistance (extraction, classification, métadonnées, PII, validation humaine), puis une préparation expérimentale à l’intégration dans une GED.

## Objectif

Le prototype **assiste** l’utilisateur dans la création et l’enrichissement des métadonnées. Il n’automatise pas une mise en production et **ne remplace pas** le jugement humain.

À partir d’un document, il permet de :

- extraire le contenu (texte natif PDF, OCR ou fichier texte) ;
- proposer une catégorie documentaire ;
- extraire certaines métadonnées (organisation, date, identifiants, etc.) ;
- signaler des données personnelles **potentielles** ;
- générer des métadonnées structurées ;
- les **corriger et valider** (approche *human-in-the-loop*) ;
- préparer leur envoi expérimental vers une GED (API REST Nuxeo).

## Fonctionnement

```text
Document
   ↓
Extraction du contenu
   ↓
Classification
   ↓
Extraction des métadonnées
   ↓
Détection PII
   ↓
Génération des métadonnées
   ↓
Validation humaine
   ↓
Métadonnées structurées
   ↓
GED / Nuxeo (expérimental)
```

## Fonctionnalités

Présentes dans le code actuel :

- dépôt de documents **PDF**, **PNG / JPEG / TIFF** et **TXT** ;
- extraction de texte PDF natif (PyMuPDF) avec repli OCR (Tesseract) pour les scans ;
- classification documentaire (TF-IDF + régression logistique si le modèle est fourni, sinon repli par mots-clés) ;
- extraction d’entités (expressions régulières + spaCy) ;
- enrichissement de métadonnées proposées (titre, organisation, mots-clés, etc.) ;
- détection indicative de données personnelles ;
- interface de revue : correction, validation ou rejet ;
- export JSON structuré ;
- envoi expérimental des métadonnées validées vers un **document Nuxeo déjà existant** (Dublin Core uniquement : `dc:title`, `dc:description`, `dc:source`). Le fichier (`file:content`) n’est pas modifié.

Non supporté dans ce prototype : documents **DOCX**, authentification utilisateur, création de documents Nuxeo, modification des permissions ou du cycle de vie.

## Technologies

| Technologie | Utilisation |
|-------------|-------------|
| Python | Traitements principaux |
| FastAPI | API backend |
| PyMuPDF | Extraction du texte natif des PDF |
| Tesseract / pytesseract | OCR des scans et images |
| spaCy | NLP / extraction d’entités |
| Regex | Extraction de motifs (SIRET, IBAN, dates, etc.) |
| scikit-learn | Classification |
| TF-IDF | Représentation du texte |
| Régression logistique | Classification documentaire |
| React / Vite | Interface de dépôt et de validation |
| nginx | Serveur statique de l’interface (image Docker) |
| JSON | Stockage local et export structuré |
| Nuxeo REST API | Intégration expérimentale (mise à jour Dublin Core) |

## Architecture

```text
Ged_Management_AI/
├── architecture/                 # Décisions d’architecture du prototype
├── samples/                      # Exemples de documents fictifs
├── services/
│   ├── demo-api/                 # Backend FastAPI (pipeline IA + Nuxeo)
│   │   ├── app/                  # Modules : OCR, classification, extraction, PII, export
│   │   ├── models/               # Emplacement du modèle .joblib (non versionné)
│   │   └── requirements.txt
│   ├── frontend/                 # Interface React / Vite
│   └── dataset/                  # Générateurs et corpus synthétiques d’entraînement
├── docker-compose.yml            # Lancement optionnel (API + frontend)
├── .env.example
├── .gitignore
└── README.md
```

- **`services/demo-api`** : unique backend du prototype (analyse, validation, export, adaptateur Nuxeo).
- **`services/frontend`** : unique écran (dépôt, analyse, correction, validation, envoi Nuxeo).
- **`services/dataset`** : textes administratifs **synthétiques** et script d’entraînement du classifieur.
- **`samples/`** : fichier d’exemple fictif pour une démonstration rapide.
- **`architecture/`** : notes de conception (périmètre volontairement réduit).

## Installation

```bash
git clone <url-de-votre-depot>
cd Ged_Management_AI
```

Prérequis : Python 3.11+, Node.js 18+, Tesseract OCR (langues `fra` et `eng`).

### Backend

```powershell
cd services\demo-api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
copy ..\..\.env.example .env
```

Sous Linux / macOS :

```bash
cd services/demo-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
cp ../../.env.example .env
```

Lancer l’API :

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Vérifier : http://127.0.0.1:8000/api/health

### Frontend

```powershell
cd services\frontend
npm install
npm run dev
```

Ouvrir http://localhost:5174 (le proxy Vite relaie `/api` vers `http://127.0.0.1:8000`).

### Docker (optionnel)

```bash
docker compose up --build
```

Interface : http://localhost:5173 — l’API Docker n’atteint en général **pas** une VM Nuxeo sur le réseau local. Pour la démonstration Nuxeo, privilégier Uvicorn sous Windows.

## Configuration

Copier `.env.example` vers `.env` (à la racine et/ou dans `services/demo-api/`). Renseigner uniquement les variables nécessaires. **Ne commitez jamais `.env`.**

| Variable | Rôle |
|----------|------|
| `DATA_DIR` | Dossier local des documents analysés |
| `NUXEO_URL` | URL de base Nuxeo (ex. `http://localhost:8080/nuxeo`) |
| `NUXEO_USERNAME` / `NUXEO_PASSWORD` | Identifiants (ne pas les publier) |
| `NUXEO_DOCUMENT_ID` | UID d’un document **déjà créé** dans Nuxeo |
| `MODEL_PATH` | Chemin optionnel vers `classifier.joblib` |

Sans `NUXEO_*`, l’analyse et la validation humaine fonctionnent ; seul l’envoi vers la GED est indisponible.

## Utilisation

1. Ouvrir l’interface (http://localhost:5174).
2. Déposer un PDF, une image ou un `.txt`.
3. Cliquer sur **Analyser**.
4. Consulter le type proposé et le niveau de confiance.
5. Consulter et, si besoin, **modifier** les métadonnées proposées.
6. Consulter le signalement de données personnelles potentielles.
7. **Valider** (ou rejeter) les propositions.
8. Afficher le JSON structuré.
9. Optionnel : **Envoyer vers Nuxeo** (après validation, si Nuxeo est configuré).

## Exemple de résultat

Exemple **entièrement fictif** (aucune donnée réelle) :

```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "document": {
    "file_name": "facture_demo.txt",
    "file_type": "text/plain",
    "document_type": { "value": "FACTURE", "source": "deterministic_rule" },
    "title": { "value": "Facture – septembre 2026 – ALPHA SERVICES DEMO" },
    "document_date": { "value": "2026-09-01" },
    "keywords": { "value": "Facture, Septembre 2026" }
  },
  "business_metadata": {
    "organization": { "value": "ALPHA SERVICES DEMO" },
    "invoice_number": { "status": "not_detected" },
    "iban": { "value": "FR7630004000500060007000890" }
  },
  "personal_data": {
    "contains_potential_personal_data": true,
    "categories": ["Adresse e-mail"],
    "entities": [
      { "type": "email", "value": "jean.dupont@example.com" }
    ]
  },
  "ai_information": {
    "ai_generated": true,
    "validation_status": "validated"
  }
}
```

## Intégration avec Nuxeo

Le prototype prépare des métadonnées structurées pouvant être exploitées par une GED telle que Nuxeo.

L’envoi consiste en une mise à jour **REST** des propriétés Dublin Core d’un document **existant** :

- `title` → `dc:title`
- résumé (type, organisation, date) → `dc:description`
- `organisation` → `dc:source`

`dc:subjects` n’est pas envoyé (vocabulaire contrôlé Nuxeo). Le PDF déjà stocké dans Nuxeo n’est **pas** remplacé.

Cette intégration est **expérimentale**. Elle ne constitue pas un déploiement complet, ni une solution de production.

## Limites

- Prototype académique, sans authentification ni multi-utilisateurs.
- Jeu d’entraînement limité et principalement synthétique.
- Qualité très dépendante du document (scan, mise en page, langue).
- L’OCR reste fragile sur les documents complexes ou de mauvaise qualité.
- La classification et l’extraction peuvent se tromper.
- La détection PII peut produire des faux positifs et des faux négatifs.
- Une **validation humaine** reste indispensable avant tout usage métier.

## Perspectives

- Enrichir le jeu d’entraînement et les catégories.
- Améliorer l’OCR et la détection PII.
- Intégrer plus complètement une GED (schémas dédiés, plus de propriétés).
- Réinjecter les corrections utilisateur dans une boucle *human-in-the-loop*.

## Contexte académique

Ce prototype a été développé dans le cadre d'un mémoire de Mastère consacré à l'utilisation de l'intelligence artificielle pour l'amélioration des métadonnées documentaires dans une Gestion Électronique des Documents (GED).

## Auteur

Hassanatou Diallo
