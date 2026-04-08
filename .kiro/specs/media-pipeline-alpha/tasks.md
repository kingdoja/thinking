# Iteration 4: 媒体链路 Alpha - 实现计划

## 概述

本迭代的目标是打通从 visual_spec 到 preview 的完整媒体生成链路。通过实现图像渲染、字幕生成、TTS 和预览合成，验证媒体 runtime 的可行性，并为后续的 QA 和导出功能做好准备。

---

## 任务列表

- [x] 1. Object Storage 集成








  - [x] 1.1 实现 Object Storage Service




    - 创建 ObjectStorageService 类
    - 实现 upload_file 方法
    - 实现 download_file 方法
    - 实现 delete_file 方法
    - 实现 get_url 方法（生成签名 URL）
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.2 配置 S3/OSS 连接




    - 添加配置项（bucket、region、credentials）
    - 实现连接测试
    - 处理认证和权限
    - _需求: 1.1_

  - [x] 1.3 实现 storage_key 生成策略




    - 设计 key 命名规则（如 {project_id}/{episode_id}/{asset_type}/{uuid}）
    - 确保 key 唯一性
    - 支持按类型和时间组织
    - _需求: 1.2_

  - [ ]* 1.4 编写 Object Storage Service 单元测试
    - 测试上传功能
    - 测试下载功能
    - 测试删除功能
    - 测试 URL 生成
    - 测试错误处理
    - _需求: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Image Provider 适配层








  - [x] 2.1 创建 Image Provider Adapter 基类




    - 定义 ImageProviderAdapter 抽象基类
    - 定义 generate_image 抽象方法
    - 定义 ImageGenerationResult 数据类
    - 定义 ProviderError 异常类
    - _需求: 3.1, 3.2_

  - [x] 2.2 实现 Stable Diffusion Adapter（或选择其他 Provider）




    - 实现 StableDiffusionAdapter 类
    - 实现参数转换逻辑
    - 实现 API 调用
    - 实现响应解析
    - 处理错误和重试
    - _需求: 3.1, 3.2, 3.3, 3.4_

  - [x] 2.3 实现 Provider 配置管理




    - 添加 Provider 选择配置
    - 添加 Provider 特定参数配置
    - 实现 Provider 工厂模式
    - _需求: 3.5_

  - [ ]* 2.4 编写 Image Provider Adapter 单元测试
    - 测试参数转换
    - 测试 API 调用（使用 Mock）
    - 测试响应解析
    - 测试错误处理
    - _需求: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Image Render Stage 实现









  - [x] 3.1 创建 Image Render Stage 类




    - 创建 ImageRenderStage 类
    - 实现 execute 方法
    - 集成 ImageRenderInputBuilder
    - 集成 Image Provider Adapter
    - 集成 Object Storage Service
    - _需求: 2.1, 2.2, 2.3_

  - [x] 3.2 实现并行图像生成逻辑



    - 实现 _generate_images_parallel 方法
    - 使用 asyncio.Semaphore 控制并发
    - 实现单个图像生成逻辑
    - 处理异常和超时
    - _需求: 11.1, 11.3_

  - [x] 3.3 实现重试机制



    - 实现指数退避重试
    - 区分临时错误和永久错误
    - 记录重试次数和错误
    - _需求: 12.1, 12.2, 12.3_

  - [x] 3.4 实现资产上传和记录创建



    - 下载生成的图像到临时文件
    - 上传到 Object Storage
    - 创建 Asset 记录
    - 清理临时文件
    - _需求: 2.3, 2.4, 9.1, 9.2_

  - [ ]* 3.5 编写 Image Render Stage 单元测试
    - 测试单个 Shot 处理
    - 测试批量处理
    - 测试并发控制
    - 测试重试逻辑
    - 测试失败处理
    - _需求: 2.1, 2.2, 2.5, 11.1, 12.1_

- [x] 4. Subtitle Generation Stage 实现


















  - [x] 4.1 创建 Subtitle Generation Stage 类



    - 创建 SubtitleGenerationStage 类
    - 实现 execute 方法
    - 集成 Document Repository
    - 集成 Shot Repository
    - _需求: 4.1, 4.2_


  - [x] 4.2 实现字幕生成逻辑



    - 从 script_draft 提取对白
    - 根据 Shot duration_ms 计算时间轴
    - 生成 VTT 格式字幕
    - 处理特殊字符和换行
    - _需求: 4.1, 4.2, 4.3_


  - [x] 4.3 实现字幕文件上传





    - 保存字幕到临时文件
    - 上传到 Object Storage
    - 创建 Asset 记录
    - _需求: 4.4_

  - [ ]* 4.4 编写 Subtitle Generation Stage 单元测试
    - 测试对白提取
    - 测试时间轴计算
    - 测试 VTT 格式生成
    - 测试文件上传
    - _需求: 4.1, 4.2, 4.3, 4.4_

