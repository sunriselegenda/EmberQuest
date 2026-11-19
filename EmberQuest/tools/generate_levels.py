"""Воспроизводимая сборка шести авторских карт без случайных тупиков."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOMS = [(1, 1), (11, 1), (21, 1), (21, 9), (11, 9), (1, 9)]
GATES = [(10, 4), (20, 4), (25, 8), (20, 12), (10, 12)]
NAMES = ['Первое пламя', 'Два отражения', 'Три цвета', 'Забытые залы', 'Пепельный путь', 'Сердце храма']
HINTS = ['Подойди к красному ключу. Пробел меняет цвет героя.',
         'Цвета переключаются по кругу: красный → синий → зелёный.',
         'Собери все кристаллы, если хочешь получить больше звёзд.',
         'Узор тоже обозначает цвет: круг, ромб или треугольник.',
         'Избегай шипов и огненных стражей. R начинает уровень заново.',
         'Верни пламя в сердце храма. Ключи одного цвета могут повторяться.']
levels = []
for n in range(6):
    board = [['#'] * 31 for _ in range(17)]
    gates = min(5, n + 1)
    sequence = ['r', 'b', 'g', 'r', 'b'] if n != 5 else ['g', 'r', 'b', 'g', 'r']
    for i in range(gates + 1):
        ox, oy = ROOMS[i]
        for y in range(oy, oy + 7):
            for x in range(ox, ox + 9): board[y][x] = '.'
        # Небольшие внутренние стены оставляют обход с обеих сторон.
        if n >= 1:
            for j in range(3): board[oy + 2 + j][ox + 4] = '#'
        if n >= 3:
            board[oy + 1][ox + 6] = '^'
            board[oy + 5][ox + 2] = '^'
        board[oy + 5][ox + 7] = '*'
        board[oy + 1][ox + 1] = '*'
        if i < gates: board[oy + 5][ox + 1] = sequence[i]
    for i in range(gates):
        x, y = GATES[i]
        board[y][x] = sequence[i].upper()
    board[4][3] = 'S'
    ox, oy = ROOMS[gates]
    board[oy + 3][ox + 7] = 'E'
    enemies = []
    if n >= 4:
        for i in range(1, gates + 1, 2):
            ox, oy = ROOMS[i]
            enemies.append({'a': [ox + 1, oy + 3], 'b': [ox + 3, oy + 3], 'speed': 1.0 + n * .1})
    levels.append({'name': NAMES[n], 'hint': HINTS[n], 'map': [''.join(r) for r in board], 'enemies': enemies})
(ROOT / 'assets' / 'levels.json').write_text(json.dumps(levels, ensure_ascii=False, indent=2), encoding='utf-8')
print('Created 6 levels')
