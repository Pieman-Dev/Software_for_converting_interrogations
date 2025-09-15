import pathlib
import types
import pytest
import python_service_initial as svc


def test_convert_to_wav_error(monkeypatch, tmp_path):
    """_convert_to_wav должен бросать RuntimeError, если ffmpeg вернул ошибку."""
    src = tmp_path / "in.mp3"
    src.write_bytes(b"fake_mp3")

    class Dummy:
        def __init__(self, ret=1):
            self.returncode = ret
            self.stderr = "boom"

    monkeypatch.setattr(svc.subprocess, "run", lambda *a, **kw: Dummy(1))
    with pytest.raises(RuntimeError):
        svc._convert_to_wav(src)


def test_run_whisper_command_build(monkeypatch, tmp_path):
    """Проверяем формирование команды без реального запуска whisper."""
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"data")

    # создаём фиктивные бинарники/модель
    fake_bin   = tmp_path / "whisper.exe";   fake_bin.write_bytes(b"")
    fake_model = tmp_path / "mdl.bin";       fake_model.write_bytes(b"")
    monkeypatch.setattr(svc, "WHISPER_BINARY", fake_bin)
    monkeypatch.setattr(svc, "WHISPER_MODEL",  fake_model)

    captured = {}
    def fake_run(cmd, capture_output, text):
        captured["cmd"] = cmd
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(svc.subprocess, "run", fake_run)
    out = tmp_path / "out"

    svc._run_whisper(wav, out, lang="ru")

    # в команде должны быть путь к бинарнику, модель, wav и --output-file
    joined = " ".join(captured["cmd"])
    assert str(fake_bin) in joined and str(fake_model) in joined
    assert str(wav) in joined and str(out) in joined
