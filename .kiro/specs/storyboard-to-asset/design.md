# Iteration 3: Storyboard 到 Asset 工作台 - 设计文档

## 概述

本迭代的核心目标是验证和完善 Shot 结构，确保 Storyboard 可以稳定驱动后续的媒体链路。通过验证 Shot 模型、visual_spec 文档结构，以及设计 image_render 输入构建逻辑，为 Iteration 4 的图像生成做好准备。

关键设计原则：
- **数据完整性优先**: 确保 Shot 和 visual_spec 包含所有必需字段
- **版本控制**: Shot 和 visual_spec 都支持版本控制，重跑不覆盖旧版本
- **关联一致性**: Shot 记录与 visual_spec 文档保持一致
- **可扩展性**: 设计支持未来的资产选择和重跑功能

## 架构

### Shot 数据流

```
Storyboard Agent
    ↓
visual_spec Document (JSON)
    ↓
Shot Records (Database)
    ↓
image_render Input Builder
    ↓
Image Render Stage
    ↓
Asset Records (Keyframes)
```

### 组件关系

```
┌─────────────────────────────────────────────────────────┐
│                  Storyboard Agent                       │
│  生成 visual_spec 和 Shot 记录                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ├─────────────────┬────────────────────┐
                   ↓                 ↓                    ↓
         ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
         │ visual_spec Doc  │ │ Shot Records │ │ character_profile│
         │ (Document table) │ │ (shots table)│ │ (Document table) │
         └──────────────────┘ └──────────────┘ └─────────────────┘
                   │                 │                    │
                   └─────────────────┴────────────────────┘
                                     ↓
                   ┌──────────────────────────────────────┐
                   │  ImageRenderInputBuilder Service     │
                   │  组装完整的图像生成参数               │
                   └──────────────────┬───────────────────┘
                                      ↓
                   ┌──────────────────────────────────────┐
                   │      Image Render Stage              │
                   │  (Iteration 4 实现)                  │
                   └──────────────────┬───────────────────┘
                                      ↓
                   ┌──────────────────────────────────────┐
                   │      Asset Records                   │
                   │  (assets table)                      │
                   └──────────────────────────────────────┘
```

## 组件和接口

### Shot 模型（已存在）

```python
class Shot:
    # 标识字段
    id: UUID
    project_id: UUID
    episode_id: UUID
    stage_task_id: UUID  # nullable
    
    # 分镜信息
    scene_no: int  # 场景编号
    shot_no: int  # 镜头编号
    shot_code: str  # 镜头代码，如 "S01_001"
    status: str  # draft, confirmed, rendering, completed
    
    # 时长和镜头参数
    duration_ms: int  # 镜头时长（毫秒）
    camera_size: str  # close-up, medium, wide
    camera_angle: str  # eye-level, low, high
    movement_type: str  # static, pan, zoom, dolly
    
    # 内容信息
    characters_jsonb: list[str]  # 出现的角色名称列表
    action_text: str  # 动作描述
    dialogue_text: str  # 对白文本
    
    # 视觉约束（核心字段）
    visual_constraints_jsonb: dict  # 详见下方结构
    
    # 版本控制
    version: int
    created_at: datetime
    updated_at: datetime
```

### visual_constraints_jsonb 结构

```python
{
    "render_prompt": str,  # 完整的渲染提示词
    "style_keywords": list[str],  # 风格关键词
    "composition": str,  # 镜头构图
    "character_refs": list[str],  # 角色引用
    "locked_fields": list[str]  # 可选：锁定的字段列表
}
```

### visual_spec 文档结构

```python
{
    "shots": [
        {
            "shot_id": str,  # 唯一镜头ID
            "render_prompt": str,  # 渲染提示词
            "character_refs": list[str],  # 角色引用
            "style_keywords": list[str],  # 风格关键词
            "composition": str  # 镜头构图
        }
    ],
    "overall_duration_ms": int,  # 总时长
    "shot_count": int,  # 镜头数量
    "visual_style": str,  # 整体视觉风格
    "camera_strategy": str  # 镜头策略
}
```

### ImageRenderInputBuilder 服务

