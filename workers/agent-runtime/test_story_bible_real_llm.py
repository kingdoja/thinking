"""
测试 Story Bible Agent 使用真实 LLM

这个脚本会：
1. 创建 Story Bible Agent 实例
2. 使用真实 LLM 生成 Story Bible
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
    print("✓ 已加载 LLM 配置")
except ImportError:
    print("⚠ python-dotenv 未安装，使用环境变量")

from story_bible_agent import StoryBibleAgent
from base_agent import StageTaskInput
from llm_service import LLMServiceFactory


def test_story_bible_agent():
    """测试 Story Bible Agent"""
    
    print("="*60)
    print("Story Bible Agent 真实 LLM 测试")
    print("="*60)
    
    # 1. 创建 LLM 服务
    print("\n[1] 创建 LLM 服务...")
    try:
        llm = LLMServiceFactory.create_from_env()
        print(f"✓ LLM 服务创建成功: {llm.model}")
    except Exception as e:
        print(f"✗ LLM 服务创建失败: {e}")
        return False
    
    # 2. 创建 Story Bible Agent
    print("\n[2] 创建 Story Bible Agent...")
    agent = StoryBibleAgent(
        db_session=None,  # 不使用数据库
        llm_service=llm,
        validator=None
    )
    print("✓ Story Bible Agent 创建成功")
    
    # 3. 准备测试输入（模拟 Brief 的输出）
    print("\n[3] 准备测试输入...")
    
    # 模拟 Brief 文档内容
    brief_content = {
        "genre": "科幻悬疑",
        "target_audience": "18-35岁，喜欢科幻和烧脑剧情的年轻观众",
        "core_selling_points": [
            "时间循环的创新设定",
            "紧张刺激的悬疑氛围",
            "意想不到的反转结局",
            "双主角合作破解谜题",
            "城市危机的高风险"
        ],
        "main_conflict": "主角必须在有限的时间循环中找出真相，打破循环并阻止城市灾难",
        "adaptation_risks": [
            "时间循环概念需要清晰表达，避免观众困惑",
            "短视频时长限制，需要精简剧情",
            "悬疑氛围的营造需要精心设计",
            "反转结局需要足够的铺垫"
        ],
        "target_style": "赛博朋克风格，霓虹灯光效果，未来感城市场景，冷色调为主",
        "tone": "紧张刺激，带有科技感和神秘氛围，节奏紧凑"
    }
    
    raw_material_summary = """
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
        stage_type="story_bible",
        input_refs=[],
        locked_refs=[],
        constraints={
            "raw_material_summary": raw_material_summary.strip(),
            "brief": brief_content
        },
        target_ref_ids=[],
        raw_material=raw_material_summary
    )
    
    print("✓ 测试输入准备完成")
    print(f"  Brief 类型: {brief_content['genre']}")
    print(f"  核心卖点数量: {len(brief_content['core_selling_points'])}")
    
    # 4. 执行 Agent
    print("\n[4] 执行 Story Bible Agent...")
    print("  (这可能需要 10-15 秒，请耐心等待...)")
    
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
    print("\n[6] 生成的 Story Bible 内容:")
    print("="*60)
    
    # 重新生成以显示内容
    print("\n重新生成以显示内容...")
    
    context = agent.loader([], [])
    normalized = agent.normalizer(context, task_input.constraints)
    plan = agent.planner(normalized, task_input)
    
    try:
        draft = agent.generator(plan)
        
        print("\n" + json.dumps(draft, ensure_ascii=False, indent=2))
        
        print("\n" + "="*60)
        print("✓ Story Bible 生成成功！")
        print("="*60)
        
        # 显示关键信息
        print(f"\n【世界规则】({len(draft.get('world_rules', []))} 条)")
        for i, rule in enumerate(draft.get('world_rules', []), 1):
            print(f"  {i}. {rule}")
        
        print(f"\n【禁止冲突】({len(draft.get('forbidden_conflicts', []))} 条)")
        for i, conflict in enumerate(draft.get('forbidden_conflicts', []), 1):
            print(f"  {i}. {conflict}")
        
        if draft.get('timeline'):
            print(f"\n【时间线】({len(draft['timeline'])} 个事件)")
            for i, event in enumerate(draft['timeline'], 1):
                print(f"  {i}. {event.get('time', 'N/A')}: {event.get('event', 'N/A')}")
        
        if draft.get('relationship_baseline'):
            print(f"\n【角色关系基线】")
            for rel, desc in draft['relationship_baseline'].items():
                print(f"  - {rel}: {desc}")
        
        if draft.get('key_settings'):
            print(f"\n【关键场景设定】")
            for setting, desc in draft['key_settings'].items():
                print(f"  - {setting}: {desc}")
        
        return True
        
    except Exception as e:
        print(f"✗ 内容生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        success = test_story_bible_agent()
        
        if success:
            print("\n" + "="*60)
            print("✓ 所有测试通过！")
            print("="*60)
            print("\n下一步:")
            print("  1. Story Bible Agent 已成功集成真实 LLM")
            print("  2. 继续更新 Character Agent")
            print("  3. 然后更新 Script Agent 和 Storyboard Agent")
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
