"""
Fingerprint - 视频指纹去重 (完整实现)
使用感知哈希 (pHash) + 帧特征检测重复/相似片段
"""

import sqlite3
import hashlib
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Set, Tuple
import json


class VideoHasher:
    """视频感知哈希计算"""
    
    @staticmethod
    def compute_frame_phash(frame: np.ndarray, hash_size: int = 16) -> str:
        """
        计算单帧的感知哈希 (pHash)
        
        Args:
            frame: BGR 格式的视频帧
            hash_size: 哈希尺寸（默认 16x16）
        
        Returns:
            str: 十六进制哈希字符串
        """
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 缩放到 hash_size x hash_size
        resized = cv2.resize(gray, (hash_size, hash_size))
        
        # 计算 DCT（离散余弦变换）
        dct = cv2.dct(np.float32(resized))
        
        # 取低频部分（左上角 8x8）
        dct_low = dct[:8, :8]
        
        # 计算平均值（排除 DC 分量）
        avg = (dct_low.sum() - dct_low[0, 0]) / 63
        
        # 生成哈希：大于平均值为 1，否则为 0
        diff = dct_low > avg
        
        # 转换为十六进制字符串
        hash_bits = diff.flatten()
        hash_hex = ''.join(
            format(int(''.join('1' if b else '0' for b in hash_bits[i:i+4]), 2), 'x')
            for i in range(0, len(hash_bits), 4)
        )
        
        return hash_hex
    
    @staticmethod
    def compute_video_fingerprint(video_path: str, 
                                  sample_interval: float = 1.0) -> Dict:
        """
        计算视频的整体指纹
        
        Args:
            video_path: 视频文件路径
            sample_interval: 采样间隔（秒）
        
        Returns:
            Dict: 包含帧哈希列表和综合指纹
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        frame_hashes = []
        sample_indices = range(0, total_frames, int(fps * sample_interval))
        
        for idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                phash = VideoHasher.compute_frame_phash(frame)
                timestamp = idx / fps
                frame_hashes.append({
                    'timestamp': timestamp,
                    'phash': phash
                })
        
        cap.release()
        
        # 生成综合指纹（所有帧哈希的聚合）
        combined_hash = hashlib.md5(
            json.dumps(frame_hashes, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        return {
            'video_path': video_path,
            'duration': duration,
            'total_frames': total_frames,
            'sampled_frames': len(frame_hashes),
            'frame_hashes': frame_hashes,
            'combined_hash': combined_hash
        }
    
    @staticmethod
    def hamming_distance(hash1: str, hash2: str) -> int:
        """计算两个哈希的汉明距离"""
        if len(hash1) != len(hash2):
            return float('inf')
        
        # 转换为二进制
        bin1 = bin(int(hash1, 16))[2:].zfill(64)
        bin2 = bin(int(hash2, 16))[2:].zfill(64)
        
        return sum(c1 != c2 for c1, c2 in zip(bin1, bin2))
    
    @staticmethod
    def is_similar(hash1: str, hash2: str, threshold: int = 5) -> bool:
        """判断两个视频是否相似"""
        return VideoHasher.hamming_distance(hash1, hash2) <= threshold


class FingerprintDB:
    """视频指纹数据库管理"""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            # 视频指纹表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    combined_hash TEXT NOT NULL,
                    duration REAL,
                    file_size INTEGER,
                    width INTEGER,
                    height INTEGER,
                    fps REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 帧哈希表（用于精确匹配片段）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS frame_hashes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    phash TEXT NOT NULL,
                    FOREIGN KEY (video_id) REFERENCES video_fingerprints(id)
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_combined_hash 
                ON video_fingerprints(combined_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_frame_phash 
                ON frame_hashes(phash)
            """)
    
    def add_video(self, fingerprint: Dict) -> int:
        """添加视频指纹到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取视频信息
            cap = cv2.VideoCapture(fingerprint['video_path'])
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            file_size = Path(fingerprint['video_path']).stat().st_size
            
            # 插入视频记录
            cursor = conn.execute("""
                INSERT OR REPLACE INTO video_fingerprints 
                (file_path, file_name, combined_hash, duration, file_size, width, height, fps)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fingerprint['video_path'],
                Path(fingerprint['video_path']).name,
                fingerprint['combined_hash'],
                fingerprint['duration'],
                file_size,
                width,
                height,
                fps
            ))
            
            video_id = cursor.lastrowid
            
            # 插入帧哈希
            for frame in fingerprint['frame_hashes']:
                conn.execute("""
                    INSERT OR REPLACE INTO frame_hashes 
                    (video_id, timestamp, phash)
                    VALUES (?, ?, ?)
                """, (video_id, frame['timestamp'], frame['phash']))
            
            return video_id
    
    def find_duplicates(self, threshold: int = 5) -> List[List[str]]:
        """
        查找重复视频组
        
        Args:
            threshold: 汉明距离阈值（越小越严格）
        
        Returns:
            List[List[str]]: 重复文件组列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT file_path, combined_hash FROM video_fingerprints"
            )
            videos = cursor.fetchall()
        
        # 使用汉明距离聚类
        hasher = VideoHasher()
        groups: List[List[str]] = []
        processed: Set[str] = set()
        
        for path1, hash1 in videos:
            if path1 in processed:
                continue
            
            group = [path1]
            processed.add(path1)
            
            for path2, hash2 in videos:
                if path2 in processed:
                    continue
                
                if hasher.is_similar(hash1, hash2, threshold):
                    group.append(path2)
                    processed.add(path2)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def find_similar_segments(self, phash: str, 
                             threshold: int = 3) -> List[Dict]:
        """
        查找包含相似片段的视频
        
        Args:
            phash: 查询的帧哈希
            threshold: 汉明距离阈值
        
        Returns:
            List[Dict]: 匹配的视频片段列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT v.file_path, v.duration, f.timestamp, f.phash
                FROM frame_hashes f
                JOIN video_fingerprints v ON f.video_id = v.id
            """)
            frames = cursor.fetchall()
        
        hasher = VideoHasher()
        matches = []
        
        for file_path, duration, timestamp, frame_phash in frames:
            distance = hasher.hamming_distance(phash, frame_phash)
            if distance <= threshold:
                matches.append({
                    'file_path': file_path,
                    'duration': duration,
                    'timestamp': timestamp,
                    'similarity': 1 - (distance / 64)  # 转换为相似度
                })
        
        return sorted(matches, key=lambda x: x['similarity'], reverse=True)
    
    def deduplicate(self, file_list: List[str], 
                   threshold: int = 5) -> List[str]:
        """
        去重文件列表，保留每组第一个
        
        Args:
            file_list: 原始文件列表
            threshold: 相似度阈值
        
        Returns:
            List[str]: 去重后的文件列表
        """
        duplicates = self.find_duplicates(threshold)
        duplicate_set: Set[str] = set()
        
        for group in duplicates:
            # 保留第一个，其余标记为重复
            for path in group[1:]:
                duplicate_set.add(path)
        
        return [f for f in file_list if f not in duplicate_set]
    
    def scan_and_index(self, directory: Path, 
                       extensions: List[str] = None,
                       progress_callback = None) -> int:
        """
        扫描目录并建立索引
        
        Args:
            directory: 扫描目录
            extensions: 视频文件扩展名列表
            progress_callback: 进度回调函数(current, total)
        
        Returns:
            int: 索引的视频数量
        """
        if extensions is None:
            extensions = ['.mp4', '.mov', '.avi', '.mkv', '.m4v']
        
        # 查找所有视频文件
        video_files = []
        for ext in extensions:
            video_files.extend(directory.rglob(f"*{ext}"))
        
        total = len(video_files)
        indexed = 0
        hasher = VideoHasher()
        
        for i, video_path in enumerate(video_files):
            try:
                # 计算指纹
                fingerprint = hasher.compute_video_fingerprint(
                    str(video_path),
                    sample_interval=2.0  # 每 2 秒采样一帧
                )
                
                # 添加到数据库
                self.add_video(fingerprint)
                indexed += 1
                
                if progress_callback:
                    progress_callback(i + 1, total)
                
            except Exception as e:
                print(f"Error indexing {video_path}: {e}")
        
        return indexed
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*), SUM(file_size), SUM(duration) "
                "FROM video_fingerprints"
            )
            count, total_size, total_duration = cursor.fetchone()
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM frame_hashes"
            )
            frame_count = cursor.fetchone()[0]
        
        return {
            'video_count': count or 0,
            'total_size_gb': (total_size or 0) / (1024**3),
            'total_duration_hours': (total_duration or 0) / 3600,
            'frame_samples': frame_count or 0
        }
