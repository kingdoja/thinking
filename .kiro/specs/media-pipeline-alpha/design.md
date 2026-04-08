# Iteration 4: 媒体链路 Alpha - 设计文档

## 概述

本迭代实现从 visual_spec 到 preview 的完整媒体生成链路，是系统从纯文本生产向多媒体生产转型的关键里程碑。通过实现图像渲染、字幕生成、TTS 和预览合成，验证媒体 runtime 的可行性。

关键设计原则：
- **Provider 可替换**: 通过适配层隔离 Provider 特定逻辑
- **失败容忍**: 单个 Shot 失败不影响其他 Shot
- **资产版本化**: 支持多个候选资产并可选择主资产
- **性能优化**: 支持并行处理和批量操作
- **成本可控**: 监控和记录所有 Provider 调用的成本

## 架构

### 媒体链路数据流

```
visual_spec + character_profile
    ↓
ImageRenderInputBuilder
    ↓
Image Render Stage
    ↓ (并行处理多个 Shot)
Image Provider (Stable Diffusion / DALL-E / etc.)
    ↓
Keyframe Assets (上传到 Object Storage)
    ↓
Subtitle Generation Stage
    ↓
Subtitle Assets
    ↓
TTS Stage
    ↓ (并行处理多个 Shot)
TTS Provider (Azure TTS / Google TTS / etc.)
    ↓
Audio Assets
    ↓
Preview Export Stage
    ↓ (FFmpeg 合成)
Preview Video Asset
```

### 组件关系

```
┌─────────────────────────────────────────────────────────┐
│                  Workflow Orchestrator                  │
│  编排媒体链路 Stage 执行顺序                            │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ├─────────────────┬────────────────────┐
                   ↓                 ↓                    ↓
         ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
         │ Image Render     │ │ Subtitle Gen │ │ TTS Stage       │
         │ Stage            │ │ Stage        │ │                 │
         └────────┬─────────┘ └──────┬───────┘ └────────┬────────┘
                  │                  │                   │
                  ↓                  ↓                   ↓
         ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
         │ Image Provider   │ │ Subtitle     │ │ TTS Provider    │
         │ Adapter          │ │ Generator    │ │ Adapter         │
         └────────┬─────────┘ └──────┬───────┘ └────────┬────────┘
                  │                  │                   │
                  └──────────────────┴───────────────────┘
                                     ↓
                   ┌──────────────────────────────────────┐
                   │      Object Storage Service          │
                   │  存储所有媒体文件                    │
                   └──────────────────┬───────────────────┘
                                      ↓
                   ┌──────────────────────────────────────┐
                   │      Asset Repository                │
                   │  管理资产元数据                      │
                   └──────────────────────────────────────┘
```

## 组件和接口

### Object Storage Service

```python
class ObjectStorageService:
    """
    对象存储服务，负责上传、下载和删除媒体文件。
    
    职责：
    1. 上传文件到对象存储
    2. 生成唯一的 storage_key
    3. 返回可访问的 URL
    4. 下载文件
    5. 删除文件
    """
    
    def upload_file(
        self,
        file_path: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """
        上传文件到对象存储。
        
        Args:
            file_path: 本地文件路径
            content_type: MIME 类型
            metadata: 可选的元数据
            
        Returns:
            UploadResult: 包含 storage_key 和 url
        """
        pass
    
    def download_file(
        self,
        storage_key: str,
        local_path: str
    ) -> bool:
        """
        从对象存储下载文件。
        
        Args:
            storage_key: 存储键
            local_path: 本地保存路径
            
        Returns:
            bool: 是否成功
        """
        pass
    
    def delete_file(
        self,
        storage_key: str
    ) -> bool:
        """
        从对象存储删除文件。
        
        Args:
            storage_key: 存储键
            
        Returns:
            bool: 是否成功
        """
        pass
    
    def get_url(
        self,
        storage_key: str,
        expires_in: int = 3600
    ) -> str:
        """
        获取文件的访问 URL。
        
        Args:
            storage_key: 存储键
            expires_in: 过期时间（秒）
            
        Returns:
            str: 可访问的 URL
        """
        pass
```

### Image Provider Adapter

