import hashlib
from typing import Optional, Dict, Any
import re


class SemanticCache:
    """語意快取 - 根據相似度返回快取結果
    
    用於減少 API 調用次數，節省成本。
    
    Attributes:
        similarity_threshold: 相似度閾值，默認 0.9
        cache: 快取存儲
    """
    
    def __init__(self, similarity_threshold: float = 0.9):
        """初始化語意快取
        
        Args:
            similarity_threshold: 相似度閾值，範圍 0-1
        """
        self.cache: Dict[str, Any] = {}
        self.similarity_threshold = similarity_threshold
    
    def _normalize(self, text: str) -> str:
        """標準化文本
        
        將文本轉換為小寫並移除多餘空格。
        
        Args:
            text: 輸入文本
            
        Returns:
            標準化後的文本
        """
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _get_key(self, text: str) -> str:
        """生成快取鍵
        
        使用 SHA256 哈希生成固定的快取鍵。
        
        Args:
            text: 輸入文本
            
        Returns:
            16位十六進制哈希鍵
        """
        normalized = self._normalize(text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """計算相似度
        
        使用 Jaccard 相似度係數計算兩個文本的相似度。
        
        Args:
            text1: 第一個文本
            text2: 第二個文本
            
        Returns:
            相似度分數，範圍 0-1
        """
        # 使用字詞重疊計算
        words1 = set(self._normalize(text1).split())
        words2 = set(self._normalize(text2).split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0
    
    def get(self, prompt: str) -> Optional[str]:
        """獲取快取結果
        
        先嘗試精確匹配，若無則進行相似度匹配。
        
        Args:
            prompt: 查詢文本
            
        Returns:
            快取的回覆，若無匹配則返回 None
        """
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
        """設置快取
        
        將查詢和回覆存入快取。
        
        Args:
            prompt: 查詢文本
            response: 回覆文本
        """
        key = self._get_key(prompt)
        self.cache[key] = response
    
    def clear(self):
        """清除快取
        
        清空所有快取數據。
        """
        self.cache.clear()
    
    def stats(self) -> Dict[str, int]:
        """快取統計
        
        Returns:
            包含快取大小的字典
        """
        return {"size": len(self.cache)}
