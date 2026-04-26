import socket
import ssl
import tkinter as tk

class URL:
  def __init__(self, url):
    self.scheme, url = url.split("://", 1)
    assert self.scheme in ("http", "https")

    if "/" not in url:
      url = url + "/"
    self.host, url = url.split("/", 1)
    self.path = "/" + url

    if self.scheme == "http":
      self.port = 80
    elif self.scheme == "https":
      self.port = 443

    if ":" in self.host:
      self.host, port = self.host.split(":", 1)
      self.port = int(port)

  def request(self):
    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    try:
      s.connect((self.host, self.port))

      if self.scheme == "https":
        try:
          import certifi
          ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
          ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=self.host)
      
      request = "GET {} HTTP/1.0\r\n".format(self.path)
      request += "Host: {}\r\n".format(self.host)
      request += "\r\n"
      s.send(request.encode("utf-8"))

      response = s.makefile("r", encoding="utf-8", newline="\r\n")
      statusline = response.readline()
      version, status, explanation = statusline.split(" ", 2)
      response_headers = {}
      while True:
        line = response.readline()
        if line == "\r\n": break
        header, value = line.split(":", 1)
        response_headers[header.casefold()] = value.strip()

      assert "transfer-encoding" not in response_headers
      assert "content-encoding" not in response_headers
      body = response.read()
      return body
    finally:
      s.close()

  def lex(self, body):
    text = ""
    in_tag = False
    for c in body:
      if c == "<":
        in_tag = True
      elif c == ">":
        in_tag = False
      elif not in_tag:
        text += c
    return text


WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

SCROLL_STEP = 100

def layout(text):
  display_list = []
  cursor_x, cursor_y = HSTEP, VSTEP
  for c in text:
    display_list.append((cursor_x, cursor_y, c))
    cursor_x += HSTEP
    if cursor_x > WIDTH - HSTEP:
      cursor_y += VSTEP
      cursor_x = HSTEP
  return display_list

class Browser:
  def __init__(self):
    self.window = tk.Tk()
    self.canvas = tk.Canvas(
      self.window,
      width=WIDTH,
      height=HEIGHT,
    )
    self.canvas.pack()
    self.scroll = 0

    self.window.bind("<Down>", self.scrolldown)

  def draw(self):
    self.canvas.delete("all")
    for x, y, c in self.display_list:
      if y > self.scroll + HEIGHT: continue
      if y + VSTEP < self.scroll: continue
      self.canvas.create_text(x, y - self.scroll, text=c)

  def load(self, url):
    u = URL(url)
    body = u.request()
    text = u.lex(body)
    self.display_list = layout(text)
    self.draw()

  def scrolldown(self, e):
    self.scroll += SCROLL_STEP
    self.draw()

if __name__ == "__main__":
  import sys
  Browser().load(sys.argv[1])
  tk.mainloop()
