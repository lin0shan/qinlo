"""
个人商业助手 — 安装包构建脚本

用法: python build_installer.py

流程:
  1. 检查构建环境（Python、Node.js、PyInstaller、NSIS）
  2. 构建前端（npm run build）
  3. 打包后端（PyInstaller --onedir）
  4. 组装 staging 目录
  5. 编译 NSIS 安装包

输出: build/个人商业助手_v1.0_setup.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ── 路径常量 ──────────────────────────────────
PROJECT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_DIR / "backend"
FRONTEND_DIR = PROJECT_DIR / "frontend"
BUILD_DIR = PROJECT_DIR / "build"
STAGE_DIR = BUILD_DIR / "stage"
NSIS_SCRIPT = PROJECT_DIR / "installer.nsi"
BUILD_VENV_DIR = PROJECT_DIR / "build_venv"
BUILD_VENV_PYTHON = BUILD_VENV_DIR / "Scripts" / "python.exe"

VERSION = "1.0.0"
SETUP_NAME = f"个人商业助手_v{VERSION}_setup.exe"

# 运行时检测的工具路径
NPM_EXE = None
NODE_EXE = None


def run_cmd(cmd, cwd=None, description=""):
    """运行命令并实时输出"""
    label = f"  [{description}]" if description else ""
    print(f"\n>>> {label}")
    print(f"    {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"\n  [错误] 命令退出码: {result.returncode}")
        sys.exit(1)
    return result


def find_nsis():
    """查找 NSIS makensis.exe"""
    paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    # 尝试从环境变量查找
    result = shutil.which("makensis")
    if result:
        return result
    print("\n[错误] 未找到 NSIS (makensis.exe)")
    print("  请安装 NSIS: https://nsis.sourceforge.io/Download")
    print("  默认安装路径: C:\\Program Files (x86)\\NSIS")
    sys.exit(1)


def find_pyinstaller():
    """查找 PyInstaller"""
    result = shutil.which("pyinstaller")
    if not result:
        print("\n[错误] 未找到 PyInstaller")
        print("  请执行: pip install pyinstaller")
        sys.exit(1)
    return result


def _find_node_tool(name):
    """查找 Node.js 工具（node.exe / npm.cmd），处理 Windows .cmd 后缀"""
    # 先尝试直接查找 .exe
    exe_path = shutil.which(f"{name}.exe")
    if exe_path:
        return exe_path
    # Windows 上尝试 .cmd
    cmd_path = shutil.which(f"{name}.cmd")
    if cmd_path:
        return cmd_path
    # 直接查找
    direct = shutil.which(name)
    if direct:
        return direct
    return None


def step1_check_env():
    """检查构建环境"""
    print("=" * 60)
    print("  [1/5] 检查构建环境")
    print("=" * 60)

    # Python
    print(f"  Python:   {sys.executable}")
    print(f"  版本:     {sys.version.split()[0]}")

    # Node.js
    global NODE_EXE
    NODE_EXE = _find_node_tool("node")
    if not NODE_EXE:
        print("\n[错误] 未找到 Node.js，请安装 https://nodejs.org")
        sys.exit(1)
    try:
        result = subprocess.run([NODE_EXE, "--version"], capture_output=True, encoding="utf-8", errors="replace")
        print(f"  Node.js:  {result.stdout.strip()}  ({NODE_EXE})")
    except Exception:
        print("\n[错误] Node.js 执行失败")
        sys.exit(1)

    # npm
    global NPM_EXE
    NPM_EXE = _find_node_tool("npm")
    if not NPM_EXE:
        print("\n[错误] 未找到 npm，请安装 Node.js")
        sys.exit(1)
    try:
        result = subprocess.run([NPM_EXE, "--version"], capture_output=True, encoding="utf-8", errors="replace")
        print(f"  npm:      {result.stdout.strip()}  ({NPM_EXE})")
    except Exception:
        print("\n[错误] npm 执行失败")
        sys.exit(1)

    # PyInstaller
    pyinstaller = find_pyinstaller()
    print(f"  PyInstaller: {pyinstaller}")

    # NSIS
    makensis = find_nsis()
    print(f"  NSIS:       {makensis}")

    # 将 node/npm 目录加入 PATH（供后续子进程使用）
    node_dir = str(Path(NODE_EXE).parent)
    if node_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = node_dir + os.pathsep + os.environ.get("PATH", "")

    # 清理旧构建
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  [OK] 构建环境就绪")


def step2_build_frontend():
    """构建前端"""
    print("\n" + "=" * 60)
    print("  [2/5] 构建前端")
    print("=" * 60)

    # 检查 node_modules
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("  安装前端依赖...")
        run_cmd([NPM_EXE, "install"], cwd=str(FRONTEND_DIR), description="npm install")

    run_cmd([NPM_EXE, "run", "build"], cwd=str(FRONTEND_DIR), description="npm build")

    dist_dir = FRONTEND_DIR / "dist"
    if not dist_dir.exists():
        print("\n[错误] 前端构建失败，dist 目录不存在")
        sys.exit(1)
    print(f"  [OK] 前端构建完成")


def step3_build_backend():
    """打包后端（使用干净的 build_venv 避免卷入系统 Python 大库）"""
    print("\n" + "=" * 60)
    print("  [3/5] 打包后端 (PyInstaller)")
    print("=" * 60)

    # 校验 build_venv 是否就绪
    if not BUILD_VENV_PYTHON.exists():
        print(f"\n[错误] 打包专用 venv 不存在: {BUILD_VENV_PYTHON}")
        print("  请先创建: python -m venv build_venv")
        print("  并安装依赖: build_venv\\Scripts\\python -m pip install -r backend\\requirements.txt pyinstaller")
        sys.exit(1)

    pyinstaller_dist = BACKEND_DIR / "dist"
    if pyinstaller_dist.exists():
        shutil.rmtree(pyinstaller_dist)

    # 隐藏导入（动态 import 的模块 PyInstaller 可能检测不到）
    hidden_imports = [
        # 核心模块
        "app.config",
        "app.database",
        "app.logging",
        "app.middleware",
        "app.middleware.auth",
        "app.middleware.logging",
        # 路由模块
        "app.routers.products",
        "app.routers.orders",
        "app.routers.inventory",
        "app.routers.members",
        "app.routers.shipments",
        "app.routers.sync",
        "app.routers.reports",
        "app.routers.backup",
        "app.routers.settings_router",
        "app.routers.import_router",
        # 数据模型
        "app.models",
        "app.models.product",
        "app.models.supplier",
        "app.models.order",
        "app.models.shipment",
        "app.models.inventory",
        "app.models.member",
        "app.models.backup",
        # 数据校验
        "app.schemas",
        "app.schemas.product",
        "app.schemas.member",
        "app.schemas.order",
        "app.schemas.inventory",
        "app.schemas.shipment",
        # 服务层
        "app.services",
        "app.services.product_service",
        "app.services.member_service",
        "app.services.order_service",
        "app.services.shipment_service",
        "app.services.import_service",
        # 工具模块
        "app.utils",
        "app.utils.image",
        "app.utils.barcode_util",
        # 第三方库
        "apscheduler",
        "apscheduler.schedulers.background",
        "apscheduler.triggers.interval",
        "structlog",
        "PIL",
        "barcode",
        "openpyxl",
    ]

    # 明确排除不需要的大库（防止 venv 中意外被安装等边缘情况）
    exclude_modules = [
        "torch", "torchvision", "cv2", "faiss", "faiss_cpu",
        "ctranslate2", "av", "numpy.random._examples",
        "matplotlib", "scipy", "pandas.tests", "pywin.debugger",
        "tcl", "tk", "tkinter",
    ]

    cmd = [
        str(BUILD_VENV_PYTHON), "-m", "PyInstaller",
        "--onedir",
        "--name=个人商业助手",
        "--noconsole",
        "--icon=app_icon.ico",
        "--clean",
        "--noconfirm",
        # 排除不需要的大库
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "cv2",
        "--exclude-module", "faiss",
        "--exclude-module", "faiss_cpu",
        "--exclude-module", "ctranslate2",
        "--exclude-module", "av",
        "--exclude-module", "matplotlib",
        "--exclude-module", "scipy",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # pystray 隐藏导入
    for imp in ["pystray", "pystray._win32", "pystray._util"]:
        cmd.extend(["--hidden-import", imp])

    # 添加数据文件
    cmd.extend(["--add-data", "app_icon.ico;."])  # 托盘图标
    cmd.extend(["--add-data", "alembic;alembic"])
    cmd.extend(["--add-data", "alembic.ini;."])

    cmd.append("run.py")

    print(f"  Python:  {BUILD_VENV_PYTHON}")
    run_cmd(cmd, cwd=str(BACKEND_DIR), description="PyInstaller")

    # 验证输出
    exe = pyinstaller_dist / "个人商业助手" / "个人商业助手.exe"
    if not exe.exists():
        print(f"\n[错误] PyInstaller 输出不存在: {exe}")
        sys.exit(1)

    print(f"  [OK] 后端打包完成 -> {exe}")


def step4_stage():
    """组装 staging 目录"""
    print("\n" + "=" * 60)
    print("  [4/5] 组装安装包文件")
    print("=" * 60)

    # 复制后端
    pyinstaller_app = BACKEND_DIR / "dist" / "个人商业助手"
    stage_app = STAGE_DIR / "app"
    if stage_app.exists():
        shutil.rmtree(stage_app)
    shutil.copytree(pyinstaller_app, stage_app)
    print(f"  [OK] 后端 -> build/stage/app/")

    # 复制前端
    stage_frontend = STAGE_DIR / "frontend" / "dist"
    stage_frontend.mkdir(parents=True, exist_ok=True)
    frontend_dist = FRONTEND_DIR / "dist"
    shutil.copytree(frontend_dist, stage_frontend, dirs_exist_ok=True)
    print(f"  [OK] 前端 -> build/stage/frontend/dist/")

    # 创建运行时空目录
    (STAGE_DIR / "data").mkdir(exist_ok=True)
    (STAGE_DIR / "data" / "backups").mkdir(exist_ok=True)
    (STAGE_DIR / "uploads").mkdir(exist_ok=True)
    (STAGE_DIR / "logs").mkdir(exist_ok=True)
    print(f"  [OK] 运行时目录已创建 (data/, uploads/, logs/)")


def step5_build_installer():
    """编译 NSIS 安装包（注意：不通过管道捕获输出，避免大量 File 日志阻塞缓冲区）"""
    print("\n" + "=" * 60)
    print("  [5/5] 编译安装包 (NSIS)")
    print("=" * 60)

    makensis = find_nsis()
    print(f"  NSIS: {makensis}")
    print(f"  正在编译...（大量文件处理时可能耗时数分钟，请耐心等待）")

    # NSIS 处理数千文件时输出海量日志，管道会阻塞，直接放行到父进程控制台
    result = subprocess.run(
        [makensis, str(NSIS_SCRIPT)],
        cwd=str(PROJECT_DIR),
        stdout=None,
        stderr=None,
    )
    if result.returncode != 0:
        print(f"\n[错误] NSIS 编译失败，退出码: {result.returncode}")
        sys.exit(1)

    output = BUILD_DIR / SETUP_NAME
    if not output.exists():
        print(f"\n[错误] 安装包未生成: {output}")
        sys.exit(1)

    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"  构建完成！")
    print(f"  安装包: {output}")
    print(f"  大小:   {size_mb:.1f} MB")
    print(f"{'=' * 60}")


def main():
    print("=" * 60)
    print(f"  个人商业助手 v{VERSION} — 安装包构建")
    print("=" * 60)

    os.chdir(str(PROJECT_DIR))

    step1_check_env()
    step2_build_frontend()
    step3_build_backend()
    step4_stage()
    step5_build_installer()


if __name__ == "__main__":
    main()
