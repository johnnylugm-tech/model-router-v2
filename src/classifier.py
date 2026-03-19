"""
任務分類器 - Task Classifier
識別任務類型：CODE_GENERATION, CODE_REVIEW, TEXT_SUMMARIZATION, 
TRANSLATION, CONVERSATION, IMAGE_UNDERSTANDING, DATA_ANALYSIS
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple


class TaskType(Enum):
    """支援的任務類型"""
    CODE_GENERATION = "CODE_GENERATION"
    CODE_REVIEW = "CODE_REVIEW"
    TEXT_SUMMARIZATION = "TEXT_SUMMARIZATION"
    TRANSLATION = "TRANSLATION"
    CONVERSATION = "CONVERSATION"
    IMAGE_UNDERSTANDING = "IMAGE_UNDERSTANDING"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    UNKNOWN = "UNKNOWN"


@dataclass
class ClassificationResult:
    """分類結果"""
    task_type: TaskType
    confidence: float  # 0.0 - 1.0
    keywords_matched: List[str]


class TaskClassifier:
    """任務分類器 - 使用關鍵詞匹配識別任務類型"""
    
    # 任務類型關鍵詞映射
    TASK_KEYWORDS: Dict[TaskType, List[str]] = {
        TaskType.CODE_GENERATION: [
            "写", "生成", "创建", "实现", "编写", "code", "write", "create", 
            "function", "class", "程序", "代码", "script", "开发", "build",
            "python", "javascript", "java", "api", "算法"
        ],
        TaskType.CODE_REVIEW: [
            "review", "审查", "检查", "优化", "改进", "refactor", "重构",
            "debug", "调试", "bug", "问题", "错误", "漏洞", "security",
            "性能", "代码审查"
        ],
        TaskType.TEXT_SUMMARIZATION: [
            "总结", "摘要", "概括", "summarize", "summary", "abstract",
            "提取", "要点", "核心", "conclusion", "概括"
        ],
        TaskType.TRANSLATION: [
            "翻译", "translate", "译", "convert", "转换语言", "language",
            "英文", "中文", "英文版", "中文版", "英文翻译"
        ],
        TaskType.CONVERSATION: [
            "对话", "聊天", "conversation", "chat", "回答", "问题", "帮忙",
            "解释", "说明", "什么是", "怎么", "如何", "为什么", "你好",
            "介绍", "请", "告诉", "帮我", "我想", "问一下", "问个问题"
        ],
        TaskType.IMAGE_UNDERSTANDING: [
            "图片", "图像", "照片", "图", "image", "picture", "photo",
            "看图", "描述图片", "图片内容", "截图", "图表"
        ],
        TaskType.DATA_ANALYSIS: [
            "分析", "数据", "统计", "分析", "analyze", "analysis", "data",
            "report", "报告", "趋势", "指标", "计算", "报表", "可视化"
        ],
    }
    
    def __init__(self):
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """構建關鍵詞索引以提高匹配效率"""
        self._keyword_to_tasks: Dict[str, List[TaskType]] = {}
        
        for task_type, keywords in self.TASK_KEYWORDS.items():
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in self._keyword_to_tasks:
                    self._keyword_to_tasks[keyword_lower] = []
                self._keyword_to_tasks[keyword_lower].append(task_type)
    
    def classify(self, task: str) -> ClassificationResult:
        """
        ReAct Pattern: Reasoning -> Action -> Observation -> Output
        
        Args:
            task: 任務描述
            
        Returns:
            ClassificationResult: 分類結果
        """
        # Reasoning: 分析任務描述
        # Action: 匹配關鍵詞
        # Observation: 計算匹配分數
        # Output: 返回分類結果
        
        if not task or not task.strip():
            return ClassificationResult(
                task_type=TaskType.UNKNOWN,
                confidence=0.0,
                keywords_matched=[]
            )
        
        task_lower = task.lower()
        
        # 支持中英文混合匹配 - 檢查每個關鍵詞是否出現在任務中
        matched_keywords = []
        
        for keyword, task_types in self._keyword_to_tasks.items():
            if keyword in task_lower:
                for task_type in task_types:
                    matched_keywords.append(keyword)
        
        # 去重
        matched_keywords = list(set(matched_keywords))
        
        if not matched_keywords:
            return ClassificationResult(
                task_type=TaskType.UNKNOWN,
                confidence=0.0,
                keywords_matched=[]
            )
        
        # 計算每個任務類型的匹配分數
        scores: Dict[TaskType, Tuple[int, List[str]]] = {}
        
        for keyword in matched_keywords:
            for task_type in self._keyword_to_tasks[keyword]:
                if task_type not in scores:
                    scores[task_type] = (0, [])
                current_score, current_keywords = scores[task_type]
                scores[task_type] = (current_score + 1, current_keywords + [keyword])
        
        if not scores:
            return ClassificationResult(
                task_type=TaskType.UNKNOWN,
                confidence=0.0,
                keywords_matched=[]
            )
        
        # 選擇得分最高的任務類型
        best_task = max(scores.items(), key=lambda x: x[1][0])
        task_type = best_task[0]
        matched_count, matched_keywords = best_task[1]
        
        # 計算置信度 (基於匹配數量和任務關鍵詞總數)
        total_keywords = len(self.TASK_KEYWORDS[task_type])
        confidence = min(matched_count / max(1, min(3, total_keywords)), 1.0)
        
        # 對於翻譯任務的特別處理
        if task_type == TaskType.TRANSLATION:
            # 檢查是否明確提到語言
            language_keywords = ["英文", "中文", "英语", "汉语", "translate", "翻译"]
            if any(lang in task_lower for lang in language_keywords):
                confidence = min(confidence + 0.2, 1.0)
        
        # 對於代碼相關任務的特別處理
        if task_type in [TaskType.CODE_GENERATION, TaskType.CODE_REVIEW]:
            code_indicators = ["def ", "class ", "function", "()", "{}", "=>", "import "]
            if any(indicator in task for indicator in code_indicators):
                confidence = min(confidence + 0.15, 1.0)
        
        return ClassificationResult(
            task_type=task_type,
            confidence=round(confidence, 2),
            keywords_matched=list(set(matched_keywords))
        )
    
    def get_task_type_name(self, task_type: TaskType) -> str:
        """獲取任務類型的顯示名稱"""
        names = {
            TaskType.CODE_GENERATION: "代碼生成",
            TaskType.CODE_REVIEW: "代碼審查",
            TaskType.TEXT_SUMMARIZATION: "文本摘要",
            TaskType.TRANSLATION: "翻譯",
            TaskType.CONVERSATION: "對話",
            TaskType.IMAGE_UNDERSTANDING: "圖像理解",
            TaskType.DATA_ANALYSIS: "數據分析",
            TaskType.UNKNOWN: "未知",
        }
        return names.get(task_type, "未知")
