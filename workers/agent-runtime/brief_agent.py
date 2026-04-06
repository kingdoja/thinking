"""
Brief Agent - Analyzes raw material and generates adaptation direction document.

Implements Requirements: 2.1, 2.2, 2.3, 2.4
"""

import json
from typing import Any, Dict, List, Tuple
from uuid import UUID

from base_agent import BaseAgent, DocumentRef, LockedRef, StageTaskInput, Warning
from llm_service import LLMServiceFactory, LLMMessage


class BriefAgent(BaseAgent):
    """
    Brief Agent generates the adaptation direction document from raw material.
    
    Implements Requirements:
    - 2.1: Extract story main line, character relationships, and core conflicts
    - 2.2: Include structured fields (genre, target_audience, core_selling_points, etc.)
    - 2.3: Persist document to database with correct associations
    - 2.4: Validate required fields
    """
    
    def __init__(self, db_session=None, llm_service=None, validator=None):
        """
        Initialize Brief Agent.
        
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
        """Get the JSON schema for brief output."""
        return {
            "type": "object",
            "required": [
                "genre",
                "target_audience",
                "core_selling_points",
                "main_conflict",
                "target_style"
            ],
            "properties": {
                "genre": {"type": "string"},
                "target_audience": {"type": "string"},
                "core_selling_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1
                },
                "main_conflict": {"type": "string"},
                "adaptation_risks": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "target_style": {"type": "string"},
                "tone": {"type": "string"}
            }
        }
    
    def loader(self, input_refs: List[DocumentRef], locked_refs: List[LockedRef]) -> Dict[str, Any]:
        """
        Load input documents (none for brief stage).
        
        Brief is the first stage, so no input documents to load.
        """
        return {
            "input_documents": [],
            "locked_fields": []
        }
    
    def normalizer(self, context: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize context for brief generation.
        
        Args:
            context: Raw context from loader
            constraints: Contains raw_material, platform, target_duration_sec, target_audience
        """
        return {
            "raw_material": constraints.get("raw_material", ""),
            "platform": constraints.get("platform", "douyin"),
            "target_duration_sec": constraints.get("target_duration_sec", 60),
            "target_audience": constraints.get("target_audience", "")
        }
    
    def planner(self, normalized: Dict[str, Any], task_input: StageTaskInput) -> Dict[str, Any]:
        """
        Create execution plan for brief generation.
        """
        return {
            "prompt": self._build_prompt(normalized),
            "schema": self.get_output_schema(),
            "temperature": 0.7
        }
    
    def generator(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call LLM to generate brief content.
        
        Implements Requirement 2.1: Extract story elements
        Implements Requirement 2.2: Generate structured fields
        """
        if not self.llm_service:
            raise RuntimeError("LLM service not configured")
        
        # Build system and user prompts
        system_prompt = """你是一个专业的影视编剧和改编顾问。你的任务是分析原始素材，并为短视频平台改编创作提供专业的创意方向。

你需要：
1. 准确识别故事类型和核心冲突
2. 提炼最具吸引力的卖点
3. 评估改编风险
4. 建议视觉风格和叙事基调

请以 JSON 格式返回结果，确保所有字段都完整且有价值。"""
        
        user_prompt = plan["prompt"]
        
        # Call LLM
        response = self.llm_service.generate_from_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=plan["temperature"],
            max_tokens=2000
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
        Review brief for quality and completeness.
        
        Brief is the first stage, so no consistency checks against upstream documents.
        """
        warnings = []
        
        # Check if core_selling_points has sufficient items
        selling_points = draft.get("core_selling_points", [])
        if len(selling_points) < 3:
            warnings.append(Warning(
                warning_type="quality",
                severity="medium",
                message="Brief has fewer than 3 core selling points, which may limit creative direction",
                field_path="core_selling_points",
                suggestion="Consider adding more selling points to provide richer creative direction"
            ))
        
        # Check if adaptation_risks are identified
        if not draft.get("adaptation_risks"):
            warnings.append(Warning(
                warning_type="quality",
                severity="low",
                message="No adaptation risks identified",
                field_path="adaptation_risks",
                suggestion="Consider identifying potential challenges in adapting this material"
            ))
        
        return draft, warnings
    
    def validator_stage(self, reviewed: Dict[str, Any], locked_refs: List[LockedRef]) -> Dict[str, Any]:
        """
        Validate brief against schema.
        
        Implements Requirement 2.4: Validate required fields
        """
        if not self.validator:
            # Fallback validation if validator not configured
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
        
        # Use validator component
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
        Persist brief document to database.
        
        Implements Requirement 2.3: Persist with correct associations
        """
        if not self.db:
            # Return mock refs if no database configured
            return {
                "documents": [
                    DocumentRef(
                        ref_type="document",
                        ref_id=str(UUID(int=1)),
                        document_type="brief",
                        version=1
                    )
                ],
                "assets": [],
                "quality_notes": ["Brief generated successfully"],
                "token_usage": self._token_usage
            }
        
        # Import here to avoid circular dependency
        from app.repositories.document_repository import DocumentRepository
        
        doc_repo = DocumentRepository(self.db)
        
        # Get next version
        version = doc_repo.latest_version_for_episode_and_type(
            task_input.episode_id,
            "brief"
        ) + 1
        
        # Create document
        document = doc_repo.create(
            commit=False,
            project_id=task_input.project_id,
            episode_id=task_input.episode_id,
            stage_task_id=None,  # Will be set by workflow service
            document_type="brief",
            version=version,
            status="draft",
            title=f"Brief v{version}",
            content_jsonb=valid,
            summary_text=self._generate_summary(valid),
            created_by=None  # AI-generated
        )
        
        self.db.flush()
        
        return {
            "documents": [
                DocumentRef(
                    ref_type="document",
                    ref_id=str(document.id),
                    document_type="brief",
                    version=version
                )
            ],
            "assets": [],
            "quality_notes": ["Brief generated successfully"],
            "token_usage": self._token_usage
        }
    
    def _build_prompt(self, normalized: Dict[str, Any]) -> str:
        """Build prompt for LLM."""
        schema = self.get_output_schema()
        
        return f"""请分析以下原始素材，为 {normalized['platform']} 平台改编创作一个创意方向文档（Brief）。

【原始素材】
{normalized['raw_material']}

【改编要求】
- 目标时长：{normalized['target_duration_sec']} 秒
- 目标受众：{normalized['target_audience'] or '大众观众'}
- 平台：{normalized['platform']}

【输出要求】
请以 JSON 格式返回，包含以下字段：

1. genre (string): 故事类型（如：科幻、爱情、悬疑、喜剧等）
2. target_audience (string): 目标受众描述（年龄段、兴趣特征等）
3. core_selling_points (array of strings): 3-5个核心卖点（最吸引观众的元素）
4. main_conflict (string): 主要冲突（故事的核心矛盾）
5. adaptation_risks (array of strings): 改编风险（可能遇到的挑战）
6. target_style (string): 目标视觉风格（如：赛博朋克、温馨治愈、紧张刺激等）
7. tone (string): 叙事基调（如：轻松幽默、严肃深沉、热血激昂等）

【示例输出格式】
```json
{{
  "genre": "科幻悬疑",
  "target_audience": "18-35岁，喜欢科幻和烧脑剧情的年轻观众",
  "core_selling_points": [
    "时间循环的创新设定",
    "紧张刺激的悬疑氛围",
    "意想不到的反转结局"
  ],
  "main_conflict": "主角必须在有限的时间循环中找出真相，打破循环",
  "adaptation_risks": [
    "时间循环概念需要清晰表达，避免观众困惑",
    "短视频时长限制，需要精简剧情"
  ],
  "target_style": "赛博朋克风格，霓虹灯光效果，未来感城市场景",
  "tone": "紧张刺激，带有科技感和神秘氛围"
}}
```

请根据原始素材生成 Brief："""
    
    def _generate_summary(self, content: Dict[str, Any]) -> str:
        """Generate summary text for brief."""
        genre = content.get("genre", "unknown")
        conflict = content.get("main_conflict", "")
        return f"Brief for {genre} adaptation. Main conflict: {conflict}"
