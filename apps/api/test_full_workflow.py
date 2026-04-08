"""
完整文本工作流测试

直接测试 TextWorkflowService，不需要启动 API 服务器
"""

import sys
import os
from pathlib import Path
from uuid import uuid4
import json

# 首先加载环境变量
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent.parent
agent_runtime_path = project_root / "workers" / "agent-runtime"
load_dotenv(agent_runtime_path / ".env")

# 然后添加路径
sys.path.insert(0, str(agent_runtime_path.absolute()))
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# 设置环境变量
os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost:5432/thinking"
os.environ["QWEN_API_KEY"] = "sk-b6cff92b308c47bbaa7ce83d77574fe8"
os.environ["LLM_PROVIDER"] = "qwen"
os.environ["LLM_MODEL"] = "qwen-plus"

from app.db.session import get_db
from app.services.text_workflow_service import TextWorkflowService
from app.repositories.project_repository import ProjectRepository
from app.repositories.episode_repository import EpisodeRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.workflow_repository import WorkflowRepository

# 导入 Agent Runtime
from services.llm_service import LLMServiceFactory
from agents.brief_agent import BriefAgent
from agents.story_bible_agent import StoryBibleAgent
from agents.character_agent import CharacterAgent
from agents.script_agent import ScriptAgent
from agents.storyboard_agent import StoryboardAgent


