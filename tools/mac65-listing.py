"""Export numbered ATASCII source for MAC/65 ENTER (E#D:WALLPONG.LST)."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
lines = (root / 'src/wallpong.m65').read_text().splitlines()
assert len(lines) * 10 < 32767
assert max(map(len, lines)) < 115, 'MAC/65 editor line too long'
output = b''.join(f'{i*10} {line}'.encode('ascii') + b'\x9b'
                  for i, line in enumerate(lines, 1))
(root / 'build/WALLPONG.LST').write_bytes(output)
print('Wrote build/WALLPONG.LST (numbered ATASCII, not a tokenized SAVE file)')
