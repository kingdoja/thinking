"""
QA Runtime Service

Executes quality assurance checks on generated content.
Implements Requirements: 1.1, 1.2, 1.3

The QA Runtime is responsible for:
1. Executing rule checks (format, structure, completeness)
2. Executing semantic checks (consistency, coherence)
3. Generating QA reports with issues and severity
4. Deciding whether to block workflow continuation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import (
    AssetModel,
    DocumentModel,
    QAReportModel,
    ShotModel,
)
from app.repositories.qa_repository import QARepository


@dataclass
class Issue:
    """Represents a single QA issue found during checking."""
    type: str  # e.g., "missing_field", "invalid_format", "inconsistency"
    severity: str  # "info", "minor", "major", "critical"
    location: str  # e.g., "brief.genre", "shot_3.dialogue"
    message: str  # Human-readable description
    suggestion: Optional[str] = None  # Suggested fix


@dataclass
class QAResult:
    """Result of a QA check execution."""
    result: str  # "passed", "failed", "warning"
    score: float  # Quality score 0-100
    severity: str  # Highest severity found: "info", "minor", "major", "critical"
    issue_count: int
    issues: List[Issue] = field(default_factory=list)
    rerun_stage_type: Optional[str] = None  # Suggested stage to rerun


class QARuntime:
    """
    QA Runtime - executes quality assurance checks.
    
    Responsibilities:
    1. Execute rule checks (Requirement 1.1)
    2. Execute semantic checks (Requirement 1.1)
    3. Generate QA reports (Requirement 1.2)
    4. Decide workflow continuation (Requirement 1.3)
    
    Implements Requirements: 1.1, 1.2, 1.3
    """
    
    def __init__(self, db: Session):
        """
        Initialize QA Runtime.
        
        Args:
            db: Database session
        """
        self.db = db
        self.qa_repo = QARepository(db)
    
    def execute_qa(
        self,
        episode_id: UUID,
        stage_task_id: UUID,
        qa_type: str,
        target_ref_type: str,
        target_ref_id: Optional[UUID] = None,
    ) -> QAResult:
        """
        Execute QA check and generate report.
        
        Implements Requirements: 1.1, 1.2, 1.3
        
        Args:
            episode_id: Episode ID
            stage_task_id: StageTask ID that triggered QA
            qa_type: Type of QA check (rule_check, semantic_check, asset_check)
            target_ref_type: Type of target (document, shot, asset, episode)
            target_ref_id: ID of the target object (optional for episode-level checks)
            
        Returns:
            QAResult with check results
        """
        # Execute the appropriate check based on qa_type
        issues: List[Issue] = []
        
        if qa_type == "rule_check":
            issues = self._execute_rule_check(target_ref_type, target_ref_id)
        elif qa_type == "semantic_check":
            issues = self._execute_semantic_check(episode_id, target_ref_type, target_ref_id)
        elif qa_type == "asset_check":
            issues = self._execute_asset_check(target_ref_id)
        else:
            raise ValueError(f"Unknown qa_type: {qa_type}")
        
        # Calculate result metrics (Requirement 1.2)
        qa_result = self._calculate_qa_result(issues)
        
        # Create QA report in database (Requirement 1.2)
        self._create_qa_report(
            episode_id=episode_id,
            stage_task_id=stage_task_id,
            qa_type=qa_type,
            target_ref_type=target_ref_type,
            target_ref_id=target_ref_id,
            qa_result=qa_result,
        )
        
        return qa_result
    
    def _execute_rule_check(
        self,
        target_ref_type: str,
        target_ref_id: Optional[UUID],
    ) -> List[Issue]:
        """
        Execute rule-based checks.
        
        Checks:
        - Required fields completeness
        - Data format correctness
        - Value range validity
        - Structure integrity
        
        Implements Requirements: 2.1, 2.2, 2.3, 2.4
        
        Args:
            target_ref_type: Type of target
            target_ref_id: Target ID
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        
        if target_ref_type == "document" and target_ref_id:
            # Get the document
            from app.repositories.document_repository import DocumentRepository
            doc_repo = DocumentRepository(self.db)
            document = doc_repo.get_by_id(target_ref_id)
            
            if not document:
                issues.append(Issue(
                    type="missing_target",
                    severity="critical",
                    location=f"document.{target_ref_id}",
                    message=f"Document {target_ref_id} not found",
                    suggestion="Ensure the document exists before running QA"
                ))
                return issues
            
            # Route to specific document type checker
            if document.document_type == "brief":
                issues.extend(self.check_brief_rules(document))
            elif document.document_type == "character_profile":
                issues.extend(self.check_character_rules(document))
            elif document.document_type == "script":
                issues.extend(self.check_script_rules(document))
            elif document.document_type == "storyboard":
                issues.extend(self.check_storyboard_rules(document))
        
        return issues
    
    def _execute_semantic_check(
        self,
        episode_id: UUID,
        target_ref_type: str,
        target_ref_id: Optional[UUID],
    ) -> List[Issue]:
        """
        Execute semantic consistency checks.
        
        Checks:
        - Character consistency across documents
        - World-building consistency
        - Plot coherence
        - Logical consistency
        
        Implements Requirements: 3.1, 3.2, 3.3
        
        Args:
            episode_id: Episode ID
            target_ref_type: Type of target
            target_ref_id: Target ID
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        
        # Execute all semantic checks
        issues.extend(self.check_character_consistency(episode_id))
        issues.extend(self.check_world_consistency(episode_id))
        issues.extend(self.check_plot_coherence(episode_id))
        
        return issues
    
    def _execute_asset_check(
        self,
        asset_id: Optional[UUID],
    ) -> List[Issue]:
        """
        Execute asset quality checks.
        
        Checks:
        - File integrity
        - Format correctness
        - Technical specifications
        - Usability
        
        Args:
            asset_id: Asset ID
            
        Returns:
            List of issues found
        """
        # Placeholder - will be implemented later
        return []
    
    def _calculate_qa_result(self, issues: List[Issue]) -> QAResult:
        """
        Calculate QA result from issues list.
        
        Implements Requirement 1.2
        
        Args:
            issues: List of issues found
            
        Returns:
            QAResult with calculated metrics
        """
        if not issues:
            return QAResult(
                result="passed",
                score=100.0,
                severity="info",
                issue_count=0,
                issues=[],
                rerun_stage_type=None,
            )
        
        # Count issues by severity
        severity_counts = {
            "critical": 0,
            "major": 0,
            "minor": 0,
            "info": 0,
        }
        
        for issue in issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        
        # Determine highest severity
        if severity_counts["critical"] > 0:
            highest_severity = "critical"
        elif severity_counts["major"] > 0:
            highest_severity = "major"
        elif severity_counts["minor"] > 0:
            highest_severity = "minor"
        else:
            highest_severity = "info"
        
        # Calculate score (deduct points based on severity)
        score = 100.0
        score -= severity_counts["critical"] * 25.0  # Critical: -25 points each
        score -= severity_counts["major"] * 10.0     # Major: -10 points each
        score -= severity_counts["minor"] * 3.0      # Minor: -3 points each
        score -= severity_counts["info"] * 1.0       # Info: -1 point each
        score = max(0.0, score)  # Don't go below 0
        
        # Determine result status
        if highest_severity == "critical":
            result = "failed"
        elif highest_severity == "major":
            result = "warning"
        else:
            result = "passed"
        
        return QAResult(
            result=result,
            score=score,
            severity=highest_severity,
            issue_count=len(issues),
            issues=issues,
            rerun_stage_type=None,  # Will be set based on issue types
        )
    
    def _create_qa_report(
        self,
        episode_id: UUID,
        stage_task_id: UUID,
        qa_type: str,
        target_ref_type: str,
        target_ref_id: Optional[UUID],
        qa_result: QAResult,
    ) -> QAReportModel:
        """
        Create QA report record in database.
        
        Implements Requirement 1.2
        
        Args:
            episode_id: Episode ID
            stage_task_id: StageTask ID
            qa_type: QA check type
            target_ref_type: Target type
            target_ref_id: Target ID
            qa_result: QA result to record
            
        Returns:
            Created QAReportModel
        """
        # Get project_id from episode
        from app.repositories.episode_repository import EpisodeRepository
        episode_repo = EpisodeRepository(self.db)
        episode = episode_repo.get(episode_id)
        if not episode:
            raise ValueError(f"Episode {episode_id} not found")
        
        # Convert issues to JSON format
        issues_jsonb = [
            {
                "type": issue.type,
                "severity": issue.severity,
                "location": issue.location,
                "message": issue.message,
                "suggestion": issue.suggestion,
            }
            for issue in qa_result.issues
        ]
        
        # Create QA report
        qa_report = QAReportModel(
            project_id=episode.project_id,
            episode_id=episode_id,
            stage_task_id=stage_task_id,
            qa_type=qa_type,
            target_ref_type=target_ref_type,
            target_ref_id=target_ref_id,
            result=qa_result.result,
            score=qa_result.score,
            severity=qa_result.severity,
            issue_count=qa_result.issue_count,
            issues_jsonb=issues_jsonb,
            rerun_stage_type=qa_result.rerun_stage_type,
        )
        
        self.db.add(qa_report)
        self.db.commit()
        self.db.refresh(qa_report)
        
        return qa_report
    
    def should_block_workflow(self, qa_result: QAResult) -> bool:
        """
        Decide whether QA result should block workflow continuation.
        
        Implements Requirement 1.3
        
        Args:
            qa_result: QA result to evaluate
            
        Returns:
            True if workflow should be blocked, False otherwise
        """
        # Block on critical issues
        if qa_result.severity == "critical":
            return True
        
        # Block if result is failed
        if qa_result.result == "failed":
            return True
        
        # Allow continuation for warnings and passed
        return False
    
    def check_brief_rules(self, document: DocumentModel) -> List[Issue]:
        """
        Check Brief document rules.
        
        Implements Requirement 2.1
        
        Checks:
        - Required fields: title, genre, target_audience, premise, tone
        - Field format validation
        - Content length validation
        
        Args:
            document: Brief document to check
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        content = document.content_jsonb or {}
        
        # Required fields check
        required_fields = {
            "title": "标题",
            "genre": "类型",
            "target_audience": "目标受众",
            "premise": "故事前提",
            "tone": "基调"
        }
        
        for field, field_name in required_fields.items():
            if not content.get(field):
                issues.append(Issue(
                    type="missing_field",
                    severity="major",
                    location=f"brief.{field}",
                    message=f"必填字段 '{field_name}' 缺失",
                    suggestion=f"请添加 {field_name} 信息"
                ))
        
        # Title length check
        title = content.get("title", "")
        if title and len(title) > 200:
            issues.append(Issue(
                type="invalid_format",
                severity="minor",
                location="brief.title",
                message=f"标题过长 ({len(title)} 字符，最大 200)",
                suggestion="请缩短标题长度"
            ))
        
        # Premise length check
        premise = content.get("premise", "")
        if premise and len(premise) < 20:
            issues.append(Issue(
                type="invalid_format",
                severity="minor",
                location="brief.premise",
                message=f"故事前提过短 ({len(premise)} 字符，建议至少 20)",
                suggestion="请提供更详细的故事前提"
            ))
        
        # Genre validation
        valid_genres = ["drama", "comedy", "action", "romance", "thriller", "sci-fi", "fantasy", "horror"]
        genre = content.get("genre", "").lower()
        if genre and genre not in valid_genres:
            issues.append(Issue(
                type="invalid_format",
                severity="info",
                location="brief.genre",
                message=f"类型 '{genre}' 不在标准列表中",
                suggestion=f"建议使用标准类型: {', '.join(valid_genres)}"
            ))
        
        return issues
    
    def check_character_rules(self, document: DocumentModel) -> List[Issue]:
        """
        Check Character Profile document rules.
        
        Implements Requirement 2.2
        
        Checks:
        - Character count (at least 1, max 10)
        - Required character fields
        - Visual anchors completeness
        
        Args:
            document: Character Profile document to check
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        content = document.content_jsonb or {}
        characters = content.get("characters", [])
        
        # Character count check
        if not characters:
            issues.append(Issue(
                type="missing_field",
                severity="critical",
                location="character_profile.characters",
                message="角色列表为空",
                suggestion="至少需要定义一个角色"
            ))
            return issues
        
        if len(characters) > 10:
            issues.append(Issue(
                type="invalid_format",
                severity="major",
                location="character_profile.characters",
                message=f"角色数量过多 ({len(characters)} 个，建议最多 10 个)",
                suggestion="考虑合并或删除次要角色"
            ))
        
        # Check each character
        required_char_fields = {
            "name": "姓名",
            "role": "角色定位",
            "personality": "性格特点",
            "appearance": "外貌描述"
        }
        
        for idx, char in enumerate(characters):
            char_location = f"character_profile.characters[{idx}]"
            
            # Required fields
            for field, field_name in required_char_fields.items():
                if not char.get(field):
                    issues.append(Issue(
                        type="missing_field",
                        severity="major",
                        location=f"{char_location}.{field}",
                        message=f"角色 {idx + 1} 缺少必填字段 '{field_name}'",
                        suggestion=f"请为角色添加 {field_name}"
                    ))
            
            # Visual anchors check
            visual_anchors = char.get("visual_anchors", [])
            if not visual_anchors:
                issues.append(Issue(
                    type="missing_field",
                    severity="minor",
                    location=f"{char_location}.visual_anchors",
                    message=f"角色 {idx + 1} ({char.get('name', 'Unknown')}) 缺少视觉锚点",
                    suggestion="添加视觉锚点以提高图像生成质量"
                ))
            elif len(visual_anchors) < 3:
                issues.append(Issue(
                    type="invalid_format",
                    severity="info",
                    location=f"{char_location}.visual_anchors",
                    message=f"角色 {idx + 1} 视觉锚点较少 ({len(visual_anchors)} 个，建议至少 3 个)",
                    suggestion="添加更多视觉锚点以提高角色一致性"
                ))
        
        return issues
    
    def check_script_rules(self, document: DocumentModel) -> List[Issue]:
        """
        Check Script document rules.
        
        Implements Requirement 2.3
        
        Checks:
        - Scene structure completeness
        - Dialogue format correctness
        - Duration reasonableness
        
        Args:
            document: Script document to check
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        content = document.content_jsonb or {}
        scenes = content.get("scenes", [])
        
        # Scene count check
        if not scenes:
            issues.append(Issue(
                type="missing_field",
                severity="critical",
                location="script.scenes",
                message="剧本场景列表为空",
                suggestion="至少需要定义一个场景"
            ))
            return issues
        
        total_duration = 0
        
        # Check each scene
        for idx, scene in enumerate(scenes):
            scene_location = f"script.scenes[{idx}]"
            
            # Required scene fields
            if not scene.get("scene_no"):
                issues.append(Issue(
                    type="missing_field",
                    severity="major",
                    location=f"{scene_location}.scene_no",
                    message=f"场景 {idx + 1} 缺少场景编号",
                    suggestion="为场景添加编号"
                ))
            
            if not scene.get("location"):
                issues.append(Issue(
                    type="missing_field",
                    severity="major",
                    location=f"{scene_location}.location",
                    message=f"场景 {idx + 1} 缺少地点信息",
                    suggestion="为场景添加地点描述"
                ))
            
            # Dialogue check
            dialogues = scene.get("dialogues", [])
            if not dialogues:
                issues.append(Issue(
                    type="missing_field",
                    severity="minor",
                    location=f"{scene_location}.dialogues",
                    message=f"场景 {idx + 1} 没有对白",
                    suggestion="考虑添加对白或确认这是无声场景"
                ))
            else:
                # Check dialogue format
                for d_idx, dialogue in enumerate(dialogues):
                    dialogue_location = f"{scene_location}.dialogues[{d_idx}]"
                    
                    if not dialogue.get("character"):
                        issues.append(Issue(
                            type="missing_field",
                            severity="major",
                            location=f"{dialogue_location}.character",
                            message=f"场景 {idx + 1} 对白 {d_idx + 1} 缺少角色名",
                            suggestion="为对白指定说话的角色"
                        ))
                    
                    if not dialogue.get("text"):
                        issues.append(Issue(
                            type="missing_field",
                            severity="major",
                            location=f"{dialogue_location}.text",
                            message=f"场景 {idx + 1} 对白 {d_idx + 1} 缺少文本内容",
                            suggestion="为对白添加文本内容"
                        ))
            
            # Duration check
            duration = scene.get("duration_sec", 0)
            if duration <= 0:
                issues.append(Issue(
                    type="invalid_format",
                    severity="major",
                    location=f"{scene_location}.duration_sec",
                    message=f"场景 {idx + 1} 时长无效或缺失",
                    suggestion="为场景设置合理的时长（秒）"
                ))
            elif duration > 300:  # 5 minutes
                issues.append(Issue(
                    type="invalid_format",
                    severity="minor",
                    location=f"{scene_location}.duration_sec",
                    message=f"场景 {idx + 1} 时长过长 ({duration} 秒)",
                    suggestion="考虑将长场景拆分为多个场景"
                ))
            
            total_duration += duration
        
        # Total duration check
        if total_duration > 1800:  # 30 minutes
            issues.append(Issue(
                type="invalid_format",
                severity="minor",
                location="script.total_duration",
                message=f"剧本总时长过长 ({total_duration} 秒 / {total_duration // 60} 分钟)",
                suggestion="考虑缩短剧本或拆分为多集"
            ))
        
        return issues
    
    def check_storyboard_rules(self, document: DocumentModel) -> List[Issue]:
        """
        Check Storyboard document rules.
        
        Implements Requirement 2.4
        
        Checks:
        - Shot count reasonableness
        - Total duration validation
        - Shot structure completeness
        
        Args:
            document: Storyboard document to check
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        
        # Get shots from database for this episode
        from app.repositories.shot_repository import ShotRepository
        shot_repo = ShotRepository(self.db)
        
        if not document.episode_id:
            issues.append(Issue(
                type="missing_field",
                severity="critical",
                location="storyboard.episode_id",
                message="Storyboard 文档缺少 episode_id",
                suggestion="确保 Storyboard 关联到正确的 Episode"
            ))
            return issues
        
        shots = shot_repo.list_current_for_episode(document.episode_id)
        
        # Shot count check
        if not shots:
            issues.append(Issue(
                type="missing_field",
                severity="critical",
                location="storyboard.shots",
                message="Storyboard 没有镜头",
                suggestion="至少需要定义一个镜头"
            ))
            return issues
        
        if len(shots) > 100:
            issues.append(Issue(
                type="invalid_format",
                severity="minor",
                location="storyboard.shots",
                message=f"镜头数量过多 ({len(shots)} 个)",
                suggestion="考虑简化镜头或拆分为多集"
            ))
        
        total_duration_ms = 0
        
        # Check each shot
        for shot in shots:
            shot_location = f"storyboard.shot[{shot.shot_code}]"
            
            # Required shot fields
            if not shot.duration_ms or shot.duration_ms <= 0:
                issues.append(Issue(
                    type="missing_field",
                    severity="major",
                    location=f"{shot_location}.duration_ms",
                    message=f"镜头 {shot.shot_code} 缺少有效时长",
                    suggestion="为镜头设置合理的时长（毫秒）"
                ))
            else:
                total_duration_ms += shot.duration_ms
                
                # Individual shot duration check
                if shot.duration_ms > 30000:  # 30 seconds
                    issues.append(Issue(
                        type="invalid_format",
                        severity="minor",
                        location=f"{shot_location}.duration_ms",
                        message=f"镜头 {shot.shot_code} 时长过长 ({shot.duration_ms / 1000} 秒)",
                        suggestion="考虑将长镜头拆分为多个镜头"
                    ))
            
            # Camera settings check
            if not shot.camera_size:
                issues.append(Issue(
                    type="missing_field",
                    severity="minor",
                    location=f"{shot_location}.camera_size",
                    message=f"镜头 {shot.shot_code} 缺少景别设置",
                    suggestion="为镜头设置景别（特写/近景/中景/远景等）"
                ))
            
            # Action or dialogue check
            if not shot.action_text and not shot.dialogue_text:
                issues.append(Issue(
                    type="missing_field",
                    severity="minor",
                    location=f"{shot_location}.content",
                    message=f"镜头 {shot.shot_code} 既没有动作描述也没有对白",
                    suggestion="为镜头添加动作描述或对白"
                ))
        
        # Total duration check
        total_duration_sec = total_duration_ms / 1000
        if total_duration_sec > 1800:  # 30 minutes
            issues.append(Issue(
                type="invalid_format",
                severity="minor",
                location="storyboard.total_duration",
                message=f"Storyboard 总时长过长 ({total_duration_sec:.1f} 秒 / {total_duration_sec / 60:.1f} 分钟)",
                suggestion="考虑缩短内容或拆分为多集"
            ))
        elif total_duration_sec < 30:  # Less than 30 seconds
            issues.append(Issue(
                type="invalid_format",
                severity="info",
                location="storyboard.total_duration",
                message=f"Storyboard 总时长较短 ({total_duration_sec:.1f} 秒)",
                suggestion="确认这是预期的时长"
            ))
        
        return issues

    def check_character_consistency(self, episode_id: UUID) -> List[Issue]:
        """
        Check character consistency across documents.
        
        Implements Requirement 3.1
        
        Compares characters defined in Character Profile with characters
        used in Script to ensure consistency.
        
        Checks:
        - All characters in Script are defined in Character Profile
        - Character descriptions are consistent
        - Character names match exactly
        
        Args:
            episode_id: Episode ID
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        
        # Get Character Profile and Script documents
        from app.repositories.document_repository import DocumentRepository
        doc_repo = DocumentRepository(self.db)
        
        documents = doc_repo.list_for_episode(episode_id)
        
        character_profile = None
        script = None
        
        for doc in documents:
            if doc.document_type == "character_profile":
                character_profile = doc
            elif doc.document_type == "script":
                script = doc
        
        # If either document is missing, we can't check consistency
        if not character_profile:
            issues.append(Issue(
                type="missing_document",
                severity="info",
                location="semantic_check.character_consistency",
                message="Character Profile 文档不存在，无法检查角色一致性",
                suggestion="先创建 Character Profile 文档"
            ))
            return issues
        
        if not script:
            issues.append(Issue(
                type="missing_document",
                severity="info",
                location="semantic_check.character_consistency",
                message="Script 文档不存在，无法检查角色一致性",
                suggestion="先创建 Script 文档"
            ))
            return issues
        
        # Extract characters from Character Profile
        char_profile_content = character_profile.content_jsonb or {}
        defined_characters = char_profile_content.get("characters", [])
        
        if not defined_characters:
            issues.append(Issue(
                type="missing_data",
                severity="major",
                location="character_profile.characters",
                message="Character Profile 中没有定义角色",
                suggestion="在 Character Profile 中定义角色"
            ))
            return issues
        
        # Build a map of character names to their definitions
        char_map = {}
        for char in defined_characters:
            name = char.get("name", "").strip()
            if name:
                char_map[name.lower()] = char
        
        # Extract characters used in Script
        script_content = script.content_jsonb or {}
        scenes = script_content.get("scenes", [])
        
        script_characters = set()
        
        for scene in scenes:
            dialogues = scene.get("dialogues", [])
            for dialogue in dialogues:
                character_name = dialogue.get("character", "").strip()
                if character_name:
                    script_characters.add(character_name)
        
        # Check if all script characters are defined in Character Profile
        for script_char in script_characters:
            if script_char.lower() not in char_map:
                issues.append(Issue(
                    type="undefined_character",
                    severity="major",
                    location=f"script.character.{script_char}",
                    message=f"Script 中使用的角色 '{script_char}' 未在 Character Profile 中定义",
                    suggestion=f"在 Character Profile 中添加角色 '{script_char}' 的定义"
                ))
        
        # Check for unused characters (defined but not used in script)
        used_char_names = {name.lower() for name in script_characters}
        for defined_name in char_map.keys():
            if defined_name not in used_char_names:
                original_name = char_map[defined_name].get("name", "")
                issues.append(Issue(
                    type="unused_character",
                    severity="info",
                    location=f"character_profile.character.{original_name}",
                    message=f"Character Profile 中定义的角色 '{original_name}' 未在 Script 中使用",
                    suggestion=f"考虑在 Script 中使用角色 '{original_name}' 或从 Character Profile 中移除"
                ))
        
        return issues
    
    def check_world_consistency(self, episode_id: UUID) -> List[Issue]:
        """
        Check world-building consistency.
        
        Implements Requirement 3.2
        
        Loads Story Bible settings and checks if Script violates
        any established world-building rules.
        
        Checks:
        - Script follows Story Bible settings
        - No contradictions with established world rules
        - Consistent use of world-specific terminology
        
        Args:
            episode_id: Episode ID
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        
        # Get Story Bible and Script documents
        from app.repositories.document_repository import DocumentRepository
        doc_repo = DocumentRepository(self.db)
        
        documents = doc_repo.list_for_episode(episode_id)
        
        story_bible = None
        script = None
        
        for doc in documents:
            if doc.document_type == "story_bible":
                story_bible = doc
            elif doc.document_type == "script":
                script = doc
        
        # If Story Bible doesn't exist, we can't check world consistency
        if not story_bible:
            issues.append(Issue(
                type="missing_document",
                severity="info",
                location="semantic_check.world_consistency",
                message="Story Bible 文档不存在，无法检查世界观一致性",
                suggestion="先创建 Story Bible 文档以定义世界观设定"
            ))
            return issues
        
        if not script:
            issues.append(Issue(
                type="missing_document",
                severity="info",
                location="semantic_check.world_consistency",
                message="Script 文档不存在，无法检查世界观一致性",
                suggestion="先创建 Script 文档"
            ))
            return issues
        
        # Extract world-building rules from Story Bible
        bible_content = story_bible.content_jsonb or {}
        world_rules = bible_content.get("world_rules", [])
        setting = bible_content.get("setting", {})
        
        if not world_rules and not setting:
            issues.append(Issue(
                type="missing_data",
                severity="minor",
                location="story_bible.world_rules",
                message="Story Bible 中没有定义世界观规则或设定",
                suggestion="在 Story Bible 中添加世界观规则和设定"
            ))
            return issues
        
        # Extract script content for checking
        script_content = script.content_jsonb or {}
        scenes = script_content.get("scenes", [])
        
        # Check for basic world consistency
        # This is a simplified check - in a real system, this would use NLP/LLM
        # to understand semantic violations
        
        # Example: Check if script mentions locations that contradict the setting
        if setting:
            time_period = setting.get("time_period", "").lower()
            location_type = setting.get("location_type", "").lower()
            
            # Check for anachronisms if time period is specified
            if "ancient" in time_period or "medieval" in time_period:
                modern_terms = ["phone", "computer", "internet", "car", "airplane", "电话", "电脑", "互联网", "汽车", "飞机"]
                
                for scene_idx, scene in enumerate(scenes):
                    scene_text = f"{scene.get('location', '')} {scene.get('action_text', '')}"
                    
                    for dialogue in scene.get("dialogues", []):
                        scene_text += f" {dialogue.get('text', '')}"
                    
                    scene_text_lower = scene_text.lower()
                    
                    for term in modern_terms:
                        if term in scene_text_lower:
                            issues.append(Issue(
                                type="world_violation",
                                severity="major",
                                location=f"script.scenes[{scene_idx}]",
                                message=f"场景 {scene_idx + 1} 中出现与时代设定 '{time_period}' 不符的现代元素 '{term}'",
                                suggestion=f"移除或替换与 {time_period} 时代不符的元素"
                            ))
        
        # Check against explicit world rules
        for rule_idx, rule in enumerate(world_rules):
            rule_text = rule.get("rule", "") if isinstance(rule, dict) else str(rule)
            
            # This is a placeholder for more sophisticated rule checking
            # In a real system, this would use semantic analysis
            if not rule_text:
                continue
            
            # Example: Check if rule mentions "no magic" but script has magic
            if "no magic" in rule_text.lower() or "无魔法" in rule_text.lower():
                magic_terms = ["magic", "spell", "wizard", "魔法", "咒语", "巫师"]
                
                for scene_idx, scene in enumerate(scenes):
                    scene_text = f"{scene.get('action_text', '')}"
                    
                    for dialogue in scene.get("dialogues", []):
                        scene_text += f" {dialogue.get('text', '')}"
                    
                    scene_text_lower = scene_text.lower()
                    
                    for term in magic_terms:
                        if term in scene_text_lower:
                            issues.append(Issue(
                                type="world_violation",
                                severity="major",
                                location=f"script.scenes[{scene_idx}]",
                                message=f"场景 {scene_idx + 1} 中出现魔法元素，违反世界观规则 '{rule_text}'",
                                suggestion="移除魔法元素或修改世界观规则"
                            ))
        
        return issues
    
    def check_plot_coherence(self, episode_id: UUID) -> List[Issue]:
        """
        Check plot coherence and continuity.
        
        Implements Requirement 3.3
        
        Checks if scene transitions are reasonable and timeline is coherent.
        
        Checks:
        - Scene transitions make sense
        - Timeline is coherent
        - No logical contradictions in plot
        - Character actions are consistent
        
        Args:
            episode_id: Episode ID
            
        Returns:
            List of issues found
        """
        issues: List[Issue] = []
        
        # Get Script document
        from app.repositories.document_repository import DocumentRepository
        doc_repo = DocumentRepository(self.db)
        
        documents = doc_repo.list_for_episode(episode_id)
        
        script = None
        for doc in documents:
            if doc.document_type == "script":
                script = doc
                break
        
        if not script:
            issues.append(Issue(
                type="missing_document",
                severity="info",
                location="semantic_check.plot_coherence",
                message="Script 文档不存在，无法检查情节连贯性",
                suggestion="先创建 Script 文档"
            ))
            return issues
        
        # Extract scenes from Script
        script_content = script.content_jsonb or {}
        scenes = script_content.get("scenes", [])
        
        if not scenes:
            issues.append(Issue(
                type="missing_data",
                severity="major",
                location="script.scenes",
                message="Script 中没有场景，无法检查情节连贯性",
                suggestion="在 Script 中添加场景"
            ))
            return issues
        
        # Check scene transitions
        for i in range(len(scenes) - 1):
            current_scene = scenes[i]
            next_scene = scenes[i + 1]
            
            current_location = current_scene.get("location", "").strip()
            next_location = next_scene.get("location", "").strip()
            
            current_time = current_scene.get("time_of_day", "").strip()
            next_time = next_scene.get("time_of_day", "").strip()
            
            # Check for abrupt location changes without explanation
            if current_location and next_location:
                # If locations are very different and there's no transition indication
                # This is a simplified check - in reality would need more context
                if current_location.lower() != next_location.lower():
                    # Check if there's any transition indication in the scene
                    current_action = current_scene.get("action_text", "").lower()
                    transition_words = ["前往", "到达", "离开", "进入", "走向", "travel", "arrive", "leave", "enter", "go to"]
                    
                    has_transition = any(word in current_action for word in transition_words)
                    
                    if not has_transition:
                        issues.append(Issue(
                            type="abrupt_transition",
                            severity="minor",
                            location=f"script.scenes[{i}].transition",
                            message=f"场景 {i + 1} 到场景 {i + 2} 的地点转换较突然（从 '{current_location}' 到 '{next_location}'）",
                            suggestion="考虑添加过渡场景或在动作描述中说明转换"
                        ))
            
            # Check for timeline coherence
            if current_time and next_time:
                time_order = ["morning", "afternoon", "evening", "night", "早晨", "上午", "下午", "傍晚", "晚上", "深夜"]
                
                try:
                    current_time_lower = current_time.lower()
                    next_time_lower = next_time.lower()
                    
                    # Find time indices
                    current_idx = -1
                    next_idx = -1
                    
                    for idx, time_word in enumerate(time_order):
                        if time_word in current_time_lower:
                            current_idx = idx
                        if time_word in next_time_lower:
                            next_idx = idx
                    
                    # Check if time goes backwards without explanation
                    if current_idx != -1 and next_idx != -1:
                        if next_idx < current_idx:
                            # Time went backwards - might be a new day or flashback
                            current_action = current_scene.get("action_text", "").lower()
                            next_action = next_scene.get("action_text", "").lower()
                            
                            flashback_words = ["回忆", "闪回", "过去", "flashback", "memory", "past"]
                            new_day_words = ["第二天", "次日", "隔天", "next day", "following day"]
                            
                            has_explanation = any(
                                word in current_action or word in next_action
                                for word in flashback_words + new_day_words
                            )
                            
                            if not has_explanation:
                                issues.append(Issue(
                                    type="timeline_inconsistency",
                                    severity="minor",
                                    location=f"script.scenes[{i}].timeline",
                                    message=f"场景 {i + 1} 到场景 {i + 2} 的时间线不连贯（从 '{current_time}' 到 '{next_time}'）",
                                    suggestion="添加时间转换说明（如'第二天'或'回忆'）"
                                ))
                except Exception:
                    # If time parsing fails, skip this check
                    pass
        
        # Check for character consistency within scenes
        # Track which characters appear in which scenes
        character_appearances = {}
        
        for scene_idx, scene in enumerate(scenes):
            scene_characters = set()
            
            # Get characters from dialogues
            for dialogue in scene.get("dialogues", []):
                char_name = dialogue.get("character", "").strip()
                if char_name:
                    scene_characters.add(char_name)
            
            # Get characters mentioned in action
            action_text = scene.get("action_text", "")
            # This is simplified - would need NLP to properly extract character mentions
            
            for char_name in scene_characters:
                if char_name not in character_appearances:
                    character_appearances[char_name] = []
                character_appearances[char_name].append(scene_idx)
        
        # Check for characters that appear, disappear, and reappear without explanation
        for char_name, appearances in character_appearances.items():
            if len(appearances) > 1:
                # Check for gaps in appearances
                for i in range(len(appearances) - 1):
                    gap = appearances[i + 1] - appearances[i]
                    
                    # If character disappears for more than 2 scenes and reappears
                    if gap > 2:
                        # Check if there's an explanation for the absence
                        missing_scenes = range(appearances[i] + 1, appearances[i + 1])
                        
                        has_explanation = False
                        for scene_idx in missing_scenes:
                            if scene_idx < len(scenes):
                                scene = scenes[scene_idx]
                                action = scene.get("action_text", "").lower()
                                
                                leave_words = ["离开", "走了", "离去", "leave", "left", "depart"]
                                if any(word in action for word in leave_words):
                                    has_explanation = True
                                    break
                        
                        if not has_explanation:
                            issues.append(Issue(
                                type="character_continuity",
                                severity="info",
                                location=f"script.character.{char_name}",
                                message=f"角色 '{char_name}' 在场景 {appearances[i] + 1} 出现后消失，在场景 {appearances[i + 1] + 1} 又重新出现",
                                suggestion="考虑说明角色的去向或添加过渡场景"
                            ))
        
        return issues
