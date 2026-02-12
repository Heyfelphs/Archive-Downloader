from pathlib import Path

from core import worker as cw
import core.picazor_client as pc


def test_download_worker_streams_to_file(monkeypatch, tmp_path: Path):
    calls = []

    def fake_download(url, path, **kwargs):
        calls.append((url, path))
        Path(path).write_bytes(b"data")

    monkeypatch.setattr(cw, "download_binary_to_file", fake_download)
    monkeypatch.setattr(
        pc.PicazorClient,
        "get_media_info",
        lambda self, url: [("http://example.com/a.jpg", "image")],
    )

    cw.download_worker("https://picazor.com/model", str(tmp_path), 1)

    assert calls
    assert Path(calls[0][1]).exists()
