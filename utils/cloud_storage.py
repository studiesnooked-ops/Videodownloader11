"""
S3 Cloud storage uploader (Render-safe)
Used for large files (500MB - 5GB+)
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("bot.cloud")

S3_BUCKET = os.environ.get("S3_BUCKET")
S3_KEY = os.environ.get("S3_KEY")
S3_SECRET = os.environ.get("S3_SECRET")

s3 = boto3.client(
    "s3",
    aws_access_key_id=S3_KEY,
    aws_secret_access_key=S3_SECRET
)


async def upload_to_s3(file_path: str, file_name: str) -> str:
    """
    Upload file to S3 and return public URL
    """

    try:
        s3.upload_file(
            file_path,
            S3_BUCKET,
            file_name,
            ExtraArgs={"ACL": "public-read"}
        )

        url = f"https://{S3_BUCKET}.s3.amazonaws.com/{file_name}"
        logger.info("Uploaded to S3: %s", url)

        return url

    except ClientError as e:
        logger.error("S3 upload failed: %s", e)
        return ""
