# ImageRenderInput 使用文档

## 概述

`ImageRenderInput` 是 image_render Stage 的输入参数数据类，包含图像生成所需的所有参数。`ImageRenderInputBuilder` 服务负责从 Shot 的 visual_constraints 和 character_profile 文档构建完整的输入参数。

本文档记录 ImageRenderInput 的所有字段、构建示例，以及如何使用 ImageRenderInputBuilder 服务。

**相关需求**: 5.1, 12.1

---

## ImageRenderInput 数据类

### 字段说明

#### 标识字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `shot_id` | UUID | Shot 的唯一标识符 |
| `episode_id` | UUID | Episode 的唯一标识符 |

#### 核心参数

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `prompt` | str | 完整的渲染提示词（已合并 visual_anchor） |
| `negative_prompt` | str | 负面提示词，指定不希望出现的元素 |

#### 风格参数

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `style_keywords` | List[str] | 风格关键词列表 |
| `visual_style` | str | 整体视觉风格（如 "anime", "realistic"） |

#### 构图参数

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `composition` | str | 镜头构图（如 "rule of thirds", "centered"） |
| `camera_size` | str | 镜头大小（close-up, medium, wide） |
| `camera_angle` | str | 镜头角度（eye-level, low, high） |

#### 角色参数

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `character_refs` | List[str] | 角色引用列表 |
| `character_anchors` | Dict[str, str] | 角色名到 visual_anchor 的映射 |

#### 技术参数

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `aspect_ratio` | str | 画面比例（如 "9:16", "16:9"） |
| `resolution` | Tuple[int, int] | 分辨率（宽度, 高度），如 (1080, 1920) |

#### 元数据

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `scene_no` | int | 场景编号 |
| `shot_no` | int | 镜头编号 |
| `shot_code` | str | 镜头代码（如 "S01_001"） |

### 验证规则

`ImageRenderInput` 在初始化后会自动验证以下规则：

1. `prompt` 不能为空
2. `style_keywords` 必须是列表类型
3. `character_refs` 必须是列表类型
4. `character_anchors` 必须是字典类型
5. `resolution` 必须是包含两个整数的元组
6. `scene_no` 和 `shot_no` 必须是正整数

如果验证失败，会抛出 `ValueError` 异常。

### 序列化方法

```python
def to_dict(self) -> Dict:
    """
    将 ImageRenderInput 序列化为字典。
    
    自动将 UUID 转换为字符串，resolution 保持为元组（JSON 序列化为数组）。
    """
```

---

## ImageRenderInputBuilder 服务

### 初始化

```python
from sqlalchemy.orm import Session
from app.services.image_render_input_builder import ImageRenderInputBuilder

# 创建 builder 实例
db: Session = ...  # 数据库会话
builder = ImageRenderInputBuilder(db)
```

### 方法说明

#### 1. build_input_for_shot

为单个 Shot 构建 image_render 输入。

```python
def build_input_for_shot(
    self,
    shot_id: UUID,
    episode_id: UUID
) -> ImageRenderInput:
    """
    为单个 Shot 构建 image_render 输入。
    
    Args:
        shot_id: Shot 的 ID
        episode_id: Episode 的 ID
        
    Returns:
        ImageRenderInput: 包含完整参数的输入对象
        
    Raises:
        ValueError: 如果 Shot 不存在或必需数据缺失
    """
```

**使用示例**:

```python
from uuid import UUID

shot_id = UUID("550e8400-e29b-41d4-a716-446655440000")
episode_id = UUID("789e0123-e89b-12d3-a456-426614174000")

try:
    render_input = builder.build_input_for_shot(shot_id, episode_id)
    print(f"Prompt: {render_input.prompt}")
    print(f"Style: {render_input.visual_style}")
    print(f"Characters: {render_input.character_refs}")
except ValueError as e:
    print(f"Error: {e}")
```

#### 2. build_inputs_for_episode

为 Episode 的所有 Shot 批量构建输入。

```python
def build_inputs_for_episode(
    self,
    episode_id: UUID
) -> List[ImageRenderInput]:
    """
    为 Episode 的所有 Shot 批量构建输入。
    
    Args:
        episode_id: Episode 的 ID
        
    Returns:
        List[ImageRenderInput]: 所有 Shot 的输入参数列表
    """
```

