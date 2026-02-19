"""
Asset Indexer - 素材索引模块
整合指纹去重 + CLIP 语义搜索
"""

from .semantic import SemanticIndex
from .fingerprint import FingerprintDB

__all__ = ["SemanticIndex", "FingerprintDB"]
