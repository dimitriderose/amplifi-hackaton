import uuid
import asyncio
from datetime import timedelta
from typing import Optional
from google.cloud import storage
from backend.config import GCS_BUCKET_NAME

_storage_client: Optional[storage.Client] = None

def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client

def get_bucket() -> storage.Bucket:
    return get_storage_client().bucket(GCS_BUCKET_NAME)

async def upload_image_to_gcs(image_bytes: bytes, mime_type: str,
                               post_id: Optional[str] = None) -> str:
    """Upload generated image bytes to GCS, return 7-day signed URL."""
    if not post_id:
        post_id = str(uuid.uuid4())

    ext = "png" if "png" in mime_type else "jpg"
    blob_path = f"generated/{post_id}/image_{uuid.uuid4().hex[:8]}.{ext}"
    bucket = get_bucket()
    blob = bucket.blob(blob_path)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: blob.upload_from_string(image_bytes, content_type=mime_type)
    )

    signed_url = await loop.run_in_executor(
        None,
        lambda: blob.generate_signed_url(expiration=timedelta(days=7), method="GET")
    )
    return signed_url

async def upload_brand_asset(brand_id: str, file_bytes: bytes,
                              filename: str, mime_type: str) -> str:
    """Upload user brand asset (logo, product photo, PDF). Returns GCS URI."""
    blob_path = f"brands/{brand_id}/{filename}"
    bucket = get_bucket()
    blob = bucket.blob(blob_path)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: blob.upload_from_string(file_bytes, content_type=mime_type)
    )
    return f"gs://{GCS_BUCKET_NAME}/{blob_path}"

async def get_signed_url(gcs_uri: str) -> str:
    """Convert a gs:// URI to a 1-hour signed URL for frontend serving."""
    blob_path = gcs_uri.replace(f"gs://{GCS_BUCKET_NAME}/", "")
    bucket = get_bucket()
    blob = bucket.blob(blob_path)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: blob.generate_signed_url(expiration=timedelta(hours=1), method="GET")
    )

async def download_from_gcs(url: str) -> bytes:
    """Download bytes from a signed URL or gs:// URI."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content

async def upload_video_to_gcs(video_bytes: bytes, post_id: str) -> tuple[str, str]:
    """Upload generated MP4 video bytes to GCS.

    Returns:
        (signed_url, gcs_uri) — 7-day signed URL and the gs:// URI.
    """
    blob_path = f"generated/{post_id}/video_{uuid.uuid4().hex[:8]}.mp4"
    bucket = get_bucket()
    blob = bucket.blob(blob_path)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: blob.upload_from_string(video_bytes, content_type="video/mp4"),
    )

    signed_url = await loop.run_in_executor(
        None,
        lambda: blob.generate_signed_url(expiration=timedelta(days=7), method="GET"),
    )

    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_path}"
    return signed_url, gcs_uri