def test_full_workflow():
    """测试完整的文本工作流"""
    
    print("="*70)
    print("完整文本工作流测试")
    print("="*70)
    
    # 1. 创建数据库会话
    print("\n[1] 连接数据库...")
    try:
        db = next(get_db())
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        print("\n请确保:")
        print("  1. PostgreSQL 已启动: docker-compose up -d postgres")
        print("  2. 数据库迁移已运行")
        return False
    
    # 2. 创建 LLM 服务
    print("\n[2] 创建 LLM 服务...")
    try:
        llm = LLMServiceFactory.create_from_env()
        print(f"✓ LLM 服务创建成功: {llm.model}")
    except Exception as e:
        print(f"✗ LLM 服务创建失败: {e}")
        return False
    
    # 3. 创建测试项目
    print("\n[3] 创建测试项目...")
    try:
        from app.schemas.project import CreateProjectRequest
        
        project_repo = ProjectRepository(db)
        
        project_payload = CreateProjectRequest(
            name="时间循环测试项目",
            source_mode="adaptation",
            genre="科幻悬疑",
            target_platform="douyin",
            target_audience="18-35岁年轻观众"
        )
        
        project = project_repo.create(project_payload)
        
        print(f"✓ 项目创建成功: {project.id}")
        project_id = project.id
        
    except Exception as e:
        print(f"✗ 项目创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. 创建测试剧集
    print("\n[4] 创建测试剧集...")
    try:
        from app.schemas.project import CreateEpisodeRequest
        
        episode_repo = EpisodeRepository(db)
        
        episode_payload = CreateEpisodeRequest(
            project_id=project_id,
            episode_no=1,
            title="第一集：循环开始",
            target_duration_sec=60
        )
        
        episode = episode_repo.create(project_id, episode_payload)
        
        print(f"✓ 剧集创建成功: {episode.id}")
        episode_id = episode.id
        
    except Exception as e:
        print(f"✗ 剧集创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 准备原始素材
    print("\n[5] 准备原始素材...")
    raw_material = """
一个年轻的程序员发现自己被困在了一个时间循环中。每天早上7点，他都会在同一个地铁站醒来，
然后经历完全相同的一天。他尝试了各种方法想要打破循环，但都失败了。

直到有一天，他注意到地铁站的一个神秘女孩，她似乎也意识到了时间循环的存在。
两人开始合作，试图找出循环的原因和打破循环的方法。

在调查过程中，他们发现这个循环与一个即将发生的重大事故有关。
如果他们不能在循环中找到真相并阻止事故，整个城市都将陷入危险。
"""
    print(f"✓ 原始素材准备完成 ({len(raw_material)} 字符)")
    
    # 6. 创建 Agents
    print("\n[6] 创建所有 Agents...")
    try:
        agents = {
            "brief": BriefAgent(db_session=db, llm_service=llm, validator=None),
            "story_bible": StoryBibleAgent(db_session=db, llm_service=llm, validator=None),
            "character": CharacterAgent(db_session=db, llm_service=llm, validator=None),
            "script": ScriptAgent(db_session=db, llm_service=llm, validator=None),
            "storyboard": StoryboardAgent(db_session=db, llm_service=llm, validator=None)
        }
        print("✓ 所有 Agents 创建成功")
    except Exception as e:
        print(f"✗ Agents 创建失败: {e}")
        return False
    
    # 7. 创建工作流服务
    print("\n[7] 创建工作流服务...")
    try:
        stage_task_repo = StageTaskRepository(db)
        doc_repo = DocumentRepository(db)
        shot_repo = ShotRepository(db)
        workflow_repo = WorkflowRepository(db)
        
        workflow_service = TextWorkflowService(
            db=db,
            stage_tasks=stage_task_repo,
            documents=doc_repo,
            shots=shot_repo,
            episodes=episode_repo,
            workflows=workflow_repo
        )
        
        # 替换为真实的 LLM 服务
        workflow_service.llm_service = llm
        workflow_service.agents = agents
        
        print("✓ 工作流服务创建成功")
    except Exception as e:
        print(f"✗ 工作流服务创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 8. 执行完整工作流
    print("\n[8] 执行完整文本工作流...")
    print("  这将依次执行:")
    print("    - Brief Agent")
    print("    - Story Bible Agent")
    print("    - Character Agent")
    print("    - Script Agent")
    print("    - Storyboard Agent")
    print("\n  预计耗时: 2-3 分钟，请耐心等待...\n")
    
    try:
        result = workflow_service.execute_text_chain(
            project_id=project_id,
            episode_id=episode_id,
            raw_material=raw_material,
            platform="douyin",
            target_duration_sec=60,
            target_audience="18-35岁年轻观众"
        )
        
        if result["status"] == "succeeded":
            print("\n✓ 工作流执行成功！")
            print(f"  总耗时: {result.get('total_duration_ms', 0)} ms")
            print(f"  总 Token: {result.get('total_tokens', 0)}")
            
        else:
            print(f"\n✗ 工作流执行失败")
            print(f"  失败阶段: {result.get('failed_stage', 'unknown')}")
            print(f"  错误信息: {result.get('error_message', 'unknown')}")
            return False
            
    except Exception as e:
        print(f"\n✗ 工作流执行异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 9. 查询生成的文档
    print("\n[9] 查询生成的文档...")
    try:
        doc_repo = DocumentRepository(db)
        
        documents = doc_repo.list_by_episode(episode_id)
        
        print(f"✓ 找到 {len(documents)} 个文档:")
        for doc in documents:
            print(f"  - {doc.document_type} v{doc.version} ({doc.status})")
        
    except Exception as e:
        print(f"✗ 文档查询失败: {e}")
        return False
    
    # 10. 显示 Brief 内容
    print("\n[10] Brief 内容预览:")
    print("="*70)
    try:
        brief_doc = next((d for d in documents if d.document_type == "brief"), None)
        if brief_doc:
            brief_content = brief_doc.content_jsonb
            
            print(f"\n【故事类型】{brief_content.get('genre', 'N/A')}")
            print(f"【目标受众】{brief_content.get('target_audience', 'N/A')}")
            print(f"【主要冲突】{brief_content.get('main_conflict', 'N/A')}")
            
            print(f"\n【核心卖点】")
            for i, point in enumerate(brief_content.get('core_selling_points', []), 1):
                print(f"  {i}. {point}")
        else:
            print("  未找到 Brief 文档")
            
    except Exception as e:
        print(f"✗ Brief 显示失败: {e}")
    
    # 11. 显示角色信息
    print("\n[11] 角色信息预览:")
    print("="*70)
    try:
        char_doc = next((d for d in documents if d.document_type == "character_profile"), None)
        if char_doc:
            char_content = char_doc.content_jsonb
            characters = char_content.get('characters', [])
            
            print(f"\n共 {len(characters)} 个角色:")
            for char in characters:
                print(f"\n  【{char.get('name', 'Unknown')}】")
                print(f"    角色: {char.get('role', 'N/A')}")
                print(f"    目标: {char.get('goal', 'N/A')}")
                print(f"    视觉锚点: {char.get('visual_anchor', 'N/A')[:50]}...")
        else:
            print("  未找到角色文档")
            
    except Exception as e:
        print(f"✗ 角色显示失败: {e}")
    
    # 12. 显示场景信息
    print("\n[12] 剧本信息预览:")
    print("="*70)
    try:
        script_doc = next((d for d in documents if d.document_type == "script_draft"), None)
        if script_doc:
            script_content = script_doc.content_jsonb
            scenes = script_content.get('scenes', [])
            
            print(f"\n共 {len(scenes)} 个场景:")
            for scene in scenes[:2]:  # 只显示前2个场景
                print(f"\n  场景 {scene.get('scene_no', '?')}: {scene.get('location', 'Unknown')}")
                print(f"    目标: {scene.get('goal', 'N/A')}")
                print(f"    时长: {scene.get('duration_estimate_sec', 0)}秒")
                print(f"    对话数: {len(scene.get('dialogue', []))}条")
        else:
            print("  未找到剧本文档")
            
    except Exception as e:
        print(f"✗ 剧本显示失败: {e}")
    
    # 13. 显示镜头信息
    print("\n[13] 分镜信息预览:")
    print("="*70)
    try:
        storyboard_doc = next((d for d in documents if d.document_type == "visual_spec"), None)
        if storyboard_doc:
            storyboard_content = storyboard_doc.content_jsonb
            shots = storyboard_content.get('shots', [])
            
            print(f"\n共 {len(shots)} 个镜头")
            print(f"总时长: {storyboard_content.get('overall_duration_ms', 0) / 1000:.1f}秒")
            print(f"视觉风格: {storyboard_content.get('visual_style', 'N/A')}")
        else:
            print("  未找到分镜文档")
            
    except Exception as e:
        print(f"✗ 分镜显示失败: {e}")
    
    return True


def main():
    """主函数"""
    print("\n准备运行完整工作流测试...")
    print("\n请确保:")
    print("  1. PostgreSQL 已启动: docker-compose up -d postgres")
    print("  2. 数据库迁移已运行")
    print("  3. LLM API Key 已配置: workers/agent-runtime/.env")
    
    input("\n按 Enter 继续...")
    
    try:
        success = test_full_workflow()
        
        if success:
            print("\n" + "="*70)
            print("✓ 完整工作流测试通过！")
            print("="*70)
            print("\n恭喜！你已经有了一个完整可用的 AI 漫剧生成系统！")
            print("\n系统能力:")
            print("  ✓ Brief 生成 - 提取核心创意")
            print("  ✓ Story Bible - 建立世界规则")
            print("  ✓ Character - 创建角色档案")
            print("  ✓ Script - 生成场景剧本")
            print("  ✓ Storyboard - 创建分镜脚本")
            print("\n下一步:")
            print("  1. 添加图像生成功能")
            print("  2. 创建前端界面")
            print("  3. 添加人工审核流程")
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("✗ 测试失败")
            print("="*70)
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