```python
class ImageProviderAdapter(ABC):
    """
    图像生成 Provider 适配层基类。
    
    职责：
    1. 将内部参数转换为 Provider 特定格式
    2. 调用 Provider API
    3. 将 Provider 响应转换为统一格式
    4. 处理错误和重试
    """
    
    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1080,
        height: int = 1920,
        style: Optional[str] = None,
        **kwargs
    ) -> ImageGenerationResult:
        """
        生成图像。
        
        Args:
            prompt: 正面提示词
            negative_prompt: 负面提示词
            width: 图像宽度
            height: 图像高度
            style: 风格参数
            **kwargs: Provider 特定参数
            
        Returns:
            ImageGenerationResult: 包含图像数据和元数据
        """
        pass


class StableDiffusionAdapter(ImageProviderAdapter):
    """Stable Diffusion 适配器实现"""
    
    def generate_image(self, ...) -> ImageGenerationResult:
        # 实现 Stable Diffusion 特定逻辑
        pass


class DALLEAdapter(ImageProviderAdapter):
    """DALL-E 适配器实现"""
    
    def generate_image(self, ...) -> ImageGenerationResult:
        # 实现 DALL-E 特定逻辑
        pass
```

### Image Render Stage

```python
class ImageRenderStage:
    """
    图像渲染 Stage，负责为所有 Shot 生成关键帧图像。
    
    职责：
    1. 使用 ImageRenderInputBuilder 构建输入
    2. 并行调用 Image Provider
    3. 上传图像到对象存储
    4. 创建 Asset 记录
    5. 处理失败和重试
    """
    
    def __init__(
        self,
        image_provider: ImageProviderAdapter,
        storage_service: ObjectStorageService,
        asset_repo: AssetRepository,
        input_builder: ImageRenderInputBuilder
    ):
        self.image_provider = image_provider
        self.storage_service = storage_service
        self.asset_repo = asset_repo
        self.input_builder = input_builder
    
    async def execute(
        self,
        episode_id: UUID,
        stage_task_id: UUID,
        max_concurrent: int = 5
    ) -> StageExecutionResult:
        """
        执行图像渲染 Stage。
        
        Args:
            episode_id: Episode ID
            stage_task_id: StageTask ID
            max_concurrent: 最大并发数
            
        Returns:
            StageExecutionResult: 执行结果
        """
        # 1. 构建所有 Shot 的输入
        inputs = self.input_builder.build_inputs_for_episode(episode_id)
        
        # 2. 并行生成图像
        results = await self._generate_images_parallel(
            inputs,
            max_concurrent
        )
        
        # 3. 上传图像并创建 Asset
        assets = await self._upload_and_create_assets(
            results,
            episode_id,
            stage_task_id
        )
        
        # 4. 返回执行结果
        return StageExecutionResult(
            status="succeeded" if all(r.success for r in results) else "partial_success",
            assets_created=len(assets),
            errors=[r.error for r in results if not r.success]
        )
    
    async def _generate_images_parallel(
        self,
        inputs: List[ImageRenderInput],
        max_concurrent: int
    ) -> List[ImageGenerationResult]:
        """并行生成图像"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(input_data):
            async with semaphore:
                return await self._generate_single_image(input_data)
        
        tasks = [generate_with_semaphore(inp) for inp in inputs]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _generate_single_image(
        self,
        input_data: ImageRenderInput
    ) -> ImageGenerationResult:
        """生成单个图像，包含重试逻辑"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await self.image_provider.generate_image(
                    prompt=input_data.prompt,
                    negative_prompt=input_data.negative_prompt,
                    width=input_data.resolution[0],
                    height=input_data.resolution[1],
                    style=input_data.visual_style
                )
                return result
            except ProviderError as e:
                if attempt == max_retries - 1:
                    return ImageGenerationResult(
                        success=False,
                        error=str(e),
                        shot_id=input_data.shot_id
                    )
                await asyncio.sleep(2 ** attempt)  # 指数退避
```

### TTS Provider Adapter

```python
class TTSProviderAdapter(ABC):
    """
    TTS Provider 适配层基类。
    
    职责：
    1. 将内部参数转换为 Provider 特定格式
    2. 调用 Provider API
    3. 将音频标准化为统一格式
    4. 处理错误和重试
    """
    
    @abstractmethod
    def synthesize_speech(
        self,
        text: str,
        voice: str,
        language: str = "zh-CN",
        speed: float = 1.0,
        **kwargs
    ) -> TTSResult:
        """
        合成语音。
        
        Args:
            text: 要合成的文本
            voice: 语音名称
            language: 语言代码
            speed: 语速
            **kwargs: Provider 特定参数
            
        Returns:
            TTSResult: 包含音频数据和元数据
        """
        pass


class AzureTTSAdapter(TTSProviderAdapter):
    """Azure TTS 适配器实现"""
    
    def synthesize_speech(self, ...) -> TTSResult:
        # 实现 Azure TTS 特定逻辑
        pass


class GoogleTTSAdapter(TTSProviderAdapter):
    """Google TTS 适配器实现"""
    
    def synthesize_speech(self, ...) -> TTSResult:
        # 实现 Google TTS 特定逻辑
        pass
```