```python
class ImageRenderInputBuilder:
    """
    构建 image_render Stage 的输入参数。
    
    职责：
    1. 加载 Shot 的 visual_constraints
    2. 加载关联的 character_profile
    3. 合并 render_prompt 和 visual_anchor
    4. 组装完整的图像生成参数
    """
    
    def build_input_for_shot(
        self,
        shot_id: UUID,
        episode_id: UUID
    ) -> ImageRenderInput:
        """
        为单个 Shot 构建 image_render 输入。
        
        Returns:
            ImageRenderInput: 包含完整参数的输入对象
        """
        pass
    
    def build_inputs_for_episode(
        self,
        episode_id: UUID
    ) -> list[ImageRenderInput]:
        """
        为整个 Episode 的所有 Shot 批量构建输入。
        
        Returns:
            list[ImageRenderInput]: 所有 Shot 的输入参数列表
        """
        pass
    
    def _merge_prompt_with_anchors(
        self,
        render_prompt: str,
        character_refs: list[str],
        character_profile: dict
    ) -> str:
        """
        合并 render_prompt 和角色的 visual_anchor。
        
        逻辑：
        1. 提取 character_refs 中每个角色的 visual_anchor
        2. 检查 render_prompt 是否已包含 visual_anchor 的关键词
        3. 如果未包含，将 visual_anchor 插入到 render_prompt 中
        4. 返回增强后的 render_prompt
        """
        pass
```

### ImageRenderInput 数据结构

```python
@dataclass
class ImageRenderInput:
    """image_render Stage 的输入参数"""
    
    shot_id: UUID
    episode_id: UUID
    
    # 核心参数
    prompt: str  # 完整的渲染提示词（已合并 visual_anchor）
    negative_prompt: str  # 负面提示词
    
    # 风格参数
    style_keywords: list[str]  # 风格关键词
    visual_style: str  # 整体视觉风格
    
    # 构图参数
    composition: str  # 镜头构图
    camera_size: str  # 镜头大小
    camera_angle: str  # 镜头角度
    
    # 角色参数
    character_refs: list[str]  # 角色引用
    character_anchors: dict[str, str]  # {角色名: visual_anchor}
    
    # 技术参数
    aspect_ratio: str  # 画面比例，如 "9:16"
    resolution: tuple[int, int]  # 分辨率，如 (1080, 1920)
    
    # 元数据
    scene_no: int
    shot_no: int
    shot_code: str
```

### ShotValidationService 验证服务

```python
class ShotValidationService:
    """
    验证 Shot 数据的完整性和一致性。
    """
    
    def validate_shot_completeness(
        self,
        shot: Shot
    ) -> ValidationResult:
        """
        验证 Shot 的必需字段是否完整。
        
        检查项：
        1. 所有必需字段是否存在
        2. visual_constraints_jsonb 结构是否完整
        3. character_refs 引用的角色是否存在
        4. duration_ms 是否合理
        """
        pass
    
    def validate_visual_constraints_schema(
        self,
        visual_constraints: dict
    ) -> ValidationResult:
        """
        验证 visual_constraints 的 Schema。
        
        检查项：
        1. render_prompt 是否非空
        2. style_keywords 是否为数组
        3. composition 是否为有效值
        4. character_refs 是否为数组
        """
        pass
    
    def validate_shot_visual_spec_consistency(
        self,
        episode_id: UUID
    ) -> ValidationResult:
        """
        验证 Shot 记录与 visual_spec 文档的一致性。
        
        检查项：
        1. Shot 数量与 visual_spec.shot_count 是否一致
        2. Shot 的 visual_constraints 是否与 visual_spec.shots 对应
        3. 总时长是否一致
        """
        pass
```

### ValidationResult 数据结构

```python
@dataclass
class ValidationResult:
    """验证结果"""
    
    is_valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationWarning]
    
@dataclass
class ValidationError:
    """验证错误"""
    
    field_path: str  # 字段路径，如 "visual_constraints.render_prompt"
    error_type: str  # missing_required, invalid_format, invalid_reference
    message: str  # 错误消息
    
@dataclass
class ValidationWarning:
    """验证警告"""
    
    field_path: str
    warning_type: str  # inconsistency, missing_optional, suboptimal
    message: str
    suggestion: str  # 改进建议
```

## 数据模型

### Shot 状态机

```
draft → confirmed → rendering → completed
  ↓         ↓           ↓
failed ← failed ← failed
```

状态说明：
- **draft**: 初始状态，Storyboard Agent 生成后的状态
- **confirmed**: 用户确认后的状态，可以进入渲染
- **rendering**: 正在渲染图像
- **completed**: 渲染完成，有可用的主资产
- **failed**: 渲染失败

### Shot 版本控制策略

1. **初始创建**: Storyboard Agent 创建 Shot 时，version = 1
2. **用户编辑**: 用户编辑 Shot 的 visual_constraints 时，创建新版本（version + 1）
3. **重跑生成**: 重跑 Storyboard Stage 时，创建新版本的所有 Shot
4. **版本查询**: 默认查询最新版本，可以指定版本号查询历史版本

