import shutil
import textwrap

PADDING = 5


def terminal_width(min_width=40):
    width = shutil.get_terminal_size(fallback=(80, 20)).columns
    return max(width, min_width + (PADDING * 2))


def content_width(min_width=40):
    return max(terminal_width(min_width) - (PADDING * 2), min_width)


def fill_width(min_width=40):
    return content_width(min_width) + PADDING


def wrap_text(text, width=None):
    if width is None:
        width = fill_width()
    indent = " " * PADDING
    lines = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        lines.append(textwrap.fill(paragraph, width=width, initial_indent=indent, subsequent_indent=indent))
    return "\n\n".join(lines)


def print_block(text):
    print(wrap_text(text))
