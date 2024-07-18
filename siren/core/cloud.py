from pathlib import Path
from typing import Any, Protocol
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from pydantic import BaseModel

from .file import File


# TODO: pray to god and fix types


class CloudProto(Protocol):

    def upload(self, file: File) -> Any: ...

    def upload_file(self, file: File, folder: str) -> Any: ...

    def create_folder(self, folder: str, parent: str) -> Any: ...


class DriveFile(BaseModel):
    kind: str
    mimeType: str
    id: str
    name: str


class Drive(CloudProto):
    def __init__(self, creds: dict[str, str], root: str):
        self.root = root
        self.creds = Credentials.from_service_account_info(creds)  # type: ignore
        self.service = build("drive", "v3", credentials=self.creds)
        self.files: list[DriveFile] = list(
            map(
                DriveFile.model_validate,
                (
                    self.service.files()
                    .list(q=f"'{root}' in parents")
                    .execute()
                    .get("files", {})
                ),
            )
        )
        target_mimetype = "application/vnd.google-apps.folder"
        self.targets = {
            df.name: df.id for df in self.files if df.mimeType == target_mimetype
        }
        # print(dumps(self.files, indent=4))

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

    def upload(self, file: File):

        origin = file.origin.__class__.__name__
        if target_id := self.targets.get(origin):
            self.upload_file(file, target_id)
        else:
            folder = self.create_folder(origin, self.root)
            folder_id = folder["id"]
            self.targets[origin] = folder_id
            self.upload_file(file, folder_id)


class Local(CloudProto):
    def __init__(self, root: Path):
        self.root = root
        assert self.root.is_dir()

    def upload_file(self, file: File, folder: str):
        with open((self.root / file.name), "wb") as f:
            f.write(file.buffer().read())

    def create_folder(self, folder: str, parent: str): ...

    def upload(self, file: File):
        self.upload_file(file, "")