### Shot 与 visual_spec 的关联关系

```
visual_spec Document (version N)
    ↓ (1:N)
Shot Records (version N)
    ↓ (1:N)
Asset Records (shot_id)
```

关联规则：
1. 一个 visual_spec 文档对应多个 Shot 记录（数量 = shot_count）
2. 一个 Shot 记录对应多个 Asset 记录（候选资产）
3. visual_spec 和 Shot 的版本号保持一致
4. 重跑时，visual_spec 和 Shot 同时创建新版本

## 正确性属性

*属性是系统在所有有效执行中应该保持的特征或行为，是人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1: Shot 必需字段完整性
*对于任何*Shot 记录，应该包含 id、project_id、episode_id、scene_no、shot_no、shot_code、duration_ms、visual_constraints_jsonb 等所有必需字段
**验证需求**: 需求 1.1, 1.2, 1.3, 1.4, 1.5

### 属性 2: visual_constraints 结构完整性
*对于任何*Shot 的 visual_constraints_jsonb，应该包含 render_prompt、style_keywords、composition、character_refs 字段
**验证需求**: 需求 2.1, 2.2, 2.3, 2.4

### 属性 3: render_prompt 非空
*对于任何*Shot 的 visual_constraints，render_prompt 字段应该非空且长度大于 10 个字符
**验证需求**: 需求 2.1

### 属性 4: character_refs 引用有效性
*对于任何*Shot 的 character_refs 中的角色名称，应该在对应 Episode 的 character_profile 文档中存在
**验证需求**: 需求 2.5

### 属性 5: visual_spec 结构完整性
*对于任何*visual_spec 文档，应该包含 shots、overall_duration_ms、shot_count、visual_style、camera_strategy 字段
**验证需求**: 需求 3.1, 3.3, 3.4

### 属性 6: visual_spec shot 元素完整性
*对于任何*visual_spec 的 shots 数组中的元素，应该包含 shot_id、render_prompt、character_refs、style_keywords、composition 字段
**验证需求**: 需求 3.2

### 属性 7: Shot 数量一致性
*对于任何*Episode，Shot 记录的数量应该等于对应 visual_spec 文档的 shot_count 字段
**验证需求**: 需求 3.5, 4.1

### 属性 8: Shot 与 visual_spec 内容一致性
*对于任何*Shot 记录，其 visual_constraints 应该与 visual_spec 的对应 shot 元素内容一致
**验证需求**: 需求 4.2

### 属性 9: Shot 版本控制
*对于任何*Shot 编辑操作，应该创建新版本而不是覆盖原版本，且 version 号递增
**验证需求**: 需求 4.3, 4.5, 7.2

### 属性 10: image_render 输入包含必需参数
*对于任何*image_render 输入构建，应该包含 prompt、style_keywords、composition、character_anchors 等所有必需参数
**验证需求**: 需求 5.1, 5.2, 5.3, 5.4

### 属性 11: render_prompt 包含 visual_anchor
*对于任何*包含角色的 Shot，构建的 image_render 输入的 prompt 应该包含角色的 visual_anchor 关键词
**验证需求**: 需求 5.2

### 属性 12: Asset 关联 Shot
*对于任何*Asset 记录，如果 asset_type 为 keyframe，应该包含有效的 shot_id 关联到对应的 Shot
**验证需求**: 需求 8.1, 8.4

### 属性 13: 主资产唯一性
*对于任何*Shot，最多只有一个 Asset 的 is_selected 为 true
**验证需求**: 需求 8.3, 10.3

### 属性 14: Workspace 返回完整 Shot 列表
*对于任何*Workspace 查询，应该返回 Episode 的所有 Shot 记录并按 scene_no 和 shot_no 排序
**验证需求**: 需求 9.1, 9.5

### 属性 15: Shot 验证脚本检查完整性
*对于任何*运行验证脚本，应该检查所有 Shot 的必需字段、visual_constraints 结构、与 visual_spec 的一致性
**验证需求**: 需求 11.1, 11.2, 11.3, 11.4

## 错误处理

### Shot 数据不完整

**场景**: Shot 记录缺少必需字段或 visual_constraints 结构不完整

**处理**:
1. 验证服务检测到错误并返回详细的 ValidationResult
2. 记录错误日志，包含 Shot ID 和缺失字段
3. 阻止 Shot 进入 confirmed 状态
4. 前端展示错误信息和修复建议

### character_refs 引用无效

**场景**: Shot 的 character_refs 引用的角色在 character_profile 中不存在

