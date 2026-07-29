#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_songs.py (v2) — пакетно обновляет все HTML-файлы песен в папке songs/.

Работает и на "чистых" файлах (сгенерированных Редактором изначально), и на уже
частично обновлённых (например, скриптом v1) — идемпотентен, можно запускать
сколько угодно раз подряд, лишнего не сломает и не задублирует.

Что делает:
  1. Footer: "Karaoke" -> "Караоке".
  2. Кнопка "назад" в nav: превращает её в <стрелка> + <текст>, где текст
     выровнен по правому краю (если переносится на 2 строки), а стрелка
     крупнее, жирнее и стоит по центру между строк текста.
  3. Хлебные крошки (Исполнитель / Название): переносит название на новую
     строку и уменьшает межстрочный интервал.
  4. Кнопка темы (☀/☾ Светлая/Тёмная): центрирует иконку с текстом
     визуально по центру капсулы.

Использование:
    python3 update_songs.py /путь/до/karaoke-site/songs

Если путь не указан — скрипт возьмёт папку "songs" рядом с самим собой.
Скрипт правит файлы НА МЕСТЕ (in-place). Перед запуском рекомендуется
сделать бэкап папки (или просто убедиться, что у вас есть git-история).
"""

import os
import re
import sys


def esc(s: str) -> str:
    """Экранирование HTML-спецсимволов — как в Редакторе."""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def unescape_basic(s: str) -> str:
    return s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')


# ── 1. Footer ─────────────────────────────────────────────────────────────
FOOTER_RE = re.compile(
    r'(<footer>\s*<a href="\.\./index\.html">)Karaoke(</a>\s*</footer>)'
)

# ── 2. Кнопка "назад" (ловит и старый "← Karaoke", и v1-вариант "← К списку
#      песен" простым текстом — в любом случае пересобирает в канонический вид) ──
NAV_BACK_RE = re.compile(
    r'(<nav>\s*)<a href="\.\./index\.html"[^>]*>.*?</a>',
    re.S
)
NAV_BACK_NEW = (
    r'\1<a href="../index.html" class="back-link">'
    r'<span class="back-arrow">←</span><span class="back-text">К списку песен</span></a>'
)

# ── 3. Хлебные крошки ────────────────────────────────────────────────────
BREADCRUMB_RE = re.compile(
    r'<span style="color:var\(--muted\); font-size:0\.85rem(?:; line-height:1\.3)?">(.*?)</span>',
    re.S
)
ARTIST_RE = re.compile(r'<span class="artist">(.*?)</span>', re.S)
H1_RE = re.compile(r'<h1>(.*?)</h1>', re.S)

# ── CSS-блоки для инъекции ───────────────────────────────────────────────
NAV_HOVER_RE = re.compile(r'(nav a:hover \{ opacity: 1; \})')
BACKLINK_CSS = (
    "\n  nav a.back-link { display: flex; align-items: center; gap: 8px; opacity: 1; }"
    "\n  .back-arrow { font-size: 1.35em; font-weight: 700; line-height: 1; flex-shrink: 0; }"
    "\n  .back-text { text-align: right; line-height: 1.3; }"
)

THEME_BTN_RE = re.compile(r'\.theme-btn\s*\{(.*?)\}', re.S)

# ── 5. Селектор "nav span" задевает вложенные .back-arrow/.back-text спаны
#      внутри кнопки назад и перекрашивает их в var(--border) — сужаем до
#      прямых потомков nav, чтобы затрагивал только "/" и хлебные крошки.
NAV_SPAN_RE = re.compile(r'nav span \{ color: var\(--border\); font-size: 0\.9rem; \}')
NAV_SPAN_NEW = 'nav > span { color: var(--border); font-size: 0.9rem; }'


BACKLINK_RULE_RE = re.compile(r'nav a\.back-link \{[^}]*\}')
BACKLINK_RULE_NEW = 'nav a.back-link { display: flex; align-items: center; gap: 8px; opacity: 1; }'


def ensure_backlink_css(html: str) -> tuple:
    m = BACKLINK_RULE_RE.search(html)
    if m:
        if 'opacity: 1' in m.group(0):
            return html, False
        new_html = html[:m.start()] + BACKLINK_RULE_NEW + html[m.end():]
        return new_html, True
    new_html, n = NAV_HOVER_RE.subn(r'\1' + BACKLINK_CSS, html, count=1)
    return (new_html, True) if n else (html, False)


def ensure_theme_btn_css(html: str) -> tuple:
    m = THEME_BTN_RE.search(html)
    if not m or 'inline-flex' in m.group(1):
        return html, False
    inner = m.group(1).rstrip()
    if not inner.endswith(';'):
        inner += ';'
    inner += (
        "\n    display: inline-flex;"
        "\n    align-items: center;"
        "\n    justify-content: center;"
        "\n    line-height: 1;\n  "
    )
    new_html = html[:m.start(1)] + inner + html[m.end(1):]
    return new_html, True


def process_file(path: str) -> list:
    with open(path, encoding='utf-8', newline='') as f:
        html = f.read()

    changes = []
    original = html

    # 1. Footer
    new_html = FOOTER_RE.sub(r'\1Караоке\2', html)
    if new_html != html:
        html = new_html
        changes.append('footer')

    # 2. Кнопка назад -> структура со стрелкой и текстом
    new_html = NAV_BACK_RE.sub(NAV_BACK_NEW, html, count=1)
    if new_html != html:
        html = new_html
        changes.append('nav-back')

    # CSS для .back-link/.back-arrow/.back-text
    html, added = ensure_backlink_css(html)
    if added:
        changes.append('back-link-css')

    # CSS для центрирования кнопки темы
    html, added = ensure_theme_btn_css(html)
    if added:
        changes.append('theme-btn-css')

    # 5. Сужаем "nav span" до "nav > span", чтобы не красить вложенные
    #    .back-arrow/.back-text в цвет разделителя
    new_html = NAV_SPAN_RE.sub(NAV_SPAN_NEW, html)
    if new_html != html:
        html = new_html
        changes.append('nav-span-scope')

    # 3. Хлебные крошки: исполнитель / перенос / название, line-height:1.3
    artist_m = ARTIST_RE.search(html)
    h1_m = H1_RE.search(html)
    if h1_m:
        title_text = unescape_basic(re.sub(r'<[^>]+>', '', h1_m.group(1))).strip()
        artist_text = unescape_basic(re.sub(r'<[^>]+>', '', artist_m.group(1))).strip() if artist_m else ''

        new_crumb_inner = f'{esc(artist_text)}<br>{esc(title_text)}' if artist_text else esc(title_text)
        new_crumb_full = (
            f'<span style="color:var(--muted); font-size:0.85rem; line-height:1.3">'
            f'{new_crumb_inner}</span>'
        )

        new_html, n = BREADCRUMB_RE.subn(lambda m: new_crumb_full, html, count=1)
        if n and new_html != html:
            html = new_html
            changes.append('breadcrumb')

    if html != original:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(html)

    return changes


def main():
    if len(sys.argv) > 1:
        songs_dir = sys.argv[1]
    else:
        songs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'songs')

    if not os.path.isdir(songs_dir):
        print(f'Папка не найдена: {songs_dir}')
        print('Укажи путь: python3 update_songs.py /путь/до/songs')
        sys.exit(1)

    files = sorted(f for f in os.listdir(songs_dir) if f.endswith('.html'))
    if not files:
        print(f'В папке {songs_dir} не найдено .html файлов')
        sys.exit(1)

    print(f'Найдено файлов: {len(files)}\n')

    stats = {
        'footer': 0, 'nav-back': 0, 'back-link-css': 0,
        'theme-btn-css': 0, 'nav-span-scope': 0, 'breadcrumb': 0, 'unchanged': 0,
    }
    unchanged_files = []

    for fname in files:
        path = os.path.join(songs_dir, fname)
        changes = process_file(path)
        if changes:
            for c in changes:
                stats[c] += 1
        else:
            stats['unchanged'] += 1
            unchanged_files.append(fname)

    print('=== Готово ===')
    print(f'  Footer (Karaoke -> Караоке):                  {stats["footer"]}')
    print(f'  Кнопка назад (стрелка + текст):                {stats["nav-back"]}')
    print(f'  CSS для кнопки назад добавлен:                 {stats["back-link-css"]}')
    print(f'  CSS для центровки кнопки темы добавлен:        {stats["theme-btn-css"]}')
    print(f'  Сужен селектор nav span (не красит стрелку):   {stats["nav-span-scope"]}')
    print(f'  Хлебные крошки (перенос + межстрочный интервал): {stats["breadcrumb"]}')
    print(f'  Файлов без изменений (уже были в порядке):     {stats["unchanged"]}')

    if unchanged_files:
        print('\nФайлы без изменений:')
        for f in unchanged_files:
            print(' ', f)


if __name__ == '__main__':
    main()
