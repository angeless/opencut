"""
OpenCut - 旅游视频全自动剪辑系统

专为旅游博主设计的 AI 剪辑助手。
8TB 素材全自动管理、剧本自适应、一键成片。
"""

__version__ = "1.0.0"
__author__ = "OpenCut Contributors"

from .editor import (
    OpenCutPipeline,
    VideoConfig,
    RenderResult
)

__all__ = [
    "OpenCutPipeline",
    "VideoConfig", 
    "RenderResult"
]
