"""Окно, ввод, анимация, звук и интерфейс Ember Quest.

Правила находятся в model.py; здесь только управление игровыми состояниями
и представление. Все координаты интерфейса рассчитаны для холста 1120×820,
который масштабируется под размер окна с сохранением пропорций.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import pygame as pg
from .model import World, COLORS
from .storage import Progress

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
ASSETS = ROOT / 'assets'
SIZE = (1120, 820)
TILE = 32
ORIGIN = (64, 150)
RGB = {'r': (248, 103, 95), 'b': (98, 181, 255), 'g': (105, 223, 168)}
NAMES = {'r': 'КРАСНЫЙ', 'b': 'СИНИЙ', 'g': 'ЗЕЛЁНЫЙ'}
INK, MUTED, GOLD = (233, 234, 225), (143, 157, 177), (239, 190, 114)


class Game:
    def __init__(self):
        pg.mixer.pre_init(22050, -16, 1, 512)
        pg.init()
        self.window = pg.display.set_mode(SIZE, pg.RESIZABLE)
        pg.display.set_caption('Ember Quest — Храм трёх огней')
        self.canvas = pg.Surface(SIZE)
        self.clock = pg.time.Clock()
        self.fonts = {s: pg.font.Font(str(ASSETS/'font.ttf'), s) for s in (12,14,16,18,20,24,28,36,52,72)}
        self.images = {p.stem: pg.image.load(str(p)).convert_alpha() for p in (ASSETS/'sprites').glob('*.png')}
        pg.display.set_icon(self.images['hero_r_0'])
        self.levels = json.loads((ASSETS/'levels.json').read_text(encoding='utf-8'))
        self.progress = Progress(len(self.levels))
        self.sounds = {}
        if pg.mixer.get_init():
            self.sounds = {p.stem: pg.mixer.Sound(str(p)) for p in (ASSETS/'audio').glob('*.wav') if p.stem != 'ambient'}
            pg.mixer.music.load(str(ASSETS/'audio'/'ambient.wav'))
            pg.mixer.music.play(-1)
        self.apply_volume()
        self.state, self.running = 'menu', True
        self.selected = 0
        self.buttons = []
        self.time = 0.
        self.particles = []
        self.world = None
        self.index = 0
        self.resume_state = 'menu'
        self.message, self.message_time = '', 0.
        self.flash = 0.
        self.rng = random.Random(12)
        self.stars = 0

    def apply_volume(self):
        if pg.mixer.get_init():
            pg.mixer.music.set_volume(0 if self.progress.muted else .38)

    def sound(self, name):
        if not self.progress.muted and name in self.sounds:
            self.sounds[name].set_volume(.35)
            self.sounds[name].play()

    def text(self, value, pos, size=18, color=INK, center=False):
        image = self.fonts[size].render(str(value), True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        self.canvas.blit(image, rect)
        return rect

    def panel(self, rect, fill=(21,29,41), border=(47,61,79), radius=12):
        pg.draw.rect(self.canvas, fill, rect, border_radius=radius)
        pg.draw.rect(self.canvas, border, rect, 1, border_radius=radius)

    def mouse(self):
        ww,wh=self.window.get_size(); scale=min(ww/SIZE[0],wh/SIZE[1])
        mx,my=pg.mouse.get_pos()
        return ((mx-(ww-SIZE[0]*scale)/2)/scale,(my-(wh-SIZE[1]*scale)/2)/scale)

    def button(self, label, rect, action, accent=False, enabled=True):
        r=pg.Rect(rect); hover=r.collidepoint(self.mouse()) and enabled
        fill=(68,49,34) if accent else (27,38,53)
        border=GOLD if accent or hover else (56,71,91)
        if hover: fill=(62,71,81)
        if not enabled: fill,border=(20,27,37),(34,43,56)
        self.panel(r,fill,border,8)
        self.text(label,r.center,18,GOLD if accent and enabled else INK if enabled else (83,95,113),True)
        if enabled: self.buttons.append((r,action))

    def toast(self, message):
        self.message,self.message_time=message,2.8

    def burst(self, p, color, count=18):
        x,y=ORIGIN[0]+p[0]*TILE+16,ORIGIN[1]+p[1]*TILE+16
        for _ in range(count):
            angle=self.rng.random()*math.tau; speed=self.rng.uniform(25,110)
            self.particles.append([x,y,math.cos(angle)*speed,math.sin(angle)*speed,self.rng.uniform(.3,.7),color])

    def start(self, index, retry=False):
        self.index=index
        self.world=World(self.levels[index])
        self.draw_pos=pg.Vector2(self.world.pos)
        self.from_pos=pg.Vector2(self.world.pos)
        self.move_left=0.
        self.walk_frame=0
        self.enemy_time=0.
        if not retry:
            self.elapsed,self.deaths,self.steps=0.,0,0
        self.particles=[]
        self.state='playing'
        self.toast(self.levels[index]['hint'])
        self.build_map()

    def build_map(self):
        self.map_surface=pg.Surface((self.world.width*TILE,self.world.height*TILE))
        self.map_surface.fill((14, 21, 31))
        self.torches=[]
        for y,row in enumerate(self.world.rows):
            for x,ch in enumerate(row):
                p=(x*TILE,y*TILE)
                # За контуром комнат оставляем тьму, а не сплошную массу кирпичей.
                if ch == '#' and all(self.world.wall((x+dx,y+dy))
                                     for dx in (-1,0,1) for dy in (-1,0,1)):
                    continue
                self.map_surface.blit(self.images['wall' if ch=='#' else f'floor_{(x*7+y*3)%4}'],p)
                if ch=='#' and y+1<self.world.height and self.world.rows[y+1][x]!='#' and x%5==2:
                    self.torches.append((x,y))

    def handle_result(self, result):
        kind=result.kind
        if kind in ('key','gem','door'):
            self.sound(kind)
            self.burst(self.world.pos,RGB.get(result.color,(153,244,229)))
        if kind=='key': self.toast('Ключ получен: '+NAMES[result.color].lower())
        elif kind=='door': self.toast('Печать снята. Путь открыт!')
        elif kind in ('wrong_color','key_color'):
            self.toast('Нужен '+NAMES[result.color].lower()+' цвет — нажми ПРОБЕЛ')
        elif kind=='need_key': self.toast('Сначала найди ключ: '+NAMES[result.color].lower())
        elif kind=='death': self.die()
        elif kind=='win':
            self.stars=1+int(self.world.collected==self.world.total_gems)+int(self.deaths==0)
            self.progress.complete(self.index,self.stars)
            self.sound('win');self.burst(self.world.pos,GOLD,55)
            self.state='win'

    def die(self):
        self.deaths+=1
        self.sound('death')
        self.start(self.index,retry=True)
        self.flash=.4
        self.toast('Пламя возрождается. Найди безопасный путь.')

    def move(self, dx, dy):
        if self.move_left>0 or self.state!='playing': return
        old=self.world.pos
        result=self.world.move(dx,dy)
        if self.world.pos!=old:
            self.steps+=1
            self.from_pos=pg.Vector2(old)
            self.move_left=.12
            self.walk_frame+=1
        else:
            self.move_left=.10  # Ограничение частоты сообщений при упоре в стену.
            self.from_pos=pg.Vector2(old)
        self.handle_result(result)

    def enemy_positions(self):
        result=[]
        for i, enemy in enumerate(self.levels[self.index].get('enemies',[])):
            a,b=pg.Vector2(enemy['a']),pg.Vector2(enemy['b'])
            phase=(self.enemy_time*enemy['speed']/(a.distance_to(b) or 1)+i*.4)%2
            result.append(a.lerp(b,phase if phase<1 else 2-phase))
        return result

    def action(self, action):
        if action=='quit': self.running=False
        elif action=='menu': self.state='menu'
        elif action=='levels': self.state='levels'; self.selected=min(self.selected,self.progress.unlocked-1)
        elif action=='continue': self.start(self.progress.unlocked-1)
        elif action=='resume': self.state='playing'
        elif action=='retry': self.deaths+=1; self.start(self.index,retry=True)
        elif action=='help': self.resume_state=self.state; self.state='help'
        elif action=='back': self.state=self.resume_state
        elif action=='next':
            if self.index+1<len(self.levels): self.start(self.index+1)
            else: self.state='levels'
        elif action.startswith('level:'): self.start(int(action.split(':')[1]))
        self.sound('click')

    def event(self, event):
        if event.type==pg.QUIT: self.running=False
        elif event.type==pg.MOUSEBUTTONDOWN and event.button==1:
            for rect,action in self.buttons:
                if rect.collidepoint(self.mouse()): self.action(action); break
        elif event.type==pg.KEYDOWN:
            key=event.key
            if key==pg.K_m:
                self.progress.muted=not self.progress.muted
                self.apply_volume(); self.progress.save()
            elif key==pg.K_F1:
                self.action('back' if self.state=='help' else 'help')
            elif self.state=='playing':
                if key==pg.K_SPACE:
                    self.world.switch(); self.sound('switch')
                    self.burst(self.world.pos,RGB[self.world.color],12)
                    self.handle_result(self.world.collect_here())
                elif key in (pg.K_ESCAPE,pg.K_p): self.state='pause'
                elif key==pg.K_r: self.action('retry')
            elif self.state=='pause' and key in (pg.K_ESCAPE,pg.K_p): self.state='playing'
            elif self.state=='menu':
                if key==pg.K_RETURN: self.action('continue')
                elif key==pg.K_ESCAPE: self.running=False
            elif self.state=='levels':
                if key==pg.K_ESCAPE: self.state='menu'
                elif key==pg.K_RIGHT: self.selected=(self.selected+1)%self.progress.unlocked
                elif key==pg.K_LEFT: self.selected=(self.selected-1)%self.progress.unlocked
                elif key==pg.K_RETURN: self.start(self.selected)
            elif self.state=='help' and key==pg.K_ESCAPE: self.state=self.resume_state
            elif self.state=='win':
                if key==pg.K_RETURN: self.action('next')
                elif key==pg.K_ESCAPE: self.state='levels'

    def update(self,dt):
        self.time+=dt
        self.message_time=max(0,self.message_time-dt)
        self.flash=max(0,self.flash-dt)
        if self.state=='playing':
            self.elapsed+=dt
            self.enemy_time+=dt
            self.move_left=max(0,self.move_left-dt)
            progress=1-self.move_left/.12
            progress=max(0,min(1,progress))
            self.draw_pos=self.from_pos.lerp(pg.Vector2(self.world.pos),progress)
            if self.move_left<=0:
                keys=pg.key.get_pressed()
                for key,dx,dy in [(pg.K_UP,0,-1),(pg.K_w,0,-1),(pg.K_DOWN,0,1),(pg.K_s,0,1),
                                  (pg.K_LEFT,-1,0),(pg.K_a,-1,0),(pg.K_RIGHT,1,0),(pg.K_d,1,0)]:
                    if keys[key]: self.move(dx,dy);break
            if self.state=='playing' and any(self.draw_pos.distance_to(p)<.58 for p in self.enemy_positions()):
                self.die()
        for p in self.particles:
            p[0]+=p[2]*dt;p[1]+=p[3]*dt;p[3]+=55*dt;p[4]-=dt
        self.particles=[p for p in self.particles if p[4]>0]

    def background(self):
        self.canvas.fill((12,18,28))
        for y in range(0,820,4):
            c=int(7*(1-y/820)); pg.draw.rect(self.canvas,(12+c,18+c,28+c),(0,y,1120,4))
        for i in range(40):
            x=(i*137+math.sin(self.time*.2+i)*15)%1120
            y=(i*81-self.time*(5+i%7))%820
            pg.draw.circle(self.canvas,(85+i%30,62+i%18,47),(int(x),int(y)),1 if i%3 else 2)

    def glow(self, center, color, radius):
        s=pg.Surface((radius*2,radius*2),pg.SRCALPHA)
        for i in range(4,0,-1):
            pg.draw.circle(s,(*color,6+i*2),(radius,radius),int(radius*i/4))
        self.canvas.blit(s,(center[0]-radius,center[1]-radius))

    def draw_world(self):
        w=self.world
        self.canvas.blit(self.map_surface,ORIGIN)
        ox,oy=ORIGIN
        def point(p): return (ox+p[0]*TILE,oy+p[1]*TILE)
        for p in self.torches:
            x,y=point(p)
            self.glow((x+16,y+18),(255,155,70),45)
            self.canvas.blit(self.images['torch'],(x,y))
        for p in w.spikes: self.canvas.blit(self.images['spikes'],point(p))
        for p,c in w.doors.items():
            self.canvas.blit(self.images['door_'+c],point(p))
        for p,c in w.keys.items():
            x,y=point(p); y+=int(math.sin(self.time*3+p[0]) * 2)
            self.glow((x+16,y+14),RGB[c],25)
            self.canvas.blit(self.images['key_'+c],(x,y))
        for p in w.gems:
            x,y=point(p);y+=int(math.sin(self.time*2+p[1])*2)
            self.canvas.blit(self.images['gem'],(x,y))
        x,y=point(w.exit)
        self.glow((x+16,y+16),(120,239,199),42)
        self.canvas.blit(self.images['portal'],(x,y))
        for p in self.enemy_positions():
            x,y=point(p); self.glow((x+16,y+16),(255,95,45),35)
            self.canvas.blit(self.images[f'fire_{int(self.time*8)%4}'],(x,y))
        # При завершении сразу показываем героя у выхода, иначе он ещё в середине шага.
        hero=pg.Vector2(w.pos) if self.state=='win' else self.draw_pos
        x,y=point(hero)
        pg.draw.ellipse(self.canvas,(13,20,29),(x+4,y+23,24,9))
        self.glow((x+16,y+12),RGB[w.color],28)
        frame=self.walk_frame%4 if self.move_left else int(self.time*2)%2*2
        self.canvas.blit(self.images[f'hero_{w.color}_{frame}'],(int(x),int(y)-10))
        for px,py,_,_,life,color in self.particles:
            pg.draw.rect(self.canvas,color,(int(px),int(py),3 if life>.25 else 2,3))
        self.text('EMBER QUEST',(64,30),28,GOLD)
        self.text(f'{self.index+1:02d} / 06   {self.levels[self.index]["name"]}',(64,72),18)
        self.text(f'{int(self.elapsed)//60:02d}:{int(self.elapsed)%60:02d}',(976,39),24,INK)
        self.text('ВРЕМЯ',(976,70),12,MUTED)
        for i,c in enumerate(COLORS):
            x=460+i*138
            active=w.color==c
            self.panel((x,34,126,61),(30,41,54),RGB[c] if active else (48,60,78),9)
            self.canvas.blit(self.images['key_'+c],(x+7,48))
            self.text(f'× {w.inventory[c]}',(x+46,49),20,RGB[c])
            if active: pg.draw.circle(self.canvas,RGB[c],(x+110,46),3)
        self.text(f'ЦВЕТ: {NAMES[w.color]}',(64,115),14,RGB[w.color])
        self.text(f'КРИСТАЛЛЫ  {w.collected}/{w.total_gems}',(410,115),14,(153,244,229))
        self.text(f'ВОЗРОЖДЕНИЯ  {self.deaths}',(776,115),14,MUTED)
        if self.message_time>0:
            self.panel((64,710,992,43),(24,34,46),(58,73,89),8)
            self.text(self.message,(84,721),16,INK)
        else:
            self.text('Найди ключи, сними цветные печати и войди в портал.',(64,724),16,MUTED)
        self.text('WASD / СТРЕЛКИ   движение     ПРОБЕЛ   цвет     R   заново     ESC   пауза',(64,779),14,MUTED)
        self.text('F1  помощь     M  звук '+('ВЫКЛ' if self.progress.muted else 'ВКЛ'),(831,779),12,MUTED)
        if self.flash:
            layer=pg.Surface(SIZE,pg.SRCALPHA);layer.fill((240,82,63,int(100*self.flash/.4)));self.canvas.blit(layer,(0,0))

    def draw_menu(self):
        self.text('A SMALL FLAME. A LONG JOURNEY.',(90,91),14,GOLD)
        self.text('EMBER',(84,144),72)
        self.text('QUEST',(84,220),72,GOLD)
        self.text('ХРАМ ТРЁХ ОГНЕЙ',(91,321),20,MUTED)
        for i,line in enumerate(['Храм погас. Последняя искра — в твоих руках.',
                                 'Меняй цвет, собирай ключи и открывай двери.',
                                 'Верни огонь в сердце древнего лабиринта.']):
            self.text(line,(91,379+i*29),16,INK)
        self.button('Продолжить  /  ENTER',(90,507,350,54),'continue',True)
        self.button('Выбор уровня',(90,577,350,48),'levels')
        self.button('Как играть  /  F1',(90,641,350,48),'help')
        self.button('Выход',(90,705,350,45),'quit')
        # Диорама на главном экране — те же реальные игровые спрайты.
        scene=pg.Surface((10*32,11*32),pg.SRCALPHA)
        for y in range(11):
            for x in range(10):
                wall=x in (0,9) or y in (0,10) or (y==4 and x not in (4,5))
                scene.blit(self.images['wall' if wall else f'floor_{(x+y)%4}'],(x*32,y*32))
        scene.blit(self.images['door_r'],(4*32,4*32));scene.blit(self.images['door_b'],(5*32,4*32))
        scene.blit(self.images['portal'],(7*32,2*32));scene.blit(self.images['gem'],(2*32,2*32))
        scene.blit(self.images['key_r'],(2*32,6*32));scene.blit(self.images['key_b'],(7*32,7*32))
        frame=int(self.time*3)%4
        scene.blit(self.images[f'hero_{COLORS[int(self.time/3)%3]}_{frame}'],(4*32,7*32-10))
        self.glow((820,440),(222,136,78),230)
        self.canvas.blit(pg.transform.scale(scene,(416,458)),(610,176))
        self.text('01  /  ЦВЕТ ОТКРЫВАЕТ ПУТЬ',(631,669),14,GOLD)
        self.text('6 уровней  •  ключи  •  древние печати',(631,700),14,MUTED)
        self.text('PYTHON + PYGAME   /   2D PUZZLE ADVENTURE',(90,787),12,MUTED)

    def draw_levels(self):
        self.text('ПУТЬ ИСКРЫ',(64,55),36,GOLD)
        self.text('Выбери открытый зал. Результаты сохраняются автоматически.',(64,110),18,MUTED)
        for i,level in enumerate(self.levels):
            x,y=64+(i%3)*338,180+(i//3)*238
            unlocked=i<self.progress.unlocked
            self.panel((x,y,316,214),(24,33,46),GOLD if i==self.selected else (52,65,82))
            self.text(f'{i+1:02d}',(x+20,y+14),36,GOLD if unlocked else MUTED)
            self.text(level['name'],(x+20,y+68),20,INK if unlocked else MUTED)
            stars=self.progress.stars.get(str(i),0)
            self.text('★'*stars+'☆'*(3-stars),(x+20,y+104),24,GOLD if unlocked else MUTED)
            self.button('Войти' if unlocked else 'Зал закрыт',(x+20,y+153,276,42),f'level:{i}',enabled=unlocked)
        self.button('Главное меню',(64,718,242,48),'menu')
        self.text('← →  выбор    ENTER  начать    ESC  меню',(360,733),16,MUTED)

    def overlay(self,title):
        layer=pg.Surface(SIZE,pg.SRCALPHA);layer.fill((5,10,18,215));self.canvas.blit(layer,(0,0))
        self.panel((230,155,660,520),(20,29,42),(94,80,60),18)
        self.text(title,(560,209),36,GOLD,True)

    def draw_help(self):
        self.overlay('КАК ИГРАТЬ')
        lines=[('WASD / стрелки','Двигайся по храму.'),('Пробел','Красный → синий → зелёный → красный.'),
               ('Ключ','Подбирается, когда его цвет совпадает с твоим.'),('Дверь','Нужны совпадающий цвет и ключ. Ключ тратится.'),
               ('Портал','Завершает уровень. Кристаллы необязательны.'),('Опасности','Шипы и стражи возвращают в начало уровня.'),
               ('R / ESC / M','Заново / пауза / включить или выключить звук.')]
        for i,(a,b) in enumerate(lines):
            self.text(a,(265,265+i*41),14,GOLD)
            self.text(b,(411,265+i*41),14,INK)
        self.text('★ пройти   ★ все кристаллы   ★ без возрождений',(560,575),16,MUTED,True)
        self.button('Понятно  /  ESC',(385,610,350,44),'back',True)

    def draw(self):
        self.buttons=[]
        self.background()
        if self.state in ('playing','pause','win') or (self.state=='help' and self.resume_state in ('playing','pause','win')):
            self.draw_world()
        elif self.state=='levels': self.draw_levels()
        elif self.state=='menu': self.draw_menu()
        if self.state=='pause':
            self.overlay('ПЛАМЯ ЖДЁТ')
            self.text('Игра на паузе. Время остановлено.',(560,281),18,MUTED,True)
            self.button('Продолжить  /  ESC',(355,333,410,52),'resume',True)
            self.button('Начать уровень заново',(355,402,410,48),'retry')
            self.button('Выбор уровня',(355,467,410,48),'levels')
            self.button('Главное меню',(355,532,410,48),'menu')
        elif self.state=='help': self.draw_help()
        elif self.state=='win':
            self.overlay('ХРАМ СНОВА ГОРИТ' if self.index==5 else 'ПЕЧАТЬ СНЯТА')
            self.text('★'*self.stars+'☆'*(3-self.stars),(560,290),52,GOLD,True)
            self.text(f'Кристаллы: {self.world.collected}/{self.world.total_gems}    Возрождения: {self.deaths}',(560,380),20,INK,True)
            self.text(f'Время: {self.elapsed:.1f} сек.    Шаги: {self.steps}',(560,423),18,MUTED,True)
            self.button('К выбору уровней' if self.index==5 else 'Следующий зал  /  ENTER',(355,491,410,54),'next',True)
            self.button('Пройти ещё раз',(355,565,410,48),f'level:{self.index}')
        if self.progress.warning:
            self.panel((36,7,1048,28),(62,37,30),(100,62,43),5)
            self.text(self.progress.warning,(49,12),12,GOLD)
        self.present()

    def present(self):
        ww,wh=self.window.get_size();scale=min(ww/SIZE[0],wh/SIZE[1])
        target=(max(1,int(SIZE[0]*scale)),max(1,int(SIZE[1]*scale)))
        self.window.fill((6,10,17))
        self.window.blit(pg.transform.smoothscale(self.canvas,target),((ww-target[0])//2,(wh-target[1])//2))
        pg.display.flip()

    def run(self):
        self.draw()
        while self.running:
            dt=min(self.clock.tick(60)/1000,.05)
            for event in pg.event.get(): self.event(event)
            self.update(dt)
            self.draw()
        pg.quit()


def main():
    parser=argparse.ArgumentParser(description='Ember Quest')
    parser.add_argument('--screenshot',type=Path,help='Сохранить кадр игры и выйти')
    parser.add_argument('--menu-screenshot',type=Path,help='Сохранить кадр меню и выйти')
    args=parser.parse_args()
    game=Game()
    if args.screenshot or args.menu_screenshot:
        if args.screenshot: game.start(5);game.message_time=0
        game.time=2;game.draw()
        pg.image.save(game.canvas,str(args.screenshot or args.menu_screenshot))
        pg.quit()
    else: game.run()
