"""Execute the shipped machine code; compare it to the C game's rules.
Reference: kentpmurphy72/8bit-atari-c-wall-pong @ 77dce46262358ff61b2da16e3eac744a8bbfa28a.
No Atari ROM is needed. Hardware registers are RAM in this CPU-level harness.
"""
from pathlib import Path
import random
import struct
import unittest
from py65.devices.mpu6502 import MPU

ROOT = Path(__file__).resolve().parents[1]
LABELS = {name: int(addr, 16) for addr, name in
          (line.split() for line in (ROOT / 'build/labels.txt').read_text().splitlines())}
WORDS = {'BX', 'BY', 'VX', 'VY', 'SCORE'}

def initial():
    return dict(BX=192, BY=848, VX=20, VY=12, SCORE=0,
                PADDLE=45, LIVES=3, PLAYING=0, FIREOLD=0)

def reference(g, up, down, fire):
    pressed = fire and not g['FIREOLD']
    g['FIREOLD'] = fire
    event = 0
    if not g['LIVES']:
        if pressed:
            g.update(initial())
            g['FIREOLD'] = 1
        return 0
    if up and g['PADDLE'] > 12:
        g['PADDLE'] -= 2
    if down and g['PADDLE'] < 78:
        g['PADDLE'] += 2
    g['PADDLE'] = min(78, max(12, g['PADDLE']))
    if not g['PLAYING']:
        g['BX'] = 192
        g['BY'] = (g['PADDLE'] + 8) * 16
        if pressed:
            g.update(PLAYING=1, VX=20, VY=12)
        return 0
    oldx = g['BX']
    g['BX'] += g['VX']
    g['BY'] += g['VY']
    if g['BY'] < 192:
        g['BY'] = 384 - g['BY']
        g['VY'] = -g['VY']
        event = 1
    if g['BY'] > 1472:
        g['BY'] = 2944 - g['BY']
        g['VY'] = -g['VY']
        event = 1
    if g['BX'] >= 2448:
        g['BX'] = 4896 - g['BX']
        g['VX'] = -g['VX']
        g['SCORE'] = min(999, g['SCORE'] + 1)
        event = 2
    if (g['VX'] < 0 and oldx >= 160 and g['BX'] <= 160 and
            g['BY'] + 32 > g['PADDLE'] * 16 and
            g['BY'] < (g['PADDLE'] + 16) * 16):
        g['BX'] = 320 - g['BX']
        g['VX'] = -g['VX']
        if g['VX'] < 40:
            g['VX'] += 1
        g['VY'] = (g['BY'] // 16 + 1 - (g['PADDLE'] + 8)) * 3 or 5
        event = 1
    if g['BX'] < 0:
        g['LIVES'] -= 1
        g['PLAYING'] = 0
        event = 3
    return event

class Machine:
    def __init__(self):
        self.cpu = MPU()
        raw = (ROOT / 'build/wall-pong.xex').read_bytes()
        assert raw[:2] == b'\xff\xff'
        pos = 2
        while pos < len(raw):
            start, end = struct.unpack_from('<HH', raw, pos)
            pos += 4
            size = end - start + 1
            assert size > 0 and pos + size <= len(raw)
            self.cpu.memory[start:end + 1] = raw[pos:pos + size]
            pos += size
        assert self.cpu.memory[0x2e0:0x2e2] == [0, 32]

    def call(self, label, limit=300000):
        c = self.cpu
        c.sp = 0xff
        c.stPushWord(0x0fff)
        c.pc = LABELS[label]
        before = c.processorCycles
        for _ in range(limit):
            if c.pc == 0x1000:
                return c.processorCycles - before
            c.step()
        raise AssertionError(f'{label} did not return, PC={c.pc:04x}')

    def put(self, **values):
        for key, val in values.items():
            a = LABELS[key]
            self.cpu.memory[a] = val & 255
            if key in WORDS:
                self.cpu.memory[a + 1] = (val >> 8) & 255

    def get(self, key):
        a = LABELS[key]
        v = self.cpu.memory[a]
        if key in WORDS:
            v |= self.cpu.memory[a + 1] << 8
            if key != 'SCORE' and v >= 32768:
                v -= 65536
        return v

class GameTests(unittest.TestCase):
    def setUp(self):
        self.m = Machine()
        self.m.call('INIT')

    def compare(self, g, up=0, down=0, fire=0):
        event = reference(g, up, down, fire)
        self.m.put(UP=up, DOWN=down, FIRE=fire)
        self.m.call('STEP')
        self.assertEqual({k: self.m.get(k) for k in g}, g)
        self.assertEqual(self.m.get('EVENT'), event)
        return event

    def test_initial_and_button_edges(self):
        g = initial()
        self.assertEqual({k: self.m.get(k) for k in g}, g)
        for fire in [0, 1, 1, 1, 0, 1]:
            self.compare(g, fire=fire)
        g.update(LIVES=0, PLAYING=0, FIREOLD=1)
        self.m.put(**g)
        for fire in [1, 0, 1, 1, 0, 1]:
            self.compare(g, fire=fire)
        self.assertEqual(g['PLAYING'], 1)

    def test_collisions_angles_and_score_limit(self):
        cases = [dict(BY=193, VY=-24), dict(BY=1470, VY=24),
                 dict(BX=2440, VX=40, SCORE=998),
                 dict(BX=2440, VX=40, SCORE=999),
                 dict(BX=1, VX=-40, BY=1200),
                 dict(BX=170, VX=-40, BY=688)]
        for offset in range(-2, 18):
            for speed in [20, 39, 40]:
                cases.append(dict(BX=170, VX=-speed, BY=(45+offset)*16))
        for changes in cases:
            with self.subTest(changes=changes):
                g = initial() | dict(PLAYING=1, BX=1000) | changes
                self.m.put(**g)
                self.compare(g)

    def test_paddle_limits(self):
        g = initial()
        for up, down in [(1,0)]*70 + [(0,1)]*70 + [(1,1)]*70:
            self.compare(g, up, down)

    def test_random_states(self):
        rng = random.Random(6502)
        for _ in range(4000):
            g = initial() | dict(BX=rng.randrange(0,2448), BY=rng.randrange(192,1473),
                VX=rng.choice([-1,1])*rng.randrange(20,41), VY=rng.randrange(-27,28),
                PADDLE=rng.randrange(12,79), SCORE=rng.randrange(1000), PLAYING=1)
            self.m.put(**g)
            self.compare(g, rng.randrange(2), rng.randrange(2), rng.randrange(2))

    def test_long_rally_and_three_lives(self):
        g = initial()
        seen = set()
        for frame in range(12000):
            target = g['BY']//16 - 7
            seen.add(self.compare(g, g['PADDLE'] > target, g['PADDLE'] < target,
                                 int(not g['PLAYING'] and not g['FIREOLD'])))
        self.assertIn(2, seen)
        self.assertGreater(g['SCORE'], 30)
        for lives in [3,2,1]:
            g.update(LIVES=lives, PLAYING=1, BX=1, VX=-20, BY=1200, PADDLE=12)
            self.m.put(**g)
            self.assertEqual(self.compare(g), 3)
            self.assertEqual(g['LIVES'], lives-1)

    def test_main_loop_inputs_audio_and_exit(self):
        # Supply OS shadow inputs and clock ticks; this is not an ANTIC/POKEY emulator.
        c = self.m.cpu
        mem = c.memory
        saved = {559: 34, 560: 0x34, 561: 0x12, 752: 0,
                 **{708+i: i*16 for i in range(5)},
                 **{0x80+i: 0xa0+i for i in range(4)}}
        for address, value in saved.items():
            mem[address] = value
        mem[632], mem[644], mem[764] = 15, 1, 255
        c.sp = 255
        c.stPushWord(0x0fff)
        c.pc = LABELS['START']
        frames = 0
        saw_audio = False
        budgets = []
        started = None
        for _ in range(500000):
            if c.pc == 0x1000:
                break
            if c.pc == LABELS['LOOP']:
                if started is not None:
                    budgets.append(c.processorCycles - started)
                frames += 1
                mem[644] = 0 if frames == 2 else 1
                if frames == 3:
                    # Force a wall return to exercise main-loop event audio.
                    self.m.put(BX=2440, VX=20, PLAYING=1)
                if frames == 6:
                    mem[764] = 28  # Atari OS key code for Escape
                started = None
            if c.pc == LABELS['WAIT']:
                mem[20] = (mem[20]+1) & 255
            if c.pc == LABELS['NOEXIT']:
                started = c.processorCycles
            if mem[0xd201] == 0xa8:
                saw_audio = True
            c.step()
        else:
            self.fail('Main loop failed to exit')
        self.assertEqual(frames, 6)
        self.assertTrue(saw_audio)
        self.assertEqual(self.m.get('SCORE'), 1)
        self.assertEqual(mem[0xd201], 0)
        for address, value in saved.items():
            self.assertEqual(mem[address], value, hex(address))
        self.assertLess(max(budgets), 23000)

    def test_video_and_renderer(self):
        self.m.call('VIDEO')
        mem = self.m.cpu.memory
        self.assertEqual(mem[0x5000:0x5006], [0x70]*3+[0x4d,0,0x60])
        self.assertEqual(mem[0x5065:0x5068], [0x41,0,0x50])
        def pixel(x,y):
            return (mem[0x6000+y*40+x//4] >> (6-2*(x%4))) & 3
        for x in range(160):
            self.assertEqual(pixel(x,10),1)
            self.assertEqual(pixel(x,94),1)
        for y in range(12,94):
            self.assertEqual(pixel(155,y),2)
            self.assertEqual(pixel(156,y),2)
        self.m.put(RX=8,RY=45,RW=2,RH=16,COLOR=1)
        cycles = self.m.call('RECT')
        self.assertLess(cycles,10000)
        for y in range(45,61):
            self.assertEqual(pixel(8,y),1)
            self.assertEqual(pixel(9,y),1)
            self.assertEqual(pixel(10,y),0)
        self.m.put(SCORE=999)
        self.m.call('NUMBERS')
        for x in [64,69,74]:
            self.assertEqual([pixel(x+c,3) for c in range(3)], [1,1,1])
            self.assertEqual([pixel(x+c,6) for c in range(3)], [0,0,1])

if __name__ == '__main__':
    unittest.main(verbosity=2)
