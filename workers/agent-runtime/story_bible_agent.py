"""
Story Bible Agent - Establishes world rules and story constraints.

Implements Requirements: 3.1, 3.2, 3.3, 3.4
"""

import json
from typing import Any, Dict, List, Tuple
from uuid import UUID

from base_agent import BaseAgent, DocumentRef, LockedRef, StageTaskInput, Warning
from llm_service import LLMServiceFactory, LLMMessage


class StoryBibleAgent(BaseAgent):
    """
    Story Bible Agent generates world rules and story constraints.
    
    Implements Requirements:
    - 3.1: Extract world rules, timeline, and relationship baseline
    - 3.2: Include structured fields (world_rules, forbidden_conflicts, etc.)
    - 3.3: Mark as constraint source for downstream stages
    - 3.4: Check for conflicts with brief
    """
    
    def __init__(self, db_session=None, llm_service=None, validator=None):
        """
        Initialize Story Bible Agent.
        
        Args:
            db_session: Database session
            llm_service: LLM service (if None, creates from environment)
            validator: Validator component
        """
        # Create LLM service if not provided
        if llm_service is None:
            llm_service = LLMServiceFactory.create_from_env()
        
        super().__init__(db_session, llm_service, validator)
        self._token_usage = 0
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for story bible output."""
        return {
            "type": "object",
            "required": [
                "world_rules",
                "forbidden_conflicts"
            ],
            "properties": {
                "world_rules": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event": {"type": "string"},
                            "time": {"type": "string"}
                        }
                    }
                },
                "relationship_baseline": {
                    "type": "object"
                },
                "forbidden_conflicts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "key_settings": {
                    "type": "object"
                }
            }
        }
    
    def loader(self, input_refs: List[DocumentRef], locked_refs: List[LockedRef]) -> Dict[str, Any]:
        """
        Load brief document as input.
        
        Implements Requirement 3.1: Load brief as input reference
        """
        if not self.db or not hasattr(self.db, 'query'):
            # Return mock data if no database or not a real SQLAlchemy session
            return {
                "input_documents": {
                    "brief": {
                        "genre": "urban_drama",
                        "core_selling_points": ["Identity reversal", "Visual anchors", "Family dynamics"],
                        "main_conflict": "Protagonist proves identity"
                    }
                },
                "locked_fields": []
            }
        
        # Import here to avoid circular dependency
        from app.db.models import DocumentModel
        
        input_documents = {}
        
        for ref in input_refs:
            if ref.ref_type == "document":
                # Load document from database
                doc = self.db.query(DocumentModel).filter_by(id=UUID(ref.ref_id)).first()
                if doc:
                    input_documents[doc.document_type] = doc.content_jsonb
        
        return {
            "input_documents": input_documents,
            "locked_fields": [lf.locked_fields for lf in locked_refs]
        }
    
    def normalizer(self, context: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize context for story bible generation.
        """
        brief = context.get("input_documents", {}).get("brief", {})
        
        return {
            "brief": brief,
            "raw_material_summary": constraints.get("raw_material_summary", ""),
            "genre": brief.get("genre", ""),
            "core_selling_points": brief.get("core_selling_points", []),
            "main_conflict": brief.get("main_conflict", "")
        }
    
    def planner(self, normalized: Dict[str, Any], task_input: StageTaskInput) -> Dict[str, Any]:
        """
        Create execution plan for story bible generation.
        """
        return {
            "prompt": self._build_prompt(normalized),
            "schema": self.get_output_schema(),
            "temperature": 0.7
        }
    
    def generator(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call LLM to generate story bible content.
        
        Implements Requirement 3.1: Extract world rules, timeline, relationship baseline
        Implements Requirement 3.2: Generate structured fields
        """
        if not self.llm_service:
            raise RuntimeError("LLM service not configured")
        
        # Build system and user prompts
        system_prompt = """你是一个专业的世界观设定师和故事架构师。你的任务是为影视作品创建详细的故事圣经（Story Bible），建立世界规则和故事约束。

你需要：
1. 定义清晰的世界规则，确保故事逻辑自洽
2. 建立时间线，梳理关键事件的先后顺序
3. 设定角色关系基线，明确初始关系状态
4. 列出禁止冲突，避免破坏故事逻辑的情节
5. 描述关键场景设定

请以 JSON 格式返回结果，确保所有字段都完整且有价值。"""
        
        user_prompt = plan["prompt"]
        
        # Call LLM
        response = self.llm_service.generate_from_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=plan["temperature"],
            max_tokens=2500
        )
        
        # Track token usage
        self._token_usage = response.token_usage.get("total_tokens", 0)
        
        # Parse JSON response
        try:
            content = json.loads(response.content)
            return content
        except json.JSONDecodeError:
            # If LLM didn't return valid JSON, try to extract it
            content_str = response.content.strip()
            
            # Try to find JSON in markdown code blocks
            if "```json" in content_str:
                start = content_str.find("```json") + 7
                end = content_str.find("```", start)
                content_str = content_str[start:end].strip()
            elif "```" in content_str:
                start = content_str.find("```") + 3
                end = content_str.find("```", start)
                content_str = content_str[start:end].strip()
            
            try:
                content = json.loads(content_str)
                return content
            except json.JSONDecodeError as e:
                raise RuntimeError(f"LLM returned invalid JSON: {e}\nResponse: {response.content}")
    
    def critic(self, draft: Dict[str, Any], normalized: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Warning]]:
        """
        Review story bible for consistency with brief.
        
        Implements Requirement 3.4: Check for conflicts with brief
        """
        warnings = []
        
        # Check if world rules conflict with core selling points
        world_rules = draft.get("world_rules", [])
        core_selling_points = normalized.get("core_selling_points", [])
        
        # Simple keyword-based conflict detection
        for rule in world_rules:
            rule_lower = rule.lower()
            for selling_point in core_selling_points:
                sp_lower = selling_point.lower()
                # Check for negation words that might indicate conflict
                if any(neg in rule_lower for neg in ["no", "never", "cannot", "forbidden"]):
                    # Check if rule contradicts selling point
                    if any(word in rule_lower for word in sp_lower.split()):
                        warnings.append(Warning(
                            warning_type="consistency",
                            severity="medium",
                            message=f"World rule may conflict with selling point: '{rule}' vs '{selling_point}'",
                            field_path="world_rules",
                            suggestion="Review world rule to ensure it supports the core selling points"
                        ))
        
        # Check if forbidden_conflicts are too restrictive
        forbidden = draft.get("forbidden_conflicts", [])
        if len(forbidden) > 5:
            warnings.append(Warning(
                warning_type="quality",
                severity="low",
                message="Many forbidden conflicts may overly constrain creative freedom",
                field_path="forbidden_conflicts",
                suggestion="Consider consolidating or prioritizing the most important constraints"
            ))
        
        return draft, warnings
    
    def validator_stage(self, reviewed: Dict[str, Any], locked_refs: List[LockedRef]) -> Dict[str, Any]:
        """
        Validate story bible against schema.
        
        Implements Requirement 3.2: Validate required fields
        """
        if not self.validator:
            # Fallback validation
            schema = self.get_output_schema()
            required = schema.get("required", [])
            errors = []
            
            for field in required:
                if field not in reviewed or not reviewed[field]:
                    errors.append({
                        "field_path": field,
                        "error_type": "missing_required",
                        "message": f"Required field '{field}' is missing or empty"
                    })
            
            return {
                "is_valid": len(errors) == 0,
                "errors": errors
            }
        
        validation_result = self.validator.validate(
            content=reviewed,
            schema=self.get_output_schema(),
            locked_refs=locked_refs
        )
        
        return {
            "is_valid": validation_result.is_valid,
            "errors": [
                {
                    "field_path": e.field_path,
                    "error_type": e.error_type,
                    "message": e.message
                }
                for e in validation_result.errors
            ]
        }
    
    def committer(self, valid: Dict[str, Any], task_input: StageTaskInput) -> Dict[str, Any]:
        """
        Persist story bible document to database.
        
        Implements Requirement 3.3: Mark as constraint source
        """
        if not self.db:
            return {
                "documents": [
                    DocumentRef(
                        ref_type="document",
                        ref_id=str(UUID(int=2)),
                        document_type="story_bible",
                        version=1
                    )
                ],
                "assets": [],
                "quality_notes": ["Story bible generated as constraint source"],
                "token_usage": self._token_usage
            }
        
        from app.repositories.document_repository import DocumentRepository
        
        doc_repo = DocumentRepository(self.db)
        
        version = doc_repo.latest_version_for_episode_and_type(
            task_input.episode_id,
            "story_bible"
        ) + 1
        
        # Create document with status indicating it's a constraint source
        document = doc_repo.create(
            commit=False,
            project_id=task_input.project_id,
            episode_id=task_input.episode_id,
            stage_task_id=None,
            document_type="story_bible",
            version=version,
            status="locked",  # Mark as constraint source
            title=f"Story Bible v{version}",
            content_jsonb=valid,
            summary_text=self._generate_summary(valid),
            created_by=None
        )
        
        self.db.flush()
        
        return {
            "documents": [
                DocumentRef(
                    ref_type="document",
                    ref_id=str(document.id),
                    document_type="story_bible",
                    version=version
                )
            ],
            "assets": [],
            "quality_notes": ["Story bible generated as constraint source for downstream stages"],
            "token_usage": self._token_usage
        }
    
    def _build_prompt(self, normalized: Dict[str, Any]) -> str:
        """Build prompt for LLM."""
        schema = self.get_output_schema()
        
        return f"""基于 Brief 文档，创建一个详细的故事圣经（Story Bible），建立世界规则和故事约束。

【Brief 信息】
- 故事类型：{normalized.get('genre', '未指定')}
- 核心卖点：{', '.join(normalized.get('core_selling_points', []))}
- 主要冲突：{normalized.get('main_conflict', '未指定')}

【原始素材摘要】
{normalized.get('raw_material_summary', '无')}

【输出要求】
请以 JSON 格式返回，包含以下字段：

1. world_rules (array of strings): 世界规则（3-5条）
   - 定义故事世界的基本规则和逻辑
   - 确保故事的自洽性
   - 支持核心卖点的实现

2. timeline (array of objects): 时间线（可选）
   - event (string): 事件描述
   - time (string): 时间点
   - 梳理关键事件的先后顺序

3. relationship_baseline (object): 角色关系基线（可选）
   - 定义主要角色之间的初始关系状态
   - 为后续角色发展提供基础

4. forbidden_conflicts (array of strings): 禁止冲突（2-4条）
   - 列出不应该出现的情节或冲突
   - 避免破坏故事逻辑或核心卖点

5. key_settings (object): 关键场景设定（可选）
   - 描述重要场景的特征和氛围
   - 为视觉呈现提供指导

【示例输出格式】
```json
{{
  "world_rules": [
    "时间循环每24小时重置一次，只有主角保留记忆",
    "循环中的事件可以被改变，但核心事故必然发生",
    "只有找到事故的真正原因才能打破循环"
  ],
  "timeline": [
    {{"event": "主角首次进入时间循环", "time": "第1天"}},
    {{"event": "主角遇到神秘女孩", "time": "第7天"}},
    {{"event": "发现事故线索", "time": "第15天"}}
  ],
  "relationship_baseline": {{
    "主角与女孩": "陌生人，但女孩似乎知道循环的秘密",
    "主角与城市": "普通程序员，对城市很熟悉"
  }},
  "forbidden_conflicts": [
    "不能让主角轻易打破循环，必须经过充分的探索",
    "不能让循环的原因过于简单或随意",
    "不能让女孩的动机不明确"
  ],
  "key_settings": {{
    "地铁站": "循环的起点，神秘而压抑的氛围",
    "城市街道": "熟悉但又陌生，每次循环都有细微变化"
  }}
}}
```

请根据 Brief 信息生成 Story Bible："""
    
    def _generate_summary(self, content: Dict[str, Any]) -> str:
        """Generate summary text for story bible."""
        rule_count = len(content.get("world_rules", []))
        forbidden_count = len(content.get("forbidden_conflicts", []))
        return f"Story bible with {rule_count} world rules and {forbidden_count} forbidden conflicts"
