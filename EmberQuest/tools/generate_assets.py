"""Авторская пиксельная графика и синтезированный звук. Только стандартная библиотека и pygame."""
import math
import os
import random
import struct
import wave
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame as pg

ROOT = Path(__file__).resolve().parents[1] / 'assets'
PALETTE = {'r': (248, 103, 95), 'b': (98, 181, 255), 'g': (105, 223, 168)}

def save(surface, name):
    (ROOT / 'sprites').mkdir(exist_ok=True)
    pg.image.save(surface, str(ROOT / 'sprites' / (name + '.png')))

def surface(w=32, h=32): return pg.Surface((w, h), pg.SRCALPHA)
def rect(s, c, r): pg.draw.rect(s, c, r)
def symbol(s, color, center, size=4):
    x, y = center
    if color == 'r': pg.draw.circle(s, (255, 241, 210), center, size, 1)
    elif color == 'b': pg.draw.polygon(s, (228, 246, 255), [(x,y-size),(x+size,y),(x,y+size),(x-size,y)],1)
    else: pg.draw.polygon(s, (229,255,239), [(x,y-size),(x+size,y+size),(x-size,y+size)],1)

def build():
    pg.init()
    rng = random.Random(417)
    for i in range(4):
        s = surface(); s.fill((27+i, 34+i, 45+i))
        rect(s, (21,27,37), (0,0,32,1)); rect(s, (21,27,37), (0,0,1,32))
        for _ in range(9):
            x,y = rng.randrange(3,29),rng.randrange(3,29)
            rect(s, (38+i,46+i,58+i), (x,y,rng.randrange(1,4),1))
        if i == 2: pg.draw.lines(s, (19,26,35), False, [(6,10),(12,13),(10,17)],1)
        save(s, f'floor_{i}')
    s = surface(); s.fill((45,54,69)); rect(s,(73,85,103),(0,0,32,4)); rect(s,(93,102,116),(1,0,30,1))
    rect(s,(26,33,46),(0,25,32,7)); rect(s,(34,42,56),(0,15,32,2))
    rect(s,(34,42,56),(15,4,2,11)); rect(s,(34,42,56),(6,17,2,8)); rect(s,(62,73,89),(1,5,13,1))
    save(s,'wall')
    for c, rgb in PALETTE.items():
        for frame in range(4):
            # 16 px sprite увеличивается без сглаживания до 32×40.
            s = surface(16,20)
            bob = 1 if frame in (1,3) else 0
            rect(s,(13,20,30),(4,17,3,2)); rect(s,(13,20,30),(10,17,3,2))
            if frame == 1: rect(s,(13,20,30),(4,16,3,2))
            if frame == 3: rect(s,(13,20,30),(10,16,3,2))
            pg.draw.polygon(s,(24,30,45),[(3,9),(12,9),(14,17),(2,17)])
            pg.draw.polygon(s,rgb,[(4,9),(11,9),(12,16),(3,16)])
            rect(s,tuple(int(v*.6) for v in rgb),(4,11,3,5))
            pg.draw.polygon(s,(24,30,45),[(8,0+bob),(3,4+bob),(3,10+bob),(13,10+bob),(13,5+bob)])
            pg.draw.polygon(s,rgb,[(8,1+bob),(4,5+bob),(4,9+bob),(12,9+bob),(12,5+bob)])
            rect(s,(20,28,43),(5,5+bob,7,4)); rect(s,(255,233,176),(6,6+bob,2,1)); rect(s,(255,233,176),(10,6+bob,1,1))
            rect(s,(245,205,126),(7,10,4,1)); rect(s,(245,205,126),(8,12,2,2))
            pg.draw.polygon(s,rgb,[(12,10),(16,12),(14,14),(12,13)])
            save(pg.transform.scale(s,(32,40)), f'hero_{c}_{frame}')
        s = surface(); pg.draw.circle(s,(18,25,35),(11,12),7)
        pg.draw.circle(s,rgb,(11,11),6,3); rect(s,rgb,(14,10,12,3)); rect(s,rgb,(22,11,3,7)); rect(s,rgb,(18,11,3,5))
        rect(s,(255,237,196),(8,6,4,1)); save(s,f'key_{c}')
        s = surface(); rect(s,(16,23,33),(1,0,30,32)); rect(s,(90,98,111),(1,0,4,32)); rect(s,(90,98,111),(27,0,4,32))
        rect(s,(117,123,135),(1,0,30,3)); rect(s,tuple(int(v*.3) for v in rgb),(5,3,22,29))
        for x in (6,13,20): rect(s,tuple(int(v*.55) for v in rgb),(x,4,2,26))
        rect(s,rgb,(6,4,20,2)); rect(s,rgb,(6,26,20,2)); pg.draw.circle(s,(16,23,33),(16,16),8)
        symbol(s,c,(16,16),5); save(s,f'door_{c}')
    s=surface(); pg.draw.polygon(s,(69,118,139),[(16,3),(24,14),(16,27),(8,14)])
    pg.draw.polygon(s,(153,244,229),[(16,3),(16,25),(8,14)])
    pg.draw.polygon(s,(228,255,242),[(16,3),(21,13),(16,16),(11,13)])
    save(s,'gem')
    s=surface(); rect(s,(16,22,31),(1,24,30,6))
    for x in (3,12,21):
        pg.draw.polygon(s,(130,144,158),[(x,25),(x+4,8),(x+8,25)])
        pg.draw.line(s,(228,218,200),(x+4,8),(x+5,22))
    save(s,'spikes')
    for frame in range(4):
        s=surface(); pg.draw.ellipse(s,(17,23,34),(2,22,28,8))
        pg.draw.polygon(s,(242,97,60),[(16,2+frame%2*3),(26,16),(23,25),(9,25),(6,16),(11,8),(12,15)])
        pg.draw.polygon(s,(255,191,91),[(17,9),(22,19),(19,25),(12,24),(11,18)])
        pg.draw.polygon(s,(255,239,181),[(16,16),(19,23),(13,23)])
        save(s,f'fire_{frame}')
    s=surface(); pg.draw.rect(s,(78,84,100),(2,0,28,32),border_radius=12)
    pg.draw.rect(s,(18,30,42),(6,3,20,29),border_radius=10)
    for radius,c in [(10,(55,100,110)),(7,(78,165,164)),(4,(182,247,210))]:
        pg.draw.ellipse(s,c,(16-radius,17-radius,radius*2,radius*2))
    save(s,'portal')
    s=surface(); rect(s,(81,69,61),(14,15,4,13)); rect(s,(139,108,74),(10,17,12,4))
    pg.draw.polygon(s,(247,138,70),[(16,1),(23,11),(19,17),(12,17),(9,11),(13,6),(13,11)])
    pg.draw.polygon(s,(255,222,151),[(16,6),(19,12),(16,16),(13,12)])
    save(s,'torch')
    (ROOT/'audio').mkdir(exist_ok=True)
    for name,notes,duration in [('switch',[330,440,660],.17),('key',[659,830,988],.26),
                                ('door',[196,247,294],.3),('gem',[880,1175],.2),
                                ('death',[220,165,110],.42),('win',[392,494,587,784],.7),('click',[440],.08)]:
        samples=[]; rate=22050
        for i in range(int(rate*duration)):
            t=i/rate; k=min(len(notes)-1,int(t/duration*len(notes)))
            env=math.sin(math.pi*((t/duration*len(notes))%1))*.22
            v=(math.sin(2*math.pi*notes[k]*t)+.2*math.sin(4*math.pi*notes[k]*t))*env
            samples.append(struct.pack('<h',int(24000*v)))
        with wave.open(str(ROOT/'audio'/f'{name}.wav'),'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(b''.join(samples))
    # Спокойный восьмисекундный ambient loop, без внешних музыкальных файлов.
    rate=22050; duration=8
    with wave.open(str(ROOT/'audio'/'ambient.wav'),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        data=bytearray()
        for i in range(rate*duration):
            t=i/rate
            value=sum(math.sin(2*math.pi*freq*t)*amp for freq,amp in [(110,.035),(165,.018),(220,.01),(277.5,.008)])
            value *= min(1,t/.5,(duration-t)/.5)
            data.extend(struct.pack('<h',int(32767*value)))
        f.writeframes(data)
    print('Created sprites and 8 audio files')
    pg.quit()

if __name__=='__main__': build()
