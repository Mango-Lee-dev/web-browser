import socket

class URL:
  def __init__(self, url):
    self.scheme, rest = url.split("://", 1)
    assert self.scheme == "http"

    if "/" not in rest:
      rest = rest + "/"
    host_part, path_part = rest.split("/", 1)
    self.path = "/" + path_part

    if ":" in host_part:
      self.host, port_str = host_part.split(":", 1)
      self.port = int(port_str)
    else:
      self.host = host_part
      self.port = 80

  def request(self):
    s = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    try:
      s.connect((self.host, self.port))
      req = (
          f"GET {self.path} HTTP/1.0\r\n"
          f"Host: {self.host}\r\n"
          f"\r\n"
      )
      s.send(req.encode("utf-8"))
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

  def show(self, body):
    in_tag = False
    for c in body:
      if c == "<":
        in_tag = True
      elif c == ">":
        in_tag = False
      elif not in_tag:
        print(c, end="")

  @staticmethod
  def load(url):
    u = URL(url)
    body = u.request()
    u.show(body)

if __name__ == "__main__":
  import sys
  URL.load(sys.argv[1])
