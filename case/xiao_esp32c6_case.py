"""Two-part case for the Seeed Studio XIAO ESP32C6 (without pin headers) with an SMA antenna.

Base: the board sits on supports, USB-C in a cutout, keyhole for wall mounting.
Lid: reset/boot holes, LED windows, diagonal vents, snaps into the base.
The SMA bulkhead connector sits in the back wall.

Coordinates: board centered in X, USB-C points to +Y. Dimensions in mm.

    pip install numpy trimesh manifold3d
    python xiao_esp32c6_case.py      # writes the two STL files next to this script
"""
import math
import numpy as np, trimesh
from manifold3d import Manifold, CrossSection, JoinType

FN = 64

# --- Board -------------------------------------------------------------
PCB_W, PCB_L, PCB_T = 17.8, 21.0, 1.2
USB_W, USB_H = 8.94, 3.26      # USB-C connector
USB_OVER = 1.75                # connector overhang past the board edge
TOP_CLR = 6.6                  # space above the board: room for the SMA nut and pigtail
BOT_CLR = 3.0                  # space below the board (battery/wire pads, screw head)

# Parts on the top side, (x from the left, y from the USB edge), top view with USB up
BTN_R = (2.3, 1.3)
BTN_B = (15.5, 1.3)
LED_CHG = (2.9, 4.7)
LED_USR = (14.9, 4.7)

# --- Case -------------------------------------------------------------
WALL, FLOOR, ROOF = 1.8, 1.6, 1.6
CH_X = 2.2                     # wire channel left/right of the board
CH_BACK = 11.6                 # back: room for the SMA connector and pigtail
USB_CLR = 0.3                  # total clearance of the USB opening (clamps the connector)
POCKET_CLR, POCKET_T = 0.15, 0.8   # pocket around the board
SMA_D = 6.6                    # hole for the SMA bulkhead connector (1/4"-36)
GAP_USB = 0.3                  # board -> front inner wall
R_OUT = 5.0                    # outer corner radius
LIP_T, LIP_H, LIP_CLR = 1.0, 2.0, 0.15

IN_W = PCB_W + 2 * CH_X
IN_L = PCB_L + GAP_USB + CH_BACK
OUT_W, OUT_L = IN_W + 2 * WALL, IN_L + 2 * WALL
Y_IN_FRONT = IN_L / 2          # front inner wall (USB)
PCB_Y1 = Y_IN_FRONT - GAP_USB  # USB edge of the board
PCB_Y0 = PCB_Y1 - PCB_L
PCB_X0 = -PCB_W / 2

Z_PCB_BOT = FLOOR + BOT_CLR
Z_PCB_TOP = Z_PCB_BOT + PCB_T
Z_USB = Z_PCB_TOP + USB_H / 2  # connector center = parting plane
Z_SPLIT = Z_USB
Z_IN_TOP = Z_PCB_TOP + TOP_CLR
Z_TOP = Z_IN_TOP + ROOF

# Snaps: center of the nub SNAP_IN inside the inner wall, radius SNAP_R
# -> reaches SNAP_R - SNAP_IN (0.25 mm) into the wall, groove in the base slightly larger
SNAP_Y0, SNAP_Y1 = -6.4, 2.6
SNAP_R, SNAP_IN, SNAP_GROOVE_R = 0.5, 0.25, 0.6
SNAP_Z = Z_SPLIT - 1.1
VENT_Y = PCB_Y1 - 12.0           # vents above the middle of the board


def pcb(xy):
    """Board coordinate (x from the left, y from the USB edge) -> case."""
    return PCB_X0 + xy[0], PCB_Y1 - xy[1]


def rrect(w, l, r):
    r = max(min(r, w / 2 - 0.01, l / 2 - 0.01), 0.01)
    return CrossSection.square((w - 2 * r, l - 2 * r), center=True).offset(r, JoinType.Round, circular_segments=FN)


def slab(w, l, r, z0, h):
    return Manifold.extrude(rrect(w, l, r), h).translate((0, 0, z0))


