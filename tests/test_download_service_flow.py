from core.services import download_service as ds


def test_orchestrator_emits_summary_and_status(monkeypatch, tmp_path):
    events = []

    class FakePool:
        def __init__(self, *args, **kwargs):
            pass

        def imap_unordered(self, func, iterable, chunksize=1):
            for item in iterable:
                func(item)
                yield item

        def close(self):
            pass

        def join(self):
            pass

        def terminate(self):
            pass

    def progress_cb(data):
        events.append(data)

    def fake_worker(url, target_dir, index, stats, progress_callback=None, **kwargs):
        stats.increment_success()

    monkeypatch.setattr(ds, "get_total_files", lambda url: 3)
    monkeypatch.setattr(ds, "download_worker_with_progress", fake_worker)
    monkeypatch.setattr(ds, "ThreadPool", FakePool)

    ds.download_orchestrator_with_progress(
        "https://fapello.com/model",
        workers=2,
        progress_callback=progress_cb,
        target_dir=tmp_path,
        download_images=True,
        download_videos=False,
    )

    status_events = [e for e in events if e.get("type") == "status"]
    summary_events = [e for e in events if e.get("type") == "summary"]

    assert status_events
    assert status_events[0]["status"] == ds.DOWNLOADING_STATUS
    assert summary_events
    assert summary_events[0]["total_expected"] == 3
    assert summary_events[0]["success"] == 3
    assert status_events[-1]["status"] == ds.COMPLETED_STATUS


def test_picazor_empty_indices_skips_extra_scan(monkeypatch, tmp_path):
    calls = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_valid_indices_multithread(self, *args, **kwargs):
            return []

    def fake_worker(url, target_dir, index, stats, progress_callback=None, **kwargs):
        calls.append(index)
        stats.increment_success()

    monkeypatch.setattr(ds, "PicazorClient", DummyClient)
    monkeypatch.setattr(ds, "download_worker_with_progress", fake_worker)

    ds.download_orchestrator_with_progress(
        "https://picazor.com/model",
        workers=1,
        progress_callback=lambda _: None,
        target_dir=tmp_path,
        download_images=True,
        download_videos=False,
    )

    assert calls == []
