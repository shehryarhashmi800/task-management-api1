"""Plain-text sanitization for user-supplied strings such as task titles."""

import re
from html.parser import HTMLParser

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HIDDEN_UNICODE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
_TAG_START = re.compile(r"<(?=[A-Za-z/!?])")
_SKIPPED_TAGS = {"script", "style"}
_MAX_PASSES = 5


class _TextExtractor(HTMLParser):
    """Collects only the text from HTML, dropping tags, comments and script/style."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        """Start skipping text inside <script> and <style>."""
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        """Stop skipping when a <script> or <style> block ends."""
        if tag in _SKIPPED_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        """Keep ordinary text."""
        if not self._skip_depth:
            self.parts.append(data)

    def handle_entityref(self, name):
        """Keep entities such as &amp; exactly as the user typed them."""
        if not self._skip_depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        """Keep numeric entities such as &#39; exactly as typed."""
        if not self._skip_depth:
            self.parts.append(f"&#{name};")


def _strip_html(text: str) -> str:
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    return "".join(parser.parts)


def sanitize_text(value: str, multiline: bool = True) -> str:
    """Return a safe plain-text version of ``value``.

    Removes HTML tags (and the contents of script/style blocks), control
    characters and invisible text-direction tricks, then trims whitespace.
    With ``multiline=False`` line breaks become single spaces.
    """
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    for _ in range(_MAX_PASSES):
        stripped = _strip_html(text)
        if stripped == text:
            break
        text = stripped
    text = _TAG_START.sub("", text)
    text = _CONTROL_CHARS.sub("", text)
    text = _HIDDEN_UNICODE.sub("", text)
    if not multiline:
        text = " ".join(text.split())
    return text.strip()
