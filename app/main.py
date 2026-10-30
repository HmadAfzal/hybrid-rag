import time
from collections import defaultdict, deque
from fastapi import FastAPI, HTTPException, Request
from app.retrieve import search
from app.answer import ask

app = FastAPI()
MAX_Q = 500
LIMIT, WINDOW = 10, 60  # requests per IP per WINDOW seconds
seen = defaultdict(deque)


def check(request: Request, q: str):
    if not q.strip() or len(q) > MAX_Q:
        raise HTTPException(400, f"q must be 1-{MAX_Q} characters")
    now = time.time()
    dq = seen[request.client.host]
    while dq and now - dq[0] > WINDOW:
        dq.popleft()
    if len(dq) >= LIMIT:
        raise HTTPException(429, "rate limit exceeded")
    dq.append(now)


@app.get("/search")
def _search(request: Request, q: str, k: int = 5):
    check(request, q)
    return search(q, min(max(k, 1), 20))


@app.get("/ask")
def _ask(request: Request, q: str):
    check(request, q)
    return ask(q)