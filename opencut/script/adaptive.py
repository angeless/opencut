"""
Adaptive Script - 剧本自适应重写
当素材不足时自动调整剧本
"""

from typing import List, Dict, Set


class AdaptiveScript:
    """自适应剧本引擎"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.similarity_threshold = config.get(
            'adaptive_rewrite', {}
        ).get('similarity_threshold', 0.6)
    
    def rewrite(self, original_script: Dict, 
                available_tags: List[str],
                emotion: str = "nostalgic") -> Dict:
        """
        根据可用素材重写剧本
        
        Args:
            original_script: 原始剧本
            available_tags: 素材库中可用的视觉标签
            emotion: 情绪基调
        
        Returns:
            Dict: 重写后的剧本
        """
        script = original_script.copy()
        
        # 提取原始剧本要求的视觉元素
        required_visual = set(original_script.get('required_visual', []))
        available_set = set(available_tags)
        
        # 计算缺失和存在的元素
        missing = required_visual - available_set
        present = required_visual & available_set
        
        if missing:
            # 需要重写
            script['was_rewritten'] = True
            script['original_narration'] = original_script.get('narration', '')
            
            # TODO: 调用 LLM 进行智能重写
            # 这里使用简单的规则重写作为示例
            script['narration'] = self._rule_based_rewrite(
                original_script.get('narration', ''),
                list(missing),
                list(present),
                emotion
            )
            
            # 更新视觉要求
            script['required_visual'] = list(present)
            script['adapted_visual'] = list(missing)
        
        return script
    
    def _rule_based_rewrite(self, original: str, 
                           missing: List[str],
                           present: List[str],
                           emotion: str) -> str:
        """基于规则的重写（简化版）"""
        # 示例：将"奔跑"改为"漫步"如果跑步素材缺失
        rewrites = {
            "奔跑": "漫步",
            "跑": "走",
            "追逐": "跟随",
            "跳跃": "站立"
        }
        
        new_text = original
        for old, new in rewrites.items():
            if old in original:
                new_text = new_text.replace(old, new)
        
        if new_text != original:
            new_text += "（根据素材调整）"
        
        return new_text
    
    def calculate_coverage(self, script: Dict, 
                          materials: List[Dict]) -> float:
        """
        计算剧本与素材的覆盖度
        
        Returns:
            float: 0-1 之间的覆盖度分数
        """
        required = set(script.get('required_visual', []))
        if not required:
            return 1.0
        
        # 收集素材中所有的标签
        available_tags: Set[str] = set()
        for m in materials:
            available_tags.update(m.get('visual_tags', []))
        
        # 计算覆盖度
        covered = required & available_tags
        return len(covered) / len(required)
