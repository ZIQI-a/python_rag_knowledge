""" 腾讯云COS客户端封装 """
import asyncio

from qcloud_cos import CosConfig, CosS3Client, CosClientError, CosServiceError

from app.core.config import settings
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger

logger = get_logger(__name__)

class CosClient:

    def __init__(self) -> None:
        if not settings.cos_configured:
            raise ConfigurationError("腾讯云COS未配置，请先配置环境变量")
        config = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key,
        )
        self._client = CosS3Client(config)
        self._bucket = settings.cos_bucket

    @property
    def bucket(self) -> str:
        return self._bucket
    @property
    def region(self) -> str:
        return settings.cos_region

    # 验证COS的可用性与凭证
    async def ping(self) -> bool:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
            return True
        except (CosClientError, CosServiceError) as exc:
            logger.warning("COS连通失败: %s", exc)
            return False

    # 上传文件到COS
    async def put_object(self, *, key: str, body: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    # 获取文件内容读取Object的全部字节
    async def get_object(self, key: str) -> bytes:
        def _read() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].get_raw_stream().read()
        return await asyncio.to_thread(_read)


    # 删除文件
    async def delete_object(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

_cos_client: CosClient | None = None

def get_cos_client() -> CosClient:
    global _cos_client
    if _cos_client is None:
        _cos_client = CosClient()
    return _cos_client

