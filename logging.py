from datetime import datetime
import logging

class DatabaseLogHandler(logging.Handler):
    def __init__(self, db):
        super().__init__()
        self.db = db

    def emit(self, record):
        timestamp = datetime.fromtimestamp(record.created)
        level = record.levelname
        message = record.getMessage()

        try:
            self.db.query(
                "INSERT INTO error_logs (time, level, message) VALUES (%s, %s, %s)",
                (timestamp, level, message)
            )
            self.db.commit()
        except Exception as e:
            # Last-resort fallback so logging never crashes your app
            print("Failed to write log to database:", e)
