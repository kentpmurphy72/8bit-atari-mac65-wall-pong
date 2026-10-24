# Wall Pong — MAC/65 / Atari 800XL

A one-player paddle-and-wall game written entirely in 6502 assembly using
MAC/65 syntax. This ports the rules and display of
[kentpmurphy72/8bit-atari-c-wall-pong](https://github.com/kentpmurphy72/8bit-atari-c-wall-pong)
(reference commit `77dce46262358ff61b2da16e3eac744a8bbfa28a`).
The game contains no C runtime, external graphics, or sound assets.

## Play

- Use a joystick in **port 1**, up/down to move the left paddle.
- Press fire to serve. Release fire before the next serve.
- Each return from the right wall earns one point, capped at **999**.
- Paddle impact position changes the rebound angle. Paddle returns gradually
  increase horizontal speed.
- You have **three lives**. After game over, press fire to reset; release and
  press again to serve.
- **Escape** exits to the binary loader/DOS and restores the previous display
  list, DMA setting, cursor setting, colors, and the zero-page bytes used.

The top digits show points and lives. The center indicator is green while
waiting to serve, blank during play, and orange at game over. POKEY tones
mark bounces, points, and misses.

## Build on a modern computer

Requires Git, GNU Make **4.3+**, a C compiler, zlib development headers/libraries, Python 3 with `venv`, and a POSIX
shell. On Debian/Ubuntu install `git build-essential zlib1g-dev python3-venv` through your
package manager. macOS users need the Xcode command line tools, Python 3, and
a recent GNU Make (for example `gmake` from Homebrew). Windows users can use
WSL with Ubuntu.

```sh
make bootstrap  # pinned ATasm source build; Python CPU-test environment
make            # build/wall-pong.xex
make test       # execute the actual assembled machine code on a simulated 6502
make mac65      # build/WALLPONG.LST: numbered ATASCII source for MAC/65
```

Bootstrap pins ATasm 1.30 to commit
`46be895a4312205dbcc4cf7a4a6721d72219d711`, checks the source revision, and
builds it into ignored `.tools/`. Its build log is `.tools/build.log`.
Tests use `py65==1.2.0` in ignored `.venv/`. No ROMs are downloaded.
Bootstrap can be rerun. Network access is needed for GitHub and PyPI only.

An existing ATasm installation can be selected with
`make ATASM=/path/to/atasm`. Use `make test PYTHON=/path/to/python` when using
an existing Python environment containing py65. `make clean` removes generated
build outputs and retains downloaded tools.

## Load the game

Load `build/wall-pong.xex` using Atari DOS, FujiNet, SIO2SD, or an emulator's
binary executable loader. Select an **800XL with 64 KB** and **disable BASIC**
(hold Option during boot on hardware). This is an XEX executable, not a boot
disk or cartridge image. Map an emulator joystick to port 1.

[Atari800](https://atari800.github.io/) and
[Altirra](https://www.virtualdub.org/altirra.html) are suitable emulators.
Supply legally obtained ROMs if your emulator requires them.
The game updates once per OS vertical blank, matching the C version; NTSC
therefore runs somewhat faster than PAL.

## Source for the original MAC/65

`src/wallpong.m65` uses standard 6502 instructions and MAC/65 directives;
ATasm provides the modern cross-build. `make mac65` exports the same source
with line numbers and Atari `$9B` line endings in `build/WALLPONG.LST`.
Transfer that file without translating its line endings, then use MAC/65's
ENTER command, for example `E#D:WALLPONG.LST`. Assemble to disk with
`ASM ,,#D:WALLPONG.XEX` so assembly does not overwrite the editor source.
The source includes the `$02E0` run vector. Do not RUN the listing as BASIC.
Native MAC/65 import/assembly is provided for use on the Atari but has not
been tested with the original cartridge in this environment.

## Implementation

- `src/wallpong.m65`: game, bitmap renderer, display list setup, input, audio,
  and loader return. Positions and velocities use the C version's 12.4 fixed
  point arithmetic, including subpixel collision reflection.
- `$2000–$2756`: assembled code, state, and row-address tables.
- `$5000–$5067`: generated display list, within one 1 KB boundary.
- `$6000–$6EFF`: generated 160×96, four-color ANTIC mode D bitmap, within one
  4 KB bank so the LMS address counter does not wrap.
- `$80–$83`: temporary zero page, saved on entry and restored on exit.
- OS VBI remains active for joystick shadows, keyboard, colors, and frame
  timing. No custom interrupt handler is installed. Sound uses POKEY channel 1.

## Validation and limits

`make test` runs seven tests against the built XEX using py65. They cover
initialization, serve/reset button edges, paddle clamping, wall reflections,
all paddle impact bands, acceleration, score saturation, misses, three-life
game over, 4,000 randomized states, and a 12,000-frame assisted rally.
Renderer tests check the display list, boundaries, paddle pixels, and score
glyphs. An integration test supplies OS input shadows and clock ticks to the
actual entry point, verifies audio register writes, and checks Escape restores
the saved display and zero-page state. Representative frame code stays below
23,000 CPU cycles, excluding interrupts and ANTIC DMA.

During development an additional 10,000 randomized machine-code steps were
compared directly with the compiled original `src/game.c`; all state and event
results matched. The committed test suite has an independent Python rendition
of those rules and does not need another repository or a C compiler.

These are CPU and framebuffer tests, not complete Atari hardware emulation.
Full ANTIC/POKEY behavior, PAL/NTSC frame timing, physical joystick input, DOS
loader compatibility, and native cartridge assembly still need an emulator or
real 800XL playtest. No full-system playtest is claimed.
