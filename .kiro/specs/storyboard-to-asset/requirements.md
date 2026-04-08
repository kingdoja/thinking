# Iteration 3: Storyboard 到 Asset 工作台 - 需求文档

## 简介

本迭代的目标是将 Storyboard 变成能驱动后续媒体链路的稳定中枢。通过验证和完善 Shot 结构、visual_spec 文档，以及设计 image_render 输入构建逻辑，为 Iteration 4 的媒体链路打下坚实基础。

## 术语表

- **Shot**: 分镜级对象，是图像渲染和局部重跑的关键锚点
- **visual_spec**: 视觉规格文档，包含每个镜头的渲染提示词和风格约束
- **visual_constraints**: 视觉约束，存储在 Shot 的 visual_constraints_jsonb 字段中
- **render_prompt**: 渲染提示词，用于 AI 图像生成的详细描述
- **visual_anchor**: 视觉锚点，角色的固定视觉特征描述
- **image_render**: 图像渲染 Stage，根据 visual_spec 生成关键帧图像
- **Asset**: 媒体资产，包括图像、音频、字幕等
- **Workspace**: 工作台，展示项目所有产物的聚合视图

## 需求

### 需求 1: Shot 模型完整性验证

**用户故事**: 作为系统开发者，我想要验证 Shot 模型包含所有必需字段，以便确保 Shot 可以支持后续的图像渲染和资产管理。

#### 验收标准

1. WHEN 查询 Shot 记录 THEN System SHALL 包含 id、project_id、episode_id、scene_no、shot_no、shot_code 字段
2. WHEN 查询 Shot 记录 THEN System SHALL 包含 duration_ms、camera_size、camera_angle、movement_type 字段
3. WHEN 查询 Shot 记录 THEN System SHALL 包含 characters_jsonb、action_text、dialogue_text 字段
4. WHEN 查询 Shot 记录 THEN System SHALL 包含 visual_constraints_jsonb 字段且结构完整
5. WHEN 查询 Shot 记录 THEN System SHALL 包含 version、status、created_at、updated_at 字段

### 需求 2: visual_constraints 结构验证

**用户故事**: 作为系统开发者，我想要验证 visual_constraints_jsonb 的结构完整性，以便确保包含图像渲染所需的所有信息。

#### 验收标准

1. WHEN Shot 包含 visual_constraints THEN System SHALL 包含 render_prompt 字段且非空
2. WHEN Shot 包含 visual_constraints THEN System SHALL 包含 style_keywords 数组字段
3. WHEN Shot 包含 visual_constraints THEN System SHALL 包含 composition 字段
4. WHEN Shot 包含 visual_constraints THEN System SHALL 包含 character_refs 数组字段
5. WHEN Shot 的 character_refs 非空 THEN System SHALL 确保引用的角色在 character_profile 中存在

### 需求 3: visual_spec 文档结构验证

**用户故事**: 作为系统开发者，我想要验证 visual_spec 文档的结构完整性，以便确保可以被 image_render Stage 正确消费。

#### 验收标准

1. WHEN visual_spec 文档创建 THEN System SHALL 包含 shots 数组字段且每个元素结构完整
2. WHEN visual_spec 包含 shot THEN System SHALL 每个 shot 包含 shot_id、render_prompt、character_refs、style_keywords、composition 字段
3. WHEN visual_spec 文档创建 THEN System SHALL 包含 overall_duration_ms、shot_count 字段
4. WHEN visual_spec 文档创建 THEN System SHALL 包含 visual_style、camera_strategy 字段
5. WHEN visual_spec 的 shot 数量 THEN System SHALL 与实际创建的 Shot 记录数量一致

### 需求 4: Shot 与 visual_spec 关联验证

**用户故事**: 作为系统开发者，我想要验证 Shot 记录与 visual_spec 文档的关联关系，以便确保数据一致性。

#### 验收标准

1. WHEN Storyboard Stage 完成 THEN System SHALL 创建 visual_spec 文档和对应数量的 Shot 记录
2. WHEN Shot 记录创建 THEN System SHALL 从 visual_spec 的对应 shot 元素提取 visual_constraints
3. WHEN Shot 的 visual_constraints 更新 THEN System SHALL 保持与 visual_spec 的一致性或创建新版本
4. WHEN 查询 Shot 列表 THEN System SHALL 可以关联查询对应的 visual_spec 文档
5. WHEN visual_spec 版本更新 THEN System SHALL 创建新版本的 Shot 记录而不是覆盖旧版本

### 需求 5: image_render 输入构建逻辑设计

**用户故事**: 作为系统开发者，我想要设计 image_render Stage 的输入构建逻辑，以便从 visual_spec 和 character_profile 组装完整的图像生成参数。

#### 验收标准

1. WHEN 构建 image_render 输入 THEN System SHALL 从 Shot 的 visual_constraints 提取 render_prompt
2. WHEN 构建 image_render 输入 THEN System SHALL 从 character_profile 提取角色的 visual_anchor 并合并到 render_prompt
3. WHEN 构建 image_render 输入 THEN System SHALL 从 visual_spec 提取 visual_style 和 style_keywords
4. WHEN 构建 image_render 输入 THEN System SHALL 组装包含所有必需参数的完整 Prompt
5. WHEN 构建 image_render 输入 THEN System SHALL 支持 Shot-level 的重跑输入构建

### 需求 6: Shot 卡片展示设计

