import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

__all__ = "File", "Cloud"


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


class Cloud(Protocol):
    def upload_file(self, file: File, folder: str) -> Any:
        ...

    def create_folder(self, folder: str, parent: str) -> Any:
        ...


class Drive(Cloud):
    def __init__(self, creds: dict[str, str]):
        self.creds = Credentials.from_service_account_info(creds)
        self.service = build("drive", "v3", credentials=self.creds)

    def create_folder(self, folder: str, parent: str) -> dict[str, str]:
        body = {
            "name": folder,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent],
        }
        return self.service.files().create(body=body, fields="id").execute()

    def upload_file(self, file: File, folder: str):
        body = {"name": file.name, "parents": [folder]}
        media = MediaIoBaseUpload(file.buffer(), mimetype=file.mimetype)
        return (
            self.service.files()
            .create(body=body, media_body=media, fields="id")
            .execute()
        )
