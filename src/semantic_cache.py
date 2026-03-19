import hashlib
from typing import Optional, Dict, Any
import re


class SemanticCache:
    """語意快取 - 根據相似度返回快取結果"""
    
    def __init__(self, similarity_threshold: float = 0.9):
        self.cache: Dict[str, Any] = {}
        self.similarity_threshold = similarity_threshold
    
    def _normalize(self, text: str) -> str:
        """標準化文本"""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _get_key(self, text: str) -> str:
        """生成快取鍵"""
        normalized = self._normalize(text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """計算相似度 (簡單實現)"""
        # 使用字詞重疊計算
        words1 = set(self._normalize(text1).split())
        words2 = set(self._normalize(text2).split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0
    
    def get(self, prompt: str) -> Optional[str]:
        """獲取快取結果"""
        key = self._get_key(prompt)
        
        # 精確匹配
        if key in self.cache:
            return self.cache[key]
        
        # 相似匹配
        for cached_prompt, response in self.cache.items():
            if self._calculate_similarity(prompt, cached_prompt) >= self.similarity_threshold:
                return response
        
        return None
    
    def set(self, prompt: str, response: str):
        """設置快取"""
        key = self._get_key(prompt)
        self.cache[key] = response
    
    def clear(self):
        """清除快取"""
        self.cache.clear()
    
    def stats(self) -> Dict[str, int]:
        """快取統計"""
        return {"size": len(self.cache)}
