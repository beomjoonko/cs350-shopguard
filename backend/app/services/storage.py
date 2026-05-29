"""
Supabase Storage service for evidence images — SRS §3.3.

Replaces the planned boto3/S3 integration. Images are stored in the
`shopguard-evidence` bucket (configurable via SUPABASE_STORAGE_BUCKET).

The bucket must be set to public in the Supabase dashboard so that
`get_public_url()` returns a directly accessible URL. If content
sensitivity requires private storage, switch to `create_signed_url()`.
"""
import mimetypes
import uuid as _uuid

from supabase import create_client

from app.config import settings


def _client():
    """Return a Supabase client authenticated with the service-role key."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def upload_evidence_image(file_bytes: bytes, original_filename: str) -> str:
    """
    Upload an evidence image to Supabase Storage.

    Files are stored at: evidence/<uuid>/<original_filename>

    Returns:
        The public URL of the uploaded object.

    Raises:
        Exception: if the Supabase Storage API returns an error.
    """
    client = _client()
    content_type = (
        mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
    )
    storage_path = f"evidence/{_uuid.uuid4()}/{original_filename}"

    client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )

    return client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(
        storage_path
    )
