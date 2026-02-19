"""
Semantic Index - CLIP 语义索引 (完整实现)
使用 OpenAI CLIP 模型进行视频内容语义理解
"""

import json
import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from PIL import Image
import cv2


class CLIPEncoder:
    """CLIP 编码器封装"""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        """
        初始化 CLIP 模型
        
        Args:
            model_name: CLIP 模型名称
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 延迟加载模型
        self._model = None
        self._processor = None
    
    @property
    def model(self):
        """懒加载模型"""
        if self._model is None:
            try:
                from transformers import CLIPModel, CLIPProcessor
                
                self._processor = CLIPProcessor.from_pretrained(self.model_name)
                self._model = CLIPModel.from_pretrained(self.model_name).to(self.device)
                self._model.eval()
                
                print(f"CLIP model loaded on {self.device}")
            except Exception as e:
                print(f"Error loading CLIP model: {e}")
                raise
        
        return self._model
    
    @property
    def processor(self):
        """懒加载处理器"""
        if self._processor is None:
            from transformers import CLIPProcessor
            self._processor = CLIPProcessor.from_pretrained(self.model_name)
        return self._processor
    
    def encode_image(self, image: np.ndarray) -> np.ndarray:
        """
        编码图像为向量
        
        Args:
            image: BGR 格式的 numpy 数组
        
        Returns:
            np.ndarray: 512 维特征向量
        """
        # BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # 预处理
        inputs = self.processor(images=pil_image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 编码
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
        
        # 归一化
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        return image_features.cpu().numpy().flatten()
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        编码文本为向量
        
        Args:
            text: 查询文本
        
        Returns:
            np.ndarray: 512 维特征向量
        """
        inputs = self.processor(text=text, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
        
        # 归一化
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        return text_features.cpu().numpy().flatten()
    
    def compute_similarity(self, image_vec: np.ndarray, 
                          text_vec: np.ndarray) -> float:
        """计算图像和文本的相似度"""
        return float(np.dot(image_vec, text_vec))


class SemanticIndex:
    """语义索引管理器"""
    
    def __init__(self, index_path: Path, model_name: str = None):
        """
        初始化语义索引
        
        Args:
            index_path: 索引存储路径
            model_name: CLIP 模型名称
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        model = model_name or "openai/clip-vit-base-patch32"
        self.encoder = CLIPEncoder(model)
        
        # 加载或创建索引
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict] = {}
        self._load_index()
    
    def _load_index(self):
        """加载已有索引"""
        vectors_file = self.index_path / "vectors.npy"
        metadata_file = self.index_path / "metadata.json"
        
        if vectors_file.exists() and metadata_file.exists():
            try:
                # 加载向量
                data = np.load(vectors_file, allow_pickle=True).item()
                self.vectors = {k: v for k, v in data.items()}
                
                # 加载元数据
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                
                print(f"Loaded {len(self.vectors)} indexed clips")
            except Exception as e:
                print(f"Error loading index: {e}")
    
    def _save_index(self):
        """保存索引到磁盘"""
        vectors_file = self.index_path / "vectors.npy"
        metadata_file = self.index_path / "metadata.json"
        
        # 保存向量
        np.save(vectors_file, self.vectors)
        
        # 保存元数据
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def extract_keyframes(self, video_path: str, 
                         num_frames: int = 5) -> List[Tuple[np.ndarray, float]]:
        """
        提取视频关键帧
        
        Args:
            video_path: 视频路径
            num_frames: 提取帧数
        
        Returns:
            List[Tuple[np.ndarray, float]]: (帧图像, 时间戳) 列表
        """
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        # 均匀采样
        indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        keyframes = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                timestamp = idx / fps
                keyframes.append((frame, timestamp))
        
        cap.release()
        return keyframes
    
    def index_video(self, video_path: str, 
                   clip_duration: float = 10.0) -> List[str]:
        """
        为视频建立语义索引
        
        Args:
            video_path: 视频路径
            clip_duration: 每个片段的时长（秒）
        
        Returns:
            List[str]: 生成的 clip ID 列表
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()
        
        clip_ids = []
        num_clips = int(duration / clip_duration) + 1
        
        for i in range(num_clips):
            start_time = i * clip_duration
            end_time = min((i + 1) * clip_duration, duration)
            
            if end_time - start_time < 1.0:  # 跳过太短片段
                continue
            
            # 提取中间帧作为代表
            mid_time = (start_time + end_time) / 2
            frame = self._extract_frame(video_path, mid_time)
            
            if frame is None:
                continue
            
            # 编码为向量
            try:
                vector = self.encoder.encode_image(frame)
            except Exception as e:
                print(f"Error encoding frame: {e}")
                continue
            
            # 生成 clip ID
            clip_id = f"{Path(video_path).stem}_{i:04d}"
            
            # 存储
            self.vectors[clip_id] = vector
            self.metadata[clip_id] = {
                'file_path': video_path,
                'file_name': Path(video_path).name,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'mid_time': mid_time
            }
            
            clip_ids.append(clip_id)
        
        return clip_ids
    
    def _extract_frame(self, video_path: str, 
                      timestamp: float) -> Optional[np.ndarray]:
        """提取指定时间戳的帧"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_idx = int(timestamp * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        
        return frame if ret else None
    
    def search(self, query: str, top_k: int = 5,
              min_duration: float = 3.0) -> List[Dict]:
        """
        语义搜索
        
        Args:
            query: 查询文本（如"山顶日落"）
            top_k: 返回前 K 个结果
            min_duration: 最小片段时长
        
        Returns:
            List[Dict]: 匹配结果列表
        """
        if not self.vectors:
            return []
        
        # 编码查询文本
        query_vec = self.encoder.encode_text(query)
        
        # 计算相似度
        similarities = []
        for clip_id, vec in self.vectors.items():
            meta = self.metadata[clip_id]
            
            # 过滤短片段
            if meta['duration'] < min_duration:
                continue
            
            similarity = float(np.dot(query_vec, vec))
            similarities.append((clip_id, similarity))
        
        # 排序并返回前 K
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for clip_id, score in similarities[:top_k]:
            meta = self.metadata[clip_id].copy()
            meta['clip_id'] = clip_id
            meta['similarity_score'] = score
            results.append(meta)
        
        return results
    
    def batch_index(self, video_files: List[str],
                   progress_callback = None) -> int:
        """
        批量索引视频文件
        
        Args:
            video_files: 视频文件路径列表
            progress_callback: 进度回调函数(current, total)
        
        Returns:
            int: 索引的片段数量
        """
        total_clips = 0
        
        for i, video_path in enumerate(video_files):
            try:
                clip_ids = self.index_video(video_path)
                total_clips += len(clip_ids)
                
                if progress_callback:
                    progress_callback(i + 1, len(video_files))
                
            except Exception as e:
                print(f"Error indexing {video_path}: {e}")
        
        # 保存索引
        self._save_index()
        
        return total_clips
    
    def get_stats(self) -> Dict:
        """获取索引统计"""
        return {
            'indexed_clips': len(self.vectors),
            'indexed_videos': len(set(
                meta['file_path'] for meta in self.metadata.values()
            ))
        }
