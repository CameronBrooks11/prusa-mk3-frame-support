// Printable Prusa MK3(S+) frame support.
// Flat face on the bed: X = width, Y = length, Z = height.

length = 206; // overall length
w_base = 80; // width at the slotted end
w_tip = 40; // width at the far end
taper_start = 35; // straight section before the taper
h = 22.2; // overall height (sheet-metal flange height)
floor_t = 5; // floor thickness
wall = 5; // side, tapered and rib wall thickness
side_wall = 3; // short straight wall at the wide end
rib_y = [30, 63, 101, 136, 171]; // rib start positions
divider_x = 41; // start of the rib splitting the first pocket
pocket_r = 10; // pocket corner radius
floor_chamfer = 4; // 45 deg chamfer where pocket floors meet the walls

slot_w = 3.3; // M3 clearance
slot_x = [14, 68];
slot_end = 7.55; // centre of the slot's round end
slot_chamfer = 0.5; // bottom-edge chamfer against elephant's foot

hole_d = 4.5; // M4 clearance
hole_y = [78, 195];
hole_z = 11.2;
head_d = 16; // screw head clearance
head_depth = 10; // measured from the inner wall face

$fn = 64;
e = pocket_r + 1; // extension past the ends so open pockets stay square there

function taper_x(y) = w_base - (w_base - w_tip) * (y - taper_start) / (length - taper_start);

module outline(ext = 0)
  polygon(
    [
      [0, -ext],
      [w_base, -ext],
      [w_base, taper_start],
      [taper_x(length + ext), length + ext],
      [0, length + ext],
    ]
  );

module cavity()
  union() {
    offset(delta=-wall) outline(ext=2 * e);
    translate([wall, -e]) square([w_base - side_wall - wall, taper_start + e]);
  }

// One convex pocket outline between y0 and y1, clipped to x0..x1.
module pocket_2d(y0, y1, x0 = -1, x1 = w_base + 1)
  offset(r=pocket_r) offset(delta=-pocket_r)
      intersection() {
        cavity();
        translate([x0, y0]) square([x1 - x0, y1 - y0]);
      }

// Each outline is convex, so a hull from the shrunk floor outline up to the
// full outline gives a 45 deg chamfer at the floor edges.
module chamfered_pocket()
  hull() {
    translate([0, 0, floor_t]) linear_extrude(0.01) offset(delta=-floor_chamfer) children();
    translate([0, 0, floor_t + floor_chamfer]) linear_extrude(h) children();
  }

module pockets() {
  starts = [for (y = rib_y) y + wall];
  ends = concat([for (i = [1:len(rib_y) - 1]) rib_y[i]], [length + e]);
  // first pocket, split by the divider rib
  chamfered_pocket() pocket_2d(-e, rib_y[0], x1=divider_x);
  chamfered_pocket() pocket_2d(-e, rib_y[0], x0=divider_x + wall);
  for (i = [0:len(starts) - 1])
    chamfered_pocket() pocket_2d(starts[i], ends[i]);
}

module slot_2d(x)
  hull() {
    translate([x, slot_end]) circle(d=slot_w);
    translate([x, -1]) circle(d=slot_w);
  }

difference() {
  linear_extrude(h) outline();

  pockets();

  for (x = slot_x) {
    translate([0, 0, -1]) linear_extrude(floor_t + 2) slot_2d(x);
    hull() {
      translate([0, 0, -1]) linear_extrude(0.01) offset(delta=slot_chamfer + 1) slot_2d(x);
      translate([0, 0, slot_chamfer]) linear_extrude(0.01) slot_2d(x);
    }
  }

  for (y = hole_y)
    translate([0, y, hole_z]) rotate([0, 90, 0]) {
        translate([0, 0, -1]) cylinder(d=hole_d, h=wall + 2);
        translate([0, 0, wall]) cylinder(d=head_d, h=head_depth);
      }
}
