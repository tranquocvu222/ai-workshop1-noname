import os
import json
import hashlib
import math
from typing import List, Dict, Any, Optional

# Define CHROMA_AVAILABLE before the try block
CHROMA_AVAILABLE = False

# Try to import chromadb; if unavailable we use an in-memory fallback
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False

# Simple deterministic hash-based embedding (fixed-size vector) to avoid extra heavy deps
EMBED_DIM = 128

def _embed_texts(texts: List[str]) -> List[List[float]]:
    vectors = []
    for t in texts:
        vec = [0.0] * EMBED_DIM
        # normalize and take tokens (simple whitespace + char ngrams)
        s = (t or "").lower()
        tokens = s.split()
        # use tokens and char ngrams to create deterministic distribution
        for token in tokens:
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest()[:8], 16)
            idx = h % EMBED_DIM
            vec[idx] += 1.0
            # add char ngrams
            for i in range(len(token)-1):
                gram = token[i:i+2]
                gh = int(hashlib.md5(gram.encode('utf-8')).hexdigest()[:8], 16)
                idx2 = gh % EMBED_DIM
                vec[idx2] += 0.5
        # normalize vector
        norm = math.sqrt(sum(x*x for x in vec)) or 1.0
        vec = [x / norm for x in vec]
        vectors.append(vec)
    return vectors

