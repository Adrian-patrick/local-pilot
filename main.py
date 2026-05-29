"""Local Pilot — OS-native contextual AI workspace.

Entry point for the application. Parses command-line arguments for
file path injection (from Windows Explorer context menu) and launches
the CustomTkinter GUI.
"""

from __future__ import annotations

import logging
import sys


def _parse_file_path() -> str | None:
    """Extract the target file path from sys.argv.

    Mirrors the Rust argument parsing logic: skip argv[0] (the script),
    skip anything starting with '-' (flags), return the first real path.
    """
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            return arg
    return None


import socket
import threading

DAEMON_PORT = 65432

def main():
    """Application entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("local-pilot")

    file_path = _parse_file_path()

    # Attempt to become the daemon
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", DAEMON_PORT))
        sock.listen(5)
    except socket.error:
        # Port is in use — the daemon is already running!
        # Connect as a client, send the file path, and exit instantly.
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("127.0.0.1", DAEMON_PORT))
            payload = file_path if file_path else "__SHOW__"
            client.sendall(payload.encode("utf-8"))
            client.close()
        except Exception as e:
            log.error("Failed to communicate with daemon: %s", e)
        return

    # We are the daemon. Start the UI.
    if file_path:
        log.info("Daemon started with file context: %s", file_path)
    else:
        log.info("Daemon started without file context.")

    import subprocess
    import sys
    import os
    
    tray_process = None
    try:
        # Spawn the tray icon in a separate process using the exact same python executable.
        # Use absolute path to tray.py because the working directory changes when launched from context menu.
        tray_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tray.py")
        tray_process = subprocess.Popen(
            [sys.executable, tray_script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
    except Exception as e:
        log.warning("Failed to launch system tray icon: %s", e)

    from app.gui.app_window import AppWindow
    app = AppWindow(file_path=file_path)

    def listen_for_clients():
        while True:
            try:
                conn, _ = sock.accept()
                data = conn.recv(4096).decode("utf-8")
                conn.close()
                if data:
                    log.info("Daemon received request: %s", data)
                    if data == "__QUIT__":
                        app.after(0, app.destroy)
                        break
                    
                    target_path = None if data == "__SHOW__" else data
                    # Schedule UI update on main thread
                    app.after(0, lambda p=target_path: app.load_new_context(p))
            except Exception as e:
                log.error("Daemon listener error: %s", e)

    t = threading.Thread(target=listen_for_clients, daemon=True)
    t.start()

    app.mainloop()
    
    # Graceful shutdown sequence
    log.info("Shutting down daemon...")
    if tray_process:
        try:
            tray_process.terminate()
            log.info("Tray process terminated.")
        except Exception as e:
            log.warning("Failed to terminate tray process: %s", e)

if __name__ == "__main__":
    main()