**处理**:
1. 验证服务检测到引用错误
2. 生成警告而不是错误（允许继续但提示用户）
3. 建议用户更新 character_profile 或修改 character_refs
4. 在 image_render 时跳过无效的角色引用

### Shot 与 visual_spec 不一致

**场景**: Shot 数量与 visual_spec.shot_count 不一致，或内容不匹配

**处理**:
1. 验证服务检测到不一致
2. 记录详细的差异信息
3. 提供修复建议（重新运行 Storyboard Stage 或手动调整）
4. 阻止进入 image_render Stage 直到一致性恢复

### image_render 输入构建失败

**场景**: 无法加载 Shot、visual_spec 或 character_profile

**处理**:
1. 捕获异常并记录详细错误信息
2. 返回包含错误的 ImageRenderInput（标记为 invalid）
3. 跳过该 Shot 的渲染，继续处理其他 Shot
4. 在 StageTask 中记录失败原因

## 测试策略

### 单元测试

1. **ShotValidationService 测试**
   - 测试必需字段检查
   - 测试 visual_constraints Schema 验证
   - 测试 character_refs 引用验证
   - 测试 Shot 与 visual_spec 一致性检查

2. **ImageRenderInputBuilder 测试**
   - 测试单个 Shot 的输入构建
   - 测试批量输入构建
   - 测试 render_prompt 与 visual_anchor 合并
   - 测试缺失数据的处理

3. **Shot Repository 测试**
   - 测试 Shot 创建和查询
   - 测试版本控制
   - 测试按 scene_no 和 shot_no 排序

### 集成测试

1. **Storyboard 到 Shot 创建测试**
   - 运行 Storyboard Agent
   - 验证 visual_spec 文档创建
   - 验证 Shot 记录创建
   - 验证数量和内容一致性

2. **Shot 编辑和版本控制测试**
   - 创建初始 Shot
   - 编辑 visual_constraints
   - 验证新版本创建
   - 验证旧版本保留

3. **image_render 输入构建测试**
   - 创建完整的 Episode 数据（包含 character_profile、visual_spec、Shot）
   - 调用 ImageRenderInputBuilder
   - 验证输入参数完整性
   - 验证 visual_anchor 合并正确

### 验证脚本测试

1. **Shot 完整性验证脚本**
   - 创建测试数据（包含完整和不完整的 Shot）
   - 运行验证脚本
   - 验证错误检测准确性
   - 验证报告格式正确

## 性能考虑

### 查询优化

- 使用已有的索引：`idx_shots_project_episode_scene_shot`
- 批量查询 Shot 时使用 `IN` 子句
- 缓存 character_profile 文档避免重复查询

### 批量处理

- ImageRenderInputBuilder 支持批量构建，减少数据库查询次数
- 一次性加载 Episode 的所有 Shot 和相关文档
- 使用连接查询减少往返次数

### 内存管理

- 大量 Shot 时使用分页查询
- 流式处理 image_render 输入构建
- 及时释放不再使用的文档对象

## 可扩展性

### 支持更多视觉约束字段

visual_constraints_jsonb 是 JSONB 类型，可以灵活添加新字段：
- `lighting`: 光照设置
- `weather`: 天气条件
- `time_of_day`: 时间段
- `mood`: 情绪氛围

### 支持多种图像生成 Provider

ImageRenderInput 设计为通用结构，可以适配不同的 Provider：
- Stable Diffusion
- DALL-E
- Midjourney
- 自定义模型

### 支持 Shot 级别的重跑

设计已考虑 Shot 级别的重跑：
- Shot 有独立的 version 字段
- ImageRenderInputBuilder 支持单个 Shot 的输入构建
- Asset 通过 shot_id 关联，支持局部更新

## 安全性

### 输入验证

- 所有 visual_constraints 字段使用 JSON Schema 验证
- render_prompt 长度限制（最大 2000 字符）
- character_refs 数量限制（最大 10 个角色）

### 数据保护

- Shot 版本控制防止意外覆盖
- 锁定字段机制保护关键内容
- 审计日志记录所有 Shot 编辑操作

## 实现优先级

### 高优先级（本迭代必须完成）

1. Shot 数据完整性验证脚本
2. visual_constraints Schema 验证
3. ImageRenderInputBuilder 服务实现
4. Shot 与 visual_spec 一致性验证

### 中优先级（本迭代尽量完成）

1. ShotValidationService 完整实现
2. Workspace 展示 Shot 详情优化
3. Shot 编辑 API 端点

### 低优先级（可推迟到 Iteration 4）

1. Shot 锁定字段功能
2. 资产选择 UI
3. Shot 卡片详细展示
