# Iteration 4: 媒体链路 Alpha - 需求文档

## 简介

本迭代的目标是打通从 visual_spec 到 preview 的完整媒体生成链路。通过实现图像渲染、字幕生成、TTS 和预览合成，验证媒体 runtime 的可行性，并为后续的 QA 和导出功能做好准备。

本迭代是系统从"纯文本生产"向"多媒体生产"转型的关键里程碑，将首次生成可视化的剧集预览。

## 术语表

- **Media Runtime**: 媒体运行时，负责执行图像渲染、TTS、字幕生成和预览合成等媒体型 Stage
- **Image Provider**: 图像生成服务提供商，如 Stable Diffusion、DALL-E、Midjourney 等
- **TTS Provider**: 文本转语音服务提供商，如 Azure TTS、Google TTS、ElevenLabs 等
- **Asset**: 媒体资产，包括关键帧图像、音频文件、字幕文件、预览视频等
- **Keyframe**: 关键帧图像，每个 Shot 的静态视觉表现
- **Preview**: 预览视频，由关键帧、音频和字幕合成的低分辨率样片
- **Object Storage**: 对象存储服务，用于存储媒体文件，如 S3、OSS 等
- **Asset Selection**: 资产选择，为每个 Shot 选择主资产的过程
- **Candidate Asset**: 候选资产，同一 Shot 的多个生成结果
- **Primary Asset**: 主资产，被选中用于预览和导出的资产
- **Storage Key**: 存储键，资产在对象存储中的唯一标识符
- **Metadata**: 元数据，资产的描述信息，如尺寸、时长、格式等

## 需求

### 需求 1: Object Storage 集成

**用户故事**: 作为系统开发者，我想要集成对象存储服务，以便存储和管理生成的媒体文件。

#### 验收标准

1. WHEN 系统需要上传媒体文件 THEN System SHALL 支持上传到配置的对象存储服务（S3/OSS）
2. WHEN 系统上传文件 THEN System SHALL 生成唯一的 storage_key 并返回可访问的 URL
3. WHEN 系统需要下载媒体文件 THEN System SHALL 支持通过 storage_key 下载文件
4. WHEN 系统上传文件失败 THEN System SHALL 记录错误信息并支持重试
5. WHEN 系统删除资产 THEN System SHALL 同时删除对象存储中的对应文件

### 需求 2: Image Render Stage 实现

**用户故事**: 作为内容创作者，我想要系统能够根据 visual_spec 生成关键帧图像，以便可视化每个镜头的视觉效果。

#### 验收标准

1. WHEN Image Render Stage 执行 THEN System SHALL 使用 ImageRenderInputBuilder 为每个 Shot 构建输入参数
2. WHEN Image Render Stage 调用 Image Provider THEN System SHALL 传入完整的 prompt、style_keywords 和技术参数
3. WHEN Image Provider 返回图像 THEN System SHALL 上传到对象存储并创建 Asset 记录
4. WHEN Image Render Stage 完成 THEN System SHALL 为每个 Shot 创建至少一个 keyframe 类型的 Asset
5. WHEN Image Render Stage 失败 THEN System SHALL 记录失败的 Shot 并继续处理其他 Shot

### 需求 3: Image Provider 适配层

**用户故事**: 作为系统开发者，我想要实现 Image Provider 适配层，以便支持多种图像生成服务并可灵活切换。

#### 验收标准

1. WHEN 系统调用 Image Provider THEN System SHALL 通过统一的适配层接口而不是直接调用 Provider SDK
2. WHEN Image Provider 适配层接收请求 THEN System SHALL 将内部参数转换为 Provider 特定的格式
3. WHEN Image Provider 返回结果 THEN System SHALL 将 Provider 特定的响应转换为统一的内部格式
4. WHEN Image Provider 调用失败 THEN System SHALL 记录 Provider 特定的错误信息和 request_id
5. WHEN 系统配置切换 Provider THEN System SHALL 无需修改业务代码即可使用新 Provider

### 需求 4: Subtitle Generation Stage 实现

**用户故事**: 作为内容创作者，我想要系统能够根据 script_draft 生成字幕文件，以便为视频添加文字说明。

#### 验收标准

