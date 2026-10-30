import time
from collections import defaultdict, deque
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from app.retrieve import search
from app.answer import ask

app = FastAPI()
INDEX = Path(__file__).parent / "static" / "index.html"
MAX_Q = 500
LIMIT, WINDOW = 10, 60 
seen = defaultdict(deque)


def guard(ip: str, q: str):
    if not q.strip() or len(q) > MAX_Q:
        raise HTTPException(400, f"q must be 1-{MAX_Q} characters")
    now = time.time()
    dq = seen[ip]
    while dq and now - dq[0] > WINDOW:
        dq.popleft()
    if len(dq) >= LIMIT:
        raise HTTPException(429, "rate limit exceeded")
    dq.append(now)


def check(request: Request, q: str):
    ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    guard(ip, q)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(INDEX)


@app.get("/search")
def _search(request: Request, q: str, k: int = 5):
    check(request, q)
    return search(q, min(max(k, 1), 20))


@app.get("/ask")
def _ask(request: Request, q: str):
    check(request, q)
    return ask(q)