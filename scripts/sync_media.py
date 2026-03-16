
import os
import cloudinary
import cloudinary.uploader
from pathlib import Path

# Cloudinary credentials from .env
cloudinary.config(
    cloud_name="dlj4gpozf",
    api_key="756455288318988",
    api_secret="0IsEjVdTLJKq-ICd56JgVwuEdI0"
)

BASE_DIR = Path("c:/Users/Little Human/Desktop/ReportFormv2")
MEDIA_ROOT = BASE_DIR / "media"

def sync_folder(relative_path):
    local_folder = MEDIA_ROOT / relative_path
    if not local_folder.exists():
        print(f"Skipping {relative_path}, folder does not exist.")
        return

    print(f"Syncing folder: {relative_path}")
    for file_path in local_folder.glob("*"):
        if file_path.is_file():
            # Cloudinary public_id should match the relative path WITHOUT the extension
            # to avoid double extensions in high-level URLs (e.g. .jpg.jpg).
            
            relative_file_path = relative_path / file_path.name
            public_id = str(relative_file_path.with_suffix("")).replace("\\", "/")
            
            print(f"Uploading {file_path} as {public_id}...")
            try:
                response = cloudinary.uploader.upload(
                    str(file_path),
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image"
                )
                print(f"Success: {response['secure_url']}")
            except Exception as e:
                print(f"Failed to upload {file_path}: {e}")

if __name__ == "__main__":
    folders_to_sync = [
        Path("counties/governors"),
        Path("counties/women_rep"),
        Path("counties"),
        Path("senators"),
        Path("parties"),
    ]
    
    for folder in folders_to_sync:
        sync_folder(folder)
    
    print("Sync complete!")
