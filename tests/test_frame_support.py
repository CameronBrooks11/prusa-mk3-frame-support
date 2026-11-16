"""Render the frame support and check its size, its mounting points, and the committed STL.

usage: python3 tests/test_frame_support.py [OPENSCAD]

- frame_support.scad renders as one solid, 80 x 206 x 22.2 mm from z = 0, with
  warnings treated as errors.
- Each mounting point the README lists is open: a probe a little narrower than
  the slot or hole, through where it should be, doesn't touch the part.
- frame_support.stl is the same part as the source renders: the same size and
  the same volume, to within 0.01 %. OpenSCAD versions mesh it differently, so
  the triangles aren't compared.
"""

import os
import re
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAD = os.path.join(ROOT, "frame_support.scad")
STL = os.path.join(ROOT, "frame_support.stl")


def triangles(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:300]:
        vs = [tuple(map(float, l.split()[1:4])) for l in data.decode().splitlines() if l.strip().startswith("vertex")]
        return [vs[i:i + 3] for i in range(0, len(vs), 3)]
    (n,) = struct.unpack_from("<I", data, 80)
    out = []
    for i in range(n):
        v = struct.unpack_from("<9f", data, 84 + i * 50 + 12)
        out.append([v[0:3], v[3:6], v[6:9]])
    return out


def measure(path):
    tris = triangles(path)
    parent = {}

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for t in tris:
        for c in t:
            parent.setdefault(c, c)
        root = find(t[0])
        for c in t[1:]:
            parent[find(c)] = root
    pts = list(parent)
    lo = [min(p[i] for p in pts) for i in range(3)]
    size = [max(p[i] for p in pts) - lo[i] for i in range(3)]
    volume = sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                  + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6 for a, b, c in tris)
    return len({find(v) for v in parent}), lo, size, volume


def variables():
    """The source's top-level numbers and number lists."""
    out = {}
    for line in open(SCAD):
        m = re.match(r"(\w+) = (\[[^\]]*\]|[-\d.]+);", line)
        if m:
            out[m.group(1)] = eval(m.group(2))
    return out


results = []


def check(label, ok, got):
    results.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {got}")


def main():
    openscad = sys.argv[1] if len(sys.argv) > 1 else "openscad"
    v = variables()
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "part.stl")
        r = subprocess.run([openscad, "--hardwarnings", "--export-format", "binstl", "-o", out, SCAD],
                           capture_output=True, text=True)
        bad = [l for l in r.stderr.splitlines() if "WARNING" in l or "ERROR" in l]
        if r.returncode != 0 or bad:
            check("renders", False, bad[:1] or f"exit {r.returncode}")
            sys.exit(1)
        solids, lo, size, volume = measure(out)
        want = (v["w_base"], v["length"], v["h"])
        check("one solid of the documented size", solids == 1 and all(abs(a - b) < 0.01 for a, b in zip(size, want))
              and all(abs(x) < 0.01 for x in lo),
              f"{solids} solid(s), {' x '.join(f'{s:.2f}' for s in size)} mm from z = {lo[2]:.2f}")

        # Probes through each mounting point, 0.4 mm narrower than the opening.
        probes = [(f"slot at x = {x}", f"translate([{x}, {v['slot_end']} / 2, -1]) cylinder(d={v['slot_w']} - 0.4, h={v['floor_t']} + 2, $fn=24);")
                  for x in v["slot_x"]]
        probes += [(f"side hole at y = {y}", f"translate([-1, {y}, {v['hole_z']}]) rotate([0, 90, 0]) cylinder(d={v['hole_d']} - 0.4, h={v['wall']} + 2, $fn=24);")
                   for y in v["hole_y"]]
        for label, probe in probes:
            path = os.path.join(tmp, "probe.scad")
            with open(path, "w") as f:
                f.write(f"intersection() {{ import(\"{out}\"); {probe} }}\n")
            r = subprocess.run([openscad, "--export-format", "binstl", "-o", os.path.join(tmp, "p.stl"), path],
                               capture_output=True, text=True)
            empty = r.returncode != 0 and "top level object is empty" in r.stderr
            check(f"{label} is open", empty, "clear" if empty else "the probe hits the part")

        c_solids, c_lo, c_size, c_volume = measure(STL)
        same = c_solids == 1 and all(abs(a - b) < 0.01 for a, b in zip(c_size, size)) \
            and abs(c_volume - volume) <= 1e-4 * volume
        check("frame_support.stl matches the source", same,
              f"{' x '.join(f'{s:.2f}' for s in c_size)} mm, {c_volume:.1f} mm3 against {volume:.1f} mm3")

    print(f"{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


main()
