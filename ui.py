"""Gradio-клиент к API interview_service.py
Запуск:
    python ui.py
Откроется страница http://127.0.0.1:7860

Перед запуском убедитесь, что FastAPI-сервис уже работает на http://127.0.0.1:8000
"""
import requests
import gradio as gr
import tempfile
import os

BACKEND = "http://127.0.0.1:8000"  # если сервис слушает другой порт/хост — поменяйте
share = True


def upload(file_path: str) -> str:
    """Отправляем файл на /transcribe/ и возвращаем текст с ID задачи."""
    if not file_path:
        return "Сначала выберите файл."

    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{BACKEND}/transcribe/",  # endpoint FastAPI-сервиса
            files={"file": f},
            params={"lang": "ru"},
        )
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        return f"Ошибка: {exc}\n{resp.text}"

    data = resp.json()
    audio_id = data.get("id")
    return f"ID задачи: {audio_id}"


def download_transcript(audio_id: str) -> str:
    """Скачиваем файл транскрипции через /transcript/{id}/download и возвращаем путь к локальному файлу."""
    if not audio_id:
        return None
    try:
        int(audio_id)
    except ValueError:
        return None

    url = f"{BACKEND}/transcript/{audio_id}/download"
    resp = requests.get(url)
    if resp.status_code != 200:
        return None

    # Сохраняем временный файл
    fd, path = tempfile.mkstemp(suffix=f"_transcript_{audio_id}.txt")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(resp.content)
    return path


with gr.Blocks() as demo:
    gr.Markdown("# KP Audio Service – загрузка и распознавание")
    inp = gr.File(
        type="filepath",
        file_types=["audio", "video"],
        label="Выберите аудио или видео файл"
    )
    status_out = gr.Textbox(label="ID задачи", lines=1)
    btn_upload = gr.Button("Загрузить и транскрибировать")
    btn_upload.click(upload, inputs=inp, outputs=status_out)

    gr.Markdown("---")
    id_in = gr.Textbox(label="Введите ID задачи для скачивания транскрипта")
    btn_download = gr.Button("Скачать транскрипт")
    file_out = gr.File(label="Файл транскрипта")
    btn_download.click(download_transcript, inputs=id_in, outputs=file_out)

if __name__ == "__main__":
    demo.launch(share=share)