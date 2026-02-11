"""
IO 工具 - 文件和网络操作
IO utility - file and network operations.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


async def download_file(url: str, dest_path: str, timeout: int = 60) -> bool:
    """
    下载文件
    Download a file.
    """
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    with open(dest_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            f.write(chunk)
                    return True
                logger.warning("下载失败: HTTP %d", resp.status)
                return False
    except Exception:
        logger.exception("下载出错: %s", url)
        return False


async def fetch_json(url: str, timeout: int = 30) -> Any:
    """
    获取 JSON 数据
    Fetch JSON data.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            return None


def ensure_dir(path: str) -> str:
    """确保目录存在 / Ensure directory exists."""
    os.makedirs(path, exist_ok=True)
    return path
