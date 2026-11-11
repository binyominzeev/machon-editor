"""Inline markup shared by the JSON format."""
import html


def parse(s):
    runs, buf, bold, ital, remo, source, main_text, i = [], [], False, False, False, False, False, 0

    def flush():
        if buf:
            runs.append(("".join(buf), bold, ital, remo, source, main_text))
            buf.clear()

    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            buf.append(s[i + 1])
            i += 2
        elif s.startswith("<r>", i):
            flush()
            remo = True
            i += 3
        elif s.startswith("</r>", i):
            flush()
            remo = False
            i += 4
        elif s.startswith("<s>", i):
            flush()
            source = True
            i += 3
        elif s.startswith("</s>", i):
            flush()
            source = False
            i += 4
        elif s.startswith("<m>", i):
            flush()
            main_text = True
            i += 3
        elif s.startswith("</m>", i):
            flush()
            main_text = False
            i += 4
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
    return t.replace("\\", "\\\\").replace("*", "\\*").replace("<", "\\<")


def serialize(runs):
    """Runs -> markup; merges equal neighbours and keeps bold/italic edge spaces unmarked."""
    merged = []
    for run in runs:
        t, b, i = run[:3]
        r, s = run[3:5] if len(run) >= 5 else (False, False)
        m = run[5] if len(run) >= 6 else False
        if not t:
            continue
        if m:
            r = s = False
        style = (b, i, r, s, m)
        if merged and merged[-1][1:] == style:
            merged[-1] = (merged[-1][0] + t, *style)
        else:
            merged.append((t, *style))
    out = []
    for t, b, i, r, s, m in merged:
        if not t.strip():
            text = _esc(t)
            if s:
                text = "<s>" + text + "</s>"
            if r:
                text = "<r>" + text + "</r>"
            if m:
                text = "<m>" + text + "</m>"
            out.append(text)
            continue
        if not (b or i or r or s or m):
            out.append(_esc(t))
            continue
        lead, trail = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):]
        text = _esc(t.strip())
        if b:
            text = "**" + text + "**"
        if i:
            text = "*" + text + "*"
        text = lead + text + trail
        if s:
            text = "<s>" + text + "</s>"
        if r:
            text = "<r>" + text + "</r>"
        if m:
            text = "<m>" + text + "</m>"
        out.append(text)
    return "".join(out)


def to_html(s):
    out = []
    for t, b, i, r, source, main_text in parse(s):
        e = html.escape(t, quote=False)
        if i:
            e = f"<i>{e}</i>"
        if b:
            e = f"<b>{e}</b>"
        if source:
            e = f'<span class="source">{e}</span>'
        if r:
            e = f'<span class="remo">{e}</span>'
        if main_text:
            e = f'<span class="main-text">{e}</span>'
        out.append(e)
    return "".join(out)


def mark_remo(lines):
    """Mark the הגה gloss and bracketed text, treating pre-gloss brackets as Remo text."""
    parsed = [parse(line) for line in lines]

    plain = "\n".join("".join(run[0] for run in runs) for runs in parsed)
    start = plain.find("הגה")
    if start < 0:
        start = len(plain)

    result = []
    offset = 0
    brackets = []
    closing_bracket = {"(": ")", "[": "]"}
    for runs in parsed:
        marked = []
        for text, bold, italic, explicit_remo, explicit_source, main_text in runs:
            for char in text:
                after_gloss = offset >= start
                is_remo = explicit_remo or after_gloss or bool(brackets) or char in closing_bracket
                is_source = explicit_source or (after_gloss and (bool(brackets) or char in closing_bracket))
                if main_text:
                    is_remo = is_source = False
                if char in closing_bracket:
                    brackets.append((closing_bracket[char], after_gloss))
                elif brackets and char == brackets[-1][0]:
                    brackets.pop()
                run = (char, bold, italic, is_remo, is_source, main_text)
                if marked and marked[-1][1:] == run[1:]:
                    marked[-1] = (marked[-1][0] + char, *run[1:])
                else:
                    marked.append(run)
                offset += 1
        result.append(serialize(marked))
        offset += 1
    return result
