import tkinter as tk

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

class BrowserCanvas:
  def __init__(self):
    self.window = tk.Tk()
    self.canvas = tk.Canvas(self.window, width=WIDTH, height=HEIGHT)
    self.canvas.pack()
    self.cursor_x, self.cursor_y = HSTEP, VSTEP

  def load(self, url):
    from browser import lex
    body = url.request()
    text = lex(body)
    for c in text:
      self.canvas.create_text(self.cursor_x, self.cursor_y, text=c, anchor="nw")
      self.cursor_x += HSTEP
      if self.cursor_x >= WIDTH - HSTEP:
        self.cursor_x = HSTEP
        self.cursor_y += VSTEP

  def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
      display_list.append((cursor_x, cursor_y, c))
      cursor_x += HSTEP
      if cursor_x >= WIDTH - HSTEP:
        cursor_x = HSTEP
        cursor_y += VSTEP
    return display_list

if __name__ == "__main__":
  import sys
  from browser import URL
  if len(sys.argv) < 2:
    print("Usage: python3 browser_canvas.py <url>")
    sys.exit(1)
  browser = BrowserCanvas()
  browser.load(URL(sys.argv[1]))
  tk.mainloop() 