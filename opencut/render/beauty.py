"""
Beauty Filter - 高级磨皮模块
针对毛孔、痘印优化 - 使用频率分解 + 局部平滑
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple


class AdvancedBeautyFilter:
    """
    高级磨皮滤镜
    
    核心算法：
    1. MediaPipe 人脸检测（定位皮肤区域）
    2. 频率分解（Frequency Separation）
       - 低频层：肤色、光影
       - 高频层：毛孔、纹理、痘印
    3. 智能平滑：只处理低频层，保留高频细节
    4. 局部增强：针对痘印区域额外处理
    """
    
    def __init__(self, 
                 smooth_strength: float = 0.8,
                 pore_reduction: float = 0.6,
                 acne_threshold: float = 0.3):
        """
        初始化磨皮参数
        
        Args:
            smooth_strength: 平滑强度 0-1（默认 0.8）
            pore_reduction: 毛孔淡化强度 0-1（默认 0.6）
            acne_threshold: 痘印检测阈值（默认 0.3）
        """
        self.smooth_strength = smooth_strength
        self.pore_reduction = pore_reduction
        self.acne_threshold = acne_threshold
        self.face_detector = None
        
    def _init_face_detector(self):
        """初始化人脸检测器（延迟加载）"""
        if self.face_detector is None:
            try:
                import mediapipe as mp
                self.mp_face = mp.solutions.face_detection
                self.face_detector = self.mp_face.FaceDetection(
                    model_selection=1,  # 高精度模型
                    min_detection_confidence=0.5
                )
            except ImportError:
                print("MediaPipe not available, using fallback")
                self.face_detector = None
    
    def detect_face_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        检测人脸区域
        
        Returns:
            List of (x, y, w, h) 人脸边界框
        """
        self._init_face_detector()
        
        if self.face_detector is None:
            # Fallback: 返回整个图像
            h, w = image.shape[:2]
            return [(0, 0, w, h)]
        
        # MediaPipe 需要 RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_detector.process(rgb_image)
        
        faces = []
        if results.detections:
            h, w = image.shape[:2]
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                faces.append((x, y, width, height))
        
        return faces
    
    def frequency_separation(self, 
                            image: np.ndarray, 
                            radius: int = 8) -> Tuple[np.ndarray, np.ndarray]:
        """
        频率分解
        
        Args:
            image: 输入图像
            radius: 高斯模糊半径（越大越平滑）
        
        Returns:
            (low_freq, high_freq): 低频层和高频层
        """
        # 低频层：高斯模糊（保留光影、肤色）
        low_freq = cv2.GaussianBlur(image, (0, 0), radius)
        
        # 高频层：原图减去低频（保留纹理、毛孔、痘印）
        high_freq = cv2.subtract(image, low_freq)
        
        return low_freq, high_freq
    
    def smooth_low_frequency(self, 
                            low_freq: np.ndarray,
                            strength: float) -> np.ndarray:
        """
        平滑低频层（不影响纹理）
        
        使用双边滤波：平滑颜色但保留边缘
        """
        # 双边滤波参数
        d = int(15 * strength)  # 邻域直径
        sigma_color = 80 * strength  # 颜色空间滤波 sigma
        sigma_space = 80 * strength  # 坐标空间滤波 sigma
        
        smoothed = cv2.bilateralFilter(
            low_freq, d, sigma_color, sigma_space
        )
        
        return smoothed
    
    def reduce_pores(self, 
                    high_freq: np.ndarray,
                    strength: float) -> np.ndarray:
        """
        淡化毛孔（高频层处理）
        
        对高频层进行轻微模糊，减少毛孔突兀感
        但不过度，保留皮肤纹理
        """
        if strength <= 0:
            return high_freq
        
        # 轻微高斯模糊
        kernel_size = max(3, int(3 * strength))
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        blurred = cv2.GaussianBlur(high_freq, (kernel_size, kernel_size), 0)
        
        # 混合：保留部分原始纹理
        result = cv2.addWeighted(high_freq, 1 - strength, blurred, strength, 0)
        
        return result
    
    def detect_acne_areas(self, 
                         image: np.ndarray,
                         face_region: Tuple[int, int, int, int]) -> np.ndarray:
        """
        检测痘印/瑕疵区域
        
        使用颜色特征检测红色痘印和深色痘印
        """
        x, y, w, h = face_region
        face_roi = image[y:y+h, x:x+w]
        
        # 转换到 LAB 颜色空间（更适合肤色分析）
        lab = cv2.cvtColor(face_roi, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 红色痘印：a 通道值高（偏红）
        # 深色痘印：L 通道值低（偏暗）
        
        # 检测红色区域
        _, red_mask = cv2.threshold(a, 140, 255, cv2.THRESH_BINARY)
        
        # 检测暗色区域
        _, dark_mask = cv2.threshold(l, 100, 255, cv2.THRESH_BINARY_INV)
        
        # 合并痘印区域
        acne_mask = cv2.bitwise_or(red_mask, dark_mask)
        
        # 形态学操作清理噪点
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        acne_mask = cv2.morphologyEx(acne_mask, cv2.MORPH_OPEN, kernel)
        acne_mask = cv2.morphologyEx(acne_mask, cv2.MORPH_CLOSE, kernel)
        
        # 放回原图尺寸
        full_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        full_mask[y:y+h, x:x+w] = acne_mask
        
        return full_mask
    
    def heal_acne_areas(self, 
                       image: np.ndarray,
                       acne_mask: np.ndarray) -> np.ndarray:
        """
        修复痘印区域
        
        使用 OpenCV 的 inpainting 算法
        """
        if np.sum(acne_mask) == 0:
            return image
        
        # 扩展掩码范围
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        acne_mask_dilated = cv2.dilate(acne_mask, kernel, iterations=1)
        
        # Inpainting 修复
        healed = cv2.inpaint(image, acne_mask_dilated, 3, cv2.INPAINT_TELEA)
        
        return healed
    
    def apply_beauty_filter(self, image: np.ndarray) -> np.ndarray:
        """
        应用完整磨皮流程
        
        Returns:
            磨皮后的图像
        """
        result = image.copy()
        
        # 1. 检测人脸
        faces = self.detect_face_regions(image)
        
        for face in faces:
            x, y, w, h = face
            
            # 提取人脸 ROI（稍微扩大区域包含脖子）
            margin = int(h * 0.2)
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(image.shape[1], x + w + margin)
            y2 = min(image.shape[0], y + h + margin)
            
            face_roi = result[y1:y2, x1:x2].copy()
            
            # 2. 检测痘印
            acne_mask = self.detect_acne_areas(result, (x1, y1, x2-x1, y2-y1))
            acne_mask_roi = acne_mask[y1:y2, x1:x2]
            
            # 3. 修复痘印
            face_roi = self.heal_acne_areas(face_roi, acne_mask_roi)
            
            # 4. 频率分解
            low_freq, high_freq = self.frequency_separation(face_roi)
            
            # 5. 平滑低频层（保留纹理）
            low_freq_smooth = self.smooth_low_frequency(
                low_freq, self.smooth_strength
            )
            
            # 6. 淡化毛孔（高频层）
            high_freq_smooth = self.reduce_pores(
                high_freq, self.pore_reduction
            )
            
            # 7. 合并
            face_result = cv2.add(low_freq_smooth, high_freq_smooth)
            
            # 8. 边缘融合（防止边界明显）
            # 创建羽化遮罩
            mask = np.zeros((y2-y1, x2-x1), dtype=np.float32)
            center_x, center_y = (x2-x1)//2, (y2-y1)//2
            cv2.ellipse(mask, (center_x, center_y), 
                       ((x2-x1)//2, (y2-y1)//2), 0, 0, 360, 1, -1)
            
            # 高斯模糊遮罩实现羽化
            mask = cv2.GaussianBlur(mask, (51, 51), 0)
            mask = np.stack([mask, mask, mask], axis=2)
            
            # 混合
            blended = (face_result * mask + face_roi * (1 - mask)).astype(np.uint8)
            
            # 应用结果
            result[y1:y2, x1:x2] = blended
        
        return result
    
    def process_video_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        处理视频单帧
        
        这是主入口函数
        """
        return self.apply_beauty_filter(frame)


# 向后兼容的简单接口
def apply_beauty_filter_simple(image: np.ndarray, 
                               strength: float = 0.7) -> np.ndarray:
    """
    简单磨皮接口（向后兼容）
    
    使用双边滤波，不涉及人脸检测
    """
    filter_obj = AdvancedBeautyFilter(
        smooth_strength=strength,
        pore_reduction=0.5
    )
    return filter_obj.apply_beauty_filter(image)
