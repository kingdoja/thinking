"""
Shot 数据完整性验证脚本

验证 Shot 表结构和数据完整性，包括：
1. 检查所有必需字段是否存在
2. 验证字段类型和约束
3. 检查 visual_constraints_jsonb 结构
4. 验证 character_refs 引用有效性
5. 验证 Shot 与 visual_spec 的一致性

需求: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1
"""

import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import ShotModel, DocumentModel
from app.repositories.shot_repository import ShotRepository
from app.repositories.document_repository import DocumentRepository


@dataclass
class ValidationError:
    """验证错误"""
    field_path: str
    error_type: str  # missing_required, invalid_format, invalid_reference, inconsistency
    message: str
    shot_id: Optional[str] = None
    episode_id: Optional[str] = None


@dataclass
class ValidationWarning:
    """验证警告"""
    field_path: str
    warning_type: str  # missing_optional, suboptimal, inconsistency
    message: str
    suggestion: str
    shot_id: Optional[str] = None
    episode_id: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class ShotIntegrityValidator:
    """Shot 数据完整性验证器"""
    
    # 必需字段列表
    REQUIRED_FIELDS = [
        'id', 'project_id', 'episode_id', 'scene_no', 'shot_no', 
        'shot_code', 'status', 'duration_ms', 'characters_jsonb',
        'visual_constraints_jsonb', 'version', 'created_at', 'updated_at'
    ]
    
    # visual_constraints 必需字段
    VISUAL_CONSTRAINTS_REQUIRED = ['render_prompt', 'style_keywords', 'composition', 'character_refs']
    
    def __init__(self, db: Session):
        self.db = db
        self.shot_repo = ShotRepository(db)
        self.doc_repo = DocumentRepository(db)
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationWarning] = []
        self.stats: Dict[str, Any] = {}
    
    def validate_all(self) -> ValidationResult:
        """执行所有验证检查"""
        print("=" * 80)
        print("Shot 数据完整性验证")
        print("=" * 80)
        print()
        
        # 1. 验证表结构
        print("1. 验证 Shot 表结构...")
        self._validate_table_structure()
        print()
        
        # 2. 验证所有 Shot 记录
        print("2. 验证 Shot 记录完整性...")
        shots = self._get_all_shots()
        self.stats['total_shots'] = len(shots)
        print(f"   找到 {len(shots)} 条 Shot 记录")
        
        for shot in shots:
            self._validate_shot_completeness(shot)
        print()
        
        # 3. 验证 visual_constraints 结构
        print("3. 验证 visual_constraints_jsonb 结构...")
        for shot in shots:
            self._validate_visual_constraints_schema(shot)
        print()
        
        # 4. 验证 character_refs 引用
        print("4. 验证 character_refs 引用有效性...")
        self._validate_character_refs(shots)
        print()
        
        # 5. 验证 Shot 与 visual_spec 一致性
        print("5. 验证 Shot 与 visual_spec 一致性...")
        self._validate_shot_visual_spec_consistency(shots)
        print()
        
        # 生成结果
        is_valid = len(self.errors) == 0
        result = ValidationResult(
            is_valid=is_valid,
            errors=self.errors,
            warnings=self.warnings,
            stats=self.stats
        )
        
        self._print_summary(result)
        return result
    
    def _validate_table_structure(self):
        """验证 Shot 表结构"""
        inspector = inspect(self.db.bind)
        
        # 检查表是否存在
        if 'shots' not in inspector.get_table_names():
            self.errors.append(ValidationError(
                field_path='shots',
                error_type='missing_required',
                message='Shot 表不存在'
            ))
            print("   ❌ Shot 表不存在")
            return
        
        # 获取列信息
        columns = {col['name']: col for col in inspector.get_columns('shots')}
        
        # 检查必需字段
        missing_fields = []
        for field in self.REQUIRED_FIELDS:
            if field not in columns:
                missing_fields.append(field)
                self.errors.append(ValidationError(
                    field_path=f'shots.{field}',
                    error_type='missing_required',
                    message=f'必需字段 {field} 不存在'
                ))
        
        if missing_fields:
            print(f"   ❌ 缺少必需字段: {', '.join(missing_fields)}")
        else:
            print(f"   ✓ 所有必需字段存在 ({len(self.REQUIRED_FIELDS)} 个)")
        
        # 检查索引
        indexes = inspector.get_indexes('shots')
        index_names = [idx['name'] for idx in indexes]
        
        expected_indexes = [
            'idx_shots_project_episode_scene_shot',
            'idx_shots_episode_version'
        ]
        
        missing_indexes = [idx for idx in expected_indexes if idx not in index_names]
        if missing_indexes:
            for idx in missing_indexes:
                self.warnings.append(ValidationWarning(
                    field_path=f'shots.index.{idx}',
                    warning_type='missing_optional',
                    message=f'推荐的索引 {idx} 不存在',
                    suggestion='创建索引以提高查询性能'
                ))
            print(f"   ⚠ 缺少推荐索引: {', '.join(missing_indexes)}")
        else:
            print(f"   ✓ 所有推荐索引存在")
    
    def _get_all_shots(self) -> List[ShotModel]:
        """获取所有 Shot 记录"""
        stmt = select(ShotModel).order_by(
            ShotModel.episode_id,
            ShotModel.version.desc(),
            ShotModel.scene_no,
            ShotModel.shot_no
        )
        return list(self.db.scalars(stmt).all())
    
    def _validate_shot_completeness(self, shot: ShotModel):
        """验证单个 Shot 的完整性"""
        shot_id = str(shot.id)
        episode_id = str(shot.episode_id)
        
        # 检查必需字段是否为 None
        if shot.scene_no is None:
            self.errors.append(ValidationError(
                field_path='scene_no',
                error_type='missing_required',
                message='scene_no 字段为空',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if shot.shot_no is None:
            self.errors.append(ValidationError(
                field_path='shot_no',
                error_type='missing_required',
                message='shot_no 字段为空',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if not shot.shot_code:
            self.errors.append(ValidationError(
                field_path='shot_code',
                error_type='missing_required',
                message='shot_code 字段为空',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if shot.duration_ms is None or shot.duration_ms <= 0:
            self.errors.append(ValidationError(
                field_path='duration_ms',
                error_type='invalid_format',
                message=f'duration_ms 无效: {shot.duration_ms}',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        # 检查可选字段
        if not shot.camera_size:
            self.warnings.append(ValidationWarning(
                field_path='camera_size',
                warning_type='missing_optional',
                message='camera_size 字段为空',
                suggestion='建议填充 camera_size 以提供完整的镜头信息',
                shot_id=shot_id,
                episode_id=episode_id
            ))
        
        if not shot.camera_angle:
            self.warnings.append(ValidationWarning(
                field_path='camera_angle',
                warning_type='missing_optional',
                message='camera_angle 字段为空',
                suggestion='建议填充 camera_angle 以提供完整的镜头信息',
                shot_id=shot_id,
                episode_id=episode_id
            ))
    
    def _validate_visual_constraints_schema(self, shot: ShotModel):
        """验证 visual_constraints_jsonb 的结构"""
        shot_id = str(shot.id)
        episode_id = str(shot.episode_id)
        
        vc = shot.visual_constraints_jsonb
        
        if not vc or not isinstance(vc, dict):
            self.errors.append(ValidationError(
                field_path='visual_constraints_jsonb',
                error_type='invalid_format',
                message='visual_constraints_jsonb 不是有效的字典',
                shot_id=shot_id,
                episode_id=episode_id
            ))
            return
        
        # 检查必需字段
        for field in self.VISUAL_CONSTRAINTS_REQUIRED:
            if field not in vc:
                self.errors.append(ValidationError(
                    field_path=f'visual_constraints_jsonb.{field}',
                    error_type='missing_required',
                    message=f'visual_constraints 缺少必需字段: {field}',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
        
        # 验证 render_prompt
        if 'render_prompt' in vc:
            prompt = vc['render_prompt']
            if not prompt or not isinstance(prompt, str):
                self.errors.append(ValidationError(
                    field_path='visual_constraints_jsonb.render_prompt',
                    error_type='invalid_format',
                    message='render_prompt 为空或不是字符串',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
            elif len(prompt) < 10:
                self.warnings.append(ValidationWarning(
                    field_path='visual_constraints_jsonb.render_prompt',
                    warning_type='suboptimal',
                    message=f'render_prompt 过短 ({len(prompt)} 字符)',
                    suggestion='建议 render_prompt 至少 10 个字符',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
        
        # 验证 style_keywords
        if 'style_keywords' in vc:
            if not isinstance(vc['style_keywords'], list):
                self.errors.append(ValidationError(
                    field_path='visual_constraints_jsonb.style_keywords',
                    error_type='invalid_format',
                    message='style_keywords 不是数组',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
        
        # 验证 character_refs
        if 'character_refs' in vc:
            if not isinstance(vc['character_refs'], list):
                self.errors.append(ValidationError(
                    field_path='visual_constraints_jsonb.character_refs',
                    error_type='invalid_format',
                    message='character_refs 不是数组',
                    shot_id=shot_id,
                    episode_id=episode_id
                ))
    
    def _validate_character_refs(self, shots: List[ShotModel]):
        """验证 character_refs 引用的有效性"""
        # 按 episode 分组
        episodes_shots: Dict[UUID, List[ShotModel]] = {}
        for shot in shots:
            if shot.episode_id not in episodes_shots:
                episodes_shots[shot.episode_id] = []
            episodes_shots[shot.episode_id].append(shot)
        
        # 对每个 episode 验证
        for episode_id, episode_shots in episodes_shots.items():
            # 获取 character_profile 文档
            character_profile = self._get_latest_document(episode_id, 'character_profile')
            
            if not character_profile:
                self.warnings.append(ValidationWarning(
                    field_path='character_profile',
                    warning_type='missing_optional',
                    message=f'Episode {episode_id} 没有 character_profile 文档',
                    suggestion='创建 character_profile 文档以验证角色引用',
                    episode_id=str(episode_id)
                ))
                continue
            
            # 提取角色名称
            character_names = self._extract_character_names(character_profile)
            
            # 验证每个 Shot 的 character_refs
            for shot in episode_shots:
                vc = shot.visual_constraints_jsonb
                if not vc or 'character_refs' not in vc:
                    continue
                
                char_refs = vc['character_refs']
                if not isinstance(char_refs, list):
                    continue
                
                for char_name in char_refs:
                    if char_name not in character_names:
                        self.errors.append(ValidationError(
                            field_path='visual_constraints_jsonb.character_refs',
                            error_type='invalid_reference',
                            message=f'角色 "{char_name}" 在 character_profile 中不存在',
                            shot_id=str(shot.id),
                            episode_id=str(episode_id)
                        ))
    
    def _validate_shot_visual_spec_consistency(self, shots: List[ShotModel]):
        """验证 Shot 与 visual_spec 的一致性"""
        # 按 episode 和 version 分组
        episodes_versions: Dict[tuple, List[ShotModel]] = {}
        for shot in shots:
            key = (shot.episode_id, shot.version)
            if key not in episodes_versions:
                episodes_versions[key] = []
            episodes_versions[key].append(shot)
        
        # 对每个 episode-version 组合验证
        for (episode_id, version), episode_shots in episodes_versions.items():
            # 获取对应版本的 visual_spec 文档
            visual_spec = self._get_document_by_version(episode_id, 'visual_spec', version)
            
            if not visual_spec:
                self.warnings.append(ValidationWarning(
                    field_path='visual_spec',
                    warning_type='inconsistency',
                    message=f'Episode {episode_id} version {version} 没有对应的 visual_spec 文档',
                    suggestion='确保 Storyboard Agent 同时创建 visual_spec 和 Shot 记录',
                    episode_id=str(episode_id)
                ))
                continue
            
            content = visual_spec.content_jsonb
            
            # 验证 shot_count
            if 'shot_count' in content:
                expected_count = content['shot_count']
                actual_count = len(episode_shots)
                
                if expected_count != actual_count:
                    self.errors.append(ValidationError(
                        field_path='shot_count',
                        error_type='inconsistency',
                        message=f'Shot 数量不一致: visual_spec.shot_count={expected_count}, 实际 Shot 数量={actual_count}',
                        episode_id=str(episode_id)
                    ))
            
            # 验证 shots 数组
            if 'shots' in content and isinstance(content['shots'], list):
                spec_shots = content['shots']
                
                # 创建 shot_code 到 Shot 的映射
                shot_map = {shot.shot_code: shot for shot in episode_shots}
                
                for spec_shot in spec_shots:
                    if 'shot_id' not in spec_shot:
                        continue
                    
                    shot_code = spec_shot.get('shot_id')
                    if shot_code not in shot_map:
                        self.warnings.append(ValidationWarning(
                            field_path='visual_spec.shots',
                            warning_type='inconsistency',
                            message=f'visual_spec 中的 shot_id "{shot_code}" 在 Shot 表中不存在',
                            suggestion='检查 Storyboard Agent 的 committer 逻辑',
                            episode_id=str(episode_id)
                        ))
    
    def _get_latest_document(self, episode_id: UUID, document_type: str) -> Optional[DocumentModel]:
        """获取最新版本的文档"""
        stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.episode_id == episode_id,
                DocumentModel.document_type == document_type
            )
            .order_by(DocumentModel.version.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
    
    def _get_document_by_version(self, episode_id: UUID, document_type: str, version: int) -> Optional[DocumentModel]:
        """获取指定版本的文档"""
        stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.episode_id == episode_id,
                DocumentModel.document_type == document_type,
                DocumentModel.version == version
            )
            .limit(1)
        )
        return self.db.scalar(stmt)
    
    def _extract_character_names(self, character_profile: DocumentModel) -> set:
        """从 character_profile 提取角色名称"""
        content = character_profile.content_jsonb
        character_names = set()
        
        if 'characters' in content and isinstance(content['characters'], list):
            for char in content['characters']:
                if 'name' in char:
                    character_names.add(char['name'])
        
        return character_names
    
    def _print_summary(self, result: ValidationResult):
        """打印验证摘要"""
        print("=" * 80)
        print("验证摘要")
        print("=" * 80)
        print()
        
        # 统计信息
        print("统计信息:")
        print(f"  总 Shot 数量: {result.stats.get('total_shots', 0)}")
        print()
        
        # 错误
        if result.errors:
            print(f"❌ 发现 {len(result.errors)} 个错误:")
            print()
            for i, error in enumerate(result.errors[:10], 1):  # 只显示前 10 个
                print(f"  {i}. [{error.error_type}] {error.field_path}")
                print(f"     {error.message}")
                if error.shot_id:
                    print(f"     Shot ID: {error.shot_id}")
                if error.episode_id:
                    print(f"     Episode ID: {error.episode_id}")
                print()
            
            if len(result.errors) > 10:
                print(f"  ... 还有 {len(result.errors) - 10} 个错误")
                print()
        else:
            print("✓ 没有发现错误")
            print()
        
        # 警告
        if result.warnings:
            print(f"⚠ 发现 {len(result.warnings)} 个警告:")
            print()
            for i, warning in enumerate(result.warnings[:10], 1):  # 只显示前 10 个
                print(f"  {i}. [{warning.warning_type}] {warning.field_path}")
                print(f"     {warning.message}")
                print(f"     建议: {warning.suggestion}")
                if warning.shot_id:
                    print(f"     Shot ID: {warning.shot_id}")
                if warning.episode_id:
                    print(f"     Episode ID: {warning.episode_id}")
                print()
            
            if len(result.warnings) > 10:
                print(f"  ... 还有 {len(result.warnings) - 10} 个警告")
                print()
        else:
            print("✓ 没有发现警告")
            print()
        
        # 最终结果
        print("=" * 80)
        if result.is_valid:
            print("✓ 验证通过")
        else:
            print("❌ 验证失败")
        print("=" * 80)


def main():
    """主函数"""
    db = SessionLocal()
    try:
        validator = ShotIntegrityValidator(db)
        result = validator.validate_all()
        
        # 返回退出码
        sys.exit(0 if result.is_valid else 1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
