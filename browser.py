import socket
import ssl
import tkinter
import tkinter.font


class BrowserError(Exception):
    """브라우저 기본 예외"""
    pass


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
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
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
    def __init__(self, text):
        self.text = text


class Tag:
    """HTML 태그 노드"""
    def __init__(self, tag):
        self.tag = tag


class HTMLLexer:
    """HTML을 Text/Tag 토큰으로 변환"""
    def tokenize(self, body):
        tokens = []
        buffer = ""
        in_tag = False
        for c in body:
            if c == "<":
                in_tag = True
                if buffer:
                    tokens.append(Text(buffer))
                buffer = ""
            elif c == ">":
                in_tag = False
                tokens.append(Tag(buffer))
                buffer = ""
            else:
                buffer += c
        if not in_tag and buffer:
            tokens.append(Text(buffer))
        return tokens

class BrowserConfig:
    """브라우저 설정 관리"""
    def __init__(self, width=800, height=600, hstep=13, vstep=18, scroll_step=100, line_spacing=1.25):
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
            self._cache[key] = tkinter.font.Font(size=size, weight=weight, slant=style)
        return self._cache[key]

class Layout:
    def __init__(self, tokens, config, font_cache):
        self.tokens = tokens
        self.config = config
        self.font_cache = font_cache
        self.display_list = []

        self.cursor_x = config.hstep
        self.cursor_y = config.vstep
        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        self.line = []
        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
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
        if not self.line: return
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
        self.lexer = HTMLLexer()

        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=self.config.width,
            height=self.config.height
        )
        self.canvas.pack()
        self.scroll = 0

        self.window.bind("<Down>", self.scrolldown)
        self.display_list = []

    def load(self, url):
        body = self.http_client.request(url)
        tokens = self.lexer.tokenize(body)
        self.display_list = Layout(tokens, self.config, self.font_cache).display_list
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + self.config.height: continue
            if y + font.metrics("linespace") < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=word, font=font, anchor="nw")

    def scrolldown(self, e):
        self.scroll += self.config.scroll_step
        self.draw()

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        prog = sys.argv[0] if sys.argv else "browser.py"
        print(f"usage: {prog} <url>", file=sys.stderr)
        sys.exit(1)

    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()