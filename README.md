# Hybrid RAG

RAG over the FastAPI docs. Dense + BM25 retrieval fused with RRF, cross-encoder reranking, and claim-level citation verification. Every sentence in the final answer was checked by an LLM judge against the source chunk it cites. Unsupported sentences are dropped.


## Evals

**Retrieval** (41 questions, a hit is a correct source file in the results)

| Mode | recall@1 | recall@5 | MRR |
|---|---|---|---|
| dense | 0.68 | 0.93 | 0.79 |
| bm25 | 0.56 | 0.80 | 0.65 |
| hybrid | 0.76 | 0.95 | 0.83 |
| hybrid + rerank | 0.80 | 0.93 | 0.86 |

Hybrid beats either retriever alone. Reranking improves ordering but dropped recall@5 by one question. One question is about 2.4 points, so small gaps are noise.

**Answer quality**

| Metric | Result |
|---|---|
| Faithfulness (claims judged supported, before filtering) | 49/56 = 0.88 |
| Answerable questions that got an answer | 24/25 |
| Refusal on off-topic questions | 12/12 |
| Refusal on near-miss questions (FastAPI-flavored, not in the docs) | 8/8 |

- Manual review of 15 judged claims agreed with the judge on 13. One was too strict, one too lenient. Small sample.
- 2 of the original 10 near-miss questions were removed after review because the docs do cover them.
- Most unsupported claims came from corpus gaps (code samples not ingested, facts cut off at a chunk boundary) or from the model adding outside knowledge.

## Guardrails

- Query length limit (500 chars) and a per-IP rate limit (10 requests/minute).
- Retrieved text is treated as untrusted in both the generator and the judge prompts. Tested with one injected instruction against the generator and one against the judge.

## Run it

```bash
cp .env.example .env              
docker compose up -d --build
git clone --depth 1 https://github.com/fastapi/fastapi corpus_src
rm corpus_src/docs/en/docs/release-notes.md
uv sync && uv run python -m app.ingest corpus_src/docs/en/docs
curl -sG localhost:8001/ask --data-urlencode "q=how do I declare a query parameter"
```

The first request downloads the models (about a minute).

Evals: `uv run --env-file .env python -m eval.run_eval` (retrieval), `-m eval.run_faith` (faithfulness and refusal), `-m eval.run_near` (near-miss refusal).

## Limits

- The same model family generates and judges, so the judge can share blind spots.
- A grounded answer can still be off-topic. Faithfulness does not measure relevance.
- Fixed-size chunking cuts some sections mid-sentence.
- The docs include code from separate files via placeholders. Those files are not ingested, so answers are prose only.
- The retrieval eval matches on source file, not on the exact passage.
- The rate limiter is in memory, single process, and resets on restart. No authentication.