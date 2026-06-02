import logging
import socket
import time


class UDPHandler(logging.Handler):
    """Small InfluxDB UDP logging handler compatible with the old influxpy API."""

    def __init__(self, host, port, database=None, global_tags=None):
        super().__init__()
        self.host = host
        self.port = int(port)
        self.database = database
        self.global_tags = global_tags or {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, record):
        try:
            message = self.format(record)
            line = self._line_protocol(record, message)
            self.socket.sendto(line.encode("utf-8"), (self.host, self.port))
        except Exception:
            self.handleError(record)

    def close(self):
        try:
            self.socket.close()
        finally:
            super().close()

    def _line_protocol(self, record, message):
        tags = {
            "level": record.levelname,
            "logger": record.name,
            **self.global_tags,
        }
        tag_text = ",".join(
            "{}={}".format(self._escape_key(key), self._escape_key(value))
            for key, value in sorted(tags.items())
        )
        timestamp = int(getattr(record, "created", time.time()) * 1_000_000_000)
        return "logging,{} message=\"{}\" {}".format(
            tag_text,
            self._escape_field(message),
            timestamp,
        )

    @staticmethod
    def _escape_key(value):
        return str(value).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

    @staticmethod
    def _escape_field(value):
        return str(value).replace("\\", "\\\\").replace('"', '\\"')
