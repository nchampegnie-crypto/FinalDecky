import re
from typing import List, Tuple
from utils import normalize_dashes, collapse_spaces

BULLET_RE = re.compile(r"^\s*[\-\*•]\s+")
NUMBERED_RE = re.compile(r"^\s*\d+[\.)]\s+")
DICT_RE = re.compile(r"^\s*([^()\n]+?)\s*\(([^)]+)\)\s+(.+)$")

EN_EM = ["–", "—"]

def first_colon_outside_parens(s: str) -> int:
    depth = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth-1)
        elif ch == ":" and depth == 0:
            return i
    return -1

def first_sep_index(s: str) -> int:
    # Priority order: TAB, colon(outside parens), en/em dash, plain hyphen
    if "\t" in s:
        return s.index("\t")
    ci = first_colon_outside_parens(s)
    cand = [ci] if ci != -1 else []
    for d in EN_EM:
        j = s.find(d)
        if j != -1:
            cand.append(j)
            break
    jh = s.find("-")
    if jh != -1:
        cand.append(jh)
    cand = [c for c in cand if c is not None and c >= 0]
    return min(cand) if cand else -1

def split_term_def_line(line: str) -> Tuple[str, str]:
    # dictionary pattern
    m = DICT_RE.match(line)
    if m:
        return f"{m.group(1).strip()} ({m.group(2).strip()})", m.group(3).strip()

    i = first_sep_index(line)
    if i != -1:
        return line[:i].strip().lstrip("-–—").strip(), line[i+1:].strip()

    # fallback: whole line as term only
    return line.strip(), ""

def looks_like_item_start(original_line: str) -> bool:
    raw = original_line.strip()
    if not raw:
        return False

    # bullets or numbers always start a new item
    m = BULLET_RE.match(raw) or NUMBERED_RE.match(raw)
    if m:
        return True

    # Evaluate split position on content (without leading bullet/number if any)
    content = raw[m.end():] if m else raw
    i = first_sep_index(content)
    if i == -1:
        return False

    # Heuristic: the separator should appear early (term zone)
    # - within first 40 chars or within first third of the line
    return i <= max(40, len(content) // 3)

def parse_free_text(text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Parse text into (Front, Back) records.
    New item when: numbered/bulleted OR a separator appears early in the line.
    Split at the first separator (TAB / ':' outside parens / en/em dash / '-').
    Definition continues by appending subsequent lines until the next item-start.
    """
    text = normalize_dashes(text)
    lines = [l.rstrip() for l in text.splitlines()]

    records: List[Tuple[str, str]] = []
    warnings: List[str] = []

    cur_term = None
    cur_def_parts: List[str] = []

    def flush():
        nonlocal cur_term, cur_def_parts
        if cur_term is not None:
            term = collapse_spaces(cur_term.strip().lstrip("-–—").strip())
            definition = collapse_spaces(" ".join([p for p in cur_def_parts if p is not None and p.strip()])).strip()
            records.append((term, definition))
        cur_term, cur_def_parts = None, []

    for raw in lines:
        line = raw.strip()
        if not line:
            if cur_term is not None:
                cur_def_parts.append("")  # keep paragraph break
            continue

        # Remove leading bullet/number for splitting
        lm = BULLET_RE.match(line) or NUMBERED_RE.match(line)
        content = line[lm.end():] if lm else line

        if looks_like_item_start(line):
            if cur_term is not None:
                flush()
            t, d = split_term_def_line(content)
            cur_term = t
            cur_def_parts = [d] if d else []
        else:
            if cur_term is None:
                cur_term = content
                cur_def_parts = []
            else:
                cur_def_parts.append(content)

    flush()

    for i, (f, b) in enumerate(records, 1):
        if not f or not b:
            warnings.append(f"Row {i} has an empty {'Front' if not f else 'Back'} field.")

    return records, warnings
