import mimetypes
from io import BytesIO
from pathlib import Path


__all__ = ("File",)


class File:
    """Represents a file that can be uploaded to a Cloud platform.
    This class normalizes the interface for files and in-memory buffers.
    """

    def __init__(self, data: bytes, name: str):
        self.data = data
        self.name = name
        self.mimetype = mimetypes.guess_type(name)[0] or "application/pdf"

    def buffer(self):
        return BytesIO(self.data)

    @classmethod
    def from_path(cls, path: Path):
        with path.open("wb") as f:
            return File(f.read(), str(path))
