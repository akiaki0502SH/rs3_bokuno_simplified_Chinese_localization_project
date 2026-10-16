"""Offline Chinese line-break proposals. No ROM, source or filesystem writes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

TOKEN = re.compile(r'\{[^{}]+\}')
NL = '{NEWLINE}'
CLOSE = set('，。、；：！？）》】」』〉〕］｝,.!?;:%％')
OPEN = set('（《【「『〈〔［｛')
COMMON = ('然后 成为 取代 我们 你们 他们 因为 所以 但是 如果 已经 现在 不能 不要 可以 '
          '能够 还有 什么 怎么 一起 自己 这里 那里 没有 敌人 我方 全体 单体 攻击 防御 '
          '恢复 解除 状态 异常 熟练 提高 降低 伤害 概率 使用 需要 消耗 获得 习得 '
          '冲击波 圣王遗物 冒险者 深渊之门 光之钻石 勇敢 祭品 这是 那是 正是 就是 原来是').split()
PAUSES = set('，。、；：！？.!?;:…')
COPULAS = {'是', '正是', '就是', '这是', '那是', '原来是'}
MODIFIERS = set(('勇敢 最小 最大 华丽 强力 精美 漂亮 美丽 珍贵 巨大 古老 强大 神圣 '
                 '重要 邪恶 神秘 稀有 特殊 普通 锋利 坚固 沉重 轻盈 年轻 年迈 可疑').split())


@dataclass(frozen=True)
class Atom:
    source: str
    display: str
    cells: int
    modifier_phrase: bool = False


def visible_without_layout(text):
    return text.replace(NL, '')


def control_sequence(text):
    return [x for x in TOKEN.findall(text) if x != NL]


def atomize(text, terms, dynamic, limit=None):
    """Names/terms are indivisible. Unknown dynamic expansions stop reflow."""
    clean = text.replace(NL, '')
    atoms = []
    at = 0
    while at < len(clean):
        if clean[at] == '{':
            end = clean.find('}', at)
            if end < 0:
                raise ValueError('unclosed token')
            token = clean[at:end + 1]
            if token not in dynamic:
                raise ValueError('dynamic/control expansion needs context: ' + token)
            display, cells = dynamic[token]
            atoms.append(Atom(token, display, cells))
            at = end + 1
            continue
        match = re.match(r'(?:[A-Za-zＡ-Ｚａ-ｚ]+[0-9０-９]*|[0-9０-９]+|…{2,}|—{2,})', clean[at:])
        term = match.group() if match else next((w for w in terms.get(clean[at], ()) if clean.startswith(w, at)), clean[at])
        atoms.append(Atom(term, term, len(term)))
        at += len(term)
    # A bounded heuristic, not a full Chinese grammar parser: protect explicit
    # adjective + 的 + term phrases. Do not interpret every X的Y as a noun
    # phrase (e.g. 统治皮多纳的路德维希 includes a larger verbal modifier).
    grouped = []
    i = 0
    while i < len(atoms):
        triple = atoms[i:i + 3]
        if (len(triple) == 3 and triple[1].display == '的'
                and triple[0].display in MODIFIERS and len(triple[2].display) >= 2
                and all(re.fullmatch(r'[\u3400-\u9fff]+', a.display) for a in (triple[0], triple[2]))
                and (limit is None or sum(a.cells for a in triple) <= limit)):
            grouped.append(Atom(''.join(a.source for a in triple), ''.join(a.display for a in triple), sum(a.cells for a in triple), True))
            i += 3
        else:
            grouped.append(atoms[i]); i += 1
    return grouped


def wrap(text, limit, rows, terms, dynamic, *, keep_natural_breaks=False):
    """Preserve wording/control order and return a proposal or a hold reason."""
    if not text:
        return text, 'empty'
    if text.startswith(NL) or text.endswith(NL) or NL + NL in text or ' ' in TOKEN.sub('', text):
        return text, 'format_or_join_boundary'
    terminal = '{BUTTON_WAIT}' if text.endswith('{BUTTON_WAIT}') else ''
    body = text[:-len(terminal)] if terminal else text
    if any(x != NL and x not in dynamic for x in TOKEN.findall(body)):
        return text, 'control_or_dynamic_context'
    try:
        atoms = atomize(body, terms, dynamic, limit)
    except ValueError:
        return text, 'control_or_dynamic_context'
    if not atoms:
        return text, 'empty'
    if any(a.cells > limit for a in atoms):
        return text, 'indivisible_term_exceeds_budget'
    widths = [0]
    for a in atoms:
        widths.append(widths[-1] + a.cells)
    if rows and widths[-1] > limit * rows:
        return text, 'text_exceeds_page_budget'
    n = len(atoms)
    # Old breaks are hints, not a linguistic oracle. Permit newly protected
    # modifier-phrase boundaries, not every dictionary-word boundary: knowing
    # two words does not make the gap between them a good sentence break.
    allowed = None
    old_widths = line_cells(body, dynamic)
    if keep_natural_breaks and NL in body and old_widths and max(old_widths) <= limit:
        allowed = set()
        position = 0
        for piece in re.split(r'(\{NEWLINE\})', body):
            if piece == NL:
                allowed.add(position)
            else:
                position += len(piece)
        position = 0
        for i, atom in enumerate(atoms):
            position += len(atom.source)
            if (atom.display[-1:] in PAUSES or atom.modifier_phrase
                    or (i + 1 < n and atoms[i + 1].modifier_phrase)):
                allowed.add(position)
        allowed.add(position)
    positions = [0]
    for atom in atoms:
        positions.append(positions[-1] + len(atom.source))

    @lru_cache(None)
    def solve(start, left):
        if start == n:
            return 0, ()
        if left <= 0:
            return None
        best = None
        for end in range(start + 1, n + 1):
            width = widths[end] - widths[start]
            if width > limit:
                break
            if atoms[end - 1].display[-1:] in OPEN:
                continue
            if end < n and atoms[end - 1].display[-1:] in '的地得':
                continue
            if end < n and atoms[end].display[:1] in CLOSE:
                continue
            if end < n and atoms[end].display in ('的', '地', '得', '了', '着', '过'):
                continue
            if allowed is not None and positions[end] not in allowed:
                continue
            rest = solve(end, left - 1)
            if rest is None:
                continue
            tail, cuts = rest
            # Prefer fewer lines and punctuation/word boundaries; penalize orphan
            # last lines. This is a review proposal, not a linguistic approval.
            boundary = 0 if end == n or atoms[end - 1].display[-1:] in PAUSES else 35
            if end < n and atoms[end - 1].display in COPULAS:
                boundary += 180
            if end < n and atoms[end].display[:1] in '的地得了着过':
                boundary += 50
            short = 80 if end == n and width <= 2 and start else 0
            score = tail + 1000 + (limit - width) ** 2 + boundary + short
            value = score, (end,) + cuts
            if best is None or value[0] < best[0]:
                best = value
        return best

    answer = solve(0, rows or max(1, len(atoms)))
    if answer is None:
        return text, 'no_legal_break_within_budget'
    lines, start = [], 0
    for end in answer[1]:
        lines.append(''.join(a.source for a in atoms[start:end]))
        start = end
    proposal = NL.join(lines) + terminal
    assert visible_without_layout(proposal) == visible_without_layout(text)
    assert control_sequence(proposal) == control_sequence(text)
    return proposal, 'changed' if proposal != text else 'unchanged'


def term_index(values):
    result = {}
    for word in set(values) | set(COMMON):
        if 2 <= len(word) <= 20 and not TOKEN.search(word) and not any(c.isspace() or c in CLOSE | OPEN for c in word):
            result.setdefault(word[0], []).append(word)
    return {c: sorted(words, key=lambda w: (-len(w), w)) for c, words in result.items()}


def expand(text, dynamic):
    for token, (display, cells) in dynamic.items():
        text = text.replace(token, display)
    return text.replace('{BUTTON_WAIT}', '').replace(NL, '\n')


def line_cells(text, dynamic):
    out = []
    for line in text.replace('{BUTTON_WAIT}', '').split(NL):
        width = 0
        for part in re.split(r'(\{[^{}]+\})', line):
            if not part:
                continue
            if part.startswith('{'):
                if part not in dynamic:
                    return None
                width += dynamic[part][1]
            else:
                width += len(part)
        out.append(width)
    return out
