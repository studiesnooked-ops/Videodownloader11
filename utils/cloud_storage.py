import os
import boto3
import uuid
import logging

logger = logging.getLogger("bot.cloud")

S3_BUCKET = os.getenv("S3_BUCKET")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS = os.getenv("S3_ACCESS_KEY")
S3_SECRET = os.getenv("S3_SECRET_KEY")

client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS,
    aws_secret_access_key=S3_SECRET,
)


async def upload_to_s3(file_path: str, filename: str) -> str:
    try:
        key = f"videos/{uuid.uuid4()}_{filename}"

        client.upload_file(file_path, S3_BUCKET, key)

        return f"{S3_ENDPOINT}/{S3_BUCKET}/{key}"

    except Exception as e:
        logger.error("S3 upload failed: %s", e)
        return ""
