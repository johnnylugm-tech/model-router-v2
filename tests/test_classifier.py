"""Tests for classifier.py"""
import sys
sys.path.insert(0, '/workspace/model-router/src')

from classifier import TaskClassifier, TaskType

def test_classifier_code_generation():
    """Test code generation classification"""
    classifier = TaskClassifier()
    task = "幫我寫一個Python函數"
    result = classifier.classify(task)
    assert result.task_type == TaskType.CODE_GENERATION
    print("✅ test_classifier_code_generation passed")

def test_classifier_translation():
    """Test translation classification"""
    classifier = TaskClassifier()
    task = "翻譯這段文章"
    result = classifier.classify(task)
    assert result.task_type == TaskType.TRANSLATION
    print("✅ test_classifier_translation passed")

def test_classifier_conversation():
    """Test conversation classification"""
    classifier = TaskClassifier()
    task = "你好嗎？"
    result = classifier.classify(task)
    assert result.task_type == TaskType.CONVERSATION
    print("✅ test_classifier_conversation passed")

if __name__ == "__main__":
    test_classifier_code_generation()
    test_classifier_translation()
    test_classifier_conversation()
    print("\n✅ All tests passed!")
