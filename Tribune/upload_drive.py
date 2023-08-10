import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

folder_id = "1tQs4MpKyco1F5UuxZnGO9Jj9IQHhGmEe"


def upload_to_drive(file_path, filename, folder_id):
    creds = service_account.Credentials.from_service_account_file(
        "service_account.json"
    )
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": filename, "parents": [folder_id]}

    media = MediaFileUpload(file_path, mimetype="text/csv")

    try:
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        print(f'File ID: "{file.get("id")}".')
    except HttpError as error:
        print(f"An error occurred: {error}")
        file = None

    return file


if __name__ == "__main__":
    file_path = "tribune.csv"
    filename = os.path.basename(file_path)
    upload_to_drive(file_path, filename, folder_id)
