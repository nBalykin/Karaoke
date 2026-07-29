#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_songs.py — пакетно обновляет все HTML-файлы песен в папке songs/:

  1. В нижней шапке (footer) меняет ссылку "Karaoke" -> "Караоке".
  2. В верхней навигации кнопку "← Karaoke" меняет на "← К списку песен".
  3. В хлебных крошках (нав) переносит название песни на новую строку
     (вместо "Исполнитель — Название" в одну строку через тире).

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


FOOTER_RE = re.compile(
    r'(<footer>\s*<a href="\.\./index\.html">)Karaoke(</a>\s*</footer>)'
)

NAV_BACK_RE = re.compile(
    r'(<a href="\.\./index\.html">)\s*←\s*Karaoke\s*(</a>)'
)

BREADCRUMB_RE = re.compile(
    r'(<span style="color:var\(--muted\); font-size:0\.85rem">)(.*?)(</span>)',
    re.S
)

ARTIST_RE = re.compile(r'<span class="artist">(.*?)</span>', re.S)
H1_RE = re.compile(r'<h1>(.*?)</h1>', re.S)


def process_file(path: str) -> list:
    """Возвращает список применённых правок (для отчёта)."""
    with open(path, encoding='utf-8', newline='') as f:
        html = f.read()

    changes = []
    original = html

    # 1. Footer: Karaoke -> Караоке
    if FOOTER_RE.search(html):
        html = FOOTER_RE.sub(r'\1Караоке\2', html)
        changes.append('footer')

    # 2. Кнопка "назад" в nav: ← Karaoke -> ← К списку песен
    if NAV_BACK_RE.search(html):
        html = NAV_BACK_RE.sub(r'\1← К списку песен\2', html)
        changes.append('nav-back')

    # 3. Хлебные крошки: переносим название на новую строку
    artist_m = ARTIST_RE.search(html)
    h1_m = H1_RE.search(html)
    if h1_m:
        title_text = unescape_basic(re.sub(r'<[^>]+>', '', h1_m.group(1))).strip()
        if artist_m:
            artist_text = unescape_basic(re.sub(r'<[^>]+>', '', artist_m.group(1))).strip()
        else:
            artist_text = ''

        if artist_text:
            new_crumb = f'{esc(artist_text)}<br>{esc(title_text)}'
        else:
            new_crumb = esc(title_text)

        def _replace_crumb(m):
            return m.group(1) + new_crumb + m.group(3)

        new_html, n = BREADCRUMB_RE.subn(_replace_crumb, html, count=1)
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

    stats = {'footer': 0, 'nav-back': 0, 'breadcrumb': 0, 'unchanged': 0}
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
    print(f'  Обновлён footer (Karaoke -> Караоке):        {stats["footer"]}')
    print(f'  Обновлена кнопка назад (-> К списку песен):   {stats["nav-back"]}')
    print(f'  Перенесено название на новую строку:          {stats["breadcrumb"]}')
    print(f'  Файлов без изменений (уже были в порядке):    {stats["unchanged"]}')

    if unchanged_files:
        print('\nФайлы без изменений:')
        for f in unchanged_files:
            print(' ', f)


if __name__ == '__main__':
    main()
