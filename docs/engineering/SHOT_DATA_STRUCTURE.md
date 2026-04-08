# Shot 数据结构文档

## 概述

Shot（分镜）是系统中的核心数据模型，代表视频中的单个镜头。每个 Shot 包含镜头的视觉约束、时长、摄像机参数等信息，是图像渲染和局部重跑的关键锚点。

本文档记录 Shot 模型的所有字段、visual_constraints 的 Schema，并提供示例数据。

**相关需求**: 1.1, 2.1

---

## Shot 模型字段

### 标识字段

| 字段名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `id` | UUID | 是 | Shot 的唯一标识符 |
| `project_id` | UUID | 是 | 所属项目 ID |
| `episode_id` | UUID | 是 | 所属剧集 ID |
| `stage_task_id` | UUID | 否 | 创建该 Shot 的 StageTask ID（可为空） |

### 分镜信息

| 字段名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `scene_no` | Integer | 是 | 场景编号（从 1 开始） |
| `shot_no` | Integer | 是 | 镜头编号（从 1 开始） |
| `shot_code` | String(64) | 是 | 镜头代码，格式如 "S01_001" |
| `status` | String(32) | 是 | 状态：draft, confirmed, rendering, completed, failed |

### 时长和摄像机参数

| 字段名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `duration_ms` | Integer | 是 | 镜头时长（毫秒） |
| `camera_size` | String(32) | 否 | 镜头大小：close-up, medium, wide, extreme-close-up, extreme-wide |
| `camera_angle` | String(32) | 否 | 镜头角度：eye-level, low, high, dutch, overhead, ground |
| `movement_type` | String(32) | 否 | 运动类型：static, pan, tilt, zoom, dolly, tracking, crane |

### 内容信息

| 字段名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `characters_jsonb` | JSONB (Array) | 是 | 出现的角色名称列表，如 ["小明", "小红"] |
| `action_text` | Text | 否 | 动作描述文本 |
| `dialogue_text` | Text | 否 | 对白文本 |

### 视觉约束（核心字段）

| 字段名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `visual_constraints_jsonb` | JSONB (Object) | 是 | 视觉约束对象，详见下方 Schema |

### 版本控制

| 字段名 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `version` | Integer | 是 | 版本号（从 1 开始） |
| `created_at` | DateTime | 是 | 创建时间（带时区） |
| `updated_at` | DateTime | 是 | 更新时间（带时区） |

---

## visual_constraints_jsonb Schema

`visual_constraints_jsonb` 字段存储镜头的视觉约束信息，是 JSONB 类型的对象。

### 必需字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `render_prompt` | String | 完整的渲染提示词，用于 AI 图像生成 |
| `style_keywords` | Array[String] | 风格关键词列表，如 ["anime", "vibrant", "detailed"] |
| `composition` | String | 镜头构图描述，如 "rule of thirds", "centered", "symmetrical" |
| `character_refs` | Array[String] | 角色引用列表，包含出现在该镜头中的角色名称 |

### 可选字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `locked_fields` | Array[String] | 锁定的字段列表，用于重跑时保护已确认的内容 |
| `negative_prompt` | String | 负面提示词，指定不希望出现的元素 |
| `lighting` | String | 光照设置，如 "natural", "dramatic", "soft" |
| `weather` | String | 天气条件，如 "sunny", "rainy", "cloudy" |
| `time_of_day` | String | 时间段，如 "morning", "noon", "evening", "night" |
| `mood` | String | 情绪氛围，如 "tense", "peaceful", "exciting" |

### Schema 验证规则

1. `render_prompt` 必须非空且长度至少 10 个字符
2. `style_keywords` 必须是数组类型
3. `composition` 必须是字符串类型
4. `character_refs` 必须是数组类型
5. `character_refs` 中的角色名称必须在 character_profile 文档中存在

---

## Shot 状态机

Shot 的 `status` 字段遵循以下状态转换：

```
draft → confirmed → rendering → completed
  ↓         ↓           ↓
failed ← failed ← failed
```

### 状态说明

