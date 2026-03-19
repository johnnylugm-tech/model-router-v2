#!/usr/bin/env python3
"""
Model Router CLI
智慧模型路由系統命令行工具 v2.0
"""

import sys
import os

# 將 src 目錄添加到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
import logging
from typing import Optional

from src.classifier import TaskClassifier, TaskType
from src.registry import ModelRegistry
from src.router import RouterEngine, RouterConfig, TaskAwareRouter
from src.cost_tracker import CostTracker
from src.trends import TrendsAnalyzer
from src.api_client import APIClientFactory, test_api_client
from src.learning import RoutingLearner
from src.regression_detector import RegressionDetector
from src.config import get_config, ConfigLoader
from src.failover import AutoFailoverRouter, create_failover_router, AllProvidersFailedError
from src.semantic_cache import SemanticCache

VERSION = "3.0.0"


def setup_logging(verbose: bool = False) -> None:
    """設置日誌"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )


def print_model_list(registry: ModelRegistry) -> None:
    """打印模型列表"""
    models = registry.list_models()
    
    print("\n" + "=" * 80)
    print("📋 可用模型列表")
    print("=" * 80)
    
    # 按提供商分組
    providers = {}
    for model in models:
        provider = registry.get_provider_name(model.provider)
        if provider not in providers:
            providers[provider] = []
        providers[provider].append(model)
    
    for provider, provider_models in providers.items():
        print(f"\n🔹 {provider}")
        print("-" * 60)
        
        for model in provider_models:
            print(f"  ├─ {model.name} ({model.id})")
            print(f"  │    成本: ${model.cost_per_1k_input:.4f}/in, ${model.cost_per_1k_output:.4f}/out")
            print(f"  │    延遲: ~{model.latency_ms}ms | 上下文: {model.context_window:,} tokens")
            print(f"  │    擅長: {', '.join(model.strengths[:3])}")
    
    print("\n" + "=" * 80)


def print_task_types(classifier: TaskClassifier) -> None:
    """打印任務類型"""
    print("\n" + "=" * 60)
    print("📌 支援的任務類型")
    print("=" * 60)
    
    for task_type in TaskType:
        if task_type == TaskType.UNKNOWN:
            continue
        name = classifier.get_task_type_name(task_type)
        print(f"  • {name:20s} → {task_type.value}")
    
    print("=" * 60)


def handle_route(
    router: RouterEngine,
    task: str,
    model: Optional[str],
    budget: str,
    tracker: CostTracker,
    verbose: bool,
    cache: SemanticCache
) -> int:
    """處理路由請求"""
    # v2.2: 語意快取 - 先檢查快取
    cached_result = cache.get(task)
    if cached_result:
        print("\n" + "=" * 60)
        print("💾 路由結果 (從快取返回)")
        print("=" * 60)
        print(cached_result)
        print("=" * 60)
        return 0
    
    try:
        # ReAct: 推理 -> 行動 -> 觀察 -> 輸出
        result = router.route(task, budget, model)
        
        print("\n" + "=" * 60)
        print("🧭 路由結果")
        print("=" * 60)
        
        print(f"\n🤖 推薦模型: {result.model_name}")
        print(f"📦 模型 ID: {result.model_id}")
        print(f"🏢 提供商: {result.provider}")
        print(f"💰 預估成本: ${result.estimated_cost:.4f}/1K tokens")
        print(f"⏱️  預估延遲: ~{result.estimated_latency}ms")
        print(f"📊 置信度: {result.confidence * 100:.0f}%")
        
        if verbose:
            print("\n" + "-" * 60)
            print("🧠 推理過程:")
            print("-" * 60)
            print(result.reasoning)
        
        print("=" * 60)
        
        # 建構結果字串用於快取
        result_str = f"""🤖 推薦模型: {result.model_name}
