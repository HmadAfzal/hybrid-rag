import json
from app.retrieve import search, client, COLLECTION

known, off = set(), None
while True:
    pts, off = client.scroll(COLLECTION, limit=500, offset=off, with_payload=["source"])
    known |= {p.payload["source"] for p in pts}
    if off is None:
        break

qs = []
for line in open("eval/questions.jsonl"):
    if line.strip():
        q = json.loads(line)
        if set(q["sources"]) & known:
            qs.append(q)
        else:
            print("WARN skipped (file not in corpus):", q["q"], q["sources"])


def rank(q, mode):
    for i, h in enumerate(search(q["q"], 5, mode=mode), 1):
        if h["source"] in q["sources"]:
            return i
    return None


print(f"{len(qs)} questions")
for mode in ["dense", "bm25", "hybrid", "rerank"]:
    r = [rank(q, mode) for q in qs]
    n = len(qs)
    r1 = sum(x == 1 for x in r) / n
    r5 = sum(x is not None for x in r) / n
    mrr = sum(1 / x for x in r if x) / n
    print(f"{mode:7} recall@1={r1:.2f}  recall@5={r5:.2f}  MRR={mrr:.2f}")