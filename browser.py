import socket
import ssl
import tkinter
import tkinter.font


class BrowserError(Exception):
  """브라우저 기본 예외"""
  def __init__(self, message):
    super().__init__(message)
    self.message = message


class UnsupportedSchemeError(BrowserError):
  """지원하지 않는 URL 스킴"""
  def __init__(self, scheme):
    super().__init__(f"Unsupported scheme: {scheme}")
    self.scheme = scheme


class UnsupportedEncodingError(BrowserError):
  """지원하지 않는 인코딩"""
  def __init__(self, encoding):
    super().__init__(f"Unsupported encoding: {encoding}")
    self.encoding = encoding


class URL:
  """URL 파싱만 담당"""
  def __init__(self, url):
    self.scheme, url = url.split("://", 1)
    if self.scheme not in ["http", "https"]:
      raise UnsupportedSchemeError(self.scheme)

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


class HttpClient:
  """HTTP/HTTPS 요청 담당"""
  def request(self, url):
    s = socket.socket(family=socket.AF_INET,
                      type=socket.SOCK_STREAM,
                      proto=socket.IPPROTO_TCP)
    try:
      s.connect((url.host, url.port))

      if url.scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=url.host)

      request = "GET {} HTTP/1.0\r\n".format(url.path)
      request += "Host: {}\r\n".format(url.host)
      request += "\r\n"
      s.send(request.encode("utf8"))

      response = s.makefile("r", encoding="utf8", newline="\r\n")

      statusline = response.readline()
      version, status, explanation = statusline.split(" ", 2)

      response_headers = {}
      while True:
        line = response.readline()
        if line == "\r\n":
          break
        header, value = line.split(":", 1)
        response_headers[header.casefold()] = value.strip()

      if "transfer-encoding" in response_headers:
        raise UnsupportedEncodingError("transfer-encoding")
      if "content-encoding" in response_headers:
        raise UnsupportedEncodingError("content-encoding")

      body = response.read()
      return body
    finally:
      s.close()


class Text:
  """HTML 텍스트 노드"""
  def __init__(self, text, parent=None):
    self.text = text
    self.children = []
    self.parent = parent

  def __repr__(self):
    return repr(self.text)


class Element:
  """HTML 엘리먼트 노드"""
  def __init__(self, tag, attributes, parent):
    self.tag = tag
    self.attributes = attributes
    self.children = []
    self.parent = parent

  def __repr__(self):
    return "<" + self.tag + ">"


class BrowserConfig:
  """브라우저 설정 관리"""
  def __init__(
      self,
      width=800,
      height=600,
      hstep=13,
      vstep=18,
      scroll_step=100,
      line_spacing=1.25,
  ):
    self.width = width
    self.height = height
    self.hstep = hstep
    self.vstep = vstep
    self.scroll_step = scroll_step
    self.line_spacing = line_spacing


class FontCache:
  """
    폰트 캐시 관리

    동일한 (size, weight, style) 조합의 폰트를 재사용하여
    메모리 사용량을 줄이고 성능을 향상시킴
    """
  def __init__(self):
    self._cache = {}

  def get(self, size, weight, style):
    key = (size, weight, style)
    if key not in self._cache:
      self._cache[key] = tkinter.font.Font(size=size,
                                           weight=weight,
                                           slant=style)
    return self._cache[key]


# Layout class: Converts tokens to a display list with positioned text, handling inline formatting (bold, italic, size) and line wrapping
# - tree: DOM tree
# - config: Browser configuration
# - font_cache: Font cache
# - display_list: Display list
# - cursor_x: Cursor x position
# - cursor_y: Cursor y position
# - weight: Font weight
# - style: Font style
# - size: Font size
class Layout:
  def __init__(self, tree, config, font_cache):
    self.config = config
    self.font_cache = font_cache
    self.display_list = []

    self.cursor_x = config.hstep
    self.cursor_y = config.vstep
    self.weight = "normal"
    self.style = "roman"
    self.size = 12

    self.line = []
    self.recurse(tree)
    self.flush()

  def recurse(self, tree):
    if isinstance(tree, Text):
      for word in tree.text.split():
        self.word(word)
    else:
      self.open_tag(tree.tag)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree.tag)

  def open_tag(self, tag):
    if tag == "i":
      self.style = "italic"
    elif tag == "b":
      self.weight = "bold"
    elif tag == "small":
      self.size -= 2
    elif tag == "big":
      self.size += 4
    elif tag == "br":
      self.flush()

  def close_tag(self, tag):
    if tag == "i":
      self.style = "roman"
    elif tag == "b":
      self.weight = "normal"
    elif tag == "small":
      self.size += 2
    elif tag == "big":
      self.size -= 4
    elif tag == "p":
      self.flush()
      self.cursor_y += self.config.vstep

  def word(self, word):
    font = self.font_cache.get(self.size, self.weight, self.style)
    w = font.measure(word)
    if self.cursor_x + w > self.config.width - self.config.hstep:
      self.flush()
    self.line.append((self.cursor_x, word, font))
    self.cursor_x += w + font.measure(" ")

  def flush(self):
    if not self.line:
      return
    metrics = [font.metrics() for x, word, font in self.line]
    max_ascent = max([metric["ascent"] for metric in metrics])
    baseline = self.cursor_y + self.config.line_spacing * max_ascent
    for x, word, font in self.line:
      y = baseline - font.metrics("ascent")
      self.display_list.append((x, y, word, font))
    max_descent = max([metric["descent"] for metric in metrics])
    self.cursor_y = baseline + self.config.line_spacing * max_descent
    self.cursor_x = self.config.hstep
    self.line = []


