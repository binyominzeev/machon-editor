"""Inline markup shared by the JSON format: **bold**, *italic*, backslash escapes."""
import html


def parse(s):
    runs, buf, bold, ital, i = [], [], False, False, 0

    def flush():
        if buf:
            runs.append(("".join(buf), bold, ital))
            buf.clear()

    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            buf.append(s[i + 1])
            i += 2
        elif s.startswith("**", i):
            flush()
            bold = not bold
            i += 2
        elif c == "*":
            flush()
            ital = not ital
            i += 1
        else:
            buf.append(c)
            i += 1
    flush()
    return runs


def _esc(t):
    return t.replace("\\", "\\\\").replace("*", "\\*")


def serialize(runs):
    """Runs -> markup. Merges equal-style neighbours, keeps edge spaces outside markers."""
    merged = []
    for t, b, i in runs:
        if not t:
            continue
        if merged and merged[-1][1:] == (b, i):
            merged[-1] = (merged[-1][0] + t, b, i)
        else:
            merged.append((t, b, i))
    out = []
    for t, b, i in merged:
        if not t.strip() or not (b or i):
            out.append(_esc(t))
            continue
        lead, trail = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):]
        m = ("**" if b else "") + ("*" if i else "")
        mr = ("*" if i else "") + ("**" if b else "")
        out.append(lead + m + _esc(t.strip()) + mr + trail)
    return "".join(out)


def to_html(s):
    out = []
    for t, b, i in parse(s):
        e = html.escape(t, quote=False)
        if i:
            e = f"<i>{e}</i>"
        if b:
            e = f"<b>{e}</b>"
        out.append(e)
    return "".join(out)
