import os
from fastembed import TextEmbedding, SparseTextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from qdrant_client import QdrantClient, models

COLLECTION = "docs"
client = QdrantClient(os.getenv("QDRANT_HOST", "localhost"), port=6333)
dense = TextEmbedding("BAAI/bge-small-en-v1.5")
sparse = SparseTextEmbedding("Qdrant/bm25")
reranker = TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2")


def search(q, k=5, pool=20, mode="rerank"):
    d = next(dense.query_embed(q)).tolist()
    s = next(sparse.query_embed(q))
    sv = models.SparseVector(indices=s.indices.tolist(), values=s.values.tolist())
    if mode == "dense":
        res = client.query_points(COLLECTION, query=d, using="dense", limit=k, with_payload=True)
    elif mode == "bm25":
        res = client.query_points(COLLECTION, query=sv, using="bm25", limit=k, with_payload=True)
    else:
        res = client.query_points(
            COLLECTION,
            prefetch=[
                models.Prefetch(query=d, using="dense", limit=30),
                models.Prefetch(query=sv, using="bm25", limit=30),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=pool if mode == "rerank" else k,
            with_payload=True,
        )
    hits = [{"score": p.score, **p.payload} for p in res.points]
    if mode != "rerank":
        return hits
    scores = list(reranker.rerank(q, [h["text"] for h in hits]))
    ranked = sorted(zip(scores, hits), key=lambda x: x[0], reverse=True)[:k]
    return [{**h, "score": float(sc)} for sc, h in ranked]