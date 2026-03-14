import os
import django
import cloudinary
import cloudinary.uploader
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from django.conf import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=settings.CLOUDINARY_STORAGE['API_KEY'],
    api_secret=settings.CLOUDINARY_STORAGE['API_SECRET']
)

def upload_media():
    media_root = Path(settings.MEDIA_ROOT)
    print(f"Uploading files from {media_root} to Cloudinary...")

    for file_path in media_root.rglob('*'):
        if file_path.is_file():
            # Skip hidden files
            if file_path.name.startswith('.'):
                continue
                
            relative_path = file_path.relative_to(media_root)
            # Cloudinary uses public_id which should include the path but not the extension
            public_id = str(relative_path.with_suffix(''))
            # Replace backslashes with forward slashes for Cloudinary paths
            public_id = public_id.replace('\\', '/')
            
            print(f"Uploading {relative_path} as {public_id}...")
            try:
                cloudinary.uploader.upload(
                    str(file_path),
                    public_id=public_id,
                    use_filename=True,
                    unique_filename=False,
                    overwrite=True,
                    resource_type="image"
                )
            except Exception as e:
                print(f"Failed to upload {relative_path}: {e}")

if __name__ == "__main__":
    if not all(settings.CLOUDINARY_STORAGE.values()):
        print("Error: Cloudinary credentials not found in environment variables.")
        print("Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET.")
    else:
        upload_media()
