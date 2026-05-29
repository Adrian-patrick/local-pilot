import socket
import sys
import logging
from PIL import Image, ImageDraw
import pystray

logging.basicConfig(filename="tray.log", level=logging.DEBUG)

DAEMON_PORT = 65432

def send_command(cmd: str):
    logging.info(f"Sending command: {cmd}")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", DAEMON_PORT))
        client.sendall(cmd.encode("utf-8"))
        client.close()
    except Exception as e:
        logging.error(f"Failed to send {cmd}: {e}")

def create_image():
    # RGBA is safer for pystray icons
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rectangle((0, 0, 64, 64), fill=(99, 102, 241, 255))
    d.ellipse((16, 16, 48, 48), fill=(255, 255, 255, 255))
    return image

def on_show(icon, item):
    send_command("__SHOW__")

def on_quit(icon, item):
    send_command("__QUIT__")
    icon.stop()
    sys.exit(0)

if __name__ == "__main__":
    try:
        logging.info("Starting tray icon...")
        menu = pystray.Menu(
            pystray.MenuItem("Open Local Pilot", on_show, default=True),
            pystray.MenuItem("Quit", on_quit)
        )
        icon = pystray.Icon("local-pilot", create_image(), "Local Pilot", menu)
        icon.run()
        logging.info("Tray icon run loop finished.")
    except Exception as e:
        logging.error(f"Error starting tray icon: {e}")