def rounded_block(w, l, r, z0, h, ebot=0.0, etop=0.0):
    """Rounded box with chamfered bottom and rounded top edge (via hull)."""
    parts, steps = [], 6
    for i in range(steps + 1):  # top edge: quarter circle
        a = math.pi / 2 * i / steps
        inset = etop * (1 - math.cos(a))
        z = z0 + h - etop + etop * math.sin(a) if etop else z0 + h
        parts.append(slab(w - 2 * inset, l - 2 * inset, r - inset, z - 0.01, 0.01))
    parts.append(slab(w - 2 * ebot, l - 2 * ebot, r - ebot, z0, 0.01))
    parts.append(slab(w, l, r, z0 + ebot, 0.01))
    return Manifold.batch_hull(parts)


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl_z(d, z0, h, x, y, d2=None, fn=FN):
    return Manifold.cylinder(h, d / 2, (d2 if d2 else d) / 2, fn).translate((x, y, z0))


def cyl_y(d, y0, length, x, z, fn=FN):
    return Manifold.cylinder(length, d / 2, d / 2, fn).rotate((-90, 0, 0)).translate((x, y0, z))


def stadium_y(w, h, y0, length, x, z):
    """Rounded slot through a wall in Y direction."""
    r = h / 2
    cs = CrossSection.square((w - h, 0.001), center=True).offset(r, JoinType.Round, circular_segments=FN)
    return Manifold.extrude(cs, length).rotate((-90, 0, 0)).translate((x, y0, z))


# ===================== Base ==========================================
def make_base():
    shell = rounded_block(OUT_W, OUT_L, R_OUT, 0, Z_SPLIT, ebot=0.6)
    cavity = slab(IN_W, IN_L, R_OUT - WALL, FLOOR, Z_SPLIT)
    body = shell - cavity

    # Supports under the board: corners on the USB side (next to the connector pins),
    # bar on the antenna side (only silkscreen on the bottom there)
    for x0, x1 in ((0.0, 3.2), (PCB_W - 3.2, PCB_W)):
        body += box(PCB_X0 + x0, PCB_Y1 - 1.6, FLOOR - 0.01, PCB_X0 + x1, PCB_Y1, Z_PCB_BOT)
    body += box(PCB_X0 + 3.0, PCB_Y0, FLOOR - 0.01, PCB_X0 + PCB_W - 3.0, PCB_Y0 + 1.4, Z_PCB_BOT)
    # Pocket: tight frame around the board (the case wall holds the front), up to just below its top
    w_in, l_in = PCB_W + 2 * POCKET_CLR, PCB_L + 2 * POCKET_CLR
    yc = (PCB_Y0 + PCB_Y1) / 2
    frame = (slab(w_in + 2 * POCKET_T, l_in + 2 * POCKET_T, 1.0 + POCKET_T, FLOOR - 0.01, Z_PCB_TOP - 0.3 - FLOOR)
             - slab(w_in, l_in, 1.0, FLOOR - 1, Z_PCB_TOP + 1)).translate((0, yc, 0))
    frame -= box(-OUT_W, PCB_Y1 - 1.0, -1, OUT_W, OUT_L, Z_TOP)
    body += frame

    # USB-C: cutout open to the top + outer recess for the plug
    y_wall = Y_IN_FRONT - 0.1
    body -= stadium_y(USB_W + USB_CLR, USB_H + USB_CLR, y_wall, WALL + 1, 0, Z_USB)
    body -= box(-(USB_W + USB_CLR) / 2, y_wall, Z_USB, (USB_W + USB_CLR) / 2, y_wall + WALL + 1, Z_SPLIT + 1)
    body -= stadium_y(12.6, 7.0, OUT_L / 2 - 0.8, 2, 0, Z_USB)

    # SMA connector in the back: lower half of the hole
    body -= cyl_y(SMA_D, -OUT_L / 2 - 1, WALL + 2, 0, Z_SPLIT)

    # Vents low on the sides (below the board)
    for sx in (-1, 1):
        x0 = OUT_W / 2 - WALL - 0.5 if sx > 0 else -OUT_W / 2 - 1
        for i in range(4):
            y = -7.0 + i * 4.2
            # slot 3.0 long (Y) x 1.2 high (Z) through the side wall
            slot = Manifold.extrude(rrect(1.2, 3.0, 0.6), WALL + 1.5).rotate((0, 90, 0))
            body -= slot.translate((x0, y, FLOOR + 1.5))

    # Grooves for the snaps of the lid
    for sx in (-1, 1):
        body -= cyl_y(2 * SNAP_GROOVE_R, SNAP_Y0 + 0.2, SNAP_Y1 - SNAP_Y0 - 0.4, sx * (IN_W / 2 - SNAP_IN), SNAP_Z)

    # Keyhole in the floor (3-3.5 mm screw, head up to 7 mm)
    kx, ky = 0, -2.0
    body -= cyl_z(7.4, -1, FLOOR + 2, kx, ky + 3.0)
    body -= box(kx - 1.8, ky - 4.0, -1, kx + 1.8, ky + 3.0, FLOOR + 1)
    body -= cyl_z(3.6, -1, FLOOR + 2, kx, ky - 4.0)
    return body


