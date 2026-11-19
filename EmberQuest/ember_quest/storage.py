"""Сохранения лежат в домашней папке пользователя, а не рядом с exe."""
import json
import os
from pathlib import Path

SAVE_DIR = Path(os.environ.get('EMBER_QUEST_SAVE_DIR', str(Path.home() / '.ember_quest')))

class Progress:
    def __init__(self, count):
        self.path = SAVE_DIR / 'progress.json'
        self.count = count
        self.unlocked, self.stars, self.muted = 1, {}, False
        self.warning = ''
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            self.unlocked = max(1, min(count, int(data.get('unlocked', 1))))
            raw = data.get('stars', {})
            if isinstance(raw, dict):
                self.stars = {str(i): max(0, min(3, int(raw.get(str(i), 0)))) for i in range(count)}
            self.muted = bool(data.get('muted', False))
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'unlocked': self.unlocked, 'stars': self.stars,
                                             'muted': self.muted}, indent=2), encoding='utf-8')
            temporary.replace(self.path)
        except OSError:
            self.warning = 'Не удалось сохранить прогресс: проверьте доступ к папке пользователя.'

    def complete(self, index, stars):
        self.stars[str(index)] = max(stars, self.stars.get(str(index), 0))
        self.unlocked = min(self.count, max(self.unlocked, index + 2))
        self.save()