- [x] 5. TTS Provider 适配层









  - [x] 5.1 创建 TTS Provider Adapter 基类




    - 定义 TTSProviderAdapter 抽象基类
    - 定义 synthesize_speech 抽象方法
    - 定义 TTSResult 数据类
    - _需求: 6.1, 6.2_

  - [x] 5.2 实现 Azure TTS Adapter（或选择其他 Provider）




    - 实现 AzureTTSAdapter 类
    - 实现参数转换逻辑
    - 实现 API 调用
    - 实现音频格式转换
    - 处理错误和重试
    - _需求: 6.1, 6.2, 6.3, 6.4_

  - [x] 5.3 实现 Provider 配置管理




    - 添加 TTS Provider 选择配置
    - 添加语音和语言配置
    - 实现 Provider 工厂模式
    - _需求: 6.5_

  - [ ]* 5.4 编写 TTS Provider Adapter 单元测试
    - 测试参数转换
    - 测试 API 调用（使用 Mock）
    - 测试音频格式转换
    - 测试错误处理
    - _需求: 6.1, 6.2, 6.3, 6.4_

- [x] 6. TTS Stage 实现










  - [x] 6.1 创建 TTS Stage 类



    - 创建 TTSStage 类
    - 实现 execute 方法
    - 集成 TTS Provider Adapter
    - 集成 Object Storage Service
    - _需求: 5.1, 5.2_


  - [x] 6.2 实现对白提取逻辑



    - 从 script_draft 提取对白
    - 关联对白到 Shot
    - 提取角色信息
    - _需求: 5.1_


  - [x] 6.3 实现并行音频生成逻辑



    - 实现 _synthesize_audio_parallel 方法
    - 使用 asyncio.Semaphore 控制并发
    - 实现单个音频生成逻辑
    - 处理异常和超时

    - _需求: 11.2, 11.3_

  - [x] 6.4 实现音频上传和记录创建



    - 保存音频到临时文件
    - 上传到 Object Storage
    - 创建 Asset 记录（包含 duration_ms）
    - 清理临时文件
    - _需求: 5.3, 5.4, 9.1, 9.3_

  - [ ]* 6.5 编写 TTS Stage 单元测试
    - 测试对白提取
    - 测试单个音频生成
    - 测试批量处理
    - 测试并发控制
    - 测试失败处理
    - _需求: 5.1, 5.2, 5.3, 5.4, 11.2_