1. WHEN Subtitle Generation Stage 执行 THEN System SHALL 从 script_draft 提取每个 Shot 的对白和旁白
2. WHEN Subtitle Generation Stage 生成字幕 THEN System SHALL 根据 Shot 的 duration_ms 计算字幕时间轴
3. WHEN Subtitle Generation Stage 完成 THEN System SHALL 生成 SRT 或 VTT 格式的字幕文件
4. WHEN 字幕文件生成 THEN System SHALL 上传到对象存储并创建 subtitle 类型的 Asset 记录
5. WHEN Subtitle Generation Stage 失败 THEN System SHALL 记录错误但不阻止后续 Stage 执行

### 需求 5: TTS Stage 实现

**用户故事**: 作为内容创作者，我想要系统能够将对白转换为语音，以便为视频添加音频。

#### 验收标准

1. WHEN TTS Stage 执行 THEN System SHALL 从 script_draft 提取每个 Shot 的对白文本
2. WHEN TTS Stage 调用 TTS Provider THEN System SHALL 传入对白文本、角色信息和语音参数
3. WHEN TTS Provider 返回音频 THEN System SHALL 上传到对象存储并创建 audio 类型的 Asset 记录
4. WHEN TTS Stage 完成 THEN System SHALL 为每个包含对白的 Shot 创建音频 Asset
5. WHEN TTS Stage 失败 THEN System SHALL 记录失败的 Shot 并继续处理其他 Shot

### 需求 6: TTS Provider 适配层

**用户故事**: 作为系统开发者，我想要实现 TTS Provider 适配层，以便支持多种 TTS 服务并可灵活切换。

#### 验收标准

1. WHEN 系统调用 TTS Provider THEN System SHALL 通过统一的适配层接口而不是直接调用 Provider SDK
2. WHEN TTS Provider 适配层接收请求 THEN System SHALL 将内部参数转换为 Provider 特定的格式
3. WHEN TTS Provider 返回结果 THEN System SHALL 将音频文件标准化为统一格式（如 MP3）
4. WHEN TTS Provider 调用失败 THEN System SHALL 记录 Provider 特定的错误信息和 request_id
5. WHEN 系统配置切换 Provider THEN System SHALL 无需修改业务代码即可使用新 Provider

### 需求 7: Preview Export Stage 实现

**用户故事**: 作为内容创作者，我想要系统能够合成预览视频，以便查看完整的剧集效果。

#### 验收标准

1. WHEN Preview Export Stage 执行 THEN System SHALL 收集所有 Shot 的主关键帧、音频和字幕
2. WHEN Preview Export Stage 合成视频 THEN System SHALL 使用 FFmpeg 或等价工具按 Shot 顺序拼接
3. WHEN Preview Export Stage 完成 THEN System SHALL 生成低分辨率的预览视频（如 720p）
4. WHEN 预览视频生成 THEN System SHALL 上传到对象存储并创建 preview 类型的 Asset 记录
5. WHEN Preview Export Stage 失败 THEN System SHALL 记录详细的错误信息和失败的 Shot 位置

### 需求 8: Asset Selection 功能

**用户故事**: 作为内容创作者，我想要为每个 Shot 选择主资产，以便控制预览和导出中使用的具体版本。

#### 验收标准

1. WHEN 用户查看 Shot 的资产列表 THEN System SHALL 展示所有候选资产及其预览
2. WHEN 用户选择主资产 THEN System SHALL 更新 Asset 的 is_selected 字段为 true
3. WHEN 用户选择新的主资产 THEN System SHALL 将同一 Shot 的其他资产的 is_selected 设置为 false
4. WHEN 系统生成预览或导出 THEN System SHALL 只使用 is_selected 为 true 的资产
5. WHEN 用户未选择主资产 THEN System SHALL 默认使用最新生成的资产

### 需求 9: Asset Metadata 管理

**用户故事**: 作为系统开发者，我想要完善 Asset 的元数据管理，以便追踪资产的来源、质量和使用情况。

#### 验收标准

1. WHEN Asset 创建 THEN System SHALL 记录 storage_key、mime_type、size_bytes 等基础信息
2. WHEN Asset 是图像 THEN System SHALL 记录 width、height、format 等图像特定信息
3. WHEN Asset 是音频 THEN System SHALL 记录 duration_ms、sample_rate、channels 等音频特定信息
4. WHEN Asset 创建 THEN System SHALL 记录生成来源（stage_task_id）和生成时间
5. WHEN Asset 被选为主资产 THEN System SHALL 记录选择时间和选择来源

