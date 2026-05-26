"""
collector.py
Module 1 — Collecteur de documents publics — Keepinbot
=======================================================
Trois sources de collecte indépendantes qui alimentent le même pipeline :

Source A — Dossier surveillé : indexe automatiquement les PDFs déposés
           dans un dossier local (data/public/)
Source B — URL directe : télécharge et indexe un PDF depuis une URL
Source C — API Légifrance : interroge l'API officielle pour récupérer
           des textes réglementaires (nécessite une clé API)

Pipeline commun (identique pour les trois sources) :
  PDF → parsing PyMuPDF → extraction métadonnées → chunking → ChromaDB

Principe de confidentialité :
Les documents collectés sont taggés "public" — ils peuvent être
traités en mode cloud sans contrainte de confidentialité.
"""

import os
import requests
import fitz  # PyMuPDF
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.rag import chunk_documents, build_vectorstore, load_vectorstore
from app.core.config import CHROMA_PATH

# Dossier de dépôt des documents publics
PUBLIC_FOLDER = "./data/public"

# Dossier des documents déjà indexés — évite les doublons
INDEXED_FOLDER = "./data/public/indexed"


# ── Parser PDF ────────────────────────────────────────────────────────────────

def parse_pdf(filepath: str) -> dict:
    """
    Extrait le texte et les métadonnées d'un fichier PDF via PyMuPDF.

    PyMuPDF (fitz) est robuste sur les PDFs complexes — colonnes,
    tableaux, PDFs scannés avec couche texte. Il extrait le texte
    page par page et reconstruit un flux continu.

    Paramètre :
    - filepath : chemin complet vers le fichier PDF

    Retourne un dict :
    {
      "content"    : texte extrait (str),
      "source"     : nom du fichier (str),
      "type"       : "public" — tag de confidentialité,
      "pages"      : nombre de pages (int),
      "date_index" : date d'indexation ISO (str),
      "error"      : message d'erreur ou None
    }
    """
    filename = os.path.basename(filepath)
    try:
        doc = fitz.open(filepath)
        pages_text = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():  # ignore les pages vides
                pages_text.append(f"[Page {page_num + 1}]\n{text}")

        full_text = "\n\n".join(pages_text)
        num_pages = len(doc)
        doc.close()

        return {
            "content": full_text,
            "source": filename,
            "type": "public",
            "pages": num_pages,
            "date_index": datetime.now().isoformat(),
            "error": None
        }
    except Exception as e:
        return {
            "content": "",
            "source": filename,
            "type": "public",
            "pages": 0,
            "date_index": datetime.now().isoformat(),
            "error": str(e)
        }


# ── Source A — Dossier surveillé ──────────────────────────────────────────────

def index_folder(folder_path: str = PUBLIC_FOLDER) -> list[dict]:
    """
    Scanne un dossier local, parse tous les PDFs présents
    et les indexe dans ChromaDB.

    Workflow :
    1. Liste les PDFs dans le dossier
    2. Parse chaque PDF avec parse_pdf()
    3. Déplace les PDFs indexés dans le sous-dossier indexed/
       pour éviter de les retraiter à la prochaine exécution
    4. Met à jour le vectorstore ChromaDB

    Paramètre :
    - folder_path : chemin vers le dossier à surveiller
                    (par défaut : data/public/)

    Retourne :
    - liste de dicts des documents indexés avec succès
    """
    os.makedirs(folder_path, exist_ok=True)
    os.makedirs(INDEXED_FOLDER, exist_ok=True)

    pdfs = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]

    if not pdfs:
        print(f"Aucun PDF trouvé dans {folder_path}")
        return []

    parsed = []
    for filename in pdfs:
        filepath = os.path.join(folder_path, filename)
        result = parse_pdf(filepath)

        if result["error"]:
            print(f"Erreur parsing {filename} : {result['error']}")
            continue

        print(f"Parsé : {filename} ({result['pages']} pages, {len(result['content'])} caractères)")
        parsed.append(result)

        # Déplacement dans indexed/ pour éviter le retraitement
        indexed_path = os.path.join(INDEXED_FOLDER, filename)
        os.rename(filepath, indexed_path)

    if parsed:
        # Mise à jour du vectorstore avec les nouveaux documents
        chunks = chunk_documents(parsed)
        build_vectorstore(chunks)
        print(f"{len(parsed)} document(s) indexé(s) dans ChromaDB")

    return parsed


# ── Source B — URL directe ────────────────────────────────────────────────────

