"""
Confirmation Flow - 三级哨位确认流
"""

from typing import Dict, List, Callable, Optional
import time


class ConfirmationFlow:
    """三级哨位确认系统"""
    
    def __init__(self, mode: str = "interactive", 
                 channels: List[str] = None):
        self.mode = mode
        self.channels = channels or ["cli"]
        self.timeout = 600  # 10分钟超时
    
    def confirm_script(self, script: Dict) -> bool:
        """
        哨位 1: 剧本确认
        
        确认内容：
        - 文案是否符合主题
        - 情绪曲线是否合理
        - 音乐选型是否合适
        """
        print("\n" + "="*60)
        print("⏸️ 哨位 1: 剧本确认")
        print("="*60)
        print(f"📖 标题: {script.get('title')}")
        print(f"📝 文案: {script.get('narration')}")
        print(f"🎵 音乐风格: {script.get('music_style')}")
        print(f"😊 情绪: {script.get('emotion', 'nostalgic')}")
        
        if self.mode == "auto":
            print("✅ 自动确认")
            return True
        
        # CLI 交互确认
        response = input("\n确认剧本? [Y/n/edit]: ").strip().lower()
        
        if response in ['', 'y', 'yes']:
            return True
        elif response == 'edit':
            # TODO: 支持编辑
            print("编辑功能待实现，默认确认")
            return True
        else:
            return False
    
    def confirm_rewrite(self, script: Dict) -> bool:
        """
        哨位 2: 素材修正确认
        
        当剧本因素材不足被重写时触发
        """
        if not script.get('was_rewritten'):
            return True
        
        print("\n" + "="*60)
        print("⏸️ 哨位 2: 素材修正确认")
        print("="*60)
        print("⚠️ 部分素材缺失，剧本已自动调整")
        print(f"\n原文案: {script.get('original_narration')}")
        print(f"调整后: {script.get('narration')}")
        print(f"\n缺失元素: {script.get('adapted_visual', [])}")
        print(f"可用元素: {script.get('required_visual', [])}")
        
        if self.mode == "auto":
            print(f"⏱️ 自动确认（{self.timeout}秒超时）")
            time.sleep(1)
            return True
        
        response = input("\n接受调整? [Y/n/retry]: ").strip().lower()
        
        if response in ['', 'y', 'yes']:
            return True
        elif response == 'retry':
            # TODO: 支持重新搜索
            print("重新搜索功能待实现")
            return False
        else:
            return False
    
    def confirm_preview(self, preview_path: str) -> bool:
        """
        哨位 3: 样片预览确认
        
        预览包含：
        - 15秒样片
        - 磨皮效果
        - 调色风格
        - 字幕样式
        """
        print("\n" + "="*60)
        print("⏸️ 哨位 3: 样片预览确认")
        print("="*60)
        print(f"🎬 样片路径: {preview_path}")
        print("\n预览效果包含：")
        print("  ✓ 智能磨皮（保留纹理）")
        print("  ✓ 电影感调色（肤色保护）")
        print("  ✓ 中英双语字幕")
        print("  ✓ BPM 节奏对齐")
        
        if self.mode == "auto":
            print("✅ 自动确认")
            return True
        
        response = input("\n确认渲染完整视频? [Y/n/regenerate]: ").strip().lower()
        
        if response in ['', 'y', 'yes']:
            return True
        elif response == 'regenerate':
            print("重新生成功能待实现")
            return False
        else:
            return False
    
    def _send_discord_notification(self, message: str):
        """发送 Discord 通知（可选）"""
        if "discord" in self.channels:
            # TODO: 集成 Discord Bot
            pass