- [x] 7. Preview Export Stage 实现












  - [x] 7.1 创建 Preview Export Stage 类



    - 创建 PreviewExportStage 类
    - 实现 execute 方法
    - 集成 Asset Repository
    - 集成 Shot Repository
    - _需求: 7.1, 7.2_


  - [x] 7.2 实现主资产收集逻辑


    - 查询所有 Shot
    - 为每个 Shot 获取主关键帧
    - 为每个 Shot 获取主音频（如果有）
    - 获取字幕文件
    - _需求: 7.1_

  - [x] 7.3 实现资产下载逻辑



    - 创建临时工作目录
    - 批量下载所有资产
    - 验证文件完整性
    - _需求: 7.1_

  - [x] 7.4 实现 FFmpeg 视频合成逻辑



    - 构建 FFmpeg 命令
    - 按 Shot 顺序拼接关键帧
    - 添加音频轨道
    - 添加字幕
    - 设置输出参数（720p, H.264）
    - _需求: 7.2, 7.3_


  - [x] 7.5 实现预览视频上传


    - 上传合成的视频到 Object Storage
    - 创建 Asset 记录（包含 duration_ms, width, height）
    - 清理临时文件
    - _需求: 7.4_

  - [ ]* 7.6 编写 Preview Export Stage 单元测试
    - 测试资产收集
    - 测试资产下载
    - 测试 FFmpeg 命令构建
    - 测试视频上传
    - 测试错误处理
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 8. Media Workflow 编排












  - [x] 8.1 创建 Media Workflow Service






    - 创建 MediaWorkflowService 类
    - 实现 execute_media_chain 方法
    - 定义 Stage 执行顺序
    - _需求: 10.1, 10.2_

  - [x] 8.2 集成所有 Media Stages




    - 集成 Image Render Stage
    - 集成 Subtitle Generation Stage
    - 集成 TTS Stage
    - 集成 Preview Export Stage
    - _需求: 10.2_

  - [x] 8.3 实现 Stage 失败处理




    - 记录失败的 Stage
    - 决定是否继续后续 Stage
    - 更新 WorkflowRun 状态
    - _需求: 10.3, 10.4_


  - [ ] 8.4 实现 StageTask 记录管理
























    - 为每个 Stage 创建 StageTask
    - 更新 StageTask 状态
    - 记录执行指标
    - _需求: 10.5_

  - [ ]* 8.5 编写 Media Workflow Service 单元测试
    - 测试完整链路执行
    - 测试 Stage 顺序
    - 测试失败处理
    - 测试 StageTask 创建
    - _需求: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 9. Asset Selection 功能




  - [ ] 9.1 实现 Asset Selection Service


    - 创建 AssetSelectionService 类
    - 实现 select_primary_asset 方法
    - 实现 get_candidate_assets 方法
    - 确保主资产唯一性
    - _需求: 8.1, 8.2, 8.3_

  - [ ] 9.2 创建 Asset Selection API 端点


    - POST /shots/{shot_id}/assets/{asset_id}/select - 选择主资产
    - GET /shots/{shot_id}/assets - 获取候选资产列表
    - _需求: 8.1, 8.2_

  - [ ] 9.3 实现选择历史记录


    - 记录选择时间
    - 记录选择来源（用户/系统）
    - 支持查询选择历史
    - _需求: 8.4_

  - [ ]* 9.4 编写 Asset Selection 单元测试
    - 测试主资产选择
    - 测试唯一性约束
    - 测试候选资产查询
    - 测试选择历史
    - _需求: 8.1, 8.2, 8.3, 8.4_

- [ ] 10. 性能监控和成本追踪




  - [ ] 10.1 实现 Provider 调用监控


    - 记录每次 Provider 调用
    - 记录调用耗时
    - 记录成功/失败状态
    - 记录 request_id
    - _需求: 13.1, 13.2, 13.4_

  - [ ] 10.2 实现成本估算


    - 为 Image Provider 估算成本
    - 为 TTS Provider 估算成本
    - 记录到 StageTask metrics
    - _需求: 13.1, 13.2_

  - [ ] 10.3 实现性能指标聚合


    - 聚合 Stage 级别指标
    - 聚合 Episode 级别指标
    - 聚合 Project 级别指标
    - _需求: 13.3, 13.5_

  - [ ]* 10.4 创建监控查询 API
    - GET /episodes/{episode_id}/metrics - 查询 Episode 指标
    - GET /stage-tasks/{stage_task_id}/metrics - 查询 Stage 指标
    - _需求: 13.4_

- [ ] 11. Preview 展示功能




  - [ ] 11.1 创建 Preview API 端点


    - GET /episodes/{episode_id}/preview - 获取预览信息
    - 返回预览视频 URL
    - 返回预览元数据
    - _需求: 14.1, 14.5_

  - [ ] 11.2 实现预览状态查询


    - 查询预览生成状态
    - 返回进度信息
    - 返回预计完成时间
    - _需求: 14.3_

  - [ ] 11.3 实现预览失败处理


    - 展示失败原因
    - 提供重试入口
    - 记录失败日志
    - _需求: 14.4_

  - [ ]* 11.4 编写 Preview API 测试
    - 测试预览查询
    - 测试状态查询
    - 测试失败处理
    - _需求: 14.1, 14.3, 14.4_

- [ ] 12. Workspace 集成媒体信息




  - [ ] 12.1 更新 Workspace 聚合逻辑


    - 包含媒体链路状态
    - 包含 Shot 主资产信息
    - 包含预览视频信息
    - _需求: 15.1, 15.2, 15.3_

  - [ ] 12.2 更新 Workspace Schema


    - 添加 media_status 字段
    - 添加 primary_assets 字段
    - 添加 preview_url 字段
    - _需求: 15.1, 15.2, 15.3_

  - [ ] 12.3 实现媒体失败信息展示


    - 展示失败的 Stage
    - 展示错误信息
    - 提供重试入口
    - _需求: 15.5_

  - [ ]* 12.4 编写 Workspace 集成测试
    - 测试媒体信息包含
    - 测试资产信息展示
    - 测试失败信息展示
    - _需求: 15.1, 15.2, 15.3, 15.5_

