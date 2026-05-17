"""
rag.py — implémentation de la pipeline RAG (Retrieval-Augmented Generation) de Keepinbot
Chunking → Embeddings → Stockage ChromaDB → Retrieval → Génération

Rôle de chaque fonction :
- load_documents    : lit les fichiers du corpus et les charge en mémoire
- chunk_documents   : découpe les documents en fragments exploitables
- build_vectorstore : génère les embeddings et stocke dans ChromaDB
- load_vectorstore  : charge un vectorstore ChromaDB existant
- retrieve          : retrouve les chunks les plus pertinents pour une question
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.embeddings.base import Embeddings
from sentence_transformers import SentenceTransformer
from app.core.config import CHUNK_SIZE, CHUNK_OVERLAP, CHROMA_PATH, TOP_K
import os


class LocalEmbeddings(Embeddings):
    """
    Classe d'embeddings locale basée sur SentenceTransformer.

    Pourquoi cette classe existe :
    HuggingFaceEmbeddings de LangChain provoque un segmentation fault
    sur certaines configurations Windows. On appelle SentenceTransformer
    directement pour contourner ce bug, tout en restant compatible
    avec l'interface Embeddings attendue par LangChain et ChromaDB.

    Paramètre :
    - model_name : nom du modèle Sentence-Transformers à utiliser.
      "all-MiniLM-L6-v2" est un modèle léger (80 Mo), rapide sur CPU,
      qui produit des vecteurs de 384 dimensions. Bon compromis
      performance / ressources pour un usage local.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Vectorise une liste de textes (les chunks du corpus).
        Appelée lors de la construction du vectorstore.

        Paramètre :
        - texts : liste de chaînes de caractères à vectoriser

        Retourne :
        - liste de vecteurs (chaque vecteur = liste de floats)
        """
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        """
        Vectorise une question posée par l'utilisateur.
        Appelée lors du retrieval pour comparer la question aux chunks.

        Paramètre :
        - text : la question en langage naturel

        Retourne :
        - un vecteur (liste de floats) représentant le sens de la question
        """
        return self.model.encode(text, convert_to_numpy=True).tolist()


def load_documents(corpus_path: str) -> list[dict]:
    """
    Charge tous les fichiers .txt présents dans le dossier corpus.

    Paramètre :
    - corpus_path : chemin vers le dossier contenant les documents
      (défini dans config.py → CORPUS_PATH = "./data/corpus")

    Retourne :
    - liste de dicts, un par document :
        {
          "content" : texte brut du document,
          "source"  : nom du fichier (ex: "procedure_rh.txt"),
          "type"    : "interne" — tag de confidentialité utilisé
                      par le routeur hybride pour décider si la donnée
                      reste en local ou peut aller sur le cloud
        }
    """
    documents = []
    for filename in os.listdir(corpus_path):
        if filename.endswith(".txt"):
            path = os.path.join(corpus_path, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            documents.append({
                "content": content,
                "source": filename,
                "type": "interne"
            })
            print(f"Chargé : {filename} ({len(content)} caractères)")
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Découpe chaque document en chunks (fragments) de taille fixe.

    Pourquoi chunker :
    Un LLM a une fenêtre de contexte limitée — on ne peut pas lui envoyer
    un document entier. On découpe en petits blocs et on n'envoie que
    les blocs pertinents pour chaque question.

    Paramètres de découpe (définis dans config.py) :
    - CHUNK_SIZE    : taille maximale d'un chunk en caractères (500).
      Trop grand → trop de bruit dans le contexte envoyé au LLM.
      Trop petit → risque de couper une information en deux.
    - CHUNK_OVERLAP : chevauchement entre deux chunks consécutifs (50).
      Evite de perdre une information qui se trouverait exactement
      à la jonction entre deux chunks.

    Stratégie RecursiveCharacterTextSplitter :
    Découpe en respectant la hiérarchie naturelle du texte :
    d'abord sur les doubles sauts de ligne (paragraphes),
    puis sur les sauts de ligne simples, puis sur les points,
    puis sur les espaces — pour éviter de couper une phrase en plein milieu.

    Paramètre :
    - documents : liste de dicts produite par load_documents()

    Retourne :
    - liste de dicts, un par chunk :
        {
          "content"  : texte du fragment,
          "source"   : fichier d'origine (conservé pour la citation des sources),
          "type"     : tag de confidentialité hérité du document parent,
          "chunk_id" : identifiant unique du chunk (nom_fichier + numéro)
        }
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "]
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, split in enumerate(splits):
            chunks.append({
                "content": split,
                "source": doc["source"],
                "type": doc["type"],
                "chunk_id": f"{doc['source']}_{i}"
            })

    print(f"Chunking : {len(documents)} documents → {len(chunks)} chunks")
    return chunks


def build_vectorstore(chunks: list[dict]) -> Chroma:
    """
    Génère les embeddings de chaque chunk et les stocke dans ChromaDB.

    Ce qui se passe :
    1. Chaque chunk est transformé en vecteur numérique (embedding)
       via LocalEmbeddings — ce vecteur représente le "sens" du texte
    2. Les vecteurs sont stockés dans ChromaDB avec leurs métadonnées
       (source, type, chunk_id) pour pouvoir les retrouver et les citer

    ChromaDB en mode local :
    Les vecteurs sont sauvegardés sur disque dans CHROMA_PATH
    (./data/chroma). Aucune donnée ne sort de la machine.
    Le vectorstore persiste entre les sessions — pas besoin de
    reconstruire à chaque démarrage.

    Paramètre :
    - chunks : liste de dicts produite par chunk_documents()

    Retourne :
    - instance Chroma prête à être interrogée
    """
    print("Chargement du modèle d'embeddings...")
    embeddings = LocalEmbeddings()

    # Séparation du contenu et des métadonnées pour ChromaDB
    texts = [c["content"] for c in chunks]
    metadatas = [
        {"source": c["source"], "type": c["type"], "chunk_id": c["chunk_id"]}
        for c in chunks
    ]

    print("Génération des embeddings et stockage ChromaDB...")
    vectorstore = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        persist_directory=CHROMA_PATH  # sauvegarde sur disque
    )

    print(f"Vectorstore créé — {len(texts)} chunks indexés dans {CHROMA_PATH}")
    return vectorstore


def load_vectorstore() -> Chroma:
    """
    Charge un vectorstore ChromaDB existant depuis le disque.

    Utilisé au démarrage de l'application pour éviter de reconstruire
    les embeddings à chaque session — la construction est coûteuse
    (quelques secondes à minutes selon le corpus), le chargement est rapide.

    Prérequis : build_vectorstore() doit avoir été appelé au moins une fois.

    Retourne :
    - instance Chroma chargée depuis CHROMA_PATH, prête à être interrogée
    """
    embeddings = LocalEmbeddings()
    vectorstore = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )
    return vectorstore


def retrieve(query: str, vectorstore: Chroma) -> list[dict]:
    """
    Retrouve les chunks les plus pertinents pour une question donnée.

    Mécanisme :
    1. La question est vectorisée (embed_query)
    2. ChromaDB calcule la similarité cosinus entre le vecteur
       de la question et tous les vecteurs stockés
    3. Les TOP_K chunks les plus proches sont retournés avec leur score

    Score de similarité cosinus dans ChromaDB :
    - Score proche de 0 → très pertinent (vecteurs presque identiques)
    - Score proche de 2 → peu pertinent (vecteurs opposés)
    Attention : ChromaDB retourne une distance, pas une similarité —
    plus le score est BAS, meilleure est la correspondance.

    Paramètres :
    - query       : question posée par l'utilisateur en langage naturel
    - vectorstore : instance Chroma chargée via load_vectorstore()
    - TOP_K       : nombre de chunks à retourner (défini dans config.py = 3)
                    Augmenter TOP_K → plus de contexte mais plus de bruit.
                    Diminuer TOP_K → contexte plus précis mais risque de manquer
                    une information répartie sur plusieurs chunks.

    Retourne :
    - liste de dicts, un par chunk retourné :
        {
          "content" : texte du chunk,
          "source"  : fichier d'origine (pour citation dans la réponse),
          "type"    : tag de confidentialité (pour le routeur hybride),
          "score"   : distance cosinus (float, plus bas = plus pertinent)
        }
    """
    results = vectorstore.similarity_search_with_score(query, k=TOP_K)

    chunks = []
    for doc, score in results:
        chunks.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "inconnu"),
            "type": doc.metadata.get("type", "inconnu"),
            "score": round(score, 3)
        })
        print(f"  → {doc.metadata.get('source')} (score : {round(score, 3)})")

    return chunks