class Browser:
  def __init__(self, config=None):
    self.config = config or BrowserConfig()
    self.font_cache = FontCache()
    self.http_client = HttpClient()

    self.window = tkinter.Tk()
    self.canvas = tkinter.Canvas(self.window,
                                 width=self.config.width,
                                 height=self.config.height)
    self.canvas.pack()
    self.scroll = 0

    self.window.bind("<Down>", self.scrolldown)
    self.display_list = []

  def load(self, url):
    body = self.http_client.request(url)
    self.nodes = HTMLParser(body).parse()
    self.display_list = Layout(self.nodes, self.config,
                               self.font_cache).display_list
    self.draw()

  def draw(self):
    self.canvas.delete("all")
    for x, y, word, font in self.display_list:
      if y > self.scroll + self.config.height:
        continue
      if y + font.metrics("linespace") < self.scroll:
        continue
      self.canvas.create_text(x,
                              y - self.scroll,
                              text=word,
                              font=font,
                              anchor="nw")

  def scrolldown(self, e):
    self.scroll += self.config.scroll_step
    self.draw()


SELF_CLOSING_TAGS = [
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
]

HEAD_TAGS = [
    "base",
    "basefont",
    "bgsound",
    "noscript",
    "link",
    "meta",
    "title",
    "style",
    "script",
]

# 전역 폰트 캐시 (BlockLayout용)
FONTS = {}


def get_font(size, weight, style):
  """폰트를 캐시에서 가져오거나 새로 생성"""
  key = (size, weight, style)
  if key not in FONTS:
    font = tkinter.font.Font(size=size, weight=weight, slant=style)
    label = tkinter.Label(font=font)  # 폰트가 GC되지 않도록 참조 유지
    FONTS[key] = (font, label)
  return FONTS[key][0]


class BlockLayout:
  """
  블록 레이아웃: 인라인 텍스트 배치를 담당

  DOM 노드를 받아서 화면에 그릴 display_list를 생성합니다.
  폰트 스타일(bold, italic, size)과 줄바꿈을 처리합니다.
  """

  HSTEP = 13  # 수평 여백
  VSTEP = 18  # 수직 여백
  WIDTH = 800  # 화면 너비

  def __init__(self, node, parent, previous):
    self.node = node  # 이 레이아웃이 담당하는 DOM 노드
    self.parent = parent  # 부모 레이아웃 (DocumentLayout)
    self.previous = previous  # 이전 형제 레이아웃 (없으면 None)
    self.children = []  # 자식 레이아웃들

  def layout(self):
    """레이아웃 계산 실행"""
    self.display_list = []  # (x, y, word, font) 튜플 리스트

    # 커서 위치 초기화
    self.cursor_x = self.HSTEP
    self.cursor_y = self.VSTEP

    # 폰트 스타일 초기화
    self.weight = "normal"  # normal 또는 bold
    self.style = "roman"  # roman 또는 italic
    self.size = 12  # 기본 폰트 크기

    self.line = []  # 현재 줄에 쌓인 단어들
    self.recurse(self.node)
    self.flush()  # 마지막 줄 처리

  def recurse(self, tree):
    """DOM 트리를 재귀적으로 순회하며 레이아웃 처리"""
    if isinstance(tree, Text):
      # 텍스트 노드: 공백으로 분리하여 각 단어 처리
      for word in tree.text.split():
        self.word(word)
    else:
      # 엘리먼트 노드: 태그 열기 → 자식 처리 → 태그 닫기
      self.open_tag(tree.tag)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree.tag)

  def open_tag(self, tag):
    """여는 태그 처리 - 스타일 변경"""
    if tag == "i":
      self.style = "italic"
    elif tag == "b":
      self.weight = "bold"
    elif tag == "small":
      self.size -= 2
    elif tag == "big":
      self.size += 4
    elif tag == "br":
      self.flush()  # 줄바꿈

  def close_tag(self, tag):
    """닫는 태그 처리 - 스타일 복원"""
    if tag == "i":
      self.style = "roman"
    elif tag == "b":
      self.weight = "normal"
    elif tag == "small":
      self.size += 2
    elif tag == "big":
      self.size -= 4
    elif tag == "p":
      self.flush()
      self.cursor_y += self.VSTEP  # 문단 간격 추가

  def word(self, word):
    """단어를 현재 줄에 배치"""
    font = get_font(self.size, self.weight, self.style)
    w = font.measure(word)

    # 줄 끝을 넘으면 줄바꿈
    if self.cursor_x + w > self.WIDTH - self.HSTEP:
      self.flush()

    self.line.append((self.cursor_x, word, font))
    self.cursor_x += w + font.measure(" ")  # 단어 + 공백 너비

  def flush(self):
    """현재 줄을 display_list에 추가하고 다음 줄로 이동"""
    if not self.line:
      return

    # 줄에서 가장 큰 ascent 찾기
    metrics = [font.metrics() for x, word, font in self.line]
    max_ascent = max([metric["ascent"] for metric in metrics])

    # baseline 계산 (1.25는 줄 간격 계수)
    baseline = self.cursor_y + 1.25 * max_ascent

    # 각 단어의 y 위치 계산하여 display_list에 추가
    for x, word, font in self.line:
      y = baseline - font.metrics("ascent")
      self.display_list.append((x, y, word, font))

    # 다음 줄로 이동
    max_descent = max([metric["descent"] for metric in metrics])
    self.cursor_y = baseline + 1.25 * max_descent
    self.cursor_x = self.HSTEP
    self.line = []