### TTS Stage

```python
class TTSStage:
    """
    TTS Stage，负责为所有包含对白的 Shot 生成音频。
    
    职责：
    1. 从 script_draft 提取对白
    2. 并行调用 TTS Provider
    3. 上传音频到对象存储
    4. 创建 Asset 记录
    5. 处理失败和重试
    """
    
    def __init__(
        self,
        tts_provider: TTSProviderAdapter,
        storage_service: ObjectStorageService,
        asset_repo: AssetRepository,
        document_repo: DocumentRepository
    ):
        self.tts_provider = tts_provider
        self.storage_service = storage_service
        self.asset_repo = asset_repo
        self.document_repo = document_repo
    
    async def execute(
        self,
        episode_id: UUID,
        stage_task_id: UUID,
        max_concurrent: int = 5
    ) -> StageExecutionResult:
        """
        执行 TTS Stage。
        
        Args:
            episode_id: Episode ID
            stage_task_id: StageTask ID
            max_concurrent: 最大并发数
            
        Returns:
            StageExecutionResult: 执行结果
        """
        # 1. 加载 script_draft
        script = self.document_repo.get_latest_by_type(
            episode_id,
            "script_draft"
        )
        
        # 2. 提取对白
        dialogues = self._extract_dialogues(script)
        
        # 3. 并行生成音频
        results = await self._synthesize_audio_parallel(
            dialogues,
            max_concurrent
        )
        
        # 4. 上传音频并创建 Asset
        assets = await self._upload_and_create_assets(
            results,
            episode_id,
            stage_task_id
        )
        
        # 5. 返回执行结果
        return StageExecutionResult(
            status="succeeded" if all(r.success for r in results) else "partial_success",
            assets_created=len(assets),
            errors=[r.error for r in results if not r.success]
        )
```

### Subtitle Generation Stage

```python
class SubtitleGenerationStage:
    """
    字幕生成 Stage，负责生成字幕文件。
    
    职责：
    1. 从 script_draft 提取对白和旁白
    2. 根据 Shot 时长计算时间轴
    3. 生成 SRT/VTT 格式字幕
    4. 上传字幕文件到对象存储
    5. 创建 Asset 记录
    """
    
    def execute(
        self,
        episode_id: UUID,
        stage_task_id: UUID
    ) -> StageExecutionResult:
        """
        执行字幕生成 Stage。
        
        Args:
            episode_id: Episode ID
            stage_task_id: StageTask ID
            
        Returns:
            StageExecutionResult: 执行结果
        """
        # 1. 加载 script_draft 和 shots
        script = self.document_repo.get_latest_by_type(
            episode_id,
            "script_draft"
        )
        shots = self.shot_repo.get_by_episode(episode_id)
        
        # 2. 生成字幕
        subtitle_content = self._generate_subtitle(script, shots)
        
        # 3. 保存为文件
        subtitle_file = self._save_subtitle_file(subtitle_content)
        
        # 4. 上传并创建 Asset
        upload_result = self.storage_service.upload_file(
            subtitle_file,
            "text/vtt"
        )
        
        asset = self.asset_repo.create_asset(
            episode_id=episode_id,
            stage_task_id=stage_task_id,
            asset_type="subtitle",
            storage_key=upload_result.storage_key,
            mime_type="text/vtt"
        )
        
        return StageExecutionResult(
            status="succeeded",
            assets_created=1
        )
    
    def _generate_subtitle(
        self,
        script: DocumentModel,
        shots: List[ShotModel]
    ) -> str:
        """
        生成 VTT 格式字幕。
        
        格式:
        WEBVTT
        
        00:00:00.000 --> 00:00:05.000
        第一句对白
        
        00:00:05.000 --> 00:00:10.000
        第二句对白
        """
        lines = ["WEBVTT", ""]
        
        current_time = 0
        for shot in shots:
            if shot.dialogue_text:
                start_time = self._format_time(current_time)
                end_time = self._format_time(current_time + shot.duration_ms)
                
                lines.append(f"{start_time} --> {end_time}")
                lines.append(shot.dialogue_text)
                lines.append("")
            
            current_time += shot.duration_ms
        
        return "\n".join(lines)
```

### Preview Export Stage