### 需求 10: Media Workflow 编排

**用户故事**: 作为系统开发者，我想要实现媒体链路的 Workflow 编排，以便按正确顺序执行各个媒体 Stage。

#### 验收标准

1. WHEN 文本链路完成 THEN System SHALL 自动启动媒体链路 Workflow
2. WHEN 媒体链路执行 THEN System SHALL 按照 image_render → subtitle → tts → preview_export 的顺序执行
3. WHEN 某个 Stage 失败 THEN System SHALL 记录失败信息并决定是否继续后续 Stage
4. WHEN 媒体链路完成 THEN System SHALL 更新 WorkflowRun 状态为 media_ready 或 media_failed
5. WHEN 媒体链路执行 THEN System SHALL 为每个 Stage 创建 StageTask 记录

### 需求 11: 批量处理和并行优化

**用户故事**: 作为系统开发者，我想要优化媒体生成的性能，以便缩短整体生成时间。

#### 验收标准

1. WHEN Image Render Stage 执行 THEN System SHALL 支持并行处理多个 Shot 的图像生成
2. WHEN TTS Stage 执行 THEN System SHALL 支持并行处理多个 Shot 的音频生成
3. WHEN 并行任务执行 THEN System SHALL 限制最大并发数以避免 Provider 限流
4. WHEN 批量任务失败 THEN System SHALL 记录每个失败任务的详细信息
5. WHEN 批量任务完成 THEN System SHALL 聚合所有任务的执行指标

### 需求 12: 错误处理和重试机制

**用户故事**: 作为系统开发者，我想要实现健壮的错误处理和重试机制，以便应对 Provider 的不稳定性。

#### 验收标准

1. WHEN Provider 调用超时 THEN System SHALL 自动重试最多 3 次
2. WHEN Provider 返回临时错误（如 429 限流）THEN System SHALL 使用指数退避策略重试
3. WHEN Provider 返回永久错误（如 400 参数错误）THEN System SHALL 不重试并记录错误
4. WHEN 重试全部失败 THEN System SHALL 记录所有重试的错误信息
5. WHEN Stage 失败 THEN System SHALL 保留已成功生成的资产不被删除

### 需求 13: 成本和性能监控

**用户故事**: 作为系统开发者，我想要监控媒体生成的成本和性能，以便优化资源使用。

#### 验收标准

1. WHEN Image Provider 调用完成 THEN System SHALL 记录调用次数、耗时和估算成本
2. WHEN TTS Provider 调用完成 THEN System SHALL 记录字符数、耗时和估算成本
3. WHEN Stage 执行完成 THEN System SHALL 记录总耗时、成功率和失败原因分布
4. WHEN 查询 StageTask THEN System SHALL 返回包含性能指标的详细信息
5. WHEN 系统运行 THEN System SHALL 支持按 Episode、Project 聚合成本和性能数据

### 需求 14: Preview 展示和播放

**用户故事**: 作为内容创作者，我想要在工作台查看生成的预览视频，以便评估剧集效果。

#### 验收标准

1. WHEN 用户访问 Preview 页面 THEN System SHALL 展示最新的预览视频
2. WHEN 预览视频存在 THEN System SHALL 提供在线播放功能
3. WHEN 预览视频不存在 THEN System SHALL 展示生成状态和预计完成时间
4. WHEN 预览生成失败 THEN System SHALL 展示失败原因和重试入口
5. WHEN 用户查看 Preview THEN System SHALL 展示预览的元数据（时长、分辨率、生成时间等）

### 需求 15: Workspace 集成媒体信息

**用户故事**: 作为内容创作者，我想要在 Workspace 查看媒体生成状态，以便了解当前进度。

#### 验收标准

1. WHEN 用户查询 Workspace THEN System SHALL 返回媒体链路的执行状态
2. WHEN Workspace 返回 Shot 信息 THEN System SHALL 包含每个 Shot 的主资产信息
3. WHEN Workspace 返回资产信息 THEN System SHALL 包含资产的预览 URL 和元数据
4. WHEN Workspace 返回 Workflow 状态 THEN System SHALL 包含当前执行的媒体 Stage
5. WHEN 媒体生成失败 THEN System SHALL 在 Workspace 中展示失败的 Stage 和错误信息

