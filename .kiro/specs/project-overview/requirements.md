# AI 漫剧生成平台 - 项目总体需求文档

## 简介

AI 漫剧生成平台是一个基于 AI 的短视频漫剧自动化生成系统，通过多 Agent 协作完成从创意到成品的完整流程。系统采用 Workflow-First 和 Artifact-First 的设计原则，支持文本生产、媒体生成、质量检查、人工审核和导出的完整闭环。

## 术语表

- **System**: AI 漫剧生成平台
- **Episode**: 单集，是系统的主要交付单元
- **Workflow**: 工作流，编排多个 Stage 的执行顺序
- **Stage**: 工作流中的一个执行阶段，如 brief、script、image_render 等
- **Agent**: 负责文本生成的智能体，如 Brief Agent、Script Agent 等
- **Document**: 文本型产物，如 brief、story_bible、script_draft 等
- **Shot**: 分镜级对象，是图像渲染和局部重跑的关键锚点
- **Asset**: 媒体型产物，如关键帧图像、音频、字幕文件、视频等
- **Workspace**: 工作台，聚合展示项目、剧集、文档、资产等信息的视图
- **LLM**: 大语言模型，如通义千问、OpenAI GPT、Claude 等
- **Provider**: 外部服务提供商，如 LLM provider、Image provider、TTS provider 等
- **Rerun**: 重跑，针对特定 Stage 或 Shot 重新执行生成流程
- **QA**: 质量检查，对生成结果进行规则和语义检查
- **Review**: 人工审核，由人工决定是否通过、打回或拒绝

## 需求

### 需求 1: 项目和剧集管理

**用户故事**: 作为内容创作者，我想要创建和管理项目及剧集，以便组织我的创作内容。

#### 验收标准

1. WHEN 用户创建项目 THEN System SHALL 记录项目名称、题材、平台、目标受众和项目状态
2. WHEN 用户创建剧集 THEN System SHALL 记录剧集标题、集数、素材来源和剧集状态
3. WHEN 用户查询项目列表 THEN System SHALL 返回所有项目及其基本信息
4. WHEN 用户查询剧集详情 THEN System SHALL 返回剧集的完整信息和当前状态

### 需求 2: 工作流编排

**用户故事**: 作为系统架构师，我想要通过工作流编排各个生产阶段，以便确保生产流程的稳定性和可追踪性。

#### 验收标准

1. WHEN 用户启动剧集工作流 THEN System SHALL 创建 WorkflowRun 记录并按顺序执行各个 Stage
2. WHEN Stage 执行开始 THEN System SHALL 创建 StageTask 记录并记录开始时间
3. WHEN Stage 执行完成 THEN System SHALL 更新 StageTask 状态并记录完成时间和产物引用
4. WHEN Stage 执行失败 THEN System SHALL 记录错误信息并支持重试机制
5. WHEN 工作流完成 THEN System SHALL 更新 WorkflowRun 状态为成功或失败

### 需求 3: 文本生产链路

**用户故事**: 作为内容创作者，我想要系统自动生成文本内容，以便快速完成从创意到剧本的创作过程。

#### 验收标准

1. WHEN Brief Stage 执行 THEN System SHALL 生成包含故事类型、目标受众、核心卖点、主要冲突和视觉风格的 brief 文档
2. WHEN Story Bible Stage 执行 THEN System SHALL 生成包含世界规则和禁忌冲突的 story_bible 文档
3. WHEN Character Stage 执行 THEN System SHALL 生成包含角色名称、角色定位、目标动机、说话风格和视觉锚点的 character_profile 文档
4. WHEN Script Stage 执行 THEN System SHALL 生成包含场次、地点、角色、对白和情感节奏的 script_draft 文档
5. WHEN Storyboard Stage 执行 THEN System SHALL 生成包含镜头编号、视觉描述、时长和视觉约束的 visual_spec 文档和 Shot 记录

### 需求 4: Agent 流水线架构

**用户故事**: 作为系统开发者，我想要统一的 Agent 执行流水线，以便确保所有 Agent 的行为一致且可测试。

