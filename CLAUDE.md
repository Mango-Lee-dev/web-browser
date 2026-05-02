# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a simple web browser implementation in Python, following the "Web Browser Engineering" book approach. It renders basic HTML pages using Tkinter for the GUI.

## Running the Browser

```bash
python browser.py <url>
```

Example:
```bash
python browser.py https://example.com/
```

## Dependencies

Install dependencies with:
```bash
pip install -r requirements.txt
```

Requires Python 3 with tkinter (usually included with Python).

## Architecture

The browser is implemented in a single file (`browser.py`) with these core components:

- **URL class**: Handles URL parsing and HTTP/HTTPS requests using raw sockets (supports both schemes with SSL)
- **Text/Tag classes**: Token types produced by the HTML lexer
- **lex()**: Tokenizes HTML into Text and Tag tokens (simple state machine, not a full parser)
- **Layout class**: Converts tokens to a display list with positioned text, handling inline formatting (bold, italic, size) and line wrapping
- **Browser class**: Tkinter GUI that renders the display list to a canvas with scroll support

Data flow: URL → request() → HTML body → lex() → tokens → Layout → display_list → Browser.draw()

## Key Constants

- `WIDTH, HEIGHT`: Window dimensions (800x600)
- `HSTEP, VSTEP`: Horizontal/vertical spacing for text layout (13, 18)
- `SCROLL_STEP`: Pixels scrolled per keypress (100)

## Supported HTML Tags

The layout engine handles: `<b>`, `<i>`, `<small>`, `<big>`, `<br>`, `</p>`
