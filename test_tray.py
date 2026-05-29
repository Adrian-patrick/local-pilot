import pystray
import threading
import tkinter as tk
from PIL import Image, ImageDraw

def create_image():
    image = Image.new('RGB', (64, 64), color=(99, 102, 241))
    d = ImageDraw.Draw(image)
    d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))
    return image

def setup_tray(root):
    image = create_image()
    def on_show(icon, item):
        pass
    def on_quit(icon, item):
        icon.stop()
        root.quit()
    menu = pystray.Menu(
        pystray.MenuItem("Open", on_show, default=True),
        pystray.MenuItem("Quit", on_quit)
    )
    icon = pystray.Icon("test", image, "Test", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    print("Tray started in thread")

root = tk.Tk()
root.title("Test")
root.geometry("200x200")
setup_tray(root)
root.mainloop()
