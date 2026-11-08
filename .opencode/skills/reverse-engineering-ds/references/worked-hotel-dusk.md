# Worked example: Hotel Dusk — intro text animation

**Illustrative only.** The reusable rules live in `runtime-debugging.md`
(Technique 1). Coordinates/addresses are game-specific.

Touch point on the bottom (touch) screen: `(125, 100)`.

```
savestate_load(0)         # title screen (PRESS START)
debug_connect("arm9")     # CPU halts
input_touch(125, 100)     # arm START touch
emu_step_frame(60)        # ~1 s; repeat 60 at a time
#  the text appears only around ~300 frames (~5 s) after the touch
screen_capture("both")    # freeze and show the text animation
```

Observed (~frame 300): top `FRIDAY DECEMBER 1972…`, bottom `NEW YORK 5:07 P…`
(rotated 90°, book mode). That frame is now reproducible from the savestate for
VRAM dumps and disassembly.
