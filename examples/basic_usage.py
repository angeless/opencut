#!/usr/bin/env python3
"""
OpenCut 使用示例
展示如何调用 API 进行全自动剪辑
"""

from opencut import OpenCutPipeline, VideoConfig


def example_basic():
    """基础用法示例"""
    # 初始化流水线
    pipeline = OpenCutPipeline("./config.json")
    
    # 创建视频配置
    config = VideoConfig(
        topic="格鲁吉亚山顶的日落",
        style="wanderlust",  # 清冷流浪感
        music="lofi-chill"
    )
    
    # 一键创建（交互式确认）
    result = pipeline.create(config, confirm_mode="interactive")
    
    if result:
        print(f"✅ 视频已生成: {result.path}")
        print(f"   时长: {result.duration:.1f}秒")
        print(f"   分辨率: {result.resolution}")
    else:
        print("❌ 创建失败")


def example_batch():
    """批量创建示例"""
    pipeline = OpenCutPipeline("./config.json")
    
    topics = [
        "冰岛黑沙滩的孤独",
        "东京雨夜的霓虹",
        "撒哈拉星空的震撼"
    ]
    
    for topic in topics:
        config = VideoConfig(topic=topic, style="cinematic")
        
        # 自动模式，批量处理
        result = pipeline.create(config, confirm_mode="auto")
        
        if result:
            print(f"✅ {topic}: {result.path}")


def example_custom_style():
    """自定义风格示例"""
    pipeline = OpenCutPipeline("./config.json")
    
    config = VideoConfig(
        topic="京都红叶的静谧",
        style="japanese_minimal",  # 可以扩展更多风格
        music="traditional-shakuhachi",
        duration=60  # 指定时长
    )
    
    result = pipeline.create(config)
    
    if result:
        print(f"✅ 定制视频已生成: {result.path}")


if __name__ == "__main__":
    print("OpenCut 使用示例")
    print("=" * 60)
    print("\n1. 基础用法:")
    example_basic()
    
    print("\n2. 批量创建:")
    # example_batch()  # 取消注释以运行
    
    print("\n3. 自定义风格:")
    # example_custom_style()  # 取消注释以运行