```python
class PreviewExportStage:
    """
    预览导出 Stage，负责合成预览视频。
    
    职责：
    1. 收集所有 Shot 的主资产
    2. 使用 FFmpeg 合成视频
    3. 上传预览视频到对象存储
    4. 创建 Asset 记录
    """
    
    def execute(
        self,
        episode_id: UUID,
        stage_task_id: UUID
    ) -> StageExecutionResult:
        """
        执行预览导出 Stage。
        
        Args:
            episode_id: Episode ID
            stage_task_id: StageTask ID
            
        Returns:
            StageExecutionResult: 执行结果
        """
        # 1. 收集主资产
        shots = self.shot_repo.get_by_episode(episode_id)
        assets = self._collect_primary_assets(shots)
        
        # 2. 下载资产到临时目录
        temp_dir = self._download_assets(assets)
        
        # 3. 使用 FFmpeg 合成
        output_file = self._compose_video(temp_dir, assets)
        
        # 4. 上传并创建 Asset
        upload_result = self.storage_service.upload_file(
            output_file,
            "video/mp4"
        )
        
        asset = self.asset_repo.create_asset(
            episode_id=episode_id,
            stage_task_id=stage_task_id,
            asset_type="preview",
            storage_key=upload_result.storage_key,
            mime_type="video/mp4"
        )
        
        # 5. 清理临时文件
        self._cleanup(temp_dir)
        
        return StageExecutionResult(
            status="succeeded",
            assets_created=1
        )
    
    def _compose_video(
        self,
        temp_dir: str,
        assets: Dict[str, List[AssetModel]]
    ) -> str:
        """
        使用 FFmpeg 合成视频。
        
        FFmpeg 命令示例:
        ffmpeg -loop 1 -t 5 -i shot1.png -i shot1.mp3 -i subtitle.vtt \
               -c:v libx264 -c:a aac -pix_fmt yuv420p \
               -vf "subtitles=subtitle.vtt" output.mp4
        """
        # 构建 FFmpeg 命令
        # 合成视频
        # 返回输出文件路径
        pass
```

## 数据模型

### Asset 扩展字段

```python
class AssetModel:
    # 现有字段
    id: UUID
    project_id: UUID
    episode_id: UUID
    stage_task_id: Optional[UUID]
    shot_id: Optional[UUID]  # 关联到 Shot
    asset_type: str  # keyframe, audio, subtitle, preview, final_video
    storage_key: str
    mime_type: str
    size_bytes: int
    version: int
    is_selected: bool  # 是否为主资产
    created_at: datetime
    
    # 新增字段
    duration_ms: Optional[int]  # 音频/视频时长
    width: Optional[int]  # 图像/视频宽度
    height: Optional[int]  # 图像/视频高度
    checksum_sha256: Optional[str]  # 文件校验和
    quality_score: Optional[float]  # 质量评分（可选）
    metadata_jsonb: dict  # Provider 特定的元数据
```

### StageTask 扩展字段

```python
class StageTaskModel:
    # 现有字段
    id: UUID
    workflow_run_id: UUID
    stage_type: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    error_code: Optional[str]
    error_message: Optional[str]
    
    # 新增字段
    metrics_jsonb: dict  # 性能指标
    # {
    #     "duration_ms": 12000,
    #     "provider_calls": 10,
    #     "success_count": 9,
    #     "failure_count": 1,
    #     "estimated_cost": 0.50,
    #     "token_usage": 0,  # 仅文本 Stage
    #     "retry_count": 2
    # }
```

## 正确性属性

*属性是系统在所有有效执行中应该保持的特征或行为，是人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1: 对象存储上传成功性
*对于任何*成功上传的文件，应该能够通过 storage_key 下载到相同内容的文件
**验证需求**: 需求 1.1, 1.2, 1.3

### 属性 2: Asset 与存储文件一致性
*对于任何*Asset 记录，其 storage_key 应该指向对象存储中存在的文件
**验证需求**: 需求 1.1, 9.1

### 属性 3: 主资产唯一性
*对于任何*Shot，最多只有一个 Asset 的 is_selected 为 true
**验证需求**: 需求 8.2, 8.3

### 属性 4: Image Render 输入完整性
*对于任何*Shot，Image Render Stage 应该能够构建包含所有必需参数的输入
**验证需求**: 需求 2.1, 2.2

### 属性 5: 并行任务失败隔离
*对于任何*批量任务，单个任务失败不应该导致其他任务失败
**验证需求**: 需求 2.5, 5.5, 11.4

