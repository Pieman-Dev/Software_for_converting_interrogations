import io

def _dummy_wav_bytes():
    """Минимальный WAV-заголовок + тишина (44 байта достаточно для теста)."""
    return (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x40\x1f\x00\x00\x80>\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

def test_transcribe_and_download(client):
    wav_bytes = _dummy_wav_bytes()

    # ───── POST /transcribe/ ─────
    resp = client.post(
        "/transcribe/",
        files={"file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")},
    )
    assert resp.status_code == 200
    audio_id = resp.json()["id"]

    # ───── GET /transcript/{id}/download ─────
    dl = client.get(f"/transcript/{audio_id}/download")
    assert dl.status_code == 200
    assert dl.headers["content-disposition"].startswith("attachment;")
    assert dl.content == b"test transcript"


def test_invalid_media_type(client):
    resp = client.post("/transcribe/", files={"file": ("bad.txt", b"hi", "text/plain")})
    assert resp.status_code == 400