📦 模型 ID: {result.model_id}
🏢 提供商: {result.provider}
💰 預估成本: ${result.estimated_cost:.4f}/1K tokens
⏱️  預估延遲: ~{result.estimated_latency}ms
📊 置信度: {result.confidence * 100:.0f}%"""
        
        # v2.2: 存入語意快取
        cache.set(task, result_str)
        
        # 記錄請求 (估算 tokens)
        tracker.record_request(
            model_id=result.model_id,
            task_type=task,
            input_tokens=len(task) // 4,  # 估算
            output_tokens=100,  # 估算
            cost=result.estimated_cost,
            latency_ms=result.estimated_latency,
            success=True
        )
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        
        # 記錄失敗請求
        tracker.record_request(
            model_id="unknown",
            task_type=task,
            success=False,
            error=str(e)
        )
        
        return 1


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        description=f"Model Router v{VERSION} - 智慧模型路由系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python main.py --task "帮我写一个Python函数"
  python main.py --task "review 代码" --budget low
  python main.py --list-models
  python main.py --task "分析这份数据" --model gpt-4 --verbose
  python main.py --trends
  python main.py --test-api --provider openai
  python main.py --learning-status
  python main.py --regression-check
        """
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="顯示版本號"
    )
    
    parser.add_argument(
        "--task", "-t",
        type=str,
        help="任務描述"
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        help="指定模型 ID (例如: gpt-4o, claude-3-5-sonnet)"
    )
    
    parser.add_argument(
        "--budget", "-b",
        type=str,
        default="auto",
        choices=["low", "balanced", "high", "auto"],
        help="預算等級: low(低成本), balanced(平衡), high(高性能), auto(自動)"
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="列出所有可用模型"
    )
    
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="列出所有支援的任務類型"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="顯示詳細推理過程"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="顯示成本統計"
    )
    
    # v2.0 新功能
    parser.add_argument(
        "--trends",
        action="store_true",
        help="顯示趨勢分析報告"
    )
    
    parser.add_argument(
        "--test-api",
        action="store_true",
        help="測試 API 客戶端連接"
    )
    
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic", "minimax", "gemini"],
        help="API 提供商 (用於 --test-api)"
    )
    
    parser.add_argument(
        "--learning-status",
        action="store_true",
        help="顯示路由學習狀態"
    )
    
    parser.add_argument(
        "--regression-check",
        action="store_true",
        help="執行 LLM 迴歸檢測"
    )
    
    # v2.1 新功能
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="顯示目前配置"
    )
    
    parser.add_argument(
        "--test-failover",
        action="store_true",
        help="測試 Failover 功能"
    )
    
    parser.add_argument(
        "--fallback",
        type=str,
        help="指定 Fallback 模型 (逗號分隔，例如: gpt-4o,gemini-flash)"
    )
    
    # v2.2 新功能：語意快取
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="顯示語意快取統計"
    )
    
    parser.add_argument(
        "--cache-clear",
        action="store_true",
        help="清除語意快取"
    )
    
    args = parser.parse_args()
    
    # 顯示版本
    if args.version:
        print(f"Model Router v{VERSION}")
        return 0
    
    # 設置日誌
    setup_logging(args.verbose)
    
    # 初始化組件
    config = RouterConfig()
    classifier = TaskClassifier()
    registry = ModelRegistry()
    router = RouterEngine(classifier, registry, config)
    tracker = CostTracker()
    
    # v2.2: 語意快取
    cache = SemanticCache(similarity_threshold=0.9)
    
    # 處理命令
    if args.list_models:
        print_model_list(registry)
        return 0
    
    if args.list_tasks:
        print_task_types(classifier)
        return 0
    
    # v2.0: 趨勢分析
    if args.trends:
        print(f"\n📈 Model Router v{VERSION} - 趨勢分析")
        print("=" * 60)
        trends = TrendsAnalyzer()
        print(trends.generate_report(days=7))
        return 0
    
    # v2.0: API 測試
    if args.test_api:
        if not args.provider:
            print("❌ 錯誤: 請使用 --provider 指定 API 提供商")
            print("可用提供商: openai, anthropic, minimax, gemini")
            return 1
        
        print(f"\n🔌 測試 API: {args.provider}")
        print("-" * 40)
        result = test_api_client(args.provider)
        
        if result["status"] == "success":
            print(f"✅ 連接成功!")
            print(f"可用模型:")
            for model in result.get("models", []):
                print(f"  • {model['name']} ({model['id']}) - Context: {model['context_window']:,}")
            print(f"請求統計: {result['stats']}")
        else:
            print(f"❌ 連接失敗: {result.get('error', 'Unknown error')}")
        
        return 0
    
    # v2.0: 學習狀態
    if args.learning_status:
        print(f"\n🧠 Model Router v{VERSION} - 路由學習")
        print("=" * 60)
        learner = RoutingLearner()
        print(learner.get_status_summary())
        return 0
    
    # v2.0: 迴歸檢測
    if args.regression_check:
        print(f"\n🔍 Model Router v{VERSION} - 迴歸檢測")
        detector = RegressionDetector()
        print(detector.check_all_models())
        return 0
    
    # v2.1: 顯示配置
    if args.show_config:
        print(f"\n⚙️ Model Router v{VERSION} - 當前配置")
        print("=" * 60)
        config_loader = ConfigLoader()
        print(config_loader.to_yaml())
        return 0
    
    # v2.1: 測試 Failover
    if args.test_failover:
        print(f"\n🔄 Model Router v{VERSION} - Failover 測試")
        print("=" * 60)
        
        # 模擬 Failover 場景
        providers = ["gpt-4o-mini", "gpt-4o", "gemini-1.5-flash"]
        
        def mock_call(provider, task):
            """模擬 API 調用"""
            print(f"  嘗試調用: {provider}")
            # 模擬第二個 provider 會失敗
            if provider == providers[1]:
                from src.failover import RateLimitError
                raise RateLimitError("Rate limit exceeded", retry_after=1.0)
            return {"status": "success", "provider": provider}
        
        try:
            failover = create_failover_router()
            result = failover.route_with_failover(
                task="測試任務",
                providers=providers,
                call_func=mock_call
            )
            print(f"\n✅ Failover 成功! 使用: {result['provider']}")
        except AllProvidersFailedError as e:
            print(f"\n❌ 所有 Provider 都失敗: {e}")
        
        # 顯示 Provider 狀態
        print("\n📊 Provider 狀態:")
        for provider, status in failover.get_provider_status().items():
            health = "✅" if status["is_healthy"] else "❌"
            print(f"  {health} {provider}: {status['error_count']} errors, "
                  f"{status['success_count']} successes")
        
        return 0
    
    # v2.2: 語意快取命令
    if args.cache_stats:
        print(f"\n💾 Model Router v{VERSION} - 語意快取統計")
        print("=" * 60)
        stats = cache.stats()
        print(f"快取大小: {stats['size']} 筆")
        print(f"相似度閾值: 0.9")
        print("=" * 60)
        return 0
    
    if args.cache_clear:
        print(f"\n🗑️ Model Router v{VERSION} - 清除語意快取")
        print("=" * 60)
        cache.clear()
        print("✅ 快取已清除!")
        print("=" * 60)
        return 0
    
    if not args.task:
        parser.print_help()
        print(f"\n\n💡 提示: 請使用 --task 指定任務描述")
        print(f"\n📌 v{VERSION} 新功能:")
        print("   --trends           趨勢分析報告")
        print("   --test-api         測試 API 連接")
        print("   --learning-status  路由學習狀態")
        print("   --regression-check 迴歸檢測")
        print("   --show-config      顯示配置 (v2.1)")
        print("   --test-failover    測試 Failover (v2.1)")
        print("   --fallback         指定 Fallback 模型 (v2.1)")
        print("   --cache-stats      顯示快取統計 (v2.2)")
        print("   --cache-clear      清除快取 (v2.2)")
        return 1
    
    # 執行路由
    return handle_route(
        router,
        args.task,
        args.model,
        args.budget,
        tracker,
        args.verbose,
        cache
    )


if __name__ == "__main__":
    sys.exit(main())