#### 验收标准

1. WHEN Agent 执行 THEN System SHALL 按照 Loader → Normalizer → Planner → Generator → Critic → Validator → Committer 的顺序执行
2. WHEN Loader 阶段执行 THEN System SHALL 加载输入文档引用和锁定字段信息
3. WHEN Generator 阶段执行 THEN System SHALL 调用 LLM 生成内容
4. WHEN Validator 阶段执行 THEN System SHALL 验证生成内容的 Schema 和必填字段
5. WHEN Committer 阶段执行 THEN System SHALL 持久化文档到数据库并返回文档引用

### 需求 5: 文档版本控制

**用户故事**: 作为内容创作者，我想要编辑文档并保留历史版本，以便在需要时回溯或对比不同版本。

#### 验收标准

1. WHEN 用户编辑文档 THEN System SHALL 创建新版本而不是覆盖原版本
2. WHEN 用户编辑文档 THEN System SHALL 记录编辑来源（用户 ID 或 Agent）
3. WHEN 用户编辑锁定字段 THEN System SHALL 拒绝编辑并返回验证错误
4. WHEN 用户编辑文档 THEN System SHALL 更新文档的 updated_at 时间戳
5. WHEN 用户编辑文档 THEN System SHALL 验证内容符合文档类型的 Schema

### 需求 6: 分镜和 Shot 管理

**用户故事**: 作为内容创作者，我想要查看和管理分镜级的 Shot 信息，以便精确控制每个镜头的视觉效果。

#### 验收标准

1. WHEN Storyboard Stage 完成 THEN System SHALL 为每个镜头创建 Shot 记录
2. WHEN Shot 创建 THEN System SHALL 包含 shot_no、scene_no、duration_sec、visual_description 和 visual_constraints_jsonb 字段
3. WHEN 用户查询 Shot 列表 THEN System SHALL 返回指定剧集的所有 Shot 并按 scene_no 和 shot_no 排序
4. WHEN Shot 包含视觉约束 THEN System SHALL 记录角色视觉锚点、场景风格和构图要求

### 需求 7: 工作台聚合视图

**用户故事**: 作为内容创作者，我想要在工作台看到项目的完整状态，以便了解当前进度和所有产物。

#### 验收标准

1. WHEN 用户查询工作台 THEN System SHALL 返回项目、剧集、最新工作流、文档、Shot 和 StageTask 的聚合信息
2. WHEN 工作台返回文档 THEN System SHALL 返回每种文档类型的最新版本
3. WHEN 工作台返回 Shot THEN System SHALL 返回完整的 Shot 列表和视觉约束信息
4. WHEN 工作台返回 StageTask THEN System SHALL 返回每个 Stage 的执行状态和时间信息

### 需求 8: 媒体生产链路

**用户故事**: 作为内容创作者，我想要系统自动生成图像、音频和视频，以便完成从分镜到成品的制作过程。

#### 验收标准

1. WHEN Image Render Stage 执行 THEN System SHALL 根据 visual_spec 和 character_profile 生成关键帧图像
2. WHEN Subtitle Stage 执行 THEN System SHALL 根据 script_draft 生成字幕文件
3. WHEN TTS Stage 执行 THEN System SHALL 根据 script_draft 和 character_profile 生成角色配音
4. WHEN Preview Export Stage 执行 THEN System SHALL 合成图像、音频和字幕生成预览视频
5. WHEN 媒体资产生成 THEN System SHALL 上传到对象存储并记录 Asset 元数据

### 需求 9: 资产管理

**用户故事**: 作为内容创作者，我想要查看和选择生成的媒体资产，以便为每个 Shot 选择最佳的视觉效果。

#### 验收标准

1. WHEN 系统生成资产 THEN System SHALL 记录资产类型、文件路径、关联的 Shot 或 Episode 和创建时间
2. WHEN 同一 Shot 有多个候选资产 THEN System SHALL 支持标记主资产
3. WHEN 用户查询资产列表 THEN System SHALL 返回指定 Episode 或 Shot 的所有资产
4. WHEN 用户选择主资产 THEN System SHALL 更新资产的 is_selected 标记

