import socket

class URL:
  def __init__(self, url):
    self.scheme, url = url.split("://", 1)
    assert self.scheme == "http"

    if "/" not in url:
      url = url + "/"
    self.host, url = url.split("/", 1)
    self.path = "/" + url

  def request(self):
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    sock.connect((self.host, 80))

    request = f"GET {self.path} HTTP/1.0\r\n".format(self.path)
    request += "Host: {}\r\n".format(self.host)
    request += "\r\n"
    sock.send(request.encode("utf-8"))

    response = sock.makefile("r", encoding="utf-8", newline="\r\n")
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
      sock.close()

      return body

def show(body):
  in_tag = False
  for c in body:
    if c == "<":
      in_tag = True
    elif c == ">":
      in_tag = False
    elif not in_tag:
      print(c, end="")

def load(url):
  body = url.request()
  show(body)

if __name__ == "__main__":
  import sys
  load(URL(sys.argv[1]))