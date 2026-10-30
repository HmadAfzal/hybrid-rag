import spaces
import gradio as gr
from app.answer import ask
from app.main import guard


@spaces.GPU
def _gpu_marker():
    return None


def run(q, request: gr.Request):
    ip = "unknown"
    if request is not None:
        ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    try:
        guard(ip, q or "")
    except Exception as e:
        return str(getattr(e, "detail", e)), ""
    r = ask(q)
    text = r["verified_answer"]
    if r["unsupported"]:
        text += f"\n\n_{r['unsupported']} unverified sentence(s) removed._"
    src = "\n\n".join(f"[{s['id']}] {s['source']}\n{s['text']}" for s in r["sources"])
    return text, src


with gr.Blocks(title="FastAPI docs Q&A") as demo:
    gr.Markdown("# FastAPI docs Q&A\nHybrid search, reranking, and every sentence checked against its source.")
    q = gr.Textbox(label="Question", placeholder="How do I declare a query parameter?", max_length=500)
    go = gr.Button("Ask", variant="primary")
    ans = gr.Markdown()
    src = gr.Textbox(label="Sources", lines=12, interactive=False)
    go.click(run, q, [ans, src])
    q.submit(run, q, [ans, src])
    gr.Button(visible=False).click(_gpu_marker)

demo.queue(default_concurrency_limit=2).launch()