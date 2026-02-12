import threading

from utils import network


def test_thread_local_sessions_are_distinct():
    main_session = network._get_session()
    other_ids = []

    def _worker():
        other_ids.append(id(network._get_session()))

    thread = threading.Thread(target=_worker)
    thread.start()
    thread.join()

    assert other_ids
    assert id(main_session) != other_ids[0]
    assert network._get_session() is main_session
