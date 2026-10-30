import html
import spaces
import gradio as gr
from app.answer import ask
from app.main import guard

STYLE = """<style>
.card { border: 1px solid var(--border-color-primary); border-radius: 10px; padding: 1rem 1.25rem; background: var(--background-fill-secondary); color: var(--body-text-color); }
.card p { margin: 0 0 .6rem; line-height: 1.6; font-size: 1rem; }
.cite { color: var(--color-accent); font-size: .85em; font-weight: 600; margin-left: 3px; }
.muted { color: var(--body-text-color-subdued); font-size: .9em; }
details.src { border: 1px solid var(--border-color-primary); border-radius: 8px; margin: .5rem 0; background: var(--background-fill-secondary); color: var(--body-text-color); }
details.src summary { cursor: pointer; padding: .6rem .9rem; font-weight: 600; }
details.src .tag { float: right; font-weight: 400; font-size: .8em; color: var(--body-text-color-subdued); }
details.src pre { white-space: pre-wrap; word-break: break-word; margin: 0; padding: .75rem .9rem; border-top: 1px solid var(--border-color-primary); font-size: .82rem; line-height: 1.5; }
</style>"""
EMPTY_ANS = STYLE + '<div class="card"><p class="muted">Ask a question to see the answer.</p></div>'
EMPTY_SRC = STYLE + '<p class="muted">Sources appear here.</p>'
EXAMPLES = [
    "How do I declare a query parameter?",
    "How do I enable CORS?",
    "How do I run a task after returning a response?",
]


def esc(s):
    return html.escape(str(s))


@spaces.GPU
def _gpu_marker():
    # ZeroGPU needs one @spaces.GPU event handler. Never clicked, the app runs on CPU.
    return None


def render(r):
    good = [c for c in r["claims"] if c["supported"]]
    cited = {n for c in good for n in c["cites"]}
    if good:
        body = "".join(
            "<p>" + esc(c["text"]) + "".join(f'<span class="cite">[{n}]</span>' for n in c["cites"]) + "</p>"
            for c in good
        )
    else:
        body = "<p>I don't know.</p>"
    note = ""
    if r["unsupported"]:
        note = f'<p class="muted">{r["unsupported"]} unverified sentence(s) removed.</p>'
    answer = STYLE + f'<div class="card">{body}{note}</div>'
    cards = "".join(
        f'<details class="src"{" open" if s["id"] in cited else ""}>'
        f'<summary>[{s["id"]}] {esc(s["source"])}'
        f'<span class="tag">{"cited" if s["id"] in cited else "not cited"}</span></summary>'
        f'<pre>{esc(s["text"])}</pre></details>'
        for s in r["sources"]
    )
    return answer, STYLE + cards


def run(q, request: gr.Request):
    ip = "unknown"
    if request is not None:
        ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    try:
        guard(ip, q or "")
    except Exception as e:
        msg = esc(getattr(e, "detail", e))
        return STYLE + f'<div class="card"><p>{msg}</p></div>', EMPTY_SRC
    try:
        return render(ask(q))
    except Exception:
        return STYLE + '<div class="card"><p>Something went wrong. Try again in a minute.</p></div>', EMPTY_SRC


with gr.Blocks(title="FastAPI docs Q&A") as demo:
    gr.Markdown("# FastAPI docs Q&A\nHybrid search, reranking, and every sentence checked against its source.")
    with gr.Row():
        q = gr.Textbox(show_label=False, container=False, scale=5, max_length=500,
                       placeholder="How do I declare a query parameter?")
        go = gr.Button("Ask", variant="primary", scale=1)
    gr.Examples(EXAMPLES, inputs=q)
    gr.Markdown("## Answer")
    ans = gr.HTML(EMPTY_ANS)
    gr.Markdown("## Sources")
    src = gr.HTML(EMPTY_SRC)
    go.click(run, q, [ans, src])
    q.submit(run, q, [ans, src])
    gr.Button(visible=False).click(_gpu_marker)

demo.queue(default_concurrency_limit=2).launch()