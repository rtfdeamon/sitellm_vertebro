# Crawler Image Handling

During a crawl each HTML page is parsed for `<img>` tags. The crawler attempts
to download images that reside within the allowed domain and compresses them to
JPEG (max dimension 1280px, quality 85) using Pillow. Metadata stored in Mongo
includes:

- `name`: sanitized filename with `.jpg` suffix
- `description`: the `<img alt>` text when available, otherwise a generic caption
- `content_type`: `image/jpeg`
- `source_content_type`: original server content type when provided
- `url`: original image URL

Compressed bytes are stored in GridFS alongside textual documents which lets the
chat/Telegram integrations expose them as attachments.

Environment variables controlling the behaviour:

| Variable                    | Default | Description                                    |
|-----------------------------|---------|------------------------------------------------|
| `CRAWL_IMAGE_MAX_DIM`       | 1280    | Maximum width/height for the resized image.    |
| `CRAWL_IMAGE_JPEG_QUALITY`  | 85      | JPEG quality used when saving the image.       |

The crawler maintains a `downloaded_images` set to avoid re-fetching the same
image multiple times within a crawl session.
