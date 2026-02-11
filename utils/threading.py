import threading
from queue import Queue

# Utilitário para executar funções em paralelo
class ThreadPool:
    def __init__(self, num_threads):
        self.num_threads = num_threads
        self.tasks = Queue()
        self.threads = []

    def worker(self):
        while True:
            func, args = self.tasks.get()
            if func is None:
                break
            try:
                func(*args)
            finally:
                self.tasks.task_done()

    def start(self):
        for _ in range(self.num_threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            self.threads.append(t)

    def add_task(self, func, *args):
        self.tasks.put((func, args))

    def wait_completion(self):
        self.tasks.join()
        for _ in self.threads:
            self.tasks.put((None, ()))
        for t in self.threads:
            t.join()
