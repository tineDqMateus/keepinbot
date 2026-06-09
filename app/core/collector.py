"""
collector.py
Module 1 — Collecteur de documents publics — Keepinbot
=======================================================

Rôle : indexer des documents réglementaires publics dans la base RAG.
Ces documents sont taggés "public" — ils peuvent être traités en mode
cloud sans contrainte de confidentialité.


Source A — Dossier surveillé (data/public/)
  Indexe les PDFs déposés manuellement dans data/public/.
  Le bouton "Indexer" dans l'onglet Collecte Réglementation déclenche
  l'indexation. Le cron Docker (6h) peut aussi déclencher l'indexation
  si des fichiers sont en attente.
  Gestion des mises à jour : si un fichier du même nom existe déjà,
  l'ancienne version est archivée dans data/public/archive/ et ses
  chunks sont supprimés de ChromaDB avant indexation de la nouvelle.

Source B — URL directe (limitations)
  Tente de télécharger un PDF depuis une URL fournie manuellement.
  Non opérationnelle sur les sites gouvernementaux français —
  bloqués par Cloudflare et protections anti-bot.
  Peut fonctionner sur des URLs sans protection (intranets, serveurs
  internes, sites partenaires).

Pipeline commun (Source A et B) :
  PDF → extraction du texte (PyMuPDF) → chunking → ChromaDB


"""

import os
import requests
import fitz  # PyMuPDF
from datetime import datetime
from app.core.rag import chunk_documents, build_vectorstore, load_vectorstore
from app.core.config import CHROMA_PATH

# Dossier de dépôt des documents publics
PUBLIC_FOLDER = "./data/public"

# Dossier des documents déjà indexés — évite les doublons
INDEXED_FOLDER = "./data/public/indexed"

# Dossier d'archive pour les documents obsolètes ou à conserver hors indexation
ARCHIVE_FOLDER = "./data/public/archive"

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
def remove_from_vectorstore(filename: str) -> None:
    """
    Supprime tous les chunks d'un document de ChromaDB.
    Appelée avant l'indexation d'une nouvelle version du même document
    pour éviter les doublons et les réponses contradictoires.

    Paramètre :
    - filename : nom du fichier source (ex: "guide_embauche.pdf")
    """
    try:
        from app.core.rag import load_vectorstore
        vs = load_vectorstore()
        vs._collection.delete(where={"source": filename})
        print(f"Chunks supprimés pour : {filename}")
    except Exception as e:
        print(f"Erreur suppression chunks {filename} : {e}")


def index_folder(folder_path: str = PUBLIC_FOLDER) -> list[dict]:
    """
    Scanne le dossier de dépôt, indexe les nouveaux PDFs
    et gère automatiquement les mises à jour de documents existants.

    Workflow :
    1. Scanne data/public/ à la recherche de PDFs
    2. Pour chaque PDF :
       - Si une version existe déjà dans indexed/ :
         → Archive l'ancienne version avec timestamp dans archive/
         → Supprime les anciens chunks dans ChromaDB
       - Parse le nouveau PDF
       - Indexe dans ChromaDB
       - Déplace dans indexed/
    3. Garantit qu'une seule version par document est dans ChromaDB

    Paramètre :
    - folder_path : dossier à scanner (défaut : data/public/)

    Retourne :
    - liste de dicts des documents indexés avec succès
    """
    from datetime import datetime

    os.makedirs(folder_path, exist_ok=True)
    os.makedirs(INDEXED_FOLDER, exist_ok=True)
    os.makedirs(ARCHIVE_FOLDER, exist_ok=True)

    pdfs = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]

    if not pdfs:
        print(f"Aucun PDF en attente dans {folder_path}")
        return []

    parsed = []
    for filename in pdfs:
        filepath = os.path.join(folder_path, filename)
        indexed_path = os.path.join(INDEXED_FOLDER, filename)

        # Mise à jour : une version existe déjà
        if os.path.exists(indexed_path):
            print(f"Mise à jour détectée : {filename}")
            # Archiver l'ancienne version avec timestamp
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_path = os.path.join(ARCHIVE_FOLDER, f"{ts}_{filename}")
            os.rename(indexed_path, archive_path)
            print(f"Archivé : {archive_path}")
            # Supprimer les anciens chunks dans ChromaDB
            remove_from_vectorstore(filename)

        # Parser le nouveau PDF
        result = parse_pdf(filepath)
        if result["error"]:
            print(f"Erreur parsing {filename} : {result['error']}")
            continue

        print(f"Parsé : {filename} ({result['pages']} pages, "
              f"{len(result['content'])} caractères)")
        parsed.append(result)

        # Déplacer dans indexed/
        os.rename(filepath, indexed_path)

    if parsed:
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



# ── Planification périodique à gérer via Windows Scheduler ──────────────────────────────────────────────────
