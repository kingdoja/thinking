from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "thinking-api"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/thinking"
    redis_url: str = "redis://localhost:6379/0"
    temporal_host: str = "localhost:7233"
    
    # Object Storage (S3/MinIO)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "thinking-media"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    
    # Image Provider Configuration
    image_provider: str = "stable_diffusion"  # Options: stable_diffusion, dalle, mock
    image_provider_api_url: str = "http://localhost:7860"  # SD WebUI default
    image_provider_api_key: str = ""
    image_provider_model: str = "sd_xl_base_1.0"
    image_provider_timeout: int = 120
    image_provider_max_retries: int = 3

    # TTS Provider Configuration
    tts_provider: str = "mock"  # Options: azure, mock
    tts_azure_subscription_key: str = ""
    tts_azure_region: str = "eastus"
    tts_default_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_default_language: str = "zh-CN"
    tts_output_format: str = "audio-16khz-128kbitrate-mono-mp3"
    tts_timeout: int = 30
    tts_max_retries: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
