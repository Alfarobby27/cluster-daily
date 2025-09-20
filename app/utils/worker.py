# app/utils/worker.py
from PyQt5.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    finished = pyqtSignal(object)   # send result or status
    progress = pyqtSignal(int)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"error": str(e)})
