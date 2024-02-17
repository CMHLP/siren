from pathlib import Path
from typing import Any, Protocol
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from .file import File


class CloudProto(Protocol):
    def upload_file(self, file: File, folder: str) -> Any: ...

    def create_folder(self, folder: str, parent: str) -> Any: ...


class Drive(CloudProto):
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

    def upload_file(self, file: File, folder: str) -> dict[str, Any]:
        body = {"name": file.name, "parents": [folder]}
        media = MediaIoBaseUpload(file.buffer(), mimetype=file.mimetype)
        return (
            self.service.files()
            .create(body=body, media_body=media, fields="id")
            .execute()
        )


class Local(CloudProto):
    def __init__(self, path: Path):
        self.path = path
        if path.exists():
            self.path = self.path.parent / f"copy-{self.path.name}"

    def upload_file(self, file: File, folder: str):
        with open(self.path, "wb") as f:
            f.write(file.buffer().read())

    def create_folder(self, folder: str, parent: str): ...
