from botocore.exceptions import ClientError

from luxtj.contexts.account.application.ports import ObjectMetadata


class S3ObjectStorage:
    def __init__(self, *, session, bucket: str, endpoint_url: str | None, region: str) -> None:
        self._session = session
        self._bucket = bucket
        self._endpoint_url = endpoint_url or None
        self._region = region

    def _client(self):
        return self._session.client(
            "s3",
            endpoint_url=self._endpoint_url,
            region_name=self._region,
        )

    async def presigned_put_url(
        self, *, object_key: str, content_type: str, expires_in: int
    ) -> str:
        async with self._client() as client:
            return await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

    async def presigned_get_url(self, *, object_key: str, expires_in: int) -> str:
        async with self._client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": object_key},
                ExpiresIn=expires_in,
            )

    async def head_object(self, *, object_key: str) -> ObjectMetadata | None:
        async with self._client() as client:
            try:
                response = await client.head_object(Bucket=self._bucket, Key=object_key)
            except ClientError:
                return None
        return ObjectMetadata(
            content_type=response.get("ContentType", ""),
            size_bytes=int(response.get("ContentLength", 0)),
        )