- [ ] 13. 文档和示例




  - [ ] 13.1 编写 Object Storage 使用文档


    - 记录配置方法
    - 提供使用示例
    - 说明 storage_key 规则
    - _需求: 1.1, 1.2_

  - [ ] 13.2 编写 Provider 适配层文档


    - 记录如何添加新 Provider
    - 提供 Adapter 实现示例
    - 说明配置方法
    - _需求: 3.1, 6.1_

  - [ ] 13.3 编写媒体链路使用指南


    - 说明完整流程
    - 提供配置示例
    - 说明常见问题和解决方法
    - _需求: 所有_

  - [ ] 13.4 编写 Iteration 4 完成报告


    - 总结完成的任务
    - 记录性能指标
    - 列出已知问题
    - 提供下一步建议
    - _需求: 所有_

- [ ] 14. Checkpoint - 确保核心功能可用
  - 运行端到端测试
  - 验证图像生成
  - 验证预览合成
  - 确认所有核心功能可用，询问用户是否有问题

---

## 任务优先级

### 高优先级（必须完成）

1. 任务 1: Object Storage 集成
2. 任务 2: Image Provider 适配层
3. 任务 3: Image Render Stage 实现
4. 任务 4: Subtitle Generation Stage 实现
5. 任务 7: Preview Export Stage 实现
6. 任务 8: Media Workflow 编排

### 中优先级（尽量完成）

1. 任务 5: TTS Provider 适配层
2. 任务 6: TTS Stage 实现
3. 任务 9: Asset Selection 功能
4. 任务 11: Preview 展示功能
5. 任务 12: Workspace 集成媒体信息

### 低优先级（可推迟）

1. 任务 10: 性能监控和成本追踪
2. 任务 13: 文档和示例

---

## 验收标准（DoD）

本迭代完成的标准：

1. ✅ Object Storage 可以上传、下载和删除文件
2. ✅ 至少一个 Image Provider 可用
3. ✅ Image Render Stage 可以为所有 Shot 生成关键帧
4. ✅ Subtitle Generation Stage 可以生成字幕文件
5. ✅ Preview Export Stage 可以合成预览视频
6. ✅ 媒体链路可以端到端执行
7. ✅ Workspace 可以展示媒体生成状态
8. ✅ 至少一个完整的 Episode 可以生成预览

---

## 风险和注意事项

### Provider 稳定性风险

**风险**: Image Provider 和 TTS Provider 可能不稳定或限流

**缓解措施**:
- 实现健壮的重试机制
- 使用指数退避策略
- 记录详细的错误信息
- 支持 Provider 切换

### 性能风险

**风险**: 大量 Shot 时生成时间可能很长

**缓解措施**:
- 实现并行处理
- 限制合理的并发数
- 优化资源使用
- 提供进度反馈

### 成本风险

**风险**: Provider 调用成本可能很高

**缓解措施**:
- 监控和记录成本
- 实现成本告警
- 优化 Provider 调用
- 使用缓存减少重复调用

### FFmpeg 依赖风险

**风险**: FFmpeg 可能不可用或版本不兼容

**缓解措施**:
- 检查 FFmpeg 安装
- 记录 FFmpeg 版本要求
- 提供安装指南
- 处理 FFmpeg 错误

---

## 相关文档

- **需求文档**: `.kiro/specs/media-pipeline-alpha/requirements.md`
- **设计文档**: `.kiro/specs/media-pipeline-alpha/design.md`
- **项目总体任务**: `.kiro/specs/project-overview/tasks.md`
- **Iteration 3 完成报告**: `.kiro/specs/storyboard-to-asset/ITERATION3_COMPLETION_REPORT.md`
- **ImageRenderInput 文档**: `docs/engineering/IMAGE_RENDER_INPUT.md`
- **Shot 数据结构文档**: `docs/engineering/SHOT_DATA_STRUCTURE.md`
- **系统蓝图**: `docs/engineering/SYSTEM-BLUEPRINT.md`

---

**创建日期**: 2026-04-07  
**预计完成**: 第 7-8 周  
**当前状态**: 准备开始

