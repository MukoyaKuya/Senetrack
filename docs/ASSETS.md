# Asset handling and image optimization

The app uses many image fields (county logos, governor/women rep photos, senator headshots, party logos). As the dataset grows, optimizing delivery and size will improve page load.

## Current setup

- **Django `ImageField`** with local `media/` storage (e.g. `media/counties/`, `media/senators/`, `media/parties/`).
- **Senator** can use either uploaded `image` or external `image_url`. A single extension point exists: **`Senator.display_image_url`** (property) returns the best URL for cards/lists. Use it in templates and APIs so that when you add thumbnails or a CDN, you only change this property (or add an ImageSpecField and return its URL here). Models docstring in `scorecard/models.py` points to this doc and the migration path.
- No resizing or thumbnails by default; full-size images are served.

## Recommended directions

### 1. Remote storage (Cloudinary, S3)

Offload files to a CDN and reduce load on the app server.

- **django-storages + S3**  
  - `pip install django-storages boto3`  
  - Set `DEFAULT_FILE_STORAGE` and AWS credentials; `MEDIA_URL` can point to CloudFront or S3 public URL.  
  - [django-storages](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html)

- **Cloudinary**  
  - `pip install cloudinary django-cloudinary-storage` (or use Cloudinary’s Django app).  
  - Configure `CLOUDINARY_URL`; use `CloudinaryField` or a custom storage so existing `ImageField` uploads go to Cloudinary.  
  - Supports on-the-fly transforms (resize, crop) via URL parameters, which can be used in templates without changing the model.

### 2. Thumbnails and responsive images (django-imagekit)

Generate fixed-size thumbnails and avoid sending full-size images everywhere.

- **django-imagekit**  
  - `pip install django-imagekit`  
  - Add `ImageSpecField` (or processors) on the model or define specs in a separate “thumbnail” module and attach to existing `ImageField`s.  
  - Example (add to a model that has an `image` field):

    ```python
    from imagekit.models import ImageSpecField
    from imagekit.processors import ResizeToFill

    class Senator(models.Model):
        image = models.ImageField(...)
        image_thumbnail = ImageSpecField(
            source="image",
            processors=[ResizeToFill(200, 260)],
            format="JPEG",
            options={"quality": 85},
        )
    ```

  - In templates use `senator.image_thumbnail.url` for cards and keep `senator.image.url` for full-size where needed.  
  - [django-imagekit](https://github.com/matthewwithanm/django-imagekit)

### 3. Front-end optimization (no backend change)

- Use `loading="lazy"` and `decoding="async"` on `<img>` (already used on senator cards where applicable).
- Add `width` and `height` to avoid layout shift.
- Consider `srcset` with a few fixed widths (e.g. 200w, 400w) if you later expose resized URLs (e.g. from Cloudinary or imagekit).

### 4. Optional: single CDN + resize URL helper

If you use Cloudinary (or another provider that supports URL-based resizing), you can centralize logic:

- Store only the “reference” (e.g. public_id or path) in the DB, or keep current `ImageField` and map to a CDN URL in a template tag or helper.
- Helper example (conceptual):

  ```python
  # e.g. in templatetags or a small utils module
  def thumbnail_url(image_field, width=200, height=260, crop="fill"):
      if not image_field:
          return ""
      # If using Cloudinary: build transform URL from image_field.url or public_id
      # If using local + imagekit: return image_field thumbnail spec URL
      return image_field.url  # fallback to original
  ```

Then use that in templates for cards and lists so all asset URLs go through one place and can be switched to CDN/thumbnails later.

## Summary

| Goal              | Option                    | Notes                                      |
|-------------------|---------------------------|--------------------------------------------|
| Offload storage   | django-storages (S3)      | Set `DEFAULT_FILE_STORAGE`, env vars       |
| CDN + transforms  | Cloudinary                | Optional CloudinaryField or URL builder     |
| Thumbnails        | django-imagekit           | Add `ImageSpecField` next to existing image|
| Lazy load         | Already in use            | Keep `loading="lazy"` on list/card images   |

Starting with **django-imagekit** for thumbnails (and keeping media in `media/` or moving to S3/Cloudinary later) is a scalable path without changing how you upload in the admin.
