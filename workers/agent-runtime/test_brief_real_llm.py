"""
测试 Brief Agent 使用真实 LLM

这个脚本会：
1. 创建 Brief Agent 实例
2. 使用真实 LLM 生成 Brief
3. 验证输出格式
4. 显示生成的内容
"""

import os
import sys
import json
from pathlib import Path
from uuid import UUID, uuid4

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    print("⚠ python-dotenv 未安装")

from brief_agent import BriefAgent
from base_agent import StageTaskInput
from llm_service import LLMServiceFactory


def test_brief_agent():
    """测试 Brief Agent"""
    
    print("="*60)
    print("Brief Agent 真实 LLM 测试")
    print("="*60)
    
    # 1. 创建 LLM 服务
    print("\n[1] 创建 LLM 服务...")
    try:
        llm = LLMServiceFactory.create_from_env()
        print(f"✓ LLM 服务创建成功: {llm.model}")
    except Exception as e:
        print(f"✗ LLM 服务创建失败: {e}")
        return False
    
    # 2. 创建 Brief Agent
    print("\n[2] 创建 Brief Agent...")
    agent = BriefAgent(
        db_session=None,  # 不使用数据库
        llm_service=llm,
        validator=None
    )
    print("✓ Brief Agent 创建成功")
    
    # 3. 准备测试输入
    print("\n[3] 准备测试输入...")
    
    raw_material = """
一个年轻的程序员发现自己被困在了一个时间循环中。每天早上7点，他都会在同一个地铁站醒来，
然后经历完全相同的一天。他尝试了各种方法想要打破循环，但都失败了。

直到有一天，他注意到地铁站的一个神秘女孩，她似乎也意识到了时间循环的存在。
两人开始合作，试图找出循环的原因和打破循环的方法。

在调查过程中，他们发现这个循环与一个即将发生的重大事故有关。
如果他们不能在循环中找到真相并阻止事故，整个城市都将陷入危险。
"""
    
    task_input = StageTaskInput(
        workflow_run_id=uuid4(),
        project_id=uuid4(),
        episode_id=uuid4(),
        stage_type="brief",
        input_refs=[],
        locked_refs=[],
        constraints={
            "raw_material": raw_material,
            "platform": "douyin",
            "target_duration_sec": 60,
            "target_audience": "18-35岁年轻观众"
        },
        target_ref_ids=[],
        raw_material=raw_material
    )
    
    print("✓ 测试输入准备完成")
    print(f"  原始素材长度: {len(raw_material)} 字符")
    
    # 4. 执行 Agent
    print("\n[4] 执行 Brief Agent...")
    print("  (这可能需要 5-10 秒，请耐心等待...)")
    
    try:
        result = agent.execute(task_input)
        print(f"✓ Agent 执行完成")
        print(f"  状态: {result.status}")
        print(f"  耗时: {result.metrics['duration_ms']} ms")
        print(f"  Token 使用: {result.metrics.get('token_usage', 0)}")
    except Exception as e:
        print(f"✗ Agent 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 验证结果
    print("\n[5] 验证结果...")
    
    if result.status != "succeeded":
        print(f"✗ Agent 执行失败")
        if result.error_message:
            print(f"  错误: {result.error_message}")
        return False
    
    if not result.document_refs:
        print("✗ 没有生成文档")
        return False
    
    print("✓ 结果验证通过")
    
    # 6. 显示生成的内容
    print("\n[6] 生成的 Brief 内容:")
    print("="*60)
    
    # 注意：由于我们没有使用数据库，需要从 agent 的内部状态获取内容
    # 这里我们重新执行 generator 来获取内容（仅用于演示）
    print("\n重新生成以显示内容...")
    
    context = agent.loader([], [])
    normalized = agent.normalizer(context, task_input.constraints)
    plan = agent.planner(normalized, task_input)
    
    try:
        draft = agent.generator(plan)
        
        print("\n" + json.dumps(draft, ensure_ascii=False, indent=2))
        
        print("\n" + "="*60)
        print("✓ Brief 生成成功！")
        print("="*60)
        
        # 显示关键信息
        print(f"\n【故事类型】{draft.get('genre', 'N/A')}")
        print(f"【目标受众】{draft.get('target_audience', 'N/A')}")
        print(f"【主要冲突】{draft.get('main_conflict', 'N/A')}")
        print(f"【视觉风格】{draft.get('target_style', 'N/A')}")
        print(f"【叙事基调】{draft.get('tone', 'N/A')}")
        
        print(f"\n【核心卖点】")
        for i, point in enumerate(draft.get('core_selling_points', []), 1):
            print(f"  {i}. {point}")
        
        print(f"\n【改编风险】")
        for i, risk in enumerate(draft.get('adaptation_risks', []), 1):
            print(f"  {i}. {risk}")
        
        return True
        
    except Exception as e:
        print(f"✗ 内容生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = test_brief_agent()
        
        if success:
            print("\n" + "="*60)
            print("✓ 所有测试通过！")
            print("="*60)
            print("\n下一步:")
            print("  1. Brief Agent 已成功集成真实 LLM")
            print("  2. 可以开始集成其他 4 个 Agent")
            print("  3. 或者先测试完整的工作流")
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("✗ 测试失败")
            print("="*60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n✗ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