### 属性 6: Provider 适配层透明性
*对于任何*Provider 切换，业务代码不应该需要修改
**验证需求**: 需求 3.5, 6.5

### 属性 7: 字幕时间轴连续性
*对于任何*生成的字幕，时间轴应该连续且不重叠
**验证需求**: 需求 4.2

### 属性 8: 预览视频包含所有 Shot
*对于任何*预览视频，应该包含所有 Shot 的主资产
**验证需求**: 需求 7.1, 7.2

### 属性 9: 重试幂等性
*对于任何*失败的 Provider 调用，重试应该产生相同的结果或相同的错误
**验证需求**: 需求 12.1, 12.2

### 属性 10: 成本记录完整性
*对于任何*Provider 调用，应该记录估算成本
**验证需求**: 需求 13.1, 13.2

## 错误处理

### Provider 超时

**场景**: Image Provider 或 TTS Provider 调用超时

**处理**:
1. 使用指数退避策略重试最多 3 次
2. 记录每次重试的耗时和错误
3. 如果全部失败，记录详细错误信息
4. 继续处理其他 Shot

### Provider 限流

**场景**: Provider 返回 429 Too Many Requests

**处理**:
1. 解析 Retry-After 头
2. 等待指定时间后重试
3. 如果没有 Retry-After，使用指数退避
4. 记录限流事件

### 存储上传失败

**场景**: 文件上传到对象存储失败

**处理**:
1. 重试最多 3 次
2. 如果失败，保留本地文件
3. 记录错误信息
4. 不创建 Asset 记录

### FFmpeg 合成失败

**场景**: 预览视频合成失败

**处理**:
1. 检查输入文件是否完整
2. 记录 FFmpeg 错误输出
3. 保留临时文件用于调试
4. 返回失败状态

## 测试策略

### 单元测试

1. **Object Storage Service 测试**
   - 测试上传、下载、删除功能
   - 测试 URL 生成
   - 测试错误处理

2. **Provider Adapter 测试**
   - 测试参数转换
   - 测试响应解析
   - 测试错误处理
   - 使用 Mock Provider

3. **Stage 执行测试**
   - 测试单个 Shot 处理
   - 测试批量处理
   - 测试失败处理
   - 测试重试逻辑

### 集成测试

1. **端到端媒体链路测试**
   - 创建完整的测试数据
   - 执行完整的媒体链路
   - 验证所有资产生成
   - 验证预览视频可播放

2. **Provider 集成测试**
   - 使用真实 Provider（可选）
   - 验证参数正确性
   - 验证响应处理

### 性能测试

1. **并发性能测试**
   - 测试不同并发数的性能
   - 测试 Provider 限流处理
   - 测试资源使用

2. **大规模测试**
   - 测试 100+ Shot 的处理
   - 测试长视频合成
   - 测试存储性能

## 性能考虑

### 并行处理

- Image Render: 默认并发 5 个 Shot
- TTS: 默认并发 5 个 Shot
- 可配置最大并发数

### 资源管理

- 临时文件及时清理
- 限制内存使用
- 使用流式处理大文件

### 成本优化

- 缓存重复的图像生成请求
- 使用低分辨率预览
- 监控和限制 Provider 调用

## 可扩展性

### 支持更多 Provider

通过实现新的 Adapter 即可支持新 Provider：
- Midjourney
- Runway
- ElevenLabs TTS
- 自定义模型

### 支持更多资产类型

扩展 asset_type 枚举：
- background_music
- sound_effects
- cover_image
- thumbnail

### 支持更多导出格式

扩展 Preview Export Stage：
- 不同分辨率
- 不同编码格式
- 不同平台优化

## 安全性

### 文件验证

- 验证文件类型和大小
- 检查文件内容安全性
- 限制上传文件大小

### 访问控制

- 使用签名 URL 限制访问
- 设置 URL 过期时间
- 记录访问日志

### 成本控制

- 限制单个 Episode 的 Provider 调用次数
- 监控异常高成本
- 实现预算告警

## 实现优先级

### 高优先级（本迭代必须完成）

1. Object Storage Service 实现
2. Image Provider Adapter（至少一个）
3. Image Render Stage 实现
4. Subtitle Generation Stage 实现
5. Preview Export Stage 基础实现

### 中优先级（本迭代尽量完成）

1. TTS Provider Adapter（至少一个）
2. TTS Stage 实现
3. Asset Selection 功能
4. 并行处理优化

### 低优先级（可推迟到后续迭代）

1. 多 Provider 支持
2. 高级性能优化
3. 成本监控面板
4. 高级错误恢复