class LocalChromaDB:
    """
    Lightweight wrapper that uses chromadb (if installed) or an in-memory fallback.
    - Collections are named (e.g., 'faqs', 'symptoms')
    - Documents structure: { "id": str, "text": str, "metadata": dict }
    """
    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        CHROMA_AVAILABLE = True
        if CHROMA_AVAILABLE:
            try:
                # Updated to use the new client initialization as per Chroma docs
                # https://docs.trychroma.com/deployment/migration
                self.client = chromadb.PersistentClient(path=self.persist_dir)
                print(f"ChromaDB initialized with persistent storage at: {self.persist_dir}")
            except Exception as e:
                print(f"Error initializing ChromaDB client: {str(e)}")
                print("Falling back to in-memory collection")
                try:
                    # Try with in-memory client as fallback
                    self.client = chromadb.Client()
                except Exception as e2:
                    print(f"Error initializing in-memory ChromaDB: {str(e2)}")
                    self.client = None
                    CHROMA_AVAILABLE = False
        else:
            self.client = None
            # simple in-memory store: {collection_name: [doc, ...]}
            self._collections = {}

    def _get_collection(self, name: str):
        if CHROMA_AVAILABLE and self.client:
            try:
                # Try to get existing collection
                return self.client.get_collection(name)
            except Exception:
                # Collection doesn't exist, create new one
                try:
                    # For the new API, specify the embedding function directly
                    return self.client.create_collection(
                        name=name,
                        metadata={"hnsw:space": "cosine"}  # Use cosine similarity
                    )
                except Exception as e:
                    print(f"Error creating collection {name}: {str(e)}")
                    return None
        else:
            # Use in-memory fallback
            return self._collections.setdefault(name, [])

    def add_documents(self, collection_name: str, docs: List[Dict[str, Any]]):
        """
        docs: list of {"id": str, "text": str, "metadata": dict}
        """
        if not docs:
            return
        if CHROMA_AVAILABLE and self.client:
            coll = self._get_collection(collection_name)
            if not coll:
                return
                
            ids = [d["id"] for d in docs]
            texts = [d.get("text", "") for d in docs]
            metadatas = [d.get("metadata", {}) for d in docs]
            embeddings = _embed_texts(texts)
            
            try:
                coll.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
                print(f"Added {len(docs)} documents to collection '{collection_name}'")
            except Exception as e:
                print(f"Error adding documents to collection '{collection_name}': {str(e)}")
        else:
            # In-memory fallback
            coll = self._get_collection(collection_name)
            # replace or append by id
            existing_ids = {d["id"]: d for d in coll}
            for d in docs:
                existing_ids[d["id"]] = d
            # store list
            self._collections[collection_name] = list(existing_ids.values())

    def query(self, collection_name: str, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Returns top-k matching documents as list of {"id","text","metadata","score"}
        """
        if CHROMA_AVAILABLE and self.client:
            try:
                coll = self._get_collection(collection_name)
                if not coll:
                    return []
                    
                q_emb = _embed_texts([query_text])
                
                # Update query parameters to use the correct format
                # The 'include' parameter now expects a list of strings, not separate parameters
                res = coll.query(
                    query_embeddings=q_emb, 
                    n_results=n_results, 
                    include=["documents", "metadatas", "distances"]
                )
                
                results = []
                docs = res.get("documents", [[]])[0]
                metadatas = res.get("metadatas", [[]])[0]
                distances = res.get("distances", [[]])[0]
                
                # Get IDs from the collection's internal order - this might not be reliable
                # but we're working with what we have since 'ids' is no longer returned
                ids = [f"doc_{i}" for i in range(len(docs))]
                
                for i in range(len(docs)):
                    results.append({
                        "id": ids[i] if i < len(ids) else f"doc_{i}",
                        "text": docs[i],
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "score": float(distances[i]) if i < len(distances) else 0.0
                    })
                    print(results)
                return results
            except Exception as e:
                print(f"Error querying collection '{collection_name}': {str(e)}")
                return []
        else:
            # simple keyword overlap ranking
            coll = self._get_collection(collection_name)
            q_tokens = set((query_text or "").lower().split())
            scored = []
            for d in coll:
                text = (d.get("text","") or "").lower()
                tokens = set(text.split())
                overlap = len(q_tokens & tokens)
                scored.append((overlap, d))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, d in scored[:n_results]:
                results.append({
                    "id": d.get("id"),
                    "text": d.get("text"),
                    "metadata": d.get("metadata", {}),
                    "score": float(score)
                })
                print(results)
            return results

    def ingest_json_file(self, collection_name: str, file_path: str, id_prefix: str = ""):
        """
        Load a JSON file and ingest into collection. Accepts two common shapes:
        - {"faqs": [ {question, answer}, ... ]}
        - [{"id":..., "text":..., "metadata":...}, ...]
        """
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading JSON file {file_path}: {str(e)}")
            return

        docs = []
        # faqs shape
        if isinstance(data, dict):
            # common keys
            if "faqs" in data and isinstance(data["faqs"], list):
                for i, item in enumerate(data["faqs"]):
                    q = item.get("question", "")
                    a = item.get("answer", "")
                    doc_id = f"{id_prefix}faq_{i}"
                    docs.append({"id": doc_id, "text": f"Q: {q}\nA: {a}", "metadata": {"source": os.path.basename(file_path), "question": q, "answer": a}})
            elif "symptoms" in data and isinstance(data["symptoms"], list):
                for i, item in enumerate(data["symptoms"]):
                    desc = item.get("description") or item.get("symptom") or json.dumps(item)
                    doc_id = f"{id_prefix}sym_{i}"
                    # Convert any lists in metadata to strings to avoid ChromaDB error
                    metadata = {"source": os.path.basename(file_path)}
                    for k, v in item.items():
                        if isinstance(v, list):
                            metadata[k] = ", ".join(str(x) for x in v)
                        else:
                            metadata[k] = v
                    docs.append({"id": doc_id, "text": desc, "metadata": metadata})
            else:
                # generic dict of entries -> flatten
                for k,v in data.items():
                    doc_id = f"{id_prefix}{k}"
                    docs.append({"id": doc_id, "text": str(v), "metadata": {"key": k, "source": os.path.basename(file_path)}})
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    doc_id = item.get("id") or f"{id_prefix}doc_{i}"
                    text = item.get("text") or item.get("content") or json.dumps(item)
                    # Convert any lists in metadata to strings
                    metadata = {}
                    for k, v in item.get("metadata", {**item}).items():
                        if isinstance(v, list):
                            metadata[k] = ", ".join(str(x) for x in v)
                        else:
                            metadata[k] = v
                    docs.append({"id": doc_id, "text": text, "metadata": metadata})
                else:
                    docs.append({"id": f"{id_prefix}doc_{i}", "text": str(item), "metadata": {}})

        if docs:
            print(f"Ingesting {len(docs)} documents into collection '{collection_name}' from {file_path}")
            self.add_documents(collection_name, docs)
        else:
            print(f"No documents found to ingest from {file_path}")

    def load_and_ingest_default_data(self, base_data_dir: str):
        """
        Look for faqs.json and symptoms.json in base_data_dir and ingest them into 'faqs' and 'symptoms' collections.
        Also ingest doctors and departments as metadata contexts (short summaries).
        """
        # Check both the standard data dir and the src/data dir
        data_dirs = [
            base_data_dir,  # Standard data directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")  # src/data directory
        ]

        for data_dir in data_dirs:
            if os.path.exists(data_dir):
                print(f"Checking for data files in: {data_dir}")

                # ingest faqs and symptoms if present
                faqs_path = os.path.join(data_dir, "faqs.json")
                symptoms_path = os.path.join(data_dir, "symptoms.json")

                if os.path.exists(faqs_path):
                    print(f"Found FAQs file: {faqs_path}")
                    self.ingest_json_file("faqs", faqs_path, id_prefix="faqs_")
                else:
                    print(f"FAQs file not found at: {faqs_path}")

                if os.path.exists(symptoms_path):
                    print(f"Found symptoms file: {symptoms_path}")
                    self.ingest_json_file("symptoms", symptoms_path, id_prefix="sym_")
                else:
                    print(f"Symptoms file not found at: {symptoms_path}")
                
                # Also ingest a simple doctors snapshot to a 'doctors' collection if there's a doctors.json
                doctors_path = os.path.join(data_dir, "doctors.json")
                if os.path.exists(doctors_path):
                    print(f"Found doctors file: {doctors_path}")
                    try:
                        with open(doctors_path, 'r', encoding='utf-8') as f:
                            ddata = json.load(f)
                        docs = []
                        for doc in ddata.get("doctors", []):
                            doc_id = doc.get("id")
                            text = f"{doc.get('name')} - {doc.get('specialty')} - {doc.get('experience')}"
                            metadata = {k: v for k, v in doc.items()}
                            docs.append({"id": doc_id, "text": text, "metadata": metadata})
                        if docs:
                            self.add_documents("doctors", docs)
                            print(f"Ingested {len(docs)} doctors into 'doctors' collection")
                    except Exception as e:
                        print(f"Error ingesting doctors data: {str(e)}")