### 需求 10: 质量检查

**用户故事**: 作为质量管理者，我想要系统自动检查生成内容的质量，以便及时发现问题并返工。

#### 验收标准

1. WHEN QA Stage 执行 THEN System SHALL 对预览视频和文档进行规则检查和语义检查
2. WHEN QA 检查发现问题 THEN System SHALL 生成 QAReport 并记录问题清单和严重级别
3. WHEN QA 检查通过 THEN System SHALL 允许工作流继续到人工审核阶段
4. WHEN QA 检查失败 THEN System SHALL 阻止工作流进入导出阶段并提供返工建议

### 需求 11: 人工审核

**用户故事**: 作为内容审核者，我想要审核生成的内容并决定是否通过，以便确保最终产品符合质量标准。

#### 验收标准

1. WHEN 工作流到达审核节点 THEN System SHALL 暂停工作流并等待人工决策
2. WHEN 审核者提交通过决策 THEN System SHALL 恢复工作流并继续到导出阶段
3. WHEN 审核者提交打回决策 THEN System SHALL 记录打回原因并支持重跑指定 Stage
4. WHEN 审核者提交拒绝决策 THEN System SHALL 终止工作流并标记为失败

### 需求 12: 重跑机制

**用户故事**: 作为内容创作者，我想要重新生成特定阶段或镜头的内容，以便在不影响其他部分的情况下修复问题。

#### 验收标准

1. WHEN 用户发起 Stage 重跑 THEN System SHALL 创建新的 WorkflowRun 并只执行目标 Stage 和必要的下游 Stage
2. WHEN 用户发起 Shot 重跑 THEN System SHALL 只重新生成指定 Shot 的图像资产
3. WHEN 重跑完成 THEN System SHALL 保留旧版本产物并创建新版本产物
4. WHEN 重跑完成 THEN System SHALL 更新工作台显示新版本产物

### 需求 13: 导出和交付

**用户故事**: 作为内容创作者，我想要导出最终的单集包，以便交付给发布平台。

#### 验收标准

1. WHEN Export Final Stage 执行 THEN System SHALL 合成所有选定资产生成最终视频
2. WHEN 导出完成 THEN System SHALL 创建 ExportBundle 记录并包含导出文件路径和元数据
3. WHEN 用户查询导出历史 THEN System SHALL 返回所有导出记录和下载链接
4. WHEN 导出失败 THEN System SHALL 记录失败原因并支持重试

### 需求 14: 可观测性

**用户故事**: 作为系统运维者，我想要查看系统的执行日志和指标，以便监控系统健康状态和排查问题。

#### 验收标准

1. WHEN Stage 开始执行 THEN System SHALL 记录 Stage 类型、开始时间和尝试次数
2. WHEN Stage 完成执行 THEN System SHALL 记录完成时间、耗时、Token 使用量和成本
3. WHEN LLM 调用发生 THEN System SHALL 记录 Prompt、模型、温度参数和响应内容
4. WHEN 文档提交 THEN System SHALL 记录文档类型、版本号和创建来源
5. WHEN 系统发生错误 THEN System SHALL 记录错误代码、错误消息和堆栈信息

### 需求 15: LLM 服务集成

**用户故事**: 作为系统开发者，我想要支持多个 LLM 提供商，以便根据成本和性能选择最合适的服务。

#### 验收标准

1. WHEN 系统初始化 THEN System SHALL 支持通义千问、OpenAI 和 Claude 三种 LLM 提供商
2. WHEN Agent 调用 LLM THEN System SHALL 使用统一的服务抽象层而不是直接调用 Provider SDK
3. WHEN LLM 调用失败 THEN System SHALL 记录失败原因和 Request ID
4. WHEN 切换 LLM 提供商 THEN System SHALL 通过环境变量配置而不需要修改代码
5. WHEN LLM 返回结果 THEN System SHALL 解析 JSON 并处理格式错误