**使用示例**:

```python
episode_id = UUID("789e0123-e89b-12d3-a456-426614174000")

render_inputs = builder.build_inputs_for_episode(episode_id)
print(f"Built {len(render_inputs)} render inputs")

for input_obj in render_inputs:
    print(f"Shot {input_obj.shot_code}: {input_obj.prompt[:50]}...")
```

### 内部逻辑

#### visual_anchor 合并逻辑

`ImageRenderInputBuilder` 的核心功能是将 Shot 的 `render_prompt` 与角色的 `visual_anchor` 智能合并：

1. **提取 visual_anchor**: 从 character_profile 文档中提取 character_refs 中每个角色的 visual_anchor
2. **检查重复**: 检查 render_prompt 是否已包含 visual_anchor 的关键词
3. **智能插入**: 如果未包含，将 visual_anchor 插入到 render_prompt 开头
4. **避免冗余**: 如果 render_prompt 已包含相关描述，则不重复添加

**示例**:

```python
# 原始 render_prompt
render_prompt = "Two students talking in a classroom"

# character_refs
character_refs = ["小明", "小红"]

# character_profile 中的 visual_anchor
# 小明: "teenage boy with short black hair and glasses"
# 小红: "teenage girl with long brown hair and bright smile"

# 合并后的 prompt
enhanced_prompt = "小明: teenage boy with short black hair and glasses, 小红: teenage girl with long brown hair and bright smile. Two students talking in a classroom"
```

#### 默认参数

`ImageRenderInputBuilder` 提供以下默认参数：

```python
DEFAULT_ASPECT_RATIO = "9:16"  # 竖屏视频
DEFAULT_RESOLUTION = (1080, 1920)  # 1080x1920 像素
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed"
DEFAULT_VISUAL_STYLE = "anime"
```

---

## 使用示例

### 示例 1: 为单个 Shot 构建输入

```python
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.image_render_input_builder import ImageRenderInputBuilder

def render_single_shot(db: Session, shot_id: UUID, episode_id: UUID):
    """为单个 Shot 构建并使用 render input"""
    
    # 创建 builder
    builder = ImageRenderInputBuilder(db)
    
    # 构建输入
    try:
        render_input = builder.build_input_for_shot(shot_id, episode_id)
        
        # 使用输入参数
        print(f"Rendering Shot {render_input.shot_code}")
        print(f"Prompt: {render_input.prompt}")
        print(f"Resolution: {render_input.resolution}")
        print(f"Style: {render_input.visual_style}")
        print(f"Characters: {', '.join(render_input.character_refs)}")
        
        # 序列化为字典（用于 API 传递）
        input_dict = render_input.to_dict()
        
        # 调用图像生成服务
        # image_service.generate(input_dict)
        
        return render_input
    except ValueError as e:
        print(f"Failed to build input: {e}")
        return None
```

### 示例 2: 批量构建 Episode 的所有 Shot

```python
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.image_render_input_builder import ImageRenderInputBuilder

def render_episode(db: Session, episode_id: UUID):
    """为 Episode 的所有 Shot 批量构建 render inputs"""
    
    # 创建 builder
    builder = ImageRenderInputBuilder(db)
    
    # 批量构建输入
    render_inputs = builder.build_inputs_for_episode(episode_id)
    
    if not render_inputs:
        print(f"No shots found for Episode {episode_id}")
        return []
    
    print(f"Built {len(render_inputs)} render inputs")
    
    # 处理每个输入
    results = []
    for render_input in render_inputs:
        print(f"\nProcessing Shot {render_input.shot_code}")
        print(f"  Scene: {render_input.scene_no}, Shot: {render_input.shot_no}")
        print(f"  Prompt: {render_input.prompt[:80]}...")
        print(f"  Characters: {', '.join(render_input.character_refs)}")
        
        # 序列化为字典
        input_dict = render_input.to_dict()
        
        # 调用图像生成服务
        # result = image_service.generate(input_dict)
        # results.append(result)
    
    return results
```

