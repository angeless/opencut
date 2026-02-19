#!/usr/bin/env python3
"""
OpenCut 端到端测试
使用本地视频素材测试完整流程：指纹索引 → 语义搜索 → 自适应剧本 → 渲染
"""

import sys
import os
sys.path.insert(0, '/home/angeless_wanganqi/.openclaw/workspace/opencut')

from pathlib import Path
from opencut.indexer.fingerprint import FingerprintDB, VideoHasher
from opencut.indexer.semantic import SemanticIndex
from opencut.script.adaptive import AdaptiveScript
from opencut.script.confirmation import ConfirmationFlow
from opencut.render.pipeline import RenderPipeline


def test_fingerprint_indexing():
    """测试 1: 指纹索引"""
    print("\n" + "="*60)
    print("🧪 测试 1: 视频指纹索引")
    print("="*60)
    
    # 测试视频
    test_videos = [
        "/home/angeless_wanganqi/.openclaw/workspace/video_test/477ed0c7-6344-4fdb-9eed-bf7977141348.mov",
        "/home/angeless_wanganqi/.openclaw/workspace/video_test/57c73514-c369-42ad-b502-50cf893a90f5.mp4"
    ]
    
    # 创建数据库
    db_path = Path("/tmp/opencut_test/fingerprints.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = FingerprintDB(db_path)
    
    # 索引视频
    print("\n📹 正在索引视频...")
    hasher = VideoHasher()
    
    for video_path in test_videos:
        if not Path(video_path).exists():
            print(f"⚠️ 视频不存在: {video_path}")
            continue
        
        print(f"\n  处理: {Path(video_path).name}")
        fingerprint = hasher.compute_video_fingerprint(video_path, sample_interval=1.0)
        video_id = db.add_video(fingerprint)
        print(f"    ✓ 已索引: {fingerprint['duration']:.1f}s, "
              f"{fingerprint['sampled_frames']} 帧")
    
    # 显示统计
    stats = db.get_stats()
    print(f"\n📊 索引统计:")
    print(f"    视频数量: {stats['video_count']}")
    print(f"    总时长: {stats['total_duration_hours']:.2f} 小时")
    print(f"    帧样本: {stats['frame_samples']}")
    
    # 检查重复
    print("\n🔍 检查重复视频...")
    duplicates = db.find_duplicates(threshold=10)
    if duplicates:
        print(f"    发现 {len(duplicates)} 组重复视频")
        for group in duplicates:
            print(f"      - {len(group)} 个文件相似")
    else:
        print("    ✓ 未发现重复")
    
    return True


def test_semantic_search():
    """测试 2: 语义搜索"""
    print("\n" + "="*60)
    print("🧪 测试 2: CLIP 语义搜索")
    print("="*60)
    
    test_videos = [
        "/home/angeless_wanganqi/.openclaw/workspace/video_test/477ed0c7-6344-4fdb-9eed-bf7977141348.mov",
        "/home/angeless_wanganqi/.openclaw/workspace/video_test/57c73514-c369-42ad-b502-50cf893a90f5.mp4"
    ]
    
    # 创建语义索引
    index_path = Path("/tmp/opencut_test/semantic_index")
    index_path.mkdir(parents=True, exist_ok=True)
    
    try:
        semantic_index = SemanticIndex(index_path)
    except Exception as e:
        print(f"⚠️ CLIP 模型加载失败: {e}")
        print("    跳过语义搜索测试")
        return False
    
    # 索引视频
    print("\n📹 正在建立语义索引...")
    existing_videos = [v for v in test_videos if Path(v).exists()]
    
    def progress(current, total):
        print(f"    进度: {current}/{total}")
    
    total_clips = semantic_index.batch_index(existing_videos, progress)
    print(f"    ✓ 已索引 {total_clips} 个片段")
    
    # 语义搜索
    print("\n🔍 执行语义搜索...")
    queries = [
        "滑雪运动",
        "风景旅游",
        "人物特写"
    ]
    
    for query in queries:
        print(f"\n  查询: '{query}'")
        results = semantic_index.search(query, top_k=3, min_duration=2.0)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"    {i}. {Path(result['file_path']).name}")
                print(f"       时间: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                print(f"       相似度: {result['similarity_score']:.3f}")
        else:
            print("    ⚠️ 未找到匹配结果")
    
    return True


def test_adaptive_script():
    """测试 3: 自适应剧本"""
    print("\n" + "="*60)
    print("🧪 测试 3: 剧本自适应重写")
    print("="*60)
    
    config = {
        'adaptive_rewrite': {
            'similarity_threshold': 0.6
        }
    }
    
    rewriter = AdaptiveScript(config)
    
    # 原始剧本
    original_script = {
        'title': '雪山冒险',
        'narration': '我在雪地里奔跑，感受自由的风吹过脸庞',
        'required_visual': ['snow', 'running', 'person', 'wind'],
        'emotion': 'excited'
    }
    
    print("\n📝 原始剧本:")
    print(f"    标题: {original_script['title']}")
    print(f"    旁白: {original_script['narration']}")
    print(f"    需要: {original_script['required_visual']}")
    
    # 场景 1: 素材充足
    print("\n✅ 场景 1: 素材充足")
    available_tags_1 = ['snow', 'running', 'person', 'mountain']
    script_1 = rewriter.rewrite(
        original_script.copy(),
        available_tags_1,
        'excited'
    )
    
    if script_1.get('was_rewritten'):
        print(f"    ⚠️ 已重写: {script_1['narration']}")
    else:
        print(f"    ✓ 无需重写")
    
    # 场景 2: 素材缺失（没有 running）
    print("\n⚠️ 场景 2: 素材缺失（缺少 'running'）")
    available_tags_2 = ['snow', 'walking', 'person', 'mountain']
    script_2 = rewriter.rewrite(
        original_script.copy(),
        available_tags_2,
        'nostalgic'
    )
    
    if script_2.get('was_rewritten'):
        print(f"    ✓ 已自适应重写:")
        print(f"      原文: {script_2['original_narration']}")
        print(f"      新文: {script_2['narration']}")
        print(f"      缺失: {script_2['adapted_visual']}")
    
    return True


def test_render_pipeline():
    """测试 4: 渲染管道"""
    print("\n" + "="*60)
    print("🧪 测试 4: 渲染管道")
    print("="*60)
    
    test_video = "/home/angeless_wanganqi/.openclaw/workspace/video_test/477ed0c7-6344-4fdb-9eed-bf7977141348.mov"
    
    if not Path(test_video).exists():
        print(f"⚠️ 测试视频不存在: {test_video}")
        return False
    
    config = {
        'beauty': {'enabled': True, 'intensity': 0.7},
        'color_grading': {'enabled': True},
        'subtitle': {'enabled': True, 'bilingual': True},
        'output': {'resolution': [1080, 1920]}
    }
    
    print("\n🎨 初始化渲染管道...")
    pipeline = RenderPipeline(config)
    
    # 模拟剧本和素材
    script = {
        'title': 'Test Video',
        'narration': '旅行的意义在于未知的风景'
    }
    
    materials = [{
        'file_path': test_video,
        'time_range': [0, 5]
    }]
    
    output_dir = Path("/tmp/opencut_test/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "test_render.mp4")
    
    print(f"\n🎬 开始渲染...")
    print(f"    输入: {test_video}")
    print(f"    输出: {output_path}")
    
    try:
        result = pipeline.render(
            script, materials,
            output_path,
            type('Config', (), {'style': 'wanderlust'})()
        )
        print(f"    ✓ 渲染完成: {result}")
        return True
    except Exception as e:
        print(f"    ✗ 渲染失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 OpenCut 端到端测试套件")
    print("="*60)
    
    results = []
    
    # 测试 1: 指纹索引
    try:
        results.append(("指纹索引", test_fingerprint_indexing()))
    except Exception as e:
        print(f"\n✗ 指纹索引测试失败: {e}")
        results.append(("指纹索引", False))
    
    # 测试 2: 语义搜索
    try:
        results.append(("语义搜索", test_semantic_search()))
    except Exception as e:
        print(f"\n✗ 语义搜索测试失败: {e}")
        results.append(("语义搜索", False))
    
    # 测试 3: 自适应剧本
    try:
        results.append(("自适应剧本", test_adaptive_script()))
    except Exception as e:
        print(f"\n✗ 自适应剧本测试失败: {e}")
        results.append(("自适应剧本", False))
    
    # 测试 4: 渲染管道
    try:
        results.append(("渲染管道", test_render_pipeline()))
    except Exception as e:
        print(f"\n✗ 渲染管道测试失败: {e}")
        results.append(("渲染管道", False))
    
    # 总结
    print("\n" + "="*60)
    print("📋 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
