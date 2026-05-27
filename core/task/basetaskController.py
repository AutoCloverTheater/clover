import threading
import time

class BaseTaskController:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self._stop_event = threading.Event()
        self.status = "pending"  # pending/running/completed/interrupted/error
        self.progress = 0
        self.result = None
        self._thread = None

    def _run(self):
        self.status = "running"
        try:
            for i in range(100):
                if self._stop_event.is_set():
                    self.status = "interrupted"
                    self.result = {"message": "用户手动中断",
                                   "progress": self.progress}
                    return

                # 模拟工作
                time.sleep(0.5)
                self.progress = i + 1

            self.status = "completed"
            self.result = {"message": "执行成功", "progress": 100}
        except Exception as e:
            self.status = "error"
            self.result = {"error": str(e)}

    def start(self):
        self._thread = threading.Thread(target=self._run)
        self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()
        return {"task_id": self.task_id, "action": "stop_signal_sent"}