# ===================== Lid =============================================
def make_lid():
    h = Z_TOP - Z_SPLIT
    shell = rounded_block(OUT_W, OUT_L, R_OUT, Z_SPLIT, h, etop=1.6)
    cavity = slab(IN_W, IN_L, R_OUT - WALL, Z_SPLIT - 1, Z_IN_TOP - Z_SPLIT + 1)
    lid = shell - cavity

    # Lip that reaches into the base (not on the USB side: the board is too close there)
    lip_o = slab(IN_W - 2 * LIP_CLR, IN_L - 2 * LIP_CLR, R_OUT - WALL - LIP_CLR, Z_SPLIT - LIP_H, LIP_H + 0.5)
    lip_i = slab(IN_W - 2 * (LIP_CLR + LIP_T), IN_L - 2 * (LIP_CLR + LIP_T),
                 R_OUT - WALL - LIP_CLR - LIP_T, Z_SPLIT - LIP_H - 1, LIP_H + 5)
    # Ring above the parting plane: joins the lip and the lid wall
    bridge = slab(IN_W + 0.2, IN_L + 0.2, R_OUT - WALL + 0.1, Z_SPLIT + 0.05, 1.5)
    lip = (lip_o + bridge) - lip_i - box(-OUT_W, Y_IN_FRONT - 4.0, Z_SPLIT - LIP_H - 2, OUT_W, OUT_L, Z_SPLIT + 2)
    # room in the back for the hex of the SMA connector
    lip -= box(-6.0, -OUT_L, Z_SPLIT - LIP_H - 2, 6.0, -IN_L / 2 + 3.0, Z_SPLIT + 2)
    # Snap tabs on the long sides: two slits make the lip springy there,
    # a round nub snaps into the groove in the base
    for sx in (-1, 1):
        xw = sx * IN_W / 2
        for yc in (SNAP_Y0, SNAP_Y1):
            lip -= box(xw - 2.0, yc - 0.3, Z_SPLIT - LIP_H - 1, xw + 2.0, yc + 0.3, Z_SPLIT + 0.04)
        lip += cyl_y(2 * SNAP_R, SNAP_Y0 + 0.5, SNAP_Y1 - SNAP_Y0 - 1.0, xw - sx * SNAP_IN, SNAP_Z)
    lid += lip

    # USB-C: upper half of the cutout + recess
    y_wall = Y_IN_FRONT - 0.1
    lid -= stadium_y(USB_W + USB_CLR, USB_H + USB_CLR, y_wall, WALL + 1, 0, Z_USB)
    lid -= stadium_y(12.6, 7.0, OUT_L / 2 - 0.8, 2, 0, Z_USB)

    # SMA connector in the back: upper half of the hole
    lid -= cyl_y(SMA_D, -OUT_L / 2 - 1, WALL + 2, 0, Z_SPLIT)

    # Hold-downs: two pins press the rear board corners down
    # (no pads and no antenna connector on top there)
    for x0, x1 in ((0.2, 1.3), (PCB_W - 1.3, PCB_W - 0.2)):
        lid += box(PCB_X0 + x0, PCB_Y1 - 20.8, Z_PCB_TOP + 0.05, PCB_X0 + x1, PCB_Y1 - 19.9, Z_IN_TOP + 0.01)

    # Reset/Boot: holes for a paper clip, countersunk outside
    for p in (BTN_R, BTN_B):
        x, y = pcb(p)
        lid -= cyl_z(1.7, Z_IN_TOP - 0.5, ROOF + 1, x, y)
        lid -= cyl_z(1.7, Z_TOP - 0.7, 0.71, x, y, d2=3.1)
    # LED windows
    for p in (LED_CHG, LED_USR):
        x, y = pcb(p)
        lid -= cyl_z(1.3, Z_IN_TOP - 0.5, ROOF + 1, x, y)
        lid -= cyl_z(1.3, Z_TOP - 0.5, 0.51, x, y, d2=2.3)

    # Diagonal vents in the lid
    win = rrect(IN_W - 3.0, 10.0, 2.5)
    win_m = Manifold.extrude(win, ROOF + 2).translate((0, VENT_Y, Z_IN_TOP - 0.5))
    slots = Manifold()
    for i in range(-8, 9):
        s = Manifold.cube((1.3, 30, ROOF + 2), center=True).rotate((0, 0, 45))
        slots += s.translate((i * 2.9, VENT_Y, Z_IN_TOP + ROOF / 2 + 0.25))
    lid -= (slots ^ win_m)
    return lid


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))


