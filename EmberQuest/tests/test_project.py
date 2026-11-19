"""python -m unittest discover -s tests -v"""
import json
import os
import tempfile
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
from ember_quest.model import World
from ember_quest import storage

ROOT=Path(__file__).resolve().parents[1]
LEVELS=json.loads((ROOT/'assets/levels.json').read_text(encoding='utf-8'))


def path_to(world,target,unsafe=()):
    """BFS ищет безопасный маршрут с учётом ещё закрытых дверей."""
    queue=deque([world.pos]);prev={world.pos:None}
    while queue:
        p=queue.popleft()
        if p==target:
            result=[]
            while prev[p] is not None:
                parent=prev[p];result.append((p[0]-parent[0],p[1]-parent[1]));p=parent
            return result[::-1]
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            q=p[0]+dx,p[1]+dy
            if q in prev or world.wall(q) or q in world.spikes or q in unsafe: continue
            if q==world.exit and q!=target: continue
            if q in world.doors and (world.doors[q]!=world.color or world.inventory[world.color]<1):continue
            prev[q]=p;queue.append(q)
    return None


def solve(level):
    """Собирает все ключи и кристаллы, затем идёт к выходу.
    Линии патруля полностью исключены: маршрут безопасен при любой фазе стражей.
    """
    world=World(level)
    unsafe=set()
    for enemy in level.get('enemies',[]):
        a,b=enemy['a'],enemy['b']
        unsafe.update((x,a[1]) for x in range(min(a[0],b[0]),max(a[0],b[0])+1))
    moves=0
    while world.keys or world.gems:
        choices=[]
        for p in list(world.keys)+list(world.gems):
            route=path_to(world,p,unsafe)
            if route is not None: choices.append((len(route),p,route))
        if not choices:
            # Следующая комната закрыта: пробуем каждую дверь с имеющимся ключом.
            for p,c in world.doors.items():
                if not world.inventory[c]:continue
                while world.color!=c:world.switch()
                route=path_to(world,p,unsafe)
                if route is not None:choices.append((len(route),p,route))
        if not choices:raise AssertionError('Нет достижимой цели')
        _,p,route=min(choices)
        for dx,dy in route:
            r=world.move(dx,dy);moves+=1
            if r.kind in ('death','wall','need_key','wrong_color','blocked'):
                raise AssertionError(r)
        if p in world.keys:
            while world.color!=world.keys[p]:world.switch()
            world.collect_here()
        if moves>3000:raise AssertionError('Маршрут зациклился')
    route=path_to(world,world.exit,unsafe)
    if route is None:raise AssertionError('Выход недостижим')
    for dx,dy in route:world.move(dx,dy);moves+=1
    return world,moves


class RulesTest(unittest.TestCase):
    def tiny(self,row):
        return World({'map':['#'*len(row),row,'#'*len(row)]})

    def test_color_cycle(self):
        w=self.tiny('#S.E#')
        self.assertEqual([w.switch() for _ in range(3)],['b','g','r'])

    def test_key_requires_color_and_can_be_collected_here(self):
        w=self.tiny('#SbE#')
        self.assertEqual(w.move(1,0).kind,'key_color')
        self.assertIn((2,1),w.keys)
        w.switch()
        self.assertEqual(w.collect_here().kind,'key')
        self.assertEqual(w.inventory['b'],1)
        self.assertEqual(w.collect_here().kind,'switch')
        self.assertEqual(w.inventory['b'],1)

    def test_door_requires_key_and_color_and_consumes_once(self):
        w=self.tiny('#SrRE#')
        w.move(1,0);w.switch()
        self.assertEqual(w.move(1,0).kind,'wrong_color')
        w.switch();w.switch()
        self.assertEqual(w.move(1,0).kind,'door')
        self.assertEqual(w.inventory['r'],0)
        w.move(-1,0)
        self.assertEqual(w.move(1,0).kind,'step')
        w=self.tiny('#SRE#')
        self.assertEqual(w.move(1,0).kind,'need_key')

    def test_walls_spikes_and_finish(self):
        w=self.tiny('#S^E#')
        self.assertEqual(w.move(-1,0).kind,'wall')
        self.assertEqual(w.move(1,0).kind,'death')
        w=self.tiny('#S*E#')
        self.assertEqual(w.move(1,0).kind,'gem')
        self.assertEqual(w.move(1,0).kind,'win')
        self.assertTrue(w.won)
        self.assertEqual(w.move(-1,0).kind,'blocked')

    def test_all_six_levels_with_every_gem_and_no_patrol_crossings(self):
        for i,level in enumerate(LEVELS):
            with self.subTest(level=i+1):
                world,moves=solve(level)
                self.assertTrue(world.won)
                self.assertEqual(world.collected,world.total_gems)
                self.assertFalse(world.doors)
                print(f'  Level {i+1}: safe route, {moves} steps, {world.collected} crystals')

    def test_repeated_key_color(self):
        w=self.tiny('#SrrRRE#')
        w.move(1,0);w.move(1,0)
        self.assertEqual(w.inventory['r'],2)
        self.assertEqual(w.move(1,0).kind,'door')
        self.assertEqual(w.move(1,0).kind,'door')
        self.assertEqual(w.inventory['r'],0)


class SaveTest(unittest.TestCase):
    def test_save_load_and_best_stars(self):
        with tempfile.TemporaryDirectory() as d,patch.object(storage,'SAVE_DIR',Path(d)):
            p=storage.Progress(6);p.complete(0,3);p.complete(0,1)
            q=storage.Progress(6)
            self.assertEqual(q.unlocked,2)
            self.assertEqual(q.stars['0'],3)

    def test_corrupt_save_falls_back(self):
        with tempfile.TemporaryDirectory() as d,patch.object(storage,'SAVE_DIR',Path(d)):
            (Path(d)/'progress.json').write_text('broken json')
            self.assertEqual(storage.Progress(6).unlocked,1)


class RuntimeTest(unittest.TestCase):
    def test_render_states_input_pause_and_restart(self):
        import pygame as pg
        from ember_quest.game import Game
        with tempfile.TemporaryDirectory() as d,patch.object(storage,'SAVE_DIR',Path(d)):
            g=Game();g.draw()
            g.start(0);g.draw()
            g.event(pg.event.Event(pg.KEYDOWN,key=pg.K_SPACE))
            self.assertEqual(g.world.color,'b')
            g.event(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE))
            before=g.elapsed;g.update(.05);self.assertEqual(g.elapsed,before)
            g.draw()
            g.event(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE))
            self.assertEqual(g.state,'playing')
            g.action('help');g.draw();g.action('back')
            g.action('retry');self.assertEqual(g.deaths,1)
            g.state='levels';g.draw()
            g.start(5);g.update(.05);g.draw()
            world,_=solve(LEVELS[5]);g.world=world
            from ember_quest.model import MoveResult
            g.handle_result(MoveResult('win'));g.draw()
            self.assertEqual(g.state,'win')
            g.action('next');self.assertEqual(g.state,'levels')
            pg.quit()

if __name__=='__main__':unittest.main()
