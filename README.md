# dhlab-app-transcribe

Record or upload audio and transcribe it with [NB-Whisper](https://huggingface.co/NbAiLab/nb-whisper-base) from the National Library of Norway.

**App:** https://nationallibraryofnorway.github.io/dhlab-app-transcribe/

The app runs entirely in the browser ([Gradio-Lite](https://www.gradio.app/guides/gradio-lite) + [transformers.js](https://huggingface.co/docs/transformers.js)) using quantized ONNX builds of NB-Whisper on the CPU. Audio never leaves the user's machine. The model is downloaded on first use (about 120–410 MB depending on size) and cached by the browser.

## Models

The browser app does **not** run the original NB-Whisper weights. It runs 8-bit quantized ONNX conversions (`dtype: "q8"`, i.e. the `*_quantized.onnx` files) made by third parties from the NbAiLab models:

| Option in app | Model ID | Based on |
|---|---|---|
| tiny | [`PierreMesure/nb-whisper-tiny-ONNX`](https://huggingface.co/PierreMesure/nb-whisper-tiny-ONNX) | [`NbAiLab/nb-whisper-tiny`](https://huggingface.co/NbAiLab/nb-whisper-tiny) |
| base (default) | [`onnx-community/nb-whisper-base-ONNX`](https://huggingface.co/onnx-community/nb-whisper-base-ONNX) | [`NbAiLab/nb-whisper-base`](https://huggingface.co/NbAiLab/nb-whisper-base) |
| small | [`onnx-community/nb-whisper-small-ONNX`](https://huggingface.co/onnx-community/nb-whisper-small-ONNX) | [`NbAiLab/nb-whisper-small`](https://huggingface.co/NbAiLab/nb-whisper-small) |

Quantization makes the models small and fast enough to run in a browser, but may reduce accuracy slightly compared to the originals. All models are Apache-2.0.

The local variant (`app.py`) runs the original, unquantized `NbAiLab/nb-whisper-tiny`, `-base` and `-small` with PyTorch.

## Development

```sh
pdm install
pdm run serve        # preview the GitHub Pages app at http://localhost:8000
pdm run local        # server-side variant (app.py) running on CPU
pdm run vendor-lite  # regenerate docs/gradio-lite/
```

GitHub Pages serves the `docs/` folder on `main`.