def index_from_url(url: str, filename: str = None) -> dict:
    """
    Télécharge un PDF depuis une URL et l'indexe dans ChromaDB.

    Cas d'usage : PDFs publics directement accessibles (rapports,
    circulaires, guides pratiques) sur des sites sans protection anti-bot.

    Paramètres :
    - url      : URL directe vers le fichier PDF
    - filename : nom à donner au fichier (optionnel —
                 déduit de l'URL si non fourni)

    Retourne :
    - dict du document indexé ou dict d'erreur

    Note : cette fonction nécessite un accès réseau au site cible.
    En cas de blocage réseau, utiliser la Source A (dépôt manuel).
    """
    if not filename:
        filename = url.split("/")[-1]
        if not filename.endswith(".pdf"):
            filename += ".pdf"

    # Téléchargement avec User-Agent navigateur pour éviter les blocages
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        print(f"Téléchargement : {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Sauvegarde temporaire pour parsing
        tmp_path = os.path.join(PUBLIC_FOLDER, filename)
        os.makedirs(PUBLIC_FOLDER, exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(response.content)

        print(f"Téléchargé : {filename} ({len(response.content)} octets)")

        # Parsing et indexation
        result = parse_pdf(tmp_path)
        if not result["error"]:
            chunks = chunk_documents([result])
            build_vectorstore(chunks)
            print(f"Indexé : {filename}")

            # Déplacement dans indexed/
            os.makedirs(INDEXED_FOLDER, exist_ok=True)
            os.rename(tmp_path, os.path.join(INDEXED_FOLDER, filename))

        return result

    except requests.exceptions.ConnectionError:
        return {"error": f"Impossible d'accéder à {url} — vérifier la connexion réseau"}
    except requests.exceptions.Timeout:
        return {"error": f"Délai dépassé pour {url}"}
    except Exception as e:
        return {"error": str(e)}


# ── Source C — API Légifrance ─────────────────────────────────────────────────

def index_from_legifrance(search_term: str, api_key: str = None) -> list[dict]:
    """
    Interroge l'API officielle Légifrance pour récupérer des textes
    réglementaires et les indexer dans ChromaDB.

    API Légifrance (DILA) :
    - Gratuite, nécessite une clé d'accès (oauth2)
    - Documentation : https://api.gouv.fr/les-api/api-legifrance
    - Inscription : https://piste.gouv.fr

    Paramètres :
    - search_term : terme de recherche (ex: "contrat de travail", "préavis")
    - api_key     : clé API Légifrance (ou None si non configurée)

    Retourne :
    - liste de dicts des textes indexés

    Note : cette source est non testable sans clé API.
    Le code est prêt pour un déploiement avec clé configurée
    dans le fichier .env (LEGIFRANCE_API_KEY).
    """
    if not api_key:
        api_key = os.getenv("LEGIFRANCE_API_KEY")

    if not api_key:
        return [{"error": "Clé API Légifrance manquante. Ajouter LEGIFRANCE_API_KEY dans .env. Inscription gratuite sur developer.aife.economie.gouv.fr"}]

    # Structure de l'appel API Légifrance (OAuth2 + REST)
    # URLs de production
    token_url = "https://oauth.piste.gouv.fr/api/oauth/token"
    search_url = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/search"

    try:
        # Authentification OAuth2
        token_response = requests.post(token_url, data={
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": os.getenv("LEGIFRANCE_API_SECRET", ""),
            "scope": "openid"
        }, timeout=10)

        if token_response.status_code != 200:
            return [{"error": f"Authentification Légifrance échouée : {token_response.status_code} — {token_response.text[:200]}"}]

        token = token_response.json().get("access_token")
        print(f"Token obtenu : {token[:20]}..." if token else "Token absent")

        # Recherche de textes
        search_response = requests.post(
            search_url,
            headers={"Authorization": f"Bearer {token}"},
            json={
                "fond": "ALL",
                "recherche": {
                    "champs": [
                        {
                            "typeChamp": "ALL",
                            "criteres": [
                                {
                                    "typeRecherche": "UN_DES_MOTS",
                                    "valeur": search_term
                                }
                            ],
                            "operateur": "ET"
                        }
                    ],
                    "pageNumber": 1,
                    "pageSize": 5,
                    "sort": "PERTINENCE"
                }
            },
            timeout=15
        )

        if search_response.status_code != 200:
            return [{"error": f"Recherche Légifrance échouée : {search_response.status_code} — {search_response.text[:300]}"}]
        
        results = search_response.json().get("results", [])
        indexed = []

        for item in results:
            title = item.get("titles", [{}])[0].get("title", "Sans titre")
            text = item.get("excerpt", "")

            if text:
                doc = {
                    "content": f"{title}\n\n{text}",
                    "source": f"legifrance_{title[:50].replace(' ', '_')}.txt",
                    "type": "public",
                    "pages": 1,
                    "date_index": datetime.now().isoformat(),
                    "error": None
                }
                indexed.append(doc)
                print(f"Récupéré : {title}")

        if indexed:
            chunks = chunk_documents(indexed)
            build_vectorstore(chunks)
            print(f"{len(indexed)} texte(s) Légifrance indexé(s)")

        return indexed

    except Exception as e:
        return [{"error": str(e)}]


# ── Planification périodique ──────────────────────────────────────────────────

def start_scheduler(interval_hours: int = 24) -> BackgroundScheduler:
    """
    Lance un planificateur qui exécute la collecte périodiquement.
    Surveille le dossier data/public/ et indexe les nouveaux PDFs.

    Paramètre :
    - interval_hours : fréquence de collecte en heures (défaut : 24h)
                       En production : 24h pour une veille quotidienne.
                       En développement : réduire pour tester.

    Retourne :
    - instance BackgroundScheduler active

    Note : le scheduler tourne en arrière-plan dans un thread séparé —
    il n'interrompt pas l'application Streamlit.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        index_folder,
        trigger="interval",
        hours=interval_hours,
        id="collecte_publique",
        name="Collecte documents publics"
    )
    scheduler.start()
    print(f"Planificateur démarré — collecte toutes les {interval_hours}h")
    return scheduler


def get_scheduler_status(scheduler: BackgroundScheduler) -> dict:
    """
    Retourne l'état du planificateur pour l'affichage dans l'interface.

    Paramètre :
    - scheduler : instance BackgroundScheduler retournée par start_scheduler()

    Retourne un dict :
    {
      "running"    : True si le scheduler est actif (bool),
      "next_run"   : date/heure de la prochaine exécution (str),
      "last_index" : nombre de fichiers dans indexed/ (int)
    }
    """
    jobs = scheduler.get_jobs()
    next_run = None
    if jobs:
        next_run = jobs[0].next_run_time.strftime("%d/%m/%Y %H:%M") if jobs[0].next_run_time else "Non planifié"

    indexed_count = len(os.listdir(INDEXED_FOLDER)) if os.path.exists(INDEXED_FOLDER) else 0

    return {
        "running": scheduler.running,
        "next_run": next_run,
        "last_index": indexed_count
    }