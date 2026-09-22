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

    # 验证COS的可用性与凭证
    async def ping(self) -> bool:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
            return True
        except (CosClientError, CosServiceError) as exc:
            logger.warning("COS连通失败: %s", exc)
            return False

_cos_client: CosClient | None = None

def get_cos_client() -> CosClient:
    global _cos_client
    if _cos_client is None:
        _cos_client = CosClient()
    return _cos_client
