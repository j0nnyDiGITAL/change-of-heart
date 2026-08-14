"""
Persona 5 Royal Save Editor — Master Standalone Desktop Application
Uses pywebview to render the Phantom Thieves UI directly inside a native desktop window.
Runs the lightweight internal HTTP daemon in a background thread with zero exposed browser tabs.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Frozen vs source root
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))


def start_background_server():
    from http.server import HTTPServer
    web_app_dir = PROJECT_ROOT / "web-app"
    if str(web_app_dir) not in sys.path:
        sys.path.insert(0, str(web_app_dir))
    import server as web_server

    server_address = ("127.0.0.1", web_server.PORT)
    try:
        httpd = HTTPServer(server_address, web_server.P5RWebHandler)
        httpd.serve_forever()
    except OSError:
        pass  # Server already running on port


def launch_native_window():
    import webview
    
    # Start the server daemon in the background
    server_thread = threading.Thread(target=start_background_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    icon_path = str(PROJECT_ROOT / "web-app" / "static" / "assets" / "joker_avatar.jpg")
    if not os.path.exists(icon_path):
        icon_path = None

    # Create standalone native desktop window
    window = webview.create_window(
        title="CHANGE OF HEART — Persona 5 Royal Save Studio (by j0nny DiGITAL)",
        url="http://127.0.0.1:5055/",
        width=1380,
        height=880,
        min_size=(1050, 700),
        background_color="#060608",
        text_select=False,
    )

    webview.start(debug=False)


def launch_tkinter_gui():
    import gui
    gui.main()


def main():
    if "--gui" in sys.argv or "--desktop" in sys.argv:
        launch_tkinter_gui()
    else:
        try:
            launch_native_window()
        except Exception as e:
            print(f"[P5R] pywebview failed: {e}. Falling back to browser launcher...")
            import webbrowser
            start_background_server()
            webbrowser.open("http://127.0.0.1:5055/")


if __name__ == "__main__":
    main()
