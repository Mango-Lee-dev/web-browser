import tkinter as tk
from browser import URL

WIDTH, HEIGHT = 800, 600
window = tk.Tk()
# canvas = tk.Canvas(window, width=WIDTH, height=HEIGHT)
# canvas.pack()

class BrowserCanvas:
  def __init__(self):
    self.window = tk.Tk()
    self.canvas = tk.Canvas(self.window, width=WIDTH, height=HEIGHT)
    self.canvas.pack()

  def load(self, url):
    body = url.request()
    in_tag = False
    for c in body:
      if c == "<":
        in_tag = True
      elif c == ">":
        in_tag = False
      elif not in_tag:
        self.canvas.create_text(0, 0, text=c, anchor="nw")

    self.canvas.create_rectangle(10, 20, 400, 300)
    self.canvas.create_oval(100, 100, 150, 150)
    self.canvas.create_text(200, 150, text="Hi")


if __name__ == "__main__":
  import sys
  if len(sys.argv) < 2:
    print("Usage: python3 browser_canvas.py <url>")
    sys.exit(1)
  browser = BrowserCanvas()
  browser.load(URL(sys.argv[1]))
  tk.mainloop()