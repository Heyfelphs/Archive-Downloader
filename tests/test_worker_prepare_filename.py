from core.worker import prepare_filename


def test_prepare_filename_short_url():
    name = prepare_filename("file.jpg", 1, "image")
    assert name.startswith("file.jpg_1")
    assert name.endswith(".jpg")
