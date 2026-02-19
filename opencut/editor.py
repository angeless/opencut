"""
OpenCut - 旅游视频全自动剪辑系统主入口
整合指纹索引、语义搜索、剧本自适应、全自动渲染
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class VideoConfig:
    """视频配置"""
    topic: str
    style: str = "wanderlust"
    music: Optional[str] = None
    duration: Optional[int] = None


@dataclass
class RenderResult:
    """渲染结果"""
    path: str
    duration: float
    resolution: tuple
    file_size: int


class OpenCutPipeline:
    """
    OpenCut 主流水线
    
    整合工作流：
    1. Asset Indexer - 指纹去重 + CLIP 语义搜索
    2. Script Engine - 剧本自适应重写 + 三级哨位确认
    3. Render Pipeline - 磨皮/调色/字幕/BPM对拍
    """
    
    def __init__(self, config_path: str = "./config.json"):
        """初始化流水线"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.output_dir = Path(self.config['output']['directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各模块（懒加载）
        self._indexer = None
        self._script_engine = None
        self._render_pipeline = None
    
    @property
    def indexer(self):
        """懒加载素材索引器"""
        if self._indexer is None:
            from .indexer.semantic import SemanticIndex
            from .indexer.fingerprint import FingerprintDB
            
            index_path = Path(self.config['storage']['path']) / ".opencut_index"
            self._indexer = {
                'semantic': SemanticIndex(index_path / "semantic"),
                'fingerprint': FingerprintDB(index_path / "fingerprints.db")
            }
        return self._indexer
    
    @property
    def script_engine(self):
        """懒加载剧本引擎"""
        if self._script_engine is None:
            from .script.adaptive import AdaptiveScript
            from .script.confirmation import ConfirmationFlow
            
            self._script_engine = {
                'adaptive': AdaptiveScript(self.config['script']),
                'confirmation': ConfirmationFlow(
                    mode=self.config['script']['confirmation']['mode'],
                    channels=self.config['script']['confirmation']['channels']
                )
            }
        return self._script_engine
    
    @property
    def render_pipeline(self):
        """懒加载渲染管道"""
        if self._render_pipeline is None:
            from .render.pipeline import RenderPipeline
            self._render_pipeline = RenderPipeline(self.config['render'])
        return self._render_pipeline
    
    def create(self, config: VideoConfig, 
               confirm_mode: str = "interactive") -> RenderResult:
        """
        一键创建视频
        
        Args:
            config: 视频配置（主题、风格、音乐等）
            confirm_mode: 确认模式 ("interactive" | "auto")
        
        Returns:
            RenderResult: 渲染结果
        """
        print(f"\n{'='*60}")
        print(f"🎬 OpenCut - 开始创建视频: {config.topic}")
        print(f"{'='*60}\n")
        
        # Step 1: 语义搜索素材
        print("[1/5] 🔍 语义搜索素材...")
        materials = self._search_materials(config.topic)
        print(f"      找到 {len(materials)} 个候选片段")
        
        # Step 2: 剧本生成与自适应重写
        print("[2/5] 📝 生成剧本...")
        script = self._generate_script(config, materials)
        
        # 检查是否需要重写
        if script['needs_rewrite']:
            print("      ⚠️ 素材不足，触发自适应重写...")
            script = self._adaptive_rewrite(script, materials)
        
        # Step 3: 三级哨位确认
        if confirm_mode == "interactive":
            print("[3/5] ⏸️ 进入三级哨位确认...")
            confirmed = self._confirmation_flow(script, materials)
            if not confirmed:
                print("❌ 用户取消，中止流程")
                return None
        else:
            print("[3/5] ✅ 自动模式，跳过确认")
        
        # Step 4: 全自动渲染
        print("[4/5] 🎨 开始渲染...")
        output_path = self._render(script, materials, config)
        
        # Step 5: 输出结果
        print("[5/5] ✅ 渲染完成!")
        result = self._package_result(output_path)
        
        print(f"\n{'='*60}")
        print(f"🎉 成片已生成: {result.path}")
        print(f"   时长: {result.duration:.1f}s | 分辨率: {result.resolution}")
        print(f"{'='*60}\n")
        
        return result
    
    def _search_materials(self, query: str) -> List[Dict]:
        """语义搜索素材"""
        # 1. 扫描存储
        all_files = self._scan_storage()
        
        # 2. 指纹去重（快速过滤）
        unique_files = self.indexer['fingerprint'].deduplicate(all_files)
        print(f"      扫描到 {len(all_files)} 个文件，去重后 {len(unique_files)} 个")
        
        # 3. 确保语义索引已建立
        existing_clips = self.indexer['semantic'].get_stats()['indexed_clips']
        if existing_clips < len(unique_files):
            print(f"      建立语义索引 ({existing_clips} -> {len(unique_files)})...")
            def progress(current, total):
                if current % 5 == 0:
                    print(f"        进度: {current}/{total}")
            self.indexer['semantic'].batch_index(unique_files, progress)
        
        # 4. CLIP 语义搜索
        results = self.indexer['semantic'].search(
            query=query,
            top_k=self.config['indexer']['semantic']['top_k']
        )
        
        return results
    
    def _generate_script(self, config: VideoConfig, 
                         materials: List[Dict]) -> Dict:
        """生成初始剧本"""
        script = {
            'title': config.topic,
            'scenes': [],
            'narration': f'在探索的路上，我们发现了不一样的美好。{config.topic}',
            'music_style': config.music or 'lofi',
            'needs_rewrite': len(materials) == 0,
            'required_visual': ['travel', 'scenery', 'adventure']
        }
        
        return script
    
    def _calculate_coverage(self, script: Dict, materials: List[Dict]) -> float:
        """计算素材覆盖度"""
        if not materials:
            return 0.0
        return min(1.0, len(materials) / 3.0)
    
    def _adaptive_rewrite(self, script: Dict, 
                          materials: List[Dict]) -> Dict:
        """剧本自适应重写"""
        rewriter = self.script_engine['adaptive']
        
        # 根据现有素材调整剧本
        available_tags = set()
        for m in materials:
            available_tags.update(m.get('tags', []))
        
        new_script = rewriter.rewrite(
            original_script=script,
            available_tags=list(available_tags),
            emotion=script.get('emotion', 'nostalgic')
        )
        
        return new_script
    
    def _confirmation_flow(self, script: Dict, 
                           materials: List[Dict]) -> bool:
        """三级哨位确认流"""
        confirmation = self.script_engine['confirmation']
        
        # 哨位 1: 剧本确认
        if not confirmation.confirm_script(script):
            return False
        
        # 哨位 2: 素材修正确认（如果需要）
        if script.get('was_rewritten'):
            if not confirmation.confirm_rewrite(script):
                return False
        
        # 哨位 3: 样片预览确认
        preview = self._generate_preview(script, materials)
        if not confirmation.confirm_preview(preview):
            return False
        
        return True
    
    def _render(self, script: Dict, materials: List[Dict],
                config: VideoConfig) -> str:
        """全自动渲染"""
        output_path = self.output_dir / f"{config.topic.replace(' ', '_')}_final.mp4"
        
        self.render_pipeline.render(
            script=script,
            materials=materials,
            output=str(output_path),
            config=config
        )
        
        return str(output_path)
    
    def _package_result(self, path: str) -> RenderResult:
        """包装渲染结果"""
        import cv2
        
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        return RenderResult(
            path=path,
            duration=duration,
            resolution=(width, height),
            file_size=os.path.getsize(path)
        )
    
    def _scan_storage(self) -> List[str]:
        """扫描存储路径"""
        storage_path = Path(self.config['storage']['path'])
        video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
        
        files = []
        for ext in video_extensions:
            files.extend(storage_path.rglob(f"*{ext}"))
        
        return [str(f) for f in files]


# CLI 入口
def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='OpenCut - 全自动视频剪辑')
    parser.add_argument('--config', default='./config.json', help='配置文件路径')
    parser.add_argument('--topic', required=True, help='视频主题')
    parser.add_argument('--style', default='wanderlust', help='风格预设')
    parser.add_argument('--music', help='背景音乐')
    parser.add_argument('--auto', action='store_true', help='自动模式（跳过确认）')
    
    args = parser.parse_args()
    
    pipeline = OpenCutPipeline(args.config)
    config = VideoConfig(
        topic=args.topic,
        style=args.style,
        music=args.music
    )
    
    result = pipeline.create(config, confirm_mode="auto" if args.auto else "interactive")
    
    if result:
        print(f"输出文件: {result.path}")
    else:
        print("创建失败")


if __name__ == "__main__":
    main()
