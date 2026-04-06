"""
快速诊断和修复脚本
检查 Python 版本和依赖安装情况
"""
import sys
import subprocess

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    print(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 版本过低，需要 3.8+")
        return False
    elif version.major == 3 and version.minor == 8:
        print("⚠️  Python 3.8 需要使用 typing.Generator 而非 collections.abc.Generator")
    else:
        print("✅ Python 版本符合要求")
    
    return True

def check_dependencies():
    """检查关键依赖"""
    dependencies = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'pydantic_settings',
        'sqlalchemy',
        'psycopg',
        'pytest',
        'hypothesis'
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} - 未安装")
            missing.append(dep)
    
    return missing

def main():
    print("=" * 50)
    print("环境诊断")
    print("=" * 50)
    
    # 检查 Python 版本
    if not check_python_version():
        return
    
    print("\n" + "=" * 50)
    print("依赖检查")
    print("=" * 50)
    
    # 检查依赖
    missing = check_dependencies()
    
    if missing:
        print("\n" + "=" * 50)
        print("修复建议")
        print("=" * 50)
        print("运行以下命令安装缺失的依赖：")
        print("pip install -r requirements.txt")
    else:
        print("\n✅ 所有依赖已安装")

if __name__ == "__main__":
    main()
