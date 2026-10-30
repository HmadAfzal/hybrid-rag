import os
import sys, uuid
from pathlib import Path
from pypdf import PdfReader
from fastembed import TextEmbedding, SparseTextEmbedding
from qdrant_client import QdrantClient, models

COLLECTION = "docs"
client = (
    QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.getenv("QDRANT_API_KEY"))
    if os.getenv("QDRANT_URL")
    else QdrantClient(os.getenv("QDRANT_HOST", "localhost"), port=6333)
)
dense = TextEmbedding("BAAI/bge-small-en-v1.5")
sparse = SparseTextEmbedding("Qdrant/bm25")


def load(path):
    if path.suffix == ".pdf":
        for i, p in enumerate(PdfReader(path).pages, 1):
            yield i, p.extract_text() or ""
    else:
        yield 1, path.read_text(errors="ignore")


def chunk(text, size=1800, overlap=200):
    # shortcut: fixed char windows (~450 tokens), upgrade to heading-aware split if chunks cut sections badly
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size].strip()]


def main(folder):
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            COLLECTION,
            vectors_config={"dense": models.VectorParams(size=384, distance=models.Distance.COSINE)},
            sparse_vectors_config={"bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
    items = [
        (f.name, page, c)
        for f in Path(folder).rglob("*") if f.suffix in {".md", ".pdf"}
        for page, text in load(f)
        for c in chunk(text)
    ]
    print(len(items), "chunks to embed", flush=True)
    for i in range(0, len(items), 16):
        batch = items[i:i + 16]
        texts = [t for _, _, t in batch]
        dv, sv = list(dense.embed(texts)), list(sparse.embed(texts))
        client.upsert(COLLECTION, [
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{src}{pg}{t}")),  # same chunk = same id, re-runs don't duplicate
                vector={"dense": d.tolist(), "bm25": models.SparseVector(indices=s.indices.tolist(), values=s.values.tolist())},
                payload={"source": src, "page": pg, "text": t},
            )
            for (src, pg, t), d, s in zip(batch, dv, sv)
        ])
        print(f"{min(i + 16, len(items))}/{len(items)}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])