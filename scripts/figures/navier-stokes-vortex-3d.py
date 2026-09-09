"""Three snapshots of the blow-up vortex core, in 3D.

Not a copy of the figure in OpenAI's paper: the threads here are trajectories
integrated from the leading-order velocity field the paper describes in
cylindrical coordinates — radial inflow, azimuthal spin-up, and axial outflow
on opposite sides of a dividing plane near z = 0 (a Burgers-type vortex, which
is the same mechanism written as an exact solution).

    u_r = -a r
    u_z =  2 a z
    u_th = (G / r) (1 - exp(-a r^2 / 2 nu))     # spin-up as r decreases

Between panels the core is scaled by the paper's own exponents, radius
~ tau^(1/2) and height ~ tau^(1/2 - h) with h < 1/100. At the true h the two
would be indistinguishable, so the axial stretching is exaggerated here, as it
is in the paper's schematic.

Usage: python scripts/figures/navier-stokes-vortex-3d.py
Writes: public/blog/navier-stokes-vortex-3d.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BG = "#1a1a24"
TEAL = "#2dd4bf"
AMBER = "#f59e0b"
MUTED = "#94a3b8"
TEXT = "#e2e8f0"

A, G, NU = 1.0, 1.0, 0.02


def trajectory(r0, th0, z0, steps=2600, dt=0.0016, zcap=2.6):
    """Integrate one fluid thread with RK2 in cylindrical coordinates."""
    r, th, z = r0, th0, z0
    out = []
    for _ in range(steps):
        if r < 0.012 or abs(z) > zcap:
            break
        def vel(r, z):
            ur = -A * r
            uz = 2.0 * A * z
            uth = (G / max(r, 1e-3)) * (1.0 - np.exp(-A * r * r / (2.0 * NU)))
            return ur, uth, uz
        ur, uth, uz = vel(r, z)
        rm, thm, zm = r + 0.5 * dt * ur, th + 0.5 * dt * uth / max(r, 1e-3), z + 0.5 * dt * uz
        ur2, uth2, uz2 = vel(max(rm, 1e-3), zm)
        r += dt * ur2
        th += dt * uth2 / max(rm, 1e-3)
        z += dt * uz2
        out.append((r * np.cos(th), r * np.sin(th), z))
    return np.array(out) if out else np.empty((0, 3))


def threads():
    """Two families: swirl threads near the mid-plane, axial threads that leave."""
    swirl, axial = [], []
    # swirl family: enters at the outer radius at a range of heights, so the
    # inward spiral reads as a spiral and not as a flat pancake
    for k in range(18):
        th0 = 2 * np.pi * k / 18
        z0 = 0.10 * np.cos(2 * np.pi * k / 18 * 2.0)
        swirl.append(trajectory(1.0, th0, z0, steps=2300, zcap=0.9))
    # axial family: fewer threads, so the core stays legible rather than
    # becoming a solid cocoon
    for k in range(7):
        th0 = 2 * np.pi * k / 7 + 0.19
        for z0 in (0.20, -0.20):
            axial.append(trajectory(0.80, th0, z0))
    return swirl, axial


def draw(ax, swirl, axial, lr, lz, label, faint):
    for tr in swirl:
        if len(tr) < 2:
            continue
        ax.plot(tr[:, 0] * lr, tr[:, 1] * lr, tr[:, 2] * lz,
                color=TEAL, lw=1.15, alpha=0.9, solid_capstyle="round")
    for tr in axial:
        if len(tr) < 2:
            continue
        ax.plot(tr[:, 0] * lr, tr[:, 1] * lr, tr[:, 2] * lz,
                color=AMBER, lw=1.0, alpha=0.6, solid_capstyle="round")
    # the axis the core collapses onto
    ax.plot([0, 0], [0, 0], [-2.6, 2.6], color=MUTED, lw=0.7, ls=(0, (2, 3)), alpha=0.55)
    # dividing plane near z = 0, drawn as a faint ring
    ph = np.linspace(0, 2 * np.pi, 120)
    ax.plot(np.cos(ph) * lr * 1.06, np.sin(ph) * lr * 1.06, np.zeros_like(ph),
            color=MUTED, lw=0.6, alpha=0.35)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.set_zlim(-2.7, 2.7)
    ax.set_box_aspect((1, 1, 2.0))
    ax.set_axis_off()
    ax.set_facecolor(BG)
    ax.view_init(elev=14, azim=-62)
    ax.text2D(0.5, 0.045, label, transform=ax.transAxes, ha="center",
              color=TEXT, fontsize=17, fontweight="bold")
    ax.text2D(0.5, -0.005, faint, transform=ax.transAxes, ha="center",
              color=MUTED, fontsize=13)


def main():
    swirl, axial = threads()
    fig = plt.figure(figsize=(12.0, 5.4), dpi=100, facecolor=BG)
    # tau = time left; radius ~ tau^(1/2), height ~ tau^(1/2-h), h exaggerated
    h_exag = 0.26
    for i, tau in enumerate((1.0, 0.45, 0.16)):
        lr = tau ** 0.5
        lz = tau ** (0.5 - h_exag)
        ax = fig.add_subplot(1, 3, i + 1, projection="3d", computed_zorder=False)
        draw(ax, swirl, axial, lr, lz, ["t₁", "t₂", "t₃ → 1"][i],
             f"radius x{lr:.2f}   ·   height x{lz:.2f}")
    for x in (0.355, 0.655):
        fig.text(x, 0.52, "→", color=MUTED, fontsize=22, ha="center", va="center")
    fig.text(0.035, 0.955, "teal", color=TEAL, fontsize=14, fontweight="bold")
    fig.text(0.075, 0.955, "· threads spiralling inward, spinning up as they go",
             color=MUTED, fontsize=14)
    fig.text(0.035, 0.905, "amber", color=AMBER, fontsize=14, fontweight="bold")
    fig.text(0.088, 0.905, "· the same fluid leaving along the axis",
             color=MUTED, fontsize=14)
    fig.text(0.965, 0.955, "the core thins faster than it shortens",
             color=MUTED, fontsize=14, ha="right")
    fig.text(0.965, 0.905, "above and below the mid-plane",
             color=MUTED, fontsize=14, ha="right")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.955, bottom=0.075, wspace=0.02)
    out = "public/blog/navier-stokes-vortex-3d.png"
    fig.savefig(out, facecolor=BG, edgecolor="none")
    print("wrote", out)


if __name__ == "__main__":
    main()
