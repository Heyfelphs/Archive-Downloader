from core.services import download_service as ds


def test_media_list_for_picazor_relative_urls(monkeypatch):
    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_media_info(self, url):
            return [("/uploads/test.jpg", "image")]

    monkeypatch.setattr(ds, "PicazorClient", DummyClient)

    items = ds._media_list_for_index(
        "https://picazor.com/model",
        1,
        download_images=True,
        download_videos=True,
    )

    assert items
    assert items[0][0] == "https://picazor.com/uploads/test.jpg"