class DocumentLayout:
  def __init__(self, node) -> None:
    self.node = node
    self.parent = None
    self.children = []

  def layout(self) -> None:
    child = BlockLayout(self.node, self, None)
    self.children.append(child)
    child.layout()


class HTMLParser:
  """HTML을 파싱하여 DOM 트리 생성"""
  def __init__(self, body):
    self.body = body
    self.unfinished = []

  def get_attributes(self, text):
    """태그 텍스트에서 태그 이름과 속성을 파싱"""
    parts = text.split()
    tag = parts[0].casefold()
    attributes = {}
    for attrpair in parts[1:]:
      if "=" in attrpair:
        key, value = attrpair.split("=", 1)
        # 따옴표 제거
        if len(value) > 2 and value[0] in ["'", '"']:
          value = value[1:-1]
        attributes[key.casefold()] = value
      else:
        attributes[attrpair.casefold()] = ""
    return tag, attributes

  def add_text(self, text):
    """텍스트 노드를 현재 부모에 추가"""
    if text.isspace():
      return
    self.implicit_tags(None)
    parent = self.unfinished[-1]
    node = Text(text, parent)
    parent.children.append(node)

  def add_tag(self, tag):
    """태그를 처리하여 트리에 추가"""
    tag, attributes = self.get_attributes(tag)
    if tag.startswith("!"):
      return  # DOCTYPE, 주석 등 무시
    self.implicit_tags(tag)

    if tag.startswith("/"):
      # 닫는 태그
      if len(self.unfinished) == 1:
        return
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    elif tag in SELF_CLOSING_TAGS:
      # self-closing 태그
      parent = self.unfinished[-1]
      node = Element(tag, attributes, parent)
      parent.children.append(node)
    else:
      # 여는 태그
      parent = self.unfinished[-1] if self.unfinished else None
      node = Element(tag, attributes, parent)
      self.unfinished.append(node)

  def implicit_tags(self, tag):
    """암묵적 태그 자동 삽입 (html, head, body)"""
    while True:
      open_tags = [node.tag for node in self.unfinished]
      if open_tags == [] and tag != "html":
        self.add_tag("html")
      elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
        if tag in HEAD_TAGS:
          self.add_tag("head")
        else:
          self.add_tag("body")
      elif open_tags == ["html", "head"] and tag not in ["/head"] + HEAD_TAGS:
        self.add_tag("/head")
      else:
        break

  def finish(self):
    """모든 열린 태그를 닫고 루트 노드 반환"""
    if not self.unfinished:
      self.implicit_tags(None)
    while len(self.unfinished) > 1:
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    return self.unfinished.pop()

  def parse(self):
    """HTML 문자열을 파싱하여 DOM 트리 반환"""
    text = ""
    in_tag = False
    for c in self.body:
      if c == "<":
        in_tag = True
        if text:
          self.add_text(text)
        text = ""
      elif c == ">":
        in_tag = False
        self.add_tag(text)
        text = ""
      else:
        text += c
    if not in_tag and text:
      self.add_text(text)
    return self.finish()

  @staticmethod
  def print_tree(node, indent=0):
    """DOM 트리를 들여쓰기하여 출력"""
    print(" " * indent, node)
    for child in node.children:
      HTMLParser.print_tree(child, indent + 2)


if __name__ == "__main__":
  import sys

  if len(sys.argv) < 2:
    prog = sys.argv[0] if sys.argv else "browser.py"
    print(f"usage: {prog} <url>", file=sys.stderr)
    sys.exit(1)

  Browser().load(URL(sys.argv[1]))
  tkinter.mainloop()
