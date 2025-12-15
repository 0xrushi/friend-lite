import io
import tempfile
from typing import List
import logging
from starlette.datastructures import UploadFile as StarletteUploadFile
import requests
from advanced_omi_backend.app_config import get_app_config

logger = logging.getLogger(__name__)
audio_logger = logging.getLogger("audio_processing")

AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".m4a")

class AudioValidationError(Exception):
    pass


async def download_and_wrap_dropbox_file(file_metadata: dict):
    access_token = get_app_config().dropbox_access_token    
    if not access_token:
        raise AudioValidationError("Dropbox access token is missing.")

    file_path = file_metadata["path_lower"]
    name = file_metadata["name"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Dropbox-API-Arg": f'{{"path": "{file_path}"}}'
    }

    response = requests.post(
        "https://content.dropboxapi.com/2/files/download",
        headers=headers
    )

    if response.status_code != 200:
        raise AudioValidationError(
            f"Failed to download Dropbox file {name}: {response.text}"
        )

    content = response.content
    if not content:
        raise AudioValidationError(f"Downloaded Dropbox file '{name}' was empty")

    tmp_file = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
    tmp_file.write(content)
    tmp_file.seek(0)

    upload_file = StarletteUploadFile(filename=name, file=tmp_file)

    original_close = upload_file.close

    def wrapped_close():
        try:
            original_close()
        finally:
            pass

    upload_file.close = wrapped_close
    return upload_file


async def download_audio_files_from_dropbox(folder_path: str) -> List[StarletteUploadFile]:
    if not folder_path:
        raise AudioValidationError("Dropbox folder path is required.")

    access_token = get_app_config().dropbox_access_token
    if not access_token:
        raise AudioValidationError("Dropbox access token is missing.")

    try:
        # -----------------------------------------------
        # Step 1: List files in folder
        # -----------------------------------------------
        list_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        list_body = {
            "path": folder_path,
            "recursive": False
        }

        list_res = requests.post(
            "https://api.dropboxapi.com/2/files/list_folder",
            headers=list_headers,
            json=list_body
        )

        if list_res.status_code != 200:
            raise AudioValidationError(f"Dropbox API list_folder error: {list_res.text}")

        items = list_res.json().get("entries", [])

        # Filter audio files
        audio_files_metadata = [
            f for f in items
            if f[".tag"] == "file" and f["name"].lower().endswith(AUDIO_EXTENSIONS)
        ]

        if not audio_files_metadata:
            raise AudioValidationError("No audio files found in folder.")

        wrapped_files = []
        skipped_count = 0

        # -----------------------------------------------
        # Step 2: Download each audio file
        # -----------------------------------------------
        for item in audio_files_metadata:
            dropbox_id = item["id"]  # Dropbox file ID

            # Check if already processed
            if await is_dropbox_file_already_processed(dropbox_id):
                audio_logger.info(f"Skipping already processed file: {item['name']}")
                skipped_count += 1
                continue

            wrapped_file = await download_and_wrap_dropbox_file(access_token, item)

            # Attach Dropbox file ID
            setattr(wrapped_file, "dropbox_file_id", dropbox_id)

            wrapped_files.append(wrapped_file)

        if not wrapped_files and skipped_count > 0:
            raise AudioValidationError(
                f"All {skipped_count} files in the folder have already been processed."
            )

        return wrapped_files

    except Exception as e:
        if isinstance(e, AudioValidationError):
            raise
        raise AudioValidationError(f"Dropbox API Error: {e}") from e


async def is_dropbox_file_already_processed(dropbox_file_id: str) -> bool:
    if not dropbox_file_id:
        return False

    from advanced_omi_backend.models.audio_file import AudioFile

    existing_file = await AudioFile.find_one(
        AudioFile.dropbox_file_id == dropbox_file_id
    )

    return existing_file is not None