def board_dummy():
    """Board for the collision check (corners r=1, connector rounded like USB-C)."""
    e = 0.01  # the board rests on the supports: contact, no overlap
    p = slab(PCB_W, PCB_L, 1.0, Z_PCB_BOT + e, PCB_T - 2 * e).translate((0, (PCB_Y0 + PCB_Y1) / 2, 0))
    p += stadium_y(USB_W, USB_H, PCB_Y1 - 6.3, 6.3 + USB_OVER, 0, Z_USB)
    p += box(PCB_X0 + 2.0, PCB_Y0 + 3.0, Z_PCB_TOP, PCB_X0 + PCB_W - 2.0, PCB_Y1 - 6.5, Z_PCB_TOP + 2.2)  # shield
    return p


def sma_dummy():
    """SMA bulkhead connector: thread through the wall, 8 mm hex + body inside, nut outside."""
    y_out = -OUT_L / 2
    s = cyl_y(6.35, y_out - 4, WALL + 8, 0, Z_SPLIT)                                   # thread
    hexi = Manifold.cylinder(2.0, 8 / math.sqrt(3), 8 / math.sqrt(3), 6).rotate((-90, 0, 0))
    s += hexi.translate((0, y_out + WALL + 0.05, Z_SPLIT))                             # hex inside
    s += cyl_y(4.5, y_out + WALL + 2, 7.0, 0, Z_SPLIT)                                  # crimp/cable
    s += hexi.translate((0, y_out - 2.05, Z_SPLIT))                                    # nut outside
    return s


if __name__ == "__main__":
    import os
    out = os.path.dirname(os.path.abspath(__file__))
    u, d = make_base(), make_lid()
    # flip the lid for printing (roof on the bed)
    d_print = d.rotate((180, 0, 0)).translate((0, 0, Z_TOP))
    to_trimesh(u).export(f"{out}/xiao-esp32c6-case-base.stl")
    to_trimesh(d_print).export(f"{out}/xiao-esp32c6-case-lid.stl")
    pd = board_dummy()
    print(f"outside {OUT_W:.1f} x {OUT_L:.1f} x {Z_TOP:.1f} mm, parting plane at z={Z_SPLIT:.2f}")
    print("Collision board/base mm3:", round((pd ^ u).volume(), 3))
    print("Collision board/lid mm3:", round((pd ^ d).volume(), 3))
    print("Collision base/lid mm3:", round((u ^ d).volume(), 3))
    sd = sma_dummy()
    print("Collision SMA/base mm3:", round((sd ^ u).volume(), 3), " SMA/lid:", round((sd ^ d).volume(), 3),
          " SMA/board:", round((sd ^ pd).volume(), 3))
    # Side play of the board in the pocket and gap of the hold-downs (should collide)
    print("Board shifted 0.2 mm sideways -> collision:", round((pd.translate((0.2, 0, 0)) ^ u).volume(), 3),
          " backwards:", round((pd.translate((0, -0.2, 0)) ^ u).volume(), 3),
          " lifted 0.1 mm:", round((pd.translate((0, 0, 0.1)) ^ d).volume(), 3))
    print("watertight:", to_trimesh(u).is_watertight, to_trimesh(d_print).is_watertight)