### 示例 3: 自定义参数

```python
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.image_render_input_builder import ImageRenderInputBuilder, ImageRenderInput

def build_custom_input(db: Session, shot_id: UUID, episode_id: UUID):
    """构建自定义参数的 render input"""
    
    builder = ImageRenderInputBuilder(db)
    
    # 先构建默认输入
    base_input = builder.build_input_for_shot(shot_id, episode_id)
    
    # 创建自定义输入（修改某些参数）
    custom_input = ImageRenderInput(
        shot_id=base_input.shot_id,
        episode_id=base_input.episode_id,
        prompt=base_input.prompt + ", high quality, detailed",  # 增强 prompt
        negative_prompt="blurry, low quality, distorted, deformed, watermark",  # 自定义负面提示
        style_keywords=base_input.style_keywords + ["cinematic"],  # 添加风格关键词
        visual_style=base_input.visual_style,
        composition=base_input.composition,
        camera_size=base_input.camera_size,
        camera_angle=base_input.camera_angle,
        character_refs=base_input.character_refs,
        character_anchors=base_input.character_anchors,
        aspect_ratio="16:9",  # 改为横屏
        resolution=(1920, 1080),  # 改为横屏分辨率
        scene_no=base_input.scene_no,
        shot_no=base_input.shot_no,
        shot_code=base_input.shot_code
    )
    
    return custom_input
```

### 示例 4: 错误处理

```python
from uuid import UUID
from sqlalchemy.orm import Session
from app.services.image_render_input_builder import ImageRenderInputBuilder

def safe_build_input(db: Session, shot_id: UUID, episode_id: UUID):
    """安全地构建 render input，处理各种错误"""
    
    builder = ImageRenderInputBuilder(db)
    
    try:
        render_input = builder.build_input_for_shot(shot_id, episode_id)
        return render_input, None
    except ValueError as e:
        # Shot 不存在或数据缺失
        error_msg = f"Validation error: {e}"
        print(error_msg)
        return None, error_msg
    except Exception as e:
        # 其他未预期的错误
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        return None, error_msg
```

---

## 完整示例数据

### 输入数据

#### Shot 记录

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "episode_id": "789e0123-e89b-12d3-a456-426614174000",
  "scene_no": 1,
  "shot_no": 1,
  "shot_code": "S01_001",
  "camera_size": "medium",
  "camera_angle": "eye-level",
  "visual_constraints_jsonb": {
    "render_prompt": "Two students talking in a bright classroom",
    "style_keywords": ["anime", "vibrant", "school"],
    "composition": "rule of thirds",
    "character_refs": ["小明", "小红"]
  }
}
```

#### character_profile 文档

```json
{
  "characters": [
    {
      "name": "小明",
      "visual_anchor": "teenage boy with short black hair, glasses, school uniform"
    },
    {
      "name": "小红",
      "visual_anchor": "teenage girl with long brown hair, bright smile, school uniform"
    }
  ]
}
```

#### visual_spec 文档

```json
{
  "visual_style": "anime",
  "shot_count": 10
}
```

### 输出数据

#### ImageRenderInput 对象

```python
ImageRenderInput(
    shot_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
    episode_id=UUID("789e0123-e89b-12d3-a456-426614174000"),
    prompt="小明: teenage boy with short black hair, glasses, school uniform, 小红: teenage girl with long brown hair, bright smile, school uniform. Two students talking in a bright classroom",
    negative_prompt="blurry, low quality, distorted, deformed",
    style_keywords=["anime", "vibrant", "school"],
    visual_style="anime",
    composition="rule of thirds",
    camera_size="medium",
    camera_angle="eye-level",
    character_refs=["小明", "小红"],
    character_anchors={
        "小明": "teenage boy with short black hair, glasses, school uniform",
        "小红": "teenage girl with long brown hair, bright smile, school uniform"
    },
    aspect_ratio="9:16",
    resolution=(1080, 1920),
    scene_no=1,
    shot_no=1,
    shot_code="S01_001"
)
```

#### 序列化为字典

```json
{
  "shot_id": "550e8400-e29b-41d4-a716-446655440000",
  "episode_id": "789e0123-e89b-12d3-a456-426614174000",
  "prompt": "小明: teenage boy with short black hair, glasses, school uniform, 小红: teenage girl with long brown hair, bright smile, school uniform. Two students talking in a bright classroom",
  "negative_prompt": "blurry, low quality, distorted, deformed",
  "style_keywords": ["anime", "vibrant", "school"],
  "visual_style": "anime",
  "composition": "rule of thirds",
  "camera_size": "medium",
  "camera_angle": "eye-level",
  "character_refs": ["小明", "小红"],
  "character_anchors": {
    "小明": "teenage boy with short black hair, glasses, school uniform",
    "小红": "teenage girl with long brown hair, bright smile, school uniform"
  },
  "aspect_ratio": "9:16",
  "resolution": [1080, 1920],
  "scene_no": 1,
  "shot_no": 1,
  "shot_code": "S01_001"
}
```

---

## 性能优化

### 批量构建优化

`build_inputs_for_episode` 方法进行了以下优化：

1. **一次性加载文档**: character_profile 和 visual_spec 只加载一次，所有 Shot 共享
2. **批量查询 Shot**: 使用 `list_current_for_episode` 一次性查询所有 Shot
3. **错误容忍**: 单个 Shot 构建失败不影响其他 Shot 的处理

### 缓存建议

对于频繁访问的 Episode，可以考虑缓存 character_profile 和 visual_spec：

```python
from functools import lru_cache