- **draft**: 初始状态，Storyboard Agent 生成后的状态
- **confirmed**: 用户确认后的状态，可以进入渲染
- **rendering**: 正在渲染图像
- **completed**: 渲染完成，有可用的主资产
- **failed**: 渲染失败

---

## 示例数据

### 示例 1: 基础 Shot

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "episode_id": "789e0123-e89b-12d3-a456-426614174000",
  "stage_task_id": "456e7890-e89b-12d3-a456-426614174000",
  "scene_no": 1,
  "shot_no": 1,
  "shot_code": "S01_001",
  "status": "draft",
  "duration_ms": 3000,
  "camera_size": "medium",
  "camera_angle": "eye-level",
  "movement_type": "static",
  "characters_jsonb": ["小明", "小红"],
  "action_text": "小明和小红在教室里交谈",
  "dialogue_text": "小明：今天天气真好！",
  "visual_constraints_jsonb": {
    "render_prompt": "Two students talking in a bright classroom, medium shot at eye level, anime style with vibrant colors",
    "style_keywords": ["anime", "vibrant", "school", "bright"],
    "composition": "rule of thirds",
    "character_refs": ["小明", "小红"]
  },
  "version": 1,
  "created_at": "2026-04-07T10:00:00Z",
  "updated_at": "2026-04-07T10:00:00Z"
}
```

### 示例 2: 带锁定字段的 Shot

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "episode_id": "789e0123-e89b-12d3-a456-426614174000",
  "stage_task_id": "456e7890-e89b-12d3-a456-426614174000",
  "scene_no": 1,
  "shot_no": 2,
  "shot_code": "S01_002",
  "status": "confirmed",
  "duration_ms": 2500,
  "camera_size": "close-up",
  "camera_angle": "low",
  "movement_type": "zoom",
  "characters_jsonb": ["小明"],
  "action_text": "小明惊讶地看着窗外",
  "dialogue_text": null,
  "visual_constraints_jsonb": {
    "render_prompt": "Close-up of a surprised student looking out the window, low angle shot with dramatic lighting, anime style",
    "style_keywords": ["anime", "dramatic", "close-up", "emotional"],
    "composition": "centered",
    "character_refs": ["小明"],
    "locked_fields": ["render_prompt", "composition"],
    "negative_prompt": "blurry, low quality, distorted",
    "lighting": "dramatic",
    "mood": "surprised"
  },
  "version": 2,
  "created_at": "2026-04-07T10:00:00Z",
  "updated_at": "2026-04-07T10:05:00Z"
}
```

