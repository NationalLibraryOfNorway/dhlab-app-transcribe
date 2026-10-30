# dhlab-app-transcribe

Record or upload audio and transcribe it with [NB-Whisper](https://huggingface.co/NbAiLab/nb-whisper-base) from the National Library of Norway.

**App:** https://nationallibraryofnorway.github.io/dhlab-app-transcribe/

The app runs entirely in the browser ([Gradio-Lite](https://www.gradio.app/guides/gradio-lite) + [transformers.js](https://huggingface.co/docs/transformers.js)) using quantized ONNX builds of NB-Whisper on the CPU. Audio never leaves the user's machine. The model is downloaded on first use (about 120–410 MB depending on size) and cached by the browser.

## Development

```sh
pdm install
pdm run serve        # preview the GitHub Pages app at http://localhost:8000
pdm run local        # server-side variant (app.py) running on CPU
pdm run vendor-lite  # regenerate docs/gradio-lite/
```

GitHub Pages serves the `docs/` folder on `main`.
