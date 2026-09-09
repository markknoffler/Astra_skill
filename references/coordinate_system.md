# Coordinate System & Grid Overlay Specification

## Logical Points vs. Physical Pixels
On modern high-DPI (Retina) displays, the operating system distinguishes between **Physical Pixels** and **Logical Points**:
- **Physical Resolution**: The actual hardware pixel matrix (e.g., 2940 x 1912).
- **Logical Resolution**: The coordinate space used by the OS for mouse positioning, window layout, and UI rendering (e.g., 1470 x 956).
- **Scale Factor**: Typically `2.0x` on Apple Retina displays.

### The Astra Alignment Rule
The overlay grid produced by `screen_daemon.py` is **calibrated directly in logical screen points**:
- A grid label displaying `(500, 300)` represents Logical X = 500, Logical Y = 300.
- When `mouse_action.py click --x 500 --y 300` is called, the OS clicks at the exact target.
- No manual scaling math is required by the agent.

---

## Grid Visual Design

The grid is engineered to be **subtle and non-intrusive**:
1. **Major Grid Lines**: Spaced every 100 logical points in faint translucent cyan (RGBA `0, 200, 255, 45`).
2. **Minor Grid Lines**: Spaced every 50 logical points in faint white (RGBA `255, 255, 255, 20`).
3. **Coordinate Chips**: Small dark pills at intersections with clear coordinates `X,Y` in high-contrast cyan font.
4. **Top & Left Rulers**: Fixed coordinate tick bars along the top edge (`X:0`, `X:100`, `X:200`...) and left edge (`Y:0`, `Y:100`, `Y:200`...).

```
   X:0       X:100       X:200       X:300       X:400
  +-----------+-----------+-----------+-----------+
Y:0| (0,0)     |           |           |           |
  |           |           |           |           |
Y:100---------+(100,100)---+(200,100)---+(300,100)--+
  |           |           |   [BUTTON]|           |
  |           |           |   (x=250, |           |
Y:200---------+(100,200)---+---y=150)---+-----------+
```

---

## Target Coordinate Calculation Procedure

When locating an element:
1. Inspect the bounding box formed by the nearest grid lines.
2. If a button lies halfway between `X:200` and `X:300`, its center X is approximately `250`.
3. If the button lies between `Y:100` and `Y:200` (e.g. at the 50% mark), its center Y is approximately `150`.
4. Invoke `mouse_action.py click --x 250 --y 150`.
