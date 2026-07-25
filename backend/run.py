"""PyInstaller entry point — system tray mode, no console window."""
import multiprocessing
import socket
import sys
import webbrowser
import threading
import os
import ctypes


def _show_error(title, msg):
    """Display error dialog in windowless (--noconsole) mode."""
    ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)


def _get_icon_path():
    """Resolve tray icon path (compatible with PyInstaller frozen bundle)."""
    if getattr(sys, "frozen", False):
        # _MEIPASS is the extraction directory when packaged by PyInstaller
        return os.path.join(sys._MEIPASS, "app_icon.ico")
    else:
        return os.path.join(os.path.dirname(__file__), "app_icon.ico")


def find_free_port(start=8000, end=8010):
    """Scan [start, end] for the first available TCP port; return None if all occupied."""
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return None


def main():
    # ── 1. Load config ──
    try:
        from app.config import get_app_root, settings
        app_root = get_app_root()
    except Exception as e:
        _show_error("启动失败", f"配置加载失败:\n{e}")
        sys.exit(1)

    # ── 2. Redirect stdout/stderr to log file ──
    # In --noconsole mode sys.stdout/stderr is None, which breaks uvicorn logging.
    _log_dir = os.path.join(app_root, "logs")
    os.makedirs(_log_dir, exist_ok=True)
    _log_fh = open(os.path.join(_log_dir, "server.log"), "a", encoding="utf-8")
    sys.stdout = _log_fh
    sys.stderr = _log_fh

    # ── 3. Find a free port ──
    port = find_free_port(8000, 8010)
    if port is None:
        _show_error("启动失败", "端口 8000 - 8010 全部被占用，无法启动。\n请释放一个端口后重试。")
        sys.exit(1)

    url = f"http://localhost:{port}"

    # ── 4. Start uvicorn in background thread ──
    try:
        import uvicorn
        from app.main import app
    except Exception as e:
        _show_error("启动失败", f"应用加载失败:\n{e}")
        sys.exit(1)

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)

    def _run_server():
        server.run()

    server_thread = threading.Thread(target=_run_server, daemon=True, name="uvicorn")
    server_thread.start()

    # ── 5. Auto-open browser ──
    webbrowser.open(url)

    # ── 6. Create system tray icon ──
    try:
        from PIL import Image
        import pystray
    except Exception as e:
        _show_error("启动失败", f"托盘组件加载失败:\n{e}")
        server.should_exit = True
        sys.exit(1)

    icon_path = _get_icon_path()
    if not os.path.exists(icon_path):
        _show_error("启动失败", f"找不到图标文件:\n{icon_path}")
        server.should_exit = True
        sys.exit(1)

    tray_icon = Image.open(icon_path)

    def _on_open():
        webbrowser.open(url)

    def _on_quit():
        # Stop uvicorn first, then exit tray loop
        server.should_exit = True
        _icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem("打开", _on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", _on_quit),
    )

    _icon = pystray.Icon(
        "personal_business_helper",
        tray_icon,
        "个人商业助手",
        menu,
    )
    _icon.run()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
