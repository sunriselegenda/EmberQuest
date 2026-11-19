"""Независимые от Pygame правила: удобны для объяснения и тестирования."""
from collections import Counter
from dataclasses import dataclass

COLORS = ('r', 'b', 'g')

@dataclass
class MoveResult:
    kind: str
    color: str = ''

class World:
    def __init__(self, level):
        self.rows = level['map']
        self.width, self.height = len(self.rows[0]), len(self.rows)
        if any(len(row) != self.width for row in self.rows):
            raise ValueError('Строки карты должны иметь одинаковую длину')
        self.keys, self.doors, self.gems, self.spikes = {}, {}, set(), set()
        starts, exits = [], []
        for y, row in enumerate(self.rows):
            for x, cell in enumerate(row):
                p = (x, y)
                if cell == 'S': starts.append(p)
                elif cell == 'E': exits.append(p)
                elif cell in 'rbg': self.keys[p] = cell
                elif cell in 'RBG': self.doors[p] = cell.lower()
                elif cell == '*': self.gems.add(p)
                elif cell == '^': self.spikes.add(p)
        if len(starts) != 1 or len(exits) != 1:
            raise ValueError('Нужны ровно один S и один E')
        self.start, self.exit = starts[0], exits[0]
        self.pos, self.color = self.start, 'r'
        self.inventory = Counter()
        self.total_gems, self.collected = len(self.gems), 0
        self.opened = 0
        self.won = False

    def switch(self):
        self.color = COLORS[(COLORS.index(self.color) + 1) % 3]
        return self.color

    def wall(self, p):
        x, y = p
        return not (0 <= x < self.width and 0 <= y < self.height) or self.rows[y][x] == '#'

    def move(self, dx, dy):
        """Один шаг по сетке. Ключ расходуется при открытии двери."""
        if self.won or abs(dx) + abs(dy) != 1:
            return MoveResult('blocked')
        p = (self.pos[0] + dx, self.pos[1] + dy)
        if self.wall(p): return MoveResult('wall')
        result = MoveResult('step')
        if p in self.doors:
            color = self.doors[p]
            if self.color != color: return MoveResult('wrong_color', color)
            if self.inventory[color] < 1: return MoveResult('need_key', color)
            self.inventory[color] -= 1
            del self.doors[p]
            self.opened += 1
            result = MoveResult('door', color)
        self.pos = p
        if p in self.spikes: return MoveResult('death')
        if p in self.keys:
            color = self.keys[p]
            if self.color == color:
                self.inventory[color] += 1
                del self.keys[p]
                result = MoveResult('key', color)
            else: result = MoveResult('key_color', color)
        if p in self.gems:
            self.gems.remove(p)
            self.collected += 1
            result = MoveResult('gem')
        if p == self.exit:
            self.won = True
            result = MoveResult('win')
        return result

    def collect_here(self):
        """После смены цвета ключ под ногами подбирается без лишнего шага."""
        if self.keys.get(self.pos) == self.color:
            del self.keys[self.pos]
            self.inventory[self.color] += 1
            return MoveResult('key', self.color)
        return MoveResult('switch')
