# Hybrid RAG with verified citations
Question answering over the FastAPI docs.

**Live demo:** https://huggingface.co/spaces/llhax/hybrid-rag (free hosting, so the first request after a quiet period is slow)


## How it works

1. **Ingest.** Markdown and PDF files are split into ~1800 character windows with 200 characters of overlap. Each chunk gets a dense embedding (`bge-small-en-v1.5`) and a BM25 sparse vector, and both go into Qdrant.
2. **Retrieve.** Dense and BM25 each return 30 candidates. Qdrant fuses them with reciprocal rank fusion, the top 20 go through a cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`), and the best 5 are kept.
3. **Answer.** The LLM (gpt-oss-120b on Groq) returns JSON: a list of one-sentence claims, each with the source numbers it relies on.
4. **Verify.** A second LLM call checks each claim against only the chunks it cites. A claim is kept only if the judge says the source directly supports it. Missing citations, bad source numbers, or unreadable judge output all count as unsupported. If nothing survives, the answer is "I don't know."

## Results

All numbers come from the scripts in `eval/`.

**Retrieval** (41 questions about the FastAPI docs; a hit means a correct source file shows up in the results)

| Method | recall@1 | recall@5 | MRR |
|---|---|---|---|
| Dense only | 0.68 | 0.93 | 0.79 |
| BM25 only | 0.56 | 0.80 | 0.65 |
| Hybrid (RRF) | 0.76 | 0.95 | 0.83 |
| Hybrid + rerank | 0.80 | 0.93 | 0.86 |

**Answers**

| Check | Result |
|---|---|
| Claims supported by their cited source (25 questions, 56 claims) | 49/56 (0.88) |
| Answerable questions that got an answer | 24/25 |
| Off-topic questions correctly refused | 12/12 |
| FastAPI-flavored questions the docs don't cover, refused | 8/8 |
| Judge vs. my own review of 15 claims | agreed on 13 |

## Findings

- First retrieval eval was too easy. Dense, hybrid and rerank all scored 0.97 recall@5, which says nothing. After adding questions with exact identifiers and paraphrases, hybrid pulled ahead on recall@1 and MRR.
- Reranking improves ordering but dropped recall@5 by one question. With 41 questions, one question is about 2.4 points, so treat small gaps as noise.
- Asking the model to put `[n]` markers in free text did not work with gpt-oss, which invented its own citation format. Having it return structured JSON claims fixed that and removed the sentence-splitting regex.
- Most unsupported claims were not wild hallucinations. They came from code samples that live in separate files (not ingested), a fact cut off at a chunk boundary, or the model adding something from its own knowledge. The judge caught those.

## Guardrails

- Questions are limited to 500 characters, and each IP gets 10 requests per minute.
- Retrieved text is treated as untrusted in both the answer prompt and the judge prompt. Tested one injected instruction against each (`tests/`).

## Run it locally

You need Docker, [uv](https://docs.astral.sh/uv/) and a free [Groq](https://console.groq.com) API key.

```bash
git clone <this repo> && cd rag
cp .env.example .env                    
docker compose up -d qdrant

git clone --depth 1 https://github.com/fastapi/fastapi corpus_src
rm corpus_src/docs/en/docs/release-notes.md
uv sync
uv run --env-file .env python -m app.ingest corpus_src/docs/en/docs

uv run --env-file .env uvicorn app.main:app --port 8001
```

Open http://localhost:8001 for the web page, or call the API directly:

```bash
curl -sG localhost:8001/ask --data-urlencode "q=how do I declare a query parameter"
```

The first request downloads the models, which takes a minute. To run the API in Docker as well, use `docker compose up -d --build`. To use Qdrant Cloud instead of the local container, set `QDRANT_URL` and `QDRANT_API_KEY` in `.env`.

Evals:

```bash
uv run --env-file .env python -m eval.run_eval    # retrieval
uv run --env-file .env python -m eval.run_faith   # faithfulness and refusals
uv run --env-file .env python -m eval.run_near    # near-miss refusals
```

## Project layout

```
app/
  ingest.py      load, chunk, embed, upsert into Qdrant
  retrieve.py    dense + BM25 + RRF + rerank
  answer.py      JSON claims and verification
  main.py        FastAPI app and guardrails
  static/        plain HTML frontend
eval/            retrieval, faithfulness and refusal evals
tests/           prompt injection checks
space.py         Gradio entrypoint for the Hugging Face Space
```

## Limitations

- The same model family writes the answer and judges it, so they can share blind spots.
- A grounded answer can still be off-topic. Faithfulness does not measure relevance.
- Fixed-size chunking cuts some sections mid-sentence.
- The FastAPI docs pull code in from separate files, which I did not ingest, so answers are prose only.
- The retrieval eval matches on source file, not on the exact passage.
- The rate limiter is in memory and resets on restart. There is no authentication.
- The injection tests are two smoke tests, not proof of robustness.

## Stack

Python, FastAPI, Qdrant, fastembed, Groq (gpt-oss-120b), Gradio, Docker.