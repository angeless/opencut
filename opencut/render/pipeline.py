"""
Render Pipeline - 渲染管道
整合磨皮/调色/字幕/BPM对拍
"""

import subprocess
from pathlib import Path
from typing import List, Dict

import cv2
import numpy as np

from .beauty import AdvancedBeautyFilter, apply_beauty_filter_simple


class RenderPipeline:
    """全自动渲染管道"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.beauty_config = config.get('beauty', {})
        self.color_config = config.get('color_grading', {})
        self.subtitle_config = config.get('subtitle', {})
        self.output_config = config.get('output', {})
        
        # 初始化高级磨皮滤镜
        if self.beauty_config.get('enabled'):
            self.beauty_filter = AdvancedBeautyFilter(
                smooth_strength=self.beauty_config.get('intensity', 0.8),
                pore_reduction=self.beauty_config.get('pore_reduction', 0.6),
                acne_threshold=self.beauty_config.get('acne_threshold', 0.3)
            )
        else:
            self.beauty_filter = None
    
    def render(self, script: Dict, materials: List[Dict],
               output: str, config: object):
        """
        执行完整渲染流程
        
        Args:
            script: 剧本数据
            materials: 素材列表
            output: 输出路径
            config: 视频配置
        """
        print("开始渲染流程...")
        
        # Step 1: 合并素材
        concat_file = self._concat_materials(materials, output)
        
        # Step 2: 应用磨皮
        if self.beauty_config.get('enabled'):
            beauty_output = self._apply_beauty_filter(concat_file, output)
        else:
            beauty_output = concat_file
        
        # Step 3: 应用调色
        if self.color_config.get('enabled'):
            color_output = self._apply_color_grading(beauty_output, output)
        else:
            color_output = beauty_output
        
        # Step 4: 生成并压制字幕
        if self.subtitle_config.get('enabled'):
            final_output = self._apply_subtitles(color_output, script, output)
        else:
            final_output = color_output
        
        print(f"渲染完成: {final_output}")
        return final_output
    
    def _concat_materials(self, materials: List[Dict], 
                         output_base: str) -> str:
        """合并视频片段"""
        # 创建 FFmpeg concat 列表
        concat_list = Path(output_base).parent / "concat_list.txt"
        
        with open(concat_list, 'w') as f:
            for m in materials:
                file_path = m.get('file_path', '')
                start = m.get('time_range', [0, 10])[0]
                end = m.get('time_range', [0, 10])[1]
                duration = end - start
                
                f.write(f"file '{file_path}'\n")
                f.write(f"inpoint {start}\n")
                f.write(f"outpoint {end}\n")
        
        concat_output = str(Path(output_base).parent / "step1_concat.mp4")
        
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            concat_output
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return concat_output
    
    def _apply_beauty_filter(self, input_path: str, 
                            output_base: str) -> str:
        """应用高级磨皮滤镜"""
        output = str(Path(output_base).parent / "step2_beauty.mp4")
        
        print("    应用高级磨皮滤镜...")
        print("    - MediaPipe 人脸检测")
        print("    - 频率分解（保留纹理）")
        print("    - 痘印修复")
        
        # 打开视频
        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 创建输出
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output, fourcc, fps, (width, height))
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 应用磨皮
            if self.beauty_filter:
                processed = self.beauty_filter.process_video_frame(frame)
            else:
                processed = frame
            
            out.write(processed)
            frame_count += 1
            
            if frame_count % 30 == 0:
                print(f"      处理帧: {frame_count}")
        
        cap.release()
        out.release()
        
        print(f"    ✓ 磨皮完成: {frame_count} 帧")
        return output
    
    def _apply_color_grading(self, input_path: str, 
                            output_base: str) -> str:
        """应用电影感调色"""
        output = str(Path(output_base).parent / "step3_color.mp4")
        
        # 使用 curves 和 eq 滤镜模拟电影感
        # 提升对比度，降低饱和度，偏冷色调
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", "eq=contrast=1.1:saturation=0.8,curves=r='0/0 0.5/0.45 1/1':g='0/0 0.5/0.48 1/1':b='0/0 0.5/0.52 1/1',format=yuv420p",
            "-c:a", "copy",
            output
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output
    
    def _apply_subtitles(self, input_path: str, 
                        script: Dict, output_base: str) -> str:
        """压制双语字幕"""
        output = str(Path(output_base).parent / "step4_final.mp4")
        
        # 生成 SRT 字幕文件
        srt_path = Path(output_base).parent / "subtitles.srt"
        self._generate_srt(script, str(srt_path))
        
        # 使用 FFmpeg 压制字幕
        font = self.subtitle_config.get('font', 'Noto Sans CJK SC')
        font_size = self.subtitle_config.get('font_size', 24)
        outline = self.subtitle_config.get('outline', 2)
        margin_v = self.subtitle_config.get('margin_v', 60)
        
        style = f"FontName={font},FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline={outline},Alignment=2,MarginV={margin_v}"
        
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"subtitles={srt_path}:force_style='{style}'",
            "-c:a", "copy",
            output
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output
    
    def _generate_srt(self, script: Dict, output_path: str):
        """生成 SRT 字幕文件"""
        # 简化版：根据剧本生成固定时间轴的字幕
        narration = script.get('narration', '')
        
        # 分割为两句（示例）
        lines = [
            ("旅行的意义", "The meaning of travel", 0, 3),
            ("在于未知的风景", "lies in the unknown scenery", 3, 6)
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, (cn, en, start, end) in enumerate(lines, 1):
                f.write(f"{i}\n")
                f.write(f"00:00:{start:02d},000 --> 00:00:{end:02d},000\n")
                f.write(f"{cn}\n{en}\n\n")