class CachedImageRenderInputBuilder(ImageRenderInputBuilder):
    """带缓存的 ImageRenderInputBuilder"""
    
    @lru_cache(maxsize=100)
    def _load_character_profile(self, episode_id: UUID):
        return super()._load_character_profile(episode_id)
    
    @lru_cache(maxsize=100)
    def _load_visual_spec(self, episode_id: UUID):
        return super()._load_visual_spec(episode_id)
```

---

## 常见问题

### Q1: 如果 Shot 没有 character_refs 怎么办？

A: 如果 `character_refs` 为空，`_merge_prompt_with_anchors` 会直接返回原始 `render_prompt`，不会添加任何 visual_anchor。

### Q2: 如果 character_profile 不存在怎么办？

A: 如果 character_profile 不存在，`_load_character_profile` 返回 `None`，`_merge_prompt_with_anchors` 会跳过 visual_anchor 合并，直接使用原始 `render_prompt`。

### Q3: 如果 render_prompt 为空怎么办？

A: 如果 `render_prompt` 为空，`build_input_for_shot` 会抛出 `ValueError`。在 `build_inputs_for_episode` 中，该 Shot 会被跳过。

### Q4: 如何自定义 aspect_ratio 和 resolution？

A: 可以在构建后修改 `ImageRenderInput` 对象，或者创建自定义的 `ImageRenderInput` 实例（参见示例 3）。

### Q5: visual_anchor 合并逻辑如何避免重复？

A: `_merge_prompt_with_anchors` 会提取 visual_anchor 的关键词，检查这些关键词是否已在 `render_prompt` 中出现。如果已存在，则不添加该 visual_anchor。

---

## 测试

### 单元测试

参见 `apps/api/tests/unit/test_image_render_input_builder.py`

测试覆盖：
- 单个 Shot 输入构建
- 批量输入构建
- visual_anchor 合并逻辑
- 缺失数据处理
- 错误情况处理

### 集成测试

创建完整的测试数据（Episode、character_profile、visual_spec、Shot），调用 `ImageRenderInputBuilder`，验证输入参数的完整性和正确性。

---

## 相关文档

- **Shot 数据结构文档**: `docs/engineering/SHOT_DATA_STRUCTURE.md`
- **ImageRenderInputBuilder 源码**: `apps/api/app/services/image_render_input_builder.py`
- **单元测试**: `apps/api/tests/unit/test_image_render_input_builder.py`
- **设计文档**: `.kiro/specs/storyboard-to-asset/design.md`
- **需求文档**: `.kiro/specs/storyboard-to-asset/requirements.md`

---

**创建日期**: 2026-04-07  
**版本**: 1.0  
**维护者**: 系统开发团队
