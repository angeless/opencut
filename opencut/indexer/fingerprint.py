"""
Fingerprint - 视频指纹去重
使用感知哈希 (pHash) 检测重复/相似片段
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Set


class FingerprintDB:
    """视频指纹数据库"""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fingerprints (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT UNIQUE NOT NULL,
                    phash TEXT NOT NULL,
                    duration REAL,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_phash 
                ON fingerprints(phash)
            """)
    
    def add_fingerprint(self, file_path: str, phash: str, 
                        duration: float = 0, file_size: int = 0):
        """添加视频指纹"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO fingerprints 
                (file_path, phash, duration, file_size)
                VALUES (?, ?, ?, ?)
            """, (file_path, phash, duration, file_size))
    
    def find_duplicates(self, threshold: float = 0.9) -> List[List[str]]:
        """
        查找重复视频
        
        Args:
            threshold: 相似度阈值
        
        Returns:
            List[List[str]]: 重复文件组列表
        """
        # TODO: 实现汉明距离计算
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT file_path, phash FROM fingerprints")
            rows = cursor.fetchall()
        
        # 按 phash 分组（简化版）
        groups: Dict[str, List[str]] = {}
        for file_path, phash in rows:
            if phash not in groups:
                groups[phash] = []
            groups[phash].append(file_path)
        
        # 返回有重复的组
        return [files for files in groups.values() if len(files) > 1]
    
    def deduplicate(self, file_list: List[str]) -> List[str]:
        """
        去重文件列表
        
        Args:
            file_list: 原始文件列表
        
        Returns:
            List[str]: 去重后的文件列表（保留每组第一个）
        """
        # 加载所有指纹
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT file_path, phash FROM fingerprints"
            )
            fingerprint_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        seen_hashes: Set[str] = set()
        unique_files: List[str] = []
        
        for file_path in file_list:
            phash = fingerprint_map.get(file_path)
            if phash and phash not in seen_hashes:
                seen_hashes.add(phash)
                unique_files.append(file_path)
            elif not phash:
                # 未索引的文件，保留
                unique_files.append(file_path)
        
        return unique_files
    
    def scan_and_index(self, directory: Path, 
                       extensions: List[str] = None):
        """扫描目录并建立指纹索引"""
        if extensions is None:
            extensions = ['.mp4', '.mov', '.avi', '.mkv']
        
        # TODO: 实现视频指纹提取
        print(f"Scanning {directory} for video files...")
        pass