### 示例 3: 无角色的环境镜头

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "episode_id": "789e0123-e89b-12d3-a456-426614174000",
  "stage_task_id": "456e7890-e89b-12d3-a456-426614174000",
  "scene_no": 2,
  "shot_no": 1,
  "shot_code": "S02_001",
  "status": "draft",
  "duration_ms": 4000,
  "camera_size": "extreme-wide",
  "camera_angle": "high",
  "movement_type": "pan",
  "characters_jsonb": [],
  "action_text": "校园全景，展示美丽的校园环境",
  "dialogue_text": null,
  "visual_constraints_jsonb": {
    "render_prompt": "Wide establishing shot of a beautiful school campus, high angle view with cherry blossoms, anime style with soft colors",
    "style_keywords": ["anime", "scenic", "peaceful", "cherry-blossoms"],
    "composition": "panoramic",
    "character_refs": [],
    "weather": "sunny",
    "time_of_day": "morning",
    "mood": "peaceful"
  },
  "version": 1,
  "created_at": "2026-04-07T10:10:00Z",
  "updated_at": "2026-04-07T10:10:00Z"
}
```

---

## 数据库索引

Shot 表包含以下索引以优化查询性能：

1. **主键索引**: `id` (自动创建)
2. **复合索引**: `idx_shots_project_episode_scene_shot`
   - 字段: `(project_id, episode_id, scene_no, shot_no)`
   - 用途: 按场景和镜头编号排序查询
3. **版本索引**: `idx_shots_episode_version`
   - 字段: `(episode_id, version)`
   - 用途: 查询特定版本的 Shot

---

## 版本控制策略

### 版本创建规则

1. **初始创建**: Storyboard Agent 创建 Shot 时，`version = 1`
2. **用户编辑**: 用户编辑 Shot 的 visual_constraints 时，创建新版本（`version + 1`）
3. **重跑生成**: 重跑 Storyboard Stage 时，创建新版本的所有 Shot
4. **版本查询**: 默认查询最新版本，可以指定版本号查询历史版本

### 版本关联

- Shot 的 `version` 与对应的 visual_spec 文档的 `version` 保持一致
- 重跑时，visual_spec 和 Shot 同时创建新版本
- 旧版本的 Shot 记录保留在数据库中，不会被删除

---

## 与其他模型的关系

### Shot → Episode

- 多对一关系
- 外键: `episode_id` → `episodes.id`
- 级联删除: 删除 Episode 时，所有关联的 Shot 也会被删除

### Shot → Project

- 多对一关系
- 外键: `project_id` → `projects.id`
- 级联删除: 删除 Project 时，所有关联的 Shot 也会被删除

### Shot → StageTask

- 多对一关系（可选）
- 外键: `stage_task_id` → `stage_tasks.id`
- 级联设置: 删除 StageTask 时，Shot 的 `stage_task_id` 设置为 NULL

### Shot ← Asset

- 一对多关系
- Asset 通过 `shot_id` 关联到 Shot
- 一个 Shot 可以有多个候选 Asset（不同的渲染结果）
- 其中一个 Asset 的 `is_selected = true` 标记为主资产

### Shot ← visual_spec Document

- 间接关系
- Shot 的 `visual_constraints_jsonb` 来源于 visual_spec 文档的对应 shot 元素
- 通过 `episode_id` 和 `version` 关联

---

## 验证规则

### 必需字段验证

所有标记为"必需"的字段必须非空：
- `id`, `project_id`, `episode_id`
- `scene_no`, `shot_no`, `shot_code`
- `status`, `duration_ms`
- `characters_jsonb`, `visual_constraints_jsonb`
- `version`, `created_at`, `updated_at`

### 字段格式验证

- `duration_ms` 必须大于 0
- `scene_no` 和 `shot_no` 必须大于 0
- `shot_code` 格式建议为 "S{scene_no:02d}_{shot_no:03d}"
- `status` 必须是有效的状态值之一
- `camera_size`, `camera_angle`, `movement_type` 如果非空，必须是预定义的值之一

### visual_constraints 验证

- 必须是有效的 JSON 对象
- 必须包含所有必需字段
- `render_prompt` 长度至少 10 个字符
- `style_keywords` 和 `character_refs` 必须是数组
- `character_refs` 中的角色必须在 character_profile 中存在

---

## 使用建议

### 创建 Shot

1. 通过 Storyboard Agent 自动创建（推荐）
2. 确保 `visual_constraints_jsonb` 包含所有必需字段
3. 设置合理的 `duration_ms`（建议 2000-5000 毫秒）
4. 填充 `camera_size`, `camera_angle`, `movement_type` 以提供完整信息

### 编辑 Shot

1. 使用 Shot 编辑 API 端点更新 `visual_constraints_jsonb`
2. 编辑会创建新版本，不会覆盖旧版本
3. 使用 `locked_fields` 保护已确认的字段
4. 验证 `character_refs` 引用的有效性

### 查询 Shot

1. 默认查询最新版本: `ShotRepository.list_current_for_episode(episode_id)`
2. 查询特定版本: 使用 `version` 参数
3. 按场景和镜头排序: 使用 `scene_no` 和 `shot_no`
4. 使用索引优化查询性能

---

## 相关文档

- **ImageRenderInput 使用文档**: `docs/engineering/IMAGE_RENDER_INPUT.md`
- **Shot 验证脚本**: `apps/api/scripts/validate_shot_integrity.py`
- **Shot Repository**: `apps/api/app/repositories/shot_repository.py`
- **Shot Validation Service**: `apps/api/app/services/shot_validation_service.py`
- **设计文档**: `.kiro/specs/storyboard-to-asset/design.md`
- **需求文档**: `.kiro/specs/storyboard-to-asset/requirements.md`

---

**创建日期**: 2026-04-07  
**版本**: 1.0  
**维护者**: 系统开发团队
