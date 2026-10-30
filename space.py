import gradio as gr
import spaces
import uvicorn
from app.main import app as api


@spaces.GPU
def _gpu_marker():
    return None


demo = gr.Blocks()
with demo:
    gr.Markdown("The app is at the root URL.")
app = gr.mount_gradio_app(api, demo, path="/gradio")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)