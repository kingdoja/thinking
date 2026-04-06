# 故障排查指南

## 常见问题

### 1. TypeError: 'ABCMeta' object is not subscriptable

**错误信息**：
```
TypeError: 'ABCMeta' object is not subscriptable
```

**原因**：
Python 3.8 不支持在类型注解中直接使用 `collections.abc.Generator[...]` 泛型语法。

**解决方案**：
已修复。使用 `typing.Generator` 替代 `collections.abc.Generator`。

```python
# ❌ 错误（Python 3.8）
from collections.abc import Generator
def get_db() -> Generator[Session, None, None]:
    ...

# ✅ 正确（Python 3.8+）
from typing import Generator
def get_db() -> Generator[Session, None, None]:
    ...
```

---

### 2. ModuleNotFoundError: No module named 'xxx'

**错误信息**：
```
ModuleNotFoundError: No module named 'pydantic_settings'
ModuleNotFoundError: No module named 'fastapi'
```

**原因**：
虚拟环境中缺少依赖包。

**解决方案**：

1. **确认虚拟环境已激活**：
   ```bash
   # 检查是否在虚拟环境中
   which python  # Linux/Mac
   where python  # Windows
   
   # 应该显示 .venv 路径
   ```

2. **重新安装依赖**：
   ```bash
   # 如果使用清华镜像有问题，切换到官方源
   pip install -r requirements.txt -i https://pypi.org/simple
   
   # 或者使用阿里云镜像
   pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
   ```

3. **验证安装**：
   ```bash
   python check_and_fix.py
   ```

---

### 3. 数据库连接错误

**错误信息**：
```
psycopg.errors.ConnectionTimeout: connection timeout expired
sqlalchemy.exc.OperationalError: could not connect to server
```

**原因**：
PostgreSQL 数据库未启动或连接配置错误。

**解决方案**：

1. **启动 PostgreSQL**：
   ```bash
   cd infra/docker
   docker-compose up -d postgres
   ```

2. **检查数据库状态**：
   ```bash
   docker-compose ps
   ```

3. **检查环境变量**：
   ```bash
   # 检查 .env 文件
   cat apps/api/.env
   
   # 应该包含：
   # DATABASE_URL=postgresql://postgres:postgres@localhost:5432/thinking
   ```

4. **测试连接**：
   ```bash
   docker exec -it <postgres_container_id> psql -U postgres -d thinking
   ```

---

### 4. 端口被占用

**错误信息**：
```
ERROR: [Errno 48] Address already in use
```

**解决方案**：

1. **查找占用端口的进程**：
   ```bash
   # Linux/Mac
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```

2. **使用不同端口**：
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

---

## 完整启动流程

### 1. 环境准备

```bash
# 1. 启动基础设施
cd infra/docker
docker-compose up -d postgres redis minio

# 2. 创建并激活虚拟环境
cd ../../apps/api
python -m venv .venv

# Linux/Mac
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行诊断
python check_and_fix.py
```

### 2. 数据库迁移

```bash
cd ../../infra/migrations
alembic upgrade head
```

### 3. 运行测试

```bash
cd ../../apps/api
pytest tests/ -v
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

访问：http://localhost:8000/docs

---

## Python 版本兼容性

### Python 3.8
- ✅ 支持
- ⚠️  需要使用 `typing.Generator` 而非 `collections.abc.Generator`
- ⚠️  某些类型注解语法受限

### Python 3.9+
- ✅ 完全支持
- ✅ 更好的类型注解支持
- ✅ 推荐使用

---

## 依赖版本要求

| 依赖 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.8 | 3.10+ |
| FastAPI | 0.115.0 | latest |
| SQLAlchemy | 2.0.36 | latest |
| PostgreSQL | 14 | 16 |
| pydantic | 2.8.0 | latest |

---

## 获取帮助

如果遇到其他问题：

1. 查看日志输出
2. 检查 `.env` 配置
3. 运行 `python check_and_fix.py` 诊断
4. 查看 `docs/engineering/` 技术文档

---

**最后更新**：2026-04-06