**用户故事**: 作为内容创作者，我想要在分镜页面看到每个 Shot 的详细信息，以便了解和管理每个镜头的视觉效果。

#### 验收标准

1. WHEN 用户查看分镜页面 THEN System SHALL 展示 Shot 列表并按 scene_no 和 shot_no 排序
2. WHEN 用户查看 Shot 卡片 THEN System SHALL 展示 shot_code、duration_ms、camera_size、camera_angle 信息
3. WHEN 用户查看 Shot 卡片 THEN System SHALL 展示 render_prompt 的摘要或完整内容
4. WHEN 用户查看 Shot 卡片 THEN System SHALL 展示 style_keywords 和 composition 信息
5. WHEN 用户查看 Shot 卡片 THEN System SHALL 展示关联的角色列表（character_refs）

### 需求 7: Shot 编辑和锁定功能设计

**用户故事**: 作为内容创作者，我想要编辑 Shot 的视觉约束并锁定关键字段，以便在重跑时保护已确认的内容。

#### 验收标准

1. WHEN 用户编辑 Shot THEN System SHALL 支持修改 visual_constraints_jsonb 的内容
2. WHEN 用户编辑 Shot THEN System SHALL 创建新版本而不是覆盖原版本
3. WHEN 用户锁定 Shot 字段 THEN System SHALL 记录锁定的字段列表
4. WHEN 重跑 image_render THEN System SHALL 尊重锁定的 visual_constraints 字段
5. WHEN 用户编辑 Shot THEN System SHALL 验证 visual_constraints 的 Schema 完整性

### 需求 8: 资产与 Shot 关联字段补齐

**用户故事**: 作为系统开发者，我想要补齐资产与 Shot 的关联字段，以便支持后续的资产选择和管理功能。

#### 验收标准

1. WHEN Asset 创建 THEN System SHALL 包含 shot_id 字段关联到对应的 Shot
2. WHEN Asset 创建 THEN System SHALL 包含 asset_type 字段标识资产类型（keyframe、audio、subtitle 等）
3. WHEN Asset 创建 THEN System SHALL 包含 is_selected 字段标记是否为主资产
4. WHEN 查询 Shot 的资产 THEN System SHALL 返回所有关联的 Asset 记录
5. WHEN 查询 Shot 的主资产 THEN System SHALL 返回 is_selected 为 true 的 Asset

### 需求 9: Workspace 展示 Shot 详情

**用户故事**: 作为内容创作者，我想要在工作台看到 Shot 的详细信息和视觉约束摘要，以便快速了解分镜状态。

#### 验收标准

1. WHEN 用户查询 Workspace THEN System SHALL 返回完整的 Shot 列表
2. WHEN Workspace 返回 Shot THEN System SHALL 包含 visual_constraints 的摘要信息
3. WHEN Workspace 返回 Shot THEN System SHALL 包含关联的 visual_spec 文档引用
4. WHEN Workspace 返回 Shot THEN System SHALL 包含 Shot 的状态和版本信息
5. WHEN Workspace 返回 Shot THEN System SHALL 按场景和镜头编号排序

### 需求 10: 为资产页预留选主资产区

**用户故事**: 作为内容创作者，我想要为每个 Shot 选择主资产，以便在后续的预览和导出中使用最佳的视觉效果。

#### 验收标准

1. WHEN 用户查看资产页 THEN System SHALL 展示每个 Shot 的候选资产列表
2. WHEN 用户选择主资产 THEN System SHALL 更新 Asset 的 is_selected 字段
3. WHEN 用户选择主资产 THEN System SHALL 确保同一 Shot 只有一个主资产
4. WHEN 用户选择主资产 THEN System SHALL 记录选择操作的时间和来源
5. WHEN 重跑生成新资产 THEN System SHALL 保留旧资产并将新资产标记为候选

### 需求 11: Shot 数据完整性验证脚本

**用户故事**: 作为系统开发者，我想要创建验证脚本检查 Shot 数据的完整性，以便在开发和测试中快速发现问题。

#### 验收标准

1. WHEN 运行验证脚本 THEN System SHALL 检查所有 Shot 记录的必需字段是否完整
2. WHEN 运行验证脚本 THEN System SHALL 检查 visual_constraints_jsonb 的结构是否符合 Schema
3. WHEN 运行验证脚本 THEN System SHALL 检查 Shot 与 visual_spec 的数量是否一致
4. WHEN 运行验证脚本 THEN System SHALL 检查 character_refs 引用的角色是否存在
5. WHEN 运行验证脚本 THEN System SHALL 输出详细的验证报告和错误列表

### 需求 12: image_render 输入构建服务

**用户故事**: 作为系统开发者，我想要实现 image_render 输入构建服务，以便为 Iteration 4 的媒体链路做好准备。

#### 验收标准

1. WHEN 调用输入构建服务 THEN System SHALL 接收 Shot ID 和 Episode ID 作为参数
2. WHEN 调用输入构建服务 THEN System SHALL 加载 Shot 的 visual_constraints 和关联的 character_profile
3. WHEN 调用输入构建服务 THEN System SHALL 合并 render_prompt 和 visual_anchor 生成完整 Prompt
4. WHEN 调用输入构建服务 THEN System SHALL 返回包含 prompt、style_keywords、composition 的完整参数对象
5. WHEN 调用输入构建服务 THEN System SHALL 支持批量构建多个 Shot 的输入参数
