"""Server-side version of docs/index.html for running locally on CPU (`pdm run local`)."""

import gradio as gr
import librosa
from transformers import pipeline

MODELS = {
    "NB-Whisper tiny": "NbAiLab/nb-whisper-tiny",
    "NB-Whisper base": "NbAiLab/nb-whisper-base",
    "NB-Whisper small": "NbAiLab/nb-whisper-small",
}
LANGUAGES = {"Bokmål": "no", "Nynorsk": "nn", "English": "en"}

pipelines = {}


def get_pipeline(model_label):
    repo = MODELS[model_label]
    if repo not in pipelines:
        pipelines[repo] = pipeline("automatic-speech-recognition", repo, device="cpu")
    return pipelines[repo]


def transcribe(audio_path, model_label, language_label):
    if not audio_path:
        raise gr.Error("Record or upload some audio first.")
    samples, _ = librosa.load(audio_path, sr=16000, mono=True)
    result = get_pipeline(model_label)(
        samples,
        return_timestamps=True,  # enables long-form transcription of audio over 30 s
        generate_kwargs={"language": LANGUAGES[language_label], "task": "transcribe"},
    )
    return result["text"].strip()


with gr.Blocks(title="NB-Whisper Transcriber", analytics_enabled=False) as demo:
    gr.Markdown(
        "# NB-Whisper Transcriber\n"
        "Record or upload audio and transcribe it with "
        "[NB-Whisper](https://huggingface.co/NbAiLab/nb-whisper-base) from the National Library of Norway."
    )
    with gr.Row():
        with gr.Column():
            audio = gr.Audio(sources=["microphone", "upload"], type="filepath", label="Audio")
            model = gr.Dropdown(list(MODELS), value="NB-Whisper base", label="Model")
            language = gr.Radio(list(LANGUAGES), value="Bokmål", label="Output language")
            button = gr.Button("Transcribe", variant="primary")
        with gr.Column():
            text = gr.Textbox(label="Transcription", lines=14, show_copy_button=True, elem_id="transcription")
    button.click(transcribe, inputs=[audio, model, language], outputs=text)

if __name__ == "__main__":
    demo.launch()
