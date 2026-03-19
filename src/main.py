#!/usr/bin/env python3
"""
Model Router CLI
智慧模型路由系統命令行工具
"""

import sys
import argparse
import logging
from typing import Optional

from .classifier import TaskClassifier, TaskType
from .registry import ModelRegistry
from .router import RouterEngine, RouterConfig
from .cost_tracker import CostTracker


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
    verbose: bool
) -> int:
    """處理路由請求"""
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
        description="Model Router - 智慧模型路由系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python main.py --task "帮我写一个Python函数"
  python main.py --task "review 代码" --budget low
  python main.py --list-models
  python main.py --task "分析这份数据" --model gpt-4 --verbose
        """
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
    
    args = parser.parse_args()
    
    # 設置日誌
    setup_logging(args.verbose)
    
    # 初始化組件
    config = RouterConfig()
    classifier = TaskClassifier()
    registry = ModelRegistry()
    router = RouterEngine(classifier, registry, config)
    tracker = CostTracker()
    
    # 處理命令
    if args.list_models:
        print_model_list(registry)
        return 0
    
    if args.list_tasks:
        print_task_types(classifier)
        return 0
    
    if not args.task:
        parser.print_help()
        print("\n\n💡 提示: 請使用 --task 指定任務描述")
        return 1
    
    # 執行路由
    return handle_route(
        router,
        args.task,
        args.model,
        args.budget,
        tracker,
        args.verbose
    )


if __name__ == "__main__":
    sys.exit(main())
