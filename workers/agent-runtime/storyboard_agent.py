"""
Storyboard Agent - Generates shots and visual specifications from script draft.

Implements Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import json
from typing import Any, Dict, List, Tuple
from uuid import UUID, uuid4

from base_agent import BaseAgent, AssetRef, DocumentRef, LockedRef, StageTaskInput, Warning
from llm_service import LLMServiceFactory, LLMMessage


class StoryboardAgent(BaseAgent):
    """
    Storyboard Agent generates shot records and visual specifications.
    
    Implements Requirements:
    - 6.1: Split script into structured shot list
    - 6.2: Assign unique id, shot_code, scene_no, shot_no, duration_ms, characters for each shot
    - 6.3: Persist shots to database with episode_id
    - 6.4: Generate visual_spec with render_prompt and style_keywords
    - 6.5: Validate total duration against target
    """
    
    def __init__(self, db_session=None, llm_service=None, validator=None):
        """
        Initialize Storyboard Agent.
        
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
        """Get the JSON schema for storyboard output."""
        return {
            "type": "object",
            "required": ["shots", "overall_duration_ms", "shot_count"],
            "properties": {
                "shots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "shot_id",
                            "render_prompt",
                            "character_refs",
                            "style_keywords",
                            "composition"
                        ],
                        "properties": {
                            "shot_id": {"type": "string"},
                            "render_prompt": {"type": "string"},
                            "character_refs": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "style_keywords": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "composition": {"type": "string"}
                        }
                    },
                    "minItems": 1
                },
                "overall_duration_ms": {"type": "integer"},
                "shot_count": {"type": "integer"},
                "visual_style": {"type": "string"},
                "camera_strategy": {"type": "string"}
            }
        }
    
    def loader(self, input_refs: List[DocumentRef], locked_refs: List[LockedRef]) -> Dict[str, Any]:
        """
        Load script_draft and platform constraints.
        
        Implements Requirement 6.1: Load script_draft as input
        """
        if not self.db or not hasattr(self.db, 'query'):
            return {
                "input_documents": {
                    "script_draft": {
                        "scenes": [
                            {
                                "scene_no": 1,
                                "location": "Mansion hall",
                                "characters": ["Lin Qingwan"],
                                "dialogue": [],
                                "duration_estimate_sec": 20
                            }
                        ]
                    },
                    "character_profile": {
                        "characters": [
                            {
                                "name": "Lin Qingwan",
                                "visual_anchor": "elegant woman in traditional dress"
                            }
                        ]
                    }
                },
                "locked_fields": []
            }
        
        from app.db.models import DocumentModel
        
        input_documents = {}
        
        for ref in input_refs:
            if ref.ref_type == "document":
                doc = self.db.query(DocumentModel).filter_by(id=UUID(ref.ref_id)).first()
                if doc:
                    input_documents[doc.document_type] = doc.content_jsonb
        
        return {
            "input_documents": input_documents,
            "locked_fields": [lf.locked_fields for lf in locked_refs]
        }
    
    def normalizer(self, context: Dict[str, Any], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize context for storyboard generation.
        """
        script_draft = context.get("input_documents", {}).get("script_draft", {})
        character_profile = context.get("input_documents", {}).get("character_profile", {})
        
        return {
            "script_draft": script_draft,
            "character_profile": character_profile,
            "scenes": script_draft.get("scenes", []),
            "characters": character_profile.get("characters", []),
            "platform": constraints.get("platform", "douyin"),
            "aspect_ratio": constraints.get("aspect_ratio", "9:16"),
            "target_duration_sec": constraints.get("target_duration_sec", 60),
            "max_shots": constraints.get("max_shots", 20)
        }
    
    def planner(self, normalized: Dict[str, Any], task_input: StageTaskInput) -> Dict[str, Any]:
        """
        Create execution plan for storyboard generation.
        """
        return {
            "prompt": self._build_prompt(normalized),
            "schema": self.get_output_schema(),
            "temperature": 0.7
        }
    
    def generator(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call LLM to generate visual spec and shot breakdown.
        
        Implements Requirement 6.1: Generate shot list
        Implements Requirement 6.4: Generate visual_spec with render prompts
        """
        if not self.llm_service:
            raise RuntimeError("LLM service not configured")
        
        # Build system and user prompts
        system_prompt = """你是一个专业的分镜师和视觉设计师。你的任务是将剧本转换为详细的分镜脚本，包含每个镜头的视觉描述。

你需要：
1. 将剧本场景拆分为具体的镜头
2. 为每个镜头生成详细的渲染提示词（用于 AI 图像生成）
3. 指定镜头构图、角色、风格关键词
4. 确保视觉风格统一
5. 控制总时长在目标范围内

请以 JSON 格式返回结果，确保所有字段都完整且有价值。"""
        
        user_prompt = plan["prompt"]
        
        # Call LLM with higher max_tokens for storyboard generation
        response = self.llm_service.generate_from_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=plan["temperature"],
            max_tokens=4000
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
        Review storyboard for consistency and constraints.
        
        Implements Requirement 6.5: Validate total duration against target
        """
        warnings = []
        
        shots = draft.get("shots", [])
        overall_duration_ms = draft.get("overall_duration_ms", 0)
        target_duration_sec = normalized.get("target_duration_sec", 60)
        characters = {c["name"]: c for c in normalized.get("characters", [])}
        
        # Check total duration (Requirement 6.5)
        target_duration_ms = target_duration_sec * 1000
        if overall_duration_ms > target_duration_ms * 1.2:
            warnings.append(Warning(
                warning_type="constraint",
                severity="high",
                message=f"Total duration ({overall_duration_ms}ms) exceeds target ({target_duration_ms}ms) by more than 20%",
                field_path="overall_duration_ms",
                suggestion=f"Consider reducing shot durations or removing shots to meet target of {target_duration_sec}s"
            ))
        
        # Check character visual anchors
        for shot_idx, shot in enumerate(shots):
            char_refs = shot.get("character_refs", [])
            for char_name in char_refs:
                if char_name in characters:
                    char_profile = characters[char_name]
                    visual_anchor = char_profile.get("visual_anchor", "")
                    
                    if not visual_anchor or visual_anchor.strip() == "":
                        warnings.append(Warning(
                            warning_type="consistency",
                            severity="medium",
                            message=f"Character '{char_name}' in shot lacks visual anchor in character profile",
                            field_path=f"shots[{shot_idx}].character_refs",
                            suggestion=f"Add visual anchor for '{char_name}' in character profile for consistent rendering"
                        ))
                    else:
                        # Check if visual anchor is referenced in render prompt
                        render_prompt = shot.get("render_prompt", "").lower()
                        anchor_keywords = visual_anchor.lower().split()
                        
                        if not any(keyword in render_prompt for keyword in anchor_keywords if len(keyword) > 3):
                            warnings.append(Warning(
                                warning_type="consistency",
                                severity="low",
                                message=f"Shot render prompt may not reference character '{char_name}' visual anchor: '{visual_anchor}'",
                                field_path=f"shots[{shot_idx}].render_prompt",
                                suggestion=f"Consider including visual anchor details: {visual_anchor}"
                            ))
        
        # Check shot count
        max_shots = normalized.get("max_shots", 20)
        if len(shots) > max_shots:
            warnings.append(Warning(
                warning_type="constraint",
                severity="medium",
                message=f"Shot count ({len(shots)}) exceeds platform maximum ({max_shots})",
                field_path="shots",
                suggestion=f"Consider consolidating shots to meet platform limit of {max_shots}"
            ))
        
        return draft, warnings
    
    def validator_stage(self, reviewed: Dict[str, Any], locked_refs: List[LockedRef]) -> Dict[str, Any]:
        """
        Validate visual spec against schema.
        
        Implements Requirement 6.2: Validate shot structure
        Implements Requirement 6.4: Validate visual_spec fields
        """
        if not self.validator:
            schema = self.get_output_schema()
            required = schema.get("required", [])
            errors = []
            
            for field in required:
                if field not in reviewed or reviewed[field] is None:
                    errors.append({
                        "field_path": field,
                        "error_type": "missing_required",
                        "message": f"Required field '{field}' is missing or empty"
                    })
            
            # Validate shot structure
            shots = reviewed.get("shots", [])
            if shots:
                shot_required = schema["properties"]["shots"]["items"]["required"]
                for idx, shot in enumerate(shots):
                    for field in shot_required:
                        if field not in shot or not shot[field]:
                            errors.append({
                                "field_path": f"shots[{idx}].{field}",
                                "error_type": "missing_required",
                                "message": f"Required shot field '{field}' is missing"
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
        Persist shots and visual_spec to database.
        
        Implements Requirement 6.2: Create shot records with all required fields
        Implements Requirement 6.3: Associate shots with episode_id
        """
        if not self.db:
            # Mock mode - return mock refs
            shot_count = valid.get("shot_count", 3)
            return {
                "documents": [
                    DocumentRef(
                        ref_type="document",
                        ref_id=str(UUID(int=5)),
                        document_type="visual_spec",
                        version=1
                    )
                ],
                "assets": [
                    AssetRef(
                        ref_type="shot",
                        ref_id=str(UUID(int=100 + i))
                    )
                    for i in range(shot_count)
                ],
                "quality_notes": [f"Generated {shot_count} shots"],
                "token_usage": self._token_usage
            }
        
        from app.repositories.document_repository import DocumentRepository
        from app.repositories.shot_repository import ShotRepository
        from app.repositories.episode_repository import EpisodeRepository
        
        doc_repo = DocumentRepository(self.db)
        shot_repo = ShotRepository(self.db)
        episode_repo = EpisodeRepository(self.db)
        
        # Create visual_spec document
        doc_version = doc_repo.latest_version_for_episode_and_type(
            task_input.episode_id,
            "visual_spec"
        ) + 1
        
        visual_spec_doc = doc_repo.create(
            commit=False,
            project_id=task_input.project_id,
            episode_id=task_input.episode_id,
            stage_task_id=None,
            document_type="visual_spec",
            version=doc_version,
            status="draft",
            title=f"Visual Spec v{doc_version}",
            content_jsonb=valid,
            summary_text=self._generate_summary(valid),
            created_by=None
        )
        
        # Create shot records from visual spec
        shots_data = valid.get("shots", [])
        script_scenes = task_input.constraints.get("script_scenes", [])
        
        shot_version = shot_repo.latest_version_for_episode(task_input.episode_id) + 1
        shot_payloads = []
        
        # Map shots to scenes based on script structure
        for shot_idx, shot_spec in enumerate(shots_data):
            # Determine scene_no and shot_no from shot_id or index
            scene_no = (shot_idx // 3) + 1  # Simple heuristic: ~3 shots per scene
            shot_no = (shot_idx % 3) + 1
            
            # Extract duration from overall_duration_ms divided by shot count
            shot_count = valid.get("shot_count", len(shots_data))
            duration_per_shot = valid.get("overall_duration_ms", 60000) // shot_count if shot_count > 0 else 5000
            
            shot_payload = {
                "id": uuid4(),
                "project_id": task_input.project_id,
                "episode_id": task_input.episode_id,
                "stage_task_id": None,
                "scene_no": scene_no,
                "shot_no": shot_no,
                "shot_code": f"S{scene_no:02d}_{shot_no:03d}",
                "status": "draft",
                "duration_ms": duration_per_shot,
                "camera_size": self._extract_camera_size(shot_spec.get("composition", "")),
                "camera_angle": self._extract_camera_angle(shot_spec.get("composition", "")),
                "movement_type": "static",  # Default
                "characters_jsonb": shot_spec.get("character_refs", []),
                "action_text": shot_spec.get("render_prompt", ""),
                "dialogue_text": "",  # Extract from script if needed
                "visual_constraints_jsonb": {
                    "render_prompt": shot_spec.get("render_prompt", ""),
                    "style_keywords": shot_spec.get("style_keywords", []),
                    "composition": shot_spec.get("composition", ""),
                    "character_refs": shot_spec.get("character_refs", [])
                },
                "version": shot_version
            }
            shot_payloads.append(shot_payload)
        
        # Persist shots
        created_shots = shot_repo.create_many(shot_payloads, commit=False)
        
        # Update episode storyboard_version
        episode_repo.update_progress(
            task_input.episode_id,
            commit=False,
            storyboard_version=shot_version
        )
        
        self.db.flush()
        
        return {
            "documents": [
                DocumentRef(
                    ref_type="document",
                    ref_id=str(visual_spec_doc.id),
                    document_type="visual_spec",
                    version=doc_version
                )
            ],
            "assets": [
                AssetRef(
                    ref_type="shot",
                    ref_id=str(shot.id)
                )
                for shot in created_shots
            ],
            "quality_notes": [
                f"Generated {len(created_shots)} shots",
                f"Total duration: {valid.get('overall_duration_ms', 0)}ms",
                f"Visual style: {valid.get('visual_style', 'N/A')}"
            ],
            "token_usage": self._token_usage
        }
    
    def _build_prompt(self, normalized: Dict[str, Any]) -> str:
        """Build prompt for LLM."""
        scenes = normalized.get("scenes", [])
        characters = normalized.get("characters", [])
        
        # Format scenes
        scene_list = []
        for i, s in enumerate(scenes):
            scene_list.append(f"  场景 {s.get('scene_no', i+1)}: {s.get('location', '未知')} - {s.get('goal', '无')}")
        scene_str = '\n'.join(scene_list) if scene_list else "  （无）"
        
        # Format characters
        char_list = []
        for c in characters:
            char_list.append(f"  - {c.get('name', '')}: {c.get('visual_anchor', '无视觉锚点')}")
        char_str = '\n'.join(char_list) if char_list else "  （无）"
        
        return f"""基于剧本草稿，创建详细的分镜脚本，包含逐镜头的视觉描述。

【平台信息】
- 平台：{normalized.get('platform', 'douyin')}
- 画面比例：{normalized.get('aspect_ratio', '9:16')}
- 目标时长：{normalized.get('target_duration_sec', 60)} 秒
- 最大镜头数：{normalized.get('max_shots', 20)}

【剧本场景】
{scene_str}

【角色信息】
{char_str}

【输出要求】
请以 JSON 格式返回，包含以下结构：

{{
  "shots": [
    {{
      "shot_id": "唯一镜头ID（如：shot_001）",
      "render_prompt": "详细的渲染提示词（用于 AI 图像生成，必须包含角色的视觉锚点）",
      "character_refs": ["出现的角色名称"],
      "style_keywords": ["风格关键词1", "风格关键词2"],
      "composition": "镜头构图（如：close-up, medium, wide, two-shot 等）"
    }}
  ],
  "overall_duration_ms": 60000,
  "shot_count": 10,
  "visual_style": "整体视觉风格描述",
  "camera_strategy": "镜头策略描述"
}}

【关键要求】
1. 每个镜头必须有唯一的 shot_id
2. render_prompt 必须详细且包含角色的视觉锚点（如果角色出现）
3. 总时长（overall_duration_ms）控制在目标范围内
4. 镜头数量（shot_count）不超过平台最大值
5. style_keywords 要具体（如：赛博朋克、冷色调、霓虹灯、未来感等）
6. composition 要明确（close-up/medium/wide/two-shot/over-shoulder 等）

【示例输出】
```json
{{
  "shots": [
    {{
      "shot_id": "shot_001",
      "render_prompt": "梧桐路地铁站B出口，清晨7点，一个年轻男子（陈屿）站在闸机前，左眼角有细长疤痕，穿着深蓝色连帽衫，黑色短发凌乱，表情困惑，赛博朋克风格，冷色调，霓虹灯光效果",
      "character_refs": ["陈屿"],
      "style_keywords": ["赛博朋克", "冷色调", "霓虹灯", "未来感", "地铁站"],
      "composition": "medium"
    }},
    {{
      "shot_id": "shot_002",
      "render_prompt": "陈屿的特写镜头，左眼角疤痕清晰可见，眼神中充满困惑和恐慌，右手下意识摸向左手腕（原本戴表的位置），背景虚化的地铁站，冷色调光线",
      "character_refs": ["陈屿"],
      "style_keywords": ["特写", "情绪表达", "细节刻画", "冷色调"],
      "composition": "close-up"
    }},
    {{
      "shot_id": "shot_003",
      "render_prompt": "地铁站台，陈屿和神秘女孩的双人镜头，女孩半透明的身影，穿着白色连衣裙（边缘有数字化像素闪烁），长发遮住右半边脸，左手腕有发光的数字编码，两人对视，紧张的氛围",
      "character_refs": ["陈屿", "神秘女孩"],
      "style_keywords": ["双人镜头", "神秘氛围", "数字化效果", "对比"],
      "composition": "two-shot"
    }}
  ],
  "overall_duration_ms": 60000,
  "shot_count": 10,
  "visual_style": "赛博朋克风格，冷色调为主，霓虹灯光效果，未来感城市场景，数字化元素点缀",
  "camera_strategy": "以中景和特写为主，通过镜头语言强化角色情绪和神秘氛围，使用双人镜头展现角色关系"
}}
```

请根据剧本生成分镜脚本："""
    
    def _generate_summary(self, content: Dict[str, Any]) -> str:
        """Generate summary text for visual spec."""
        shot_count = content.get("shot_count", 0)
        duration_ms = content.get("overall_duration_ms", 0)
        duration_sec = duration_ms / 1000
        return f"Visual spec with {shot_count} shots, total duration {duration_sec:.1f}s"
    
    def _extract_camera_size(self, composition: str) -> str:
        """Extract camera size from composition string."""
        composition_lower = composition.lower()
        if "close" in composition_lower or "extreme_close" in composition_lower:
            return "close-up"
        elif "wide" in composition_lower:
            return "wide"
        else:
            return "medium"
    
    def _extract_camera_angle(self, composition: str) -> str:
        """Extract camera angle from composition string."""
        composition_lower = composition.lower()
        if "low" in composition_lower:
            return "low"
        elif "high" in composition_lower:
            return "high"
        else:
            return "eye-level"
