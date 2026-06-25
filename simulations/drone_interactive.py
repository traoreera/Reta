"""
RETA — Simulation Interactive Drone 3D
=======================================
Un seul drone que vous pilotez. Activez/désactivez RETA pour voir la différence.

Pilotage :
  ← → : roulis (roll gauche/droite)
  ↑ ↓ : tangage (pitch avant/arrière)
  A / D : lacet (yaw)
  W / S : monter / descendre
  ESPACE : activer / désactiver RETA
  G : couper le GPS (simule jamming)
  R : réinitialiser tout

Sliders (en bas) :
  Vent     : force d'une perturbation latérale continue
  Biais    : vitesse de dérive thermique du gyroscope
  GPS Hz   : fréquence des corrections GPS
  Bruit    : amplitude du bruit gyro
"""

import numpy as np
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as anim
from matplotlib.widgets import Slider, Button
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3DCollection
import matplotlib.gridspec as gridspec

rng = np.random.default_rng(0)

# ─── Constantes ───────────────────────────────────────────────────────────────
DT       = 0.05          # pas de simulation [s]
G        = 9.81          # gravité [m/s²]
Y_MAX    = 20.0          # seuil RETA [°]
E_REF    = Y_MAX / 2.0
TRAIL_LEN = 120          # longueur de la trajectoire affichée
HIST_LEN  = 300          # points d'historique des courbes

# ─── État de la simulation ────────────────────────────────────────────────────
class Sim:
    def __init__(self):
        self.reset()

    def reset(self):
        self.t       = 0.0
        self.phi     = np.zeros(3)       # roll, pitch, yaw [°]
        self.pos     = np.array([0.,0.,5.])  # x, y, z [m]
        self.vel     = np.zeros(3)

        # Biais gyro vrai (°/s) — dérive thermique
        self.b_true  = np.zeros(3)
        self.b_dot   = np.array([0.04, 0.05, 0.03])  # vitesse de dérive init

        # Kalman par axe : état [phi_est, b_est], P
        self.x_k     = [np.zeros(2) for _ in range(3)]
        self.P_k     = [np.diag([1.0, 0.01]) for _ in range(3)]
        self.Q_b     = np.array([2e-4, 2e-4, 2e-4])  # adaptatif v1.3

        # PI
        self.Kp      = np.array([6.0, 6.0, 3.0])
        self.Ki      = np.array([3.0, 3.0, 1.5])
        self.I_e     = np.zeros(3)
        self.t_gps   = 0.0

        # Historiques pour les courbes
        self.h_t     = []
        self.h_phi   = []
        self.h_b_true= []
        self.h_b_est = []
        self.h_bound = []
        self.trail   = []  # positions 3D

        self.ruptured = False

sim = Sim()

# ─── Contrôle clavier ─────────────────────────────────────────────────────────
keys   = set()
reta_on  = True
gps_on   = True

# ─── Physique + RETA ──────────────────────────────────────────────────────────
A_kal = np.array([[1., -DT], [0., 1.]])
H_kal = np.array([[1., 0.]])
R_GPS = 0.04
Q_ANG = 1e-5
ALPHA_Q = 0.3
Q_MIN   = 1e-8

def kalman_step(s, axis, omega_meas, phi_gps=None):
    x, P, Qb = s.x_k[axis], s.P_k[axis], s.Q_b[axis]
    # Predict
    B = np.array([DT, 0.])
    x = A_kal @ x + B * omega_meas
    P = A_kal @ P @ A_kal.T + np.diag([Q_ANG, Qb])
    nu = 0.0
    # Update GPS
    if phi_gps is not None:
        S  = float(H_kal @ P @ H_kal.T) + R_GPS
        K  = (P @ H_kal.T) / S
        nu = float(phi_gps) - float(H_kal @ x)
        x  = x + K.flatten() * nu
        P  = (np.eye(2) - np.outer(K.flatten(), H_kal)) @ P
        if reta_on:
            dr   = abs(nu) / max(s.t_gps, 0.5)
            q_i  = max((dr * DT)**2, Q_MIN)
            s.Q_b[axis] = (1-ALPHA_Q)*s.Q_b[axis] + ALPHA_Q*q_i
    s.x_k[axis] = x; s.P_k[axis] = P
    return float(x[0]), float(x[1]), nu

def physics_step(s, cmd, wind, bias_rate, noise_amp, gps_hz):
    if s.ruptured:
        return

    # Mise à jour biais thermique
    tau = 120.0
    for i in range(3):
        s.b_true[i] += bias_rate * s.b_dot[i] * (1.0 - s.b_true[i] / (s.b_dot[i]*tau)) * DT

    noise = rng.standard_normal(3) * noise_amp

    # Commande PI par axe
    u = np.zeros(3)
    for i in range(3):
        phi_est = float(s.x_k[i][0])
        e = phi_est - cmd[i]
        s.I_e[i] += e * DT
        s.I_e[i]  = np.clip(s.I_e[i], -30, 30)
        u[i] = -(s.Kp[i] * e + s.Ki[i] * s.I_e[i])

    # Physique boucle fermée : phi_true évolue selon u
    omega_true = u + s.b_true + noise
    omega_true[:2] += wind   # vent sur roll et pitch

    s.phi += omega_true * DT
    s.phi  = np.clip(s.phi, -90, 90)

    # GPS
    s.t_gps += DT
    gps_avail = gps_on and (gps_hz > 0) and (s.t_gps >= 1.0/gps_hz)
    if gps_avail:
        s.t_gps = 0.0

    for i in range(3):
        phi_gps = s.phi[i] + rng.standard_normal() * np.sqrt(R_GPS) if gps_avail else None
        omega_meas = u[i] + s.b_true[i] + noise[i]
        phi_est, b_est, nu = kalman_step(s, i, omega_meas, phi_gps)

    # Position : drone se déplace selon son inclinaison
    ax_w =  G * np.sin(np.radians(s.phi[1]))   # pitch → avance
    ay_w = -G * np.sin(np.radians(s.phi[0]))   # roll  → latéral
    s.vel[0] += ax_w * DT
    s.vel[1] += ay_w * DT
    s.vel[2] += cmd[3] * DT   # commande verticale (W/S)
    s.vel    *= 0.97           # amortissement air
    s.pos    += s.vel * DT
    s.pos[2]  = max(0.0, s.pos[2])  # sol

    s.t += DT

    # Historique
    b_est_v = np.array([float(s.x_k[i][1]) for i in range(3)])
    z = np.abs(s.b_true - b_est_v)
    zmax = max(z.max(), 1e-9)
    rem  = Y_MAX - np.abs(s.phi).max()
    bound = s.t + rem / zmax if rem > 0 and zmax > 0 else s.t

    s.h_t.append(s.t)
    s.h_phi.append(s.phi.copy())
    s.h_b_true.append(s.b_true.copy())
    s.h_b_est.append(b_est_v.copy())
    s.h_bound.append(bound)
    s.trail.append(s.pos.copy())

    if len(s.h_t) > HIST_LEN:
        s.h_t.pop(0); s.h_phi.pop(0); s.h_b_true.pop(0)
        s.h_b_est.pop(0); s.h_bound.pop(0)
    if len(s.trail) > TRAIL_LEN:
        s.trail.pop(0)

    if np.abs(s.phi).max() > Y_MAX:
        s.ruptured = True

# ─── Dessin drone 3D ──────────────────────────────────────────────────────────
def rot_matrix(roll_d, pitch_d, yaw_d):
    r, p, y = np.radians([roll_d, pitch_d, yaw_d])
    Rx = np.array([[1,0,0],[0,np.cos(r),-np.sin(r)],[0,np.sin(r),np.cos(r)]])
    Ry = np.array([[np.cos(p),0,np.sin(p)],[0,1,0],[-np.sin(p),0,np.cos(p)]])
    Rz = np.array([[np.cos(y),-np.sin(y),0],[np.sin(y),np.cos(y),0],[0,0,1]])
    return Rz @ Ry @ Rx

def draw_drone(ax, pos, phi, color, alpha=1.0, arm=0.6):
    R = rot_matrix(*phi)
    tips = []
    for ang in [45, 135, 225, 315]:
        local = arm * np.array([np.cos(np.radians(ang)),
                                np.sin(np.radians(ang)), 0.])
        world = pos + R @ local
        ax.plot([pos[0], world[0]], [pos[1], world[1]], [pos[2], world[2]],
                color=color, lw=3, alpha=alpha, solid_capstyle='round')
        tips.append(world)

        # Rotor (petit cercle)
        theta = np.linspace(0, 2*np.pi, 16)
        rv = 0.18
        cx_pts = np.array([world + R @ np.array([rv*np.cos(t), rv*np.sin(t), 0.]) for t in theta])
        ax.plot(cx_pts[:,0], cx_pts[:,1], cx_pts[:,2],
                color=color, lw=1.5, alpha=alpha*0.6)

    # Nez (indicateur direction)
    nose = pos + R @ np.array([arm*1.1, 0, 0.05])
    ax.plot([pos[0], nose[0]], [pos[1], nose[1]], [pos[2], nose[2]],
            color='white', lw=2, alpha=alpha)

    # Corps central
    ax.scatter(*pos, color=color, s=120, alpha=alpha, zorder=5)

# ─── Interface graphique ──────────────────────────────────────────────────────
plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 9), facecolor='#0a0a0a')
fig.canvas.manager.set_window_title("RETA — Simulation Interactive Drone 3D")

gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.35,
                       left=0.05, right=0.97, top=0.93, bottom=0.22)

ax3d   = fig.add_subplot(gs[:, 0], projection='3d')
ax_phi = fig.add_subplot(gs[0, 1:])
ax_b   = fig.add_subplot(gs[1, 1:])
ax_bnd = fig.add_subplot(gs[2, 1:])

ax3d.set_facecolor('#0d1117')
for ax in [ax_phi, ax_b, ax_bnd]:
    ax.set_facecolor('#0d1117')
    ax.tick_params(colors='#888')
    for sp in ax.spines.values(): sp.set_color('#333')

# Sliders
ax_wind  = fig.add_axes([0.07, 0.12, 0.20, 0.025], facecolor='#1a1a2e')
ax_bias  = fig.add_axes([0.07, 0.08, 0.20, 0.025], facecolor='#1a1a2e')
ax_gps   = fig.add_axes([0.35, 0.12, 0.20, 0.025], facecolor='#1a1a2e')
ax_noise = fig.add_axes([0.35, 0.08, 0.20, 0.025], facecolor='#1a1a2e')

sl_wind  = Slider(ax_wind,  'Vent',     0.0, 3.0,  valinit=0.3,  color='#264653')
sl_bias  = Slider(ax_bias,  'Biais °/s',0.1, 5.0,  valinit=1.0,  color='#2a9d8f')
sl_gps   = Slider(ax_gps,   'GPS Hz',   0.0, 2.0,  valinit=0.2,  color='#e9c46a')
sl_noise = Slider(ax_noise, 'Bruit',    0.0, 0.5,  valinit=0.05, color='#e76f51')

# Boutons
ax_reta  = fig.add_axes([0.63, 0.085, 0.10, 0.055], facecolor='#0d1117')
ax_gpsb  = fig.add_axes([0.74, 0.085, 0.10, 0.055], facecolor='#0d1117')
ax_reset = fig.add_axes([0.85, 0.085, 0.10, 0.055], facecolor='#0d1117')
btn_reta  = Button(ax_reta,  'RETA ON',  color='#1b4332', hovercolor='#2d6a4f')
btn_gps   = Button(ax_gpsb,  'GPS ON',   color='#1b3a5c', hovercolor='#1d6fa4')
btn_reset = Button(ax_reset, 'RESET',    color='#4a1942', hovercolor='#6a2c63')

def toggle_reta(event=None):
    global reta_on
    reta_on = not reta_on
    btn_reta.label.set_text(f"RETA {'ON' if reta_on else 'OFF'}")
    btn_reta.ax.set_facecolor('#1b4332' if reta_on else '#7f1d1d')
    fig.canvas.draw_idle()

def toggle_gps(event=None):
    global gps_on
    gps_on = not gps_on
    btn_gps.label.set_text(f"GPS {'ON' if gps_on else 'OFF ⚠️'}")
    btn_gps.ax.set_facecolor('#1b3a5c' if gps_on else '#78350f')
    fig.canvas.draw_idle()

def do_reset(event=None):
    global reta_on, gps_on
    reta_on = True; gps_on = True
    btn_reta.label.set_text("RETA ON"); btn_reta.ax.set_facecolor('#1b4332')
    btn_gps.label.set_text("GPS ON");   btn_gps.ax.set_facecolor('#1b3a5c')
    keys.clear()
    sim.reset()

btn_reta.on_clicked(toggle_reta)
btn_gps.on_clicked(toggle_gps)
btn_reset.on_clicked(do_reset)

# ─── Clavier ─────────────────────────────────────────────────────────────────
def on_key_press(event):
    if event.key:
        keys.add(event.key.lower())
        if event.key == ' ':     toggle_reta()
        if event.key.lower() == 'g': toggle_gps()
        if event.key.lower() == 'r': do_reset()

def on_key_release(event):
    if event.key:
        keys.discard(event.key.lower())

fig.canvas.mpl_connect('key_press_event',   on_key_press)
fig.canvas.mpl_connect('key_release_event', on_key_release)

# ─── Légende contrôles ───────────────────────────────────────────────────────
ctrl_txt = (
    "← → : Roulis    ↑ ↓ : Tangage    A D : Lacet    W S : Altitude\n"
    "ESPACE : RETA ON/OFF    G : GPS ON/OFF    R : Reset"
)
fig.text(0.50, 0.03, ctrl_txt, ha='center', va='bottom',
         color='#888', fontsize=9, family='monospace')

# ─── Initialiser artistes ────────────────────────────────────────────────────
(ln_roll,)  = ax_phi.plot([], [], color='#ef4444', lw=1.5, label='Roll')
(ln_pitch,) = ax_phi.plot([], [], color='#22d3ee', lw=1.5, label='Pitch')
(ln_yaw,)   = ax_phi.plot([], [], color='#a78bfa', lw=1.5, label='Yaw')
ax_phi.axhline( Y_MAX, color='#ef4444', ls='--', lw=0.8, alpha=0.5)
ax_phi.axhline(-Y_MAX, color='#ef4444', ls='--', lw=0.8, alpha=0.5)
ax_phi.set_ylabel('Angle [°]', color='#aaa')
ax_phi.legend(loc='upper left', fontsize=8, framealpha=0.2)
ax_phi.set_ylim(-30, 30)

(ln_bt_r,)  = ax_b.plot([], [], color='#ef4444', lw=1.5, ls='--', label='b_true Roll')
(ln_be_r,)  = ax_b.plot([], [], color='#ef4444', lw=1.5, label='b_est Roll')
(ln_bt_p,)  = ax_b.plot([], [], color='#22d3ee', lw=1.5, ls='--', label='b_true Pitch')
(ln_be_p,)  = ax_b.plot([], [], color='#22d3ee', lw=1.5, label='b_est Pitch')
ax_b.set_ylabel('Biais [°/s]', color='#aaa')
ax_b.legend(loc='upper left', fontsize=7, framealpha=0.2, ncol=2)

(ln_bnd,)   = ax_bnd.plot([], [], color='#facc15', lw=2, label='t_rup prédit')
(ln_now,)   = ax_bnd.plot([], [], color='#888', lw=1, ls=':', label='t actuel')
ax_bnd.set_ylabel('t_rup [s]', color='#aaa')
ax_bnd.set_xlabel('Temps [s]', color='#aaa')
ax_bnd.legend(loc='upper left', fontsize=8, framealpha=0.2)

title_txt = fig.text(0.5, 0.96, '', ha='center', va='top',
                     color='white', fontsize=13, fontweight='bold')
status_txt = ax3d.text2D(0.02, 0.98, '', transform=ax3d.transAxes,
                         color='white', fontsize=9, va='top', family='monospace')

# ─── Update ──────────────────────────────────────────────────────────────────
CMD_RATE = 8.0   # °/s par touche

def update(frame):
    # Commandes utilisateur
    cmd = np.zeros(4)   # [roll, pitch, yaw, vz]
    if 'right'    in keys: cmd[0] += CMD_RATE
    if 'left'     in keys: cmd[0] -= CMD_RATE
    if 'down'     in keys: cmd[1] += CMD_RATE
    if 'up'       in keys: cmd[1] -= CMD_RATE
    if 'd'        in keys: cmd[2] += CMD_RATE * 0.5
    if 'a'        in keys: cmd[2] -= CMD_RATE * 0.5
    if 'w'        in keys: cmd[3]  =  2.0
    if 's'        in keys: cmd[3]  = -2.0

    wind_val  = sl_wind.val
    bias_val  = sl_bias.val
    gps_val   = sl_gps.val
    noise_val = sl_noise.val

    # Vent = perturbation roll+pitch
    wind = np.array([wind_val * np.sin(sim.t * 0.3),
                     wind_val * np.cos(sim.t * 0.5)])

    for _ in range(2):   # 2 pas physique par frame
        physics_step(sim, cmd, wind, bias_val, noise_val, gps_val)

    # ── 3D ──
    ax3d.cla()
    ax3d.set_facecolor('#0d1117')
    ax3d.set_xlabel('X [m]', color='#555', labelpad=2)
    ax3d.set_ylabel('Y [m]', color='#555', labelpad=2)
    ax3d.set_zlabel('Z [m]', color='#555', labelpad=2)
    ax3d.tick_params(colors='#444')
    ax3d.xaxis.pane.fill = ax3d.yaxis.pane.fill = ax3d.zaxis.pane.fill = False
    ax3d.xaxis.pane.set_edgecolor('#222')
    ax3d.yaxis.pane.set_edgecolor('#222')
    ax3d.zaxis.pane.set_edgecolor('#222')

    p = sim.pos
    # Sol (grille)
    gx = np.linspace(p[0]-8, p[0]+8, 10)
    gy = np.linspace(p[1]-8, p[1]+8, 10)
    for xx in gx: ax3d.plot([xx,xx],[gy[0],gy[-1]],[0,0], color='#1a1a2e', lw=0.5)
    for yy in gy: ax3d.plot([gx[0],gx[-1]],[yy,yy],[0,0], color='#1a1a2e', lw=0.5)

    # Trajectoire
    if len(sim.trail) > 2:
        tr = np.array(sim.trail)
        ax3d.plot(tr[:,0], tr[:,1], tr[:,2], color='#334155', lw=1.5, alpha=0.5)

    # Ombre au sol
    ax3d.scatter(p[0], p[1], 0, color='#ffffff', s=30, alpha=0.15, marker='o')
    ax3d.plot([p[0],p[0]], [p[1],p[1]], [0, p[2]], color='#334155', lw=0.8, ls='--', alpha=0.4)

    # Couleur selon état
    max_phi = np.abs(sim.phi).max()
    if sim.ruptured:
        drone_color = '#ef4444'
    elif max_phi > Y_MAX * 0.7:
        drone_color = '#f97316'
    elif max_phi > Y_MAX * 0.4:
        drone_color = '#eab308'
    elif reta_on:
        drone_color = '#22d3ee'
    else:
        drone_color = '#94a3b8'

    draw_drone(ax3d, p, sim.phi, drone_color)

    ax3d.set_xlim(p[0]-6, p[0]+6)
    ax3d.set_ylim(p[1]-6, p[1]+6)
    ax3d.set_zlim(0, max(12, p[2]+4))
    ax3d.view_init(elev=20, azim=sim.t * 3 % 360 if len(sim.h_t) < 5 else ax3d.azim)

    # ── Courbes ──
    if len(sim.h_t) < 2:
        return

    t_arr  = np.array(sim.h_t)
    ph_arr = np.array(sim.h_phi)
    bt_arr = np.array(sim.h_b_true)
    be_arr = np.array(sim.h_b_est)
    bd_arr = np.array(sim.h_bound)

    ln_roll.set_data(t_arr, ph_arr[:,0])
    ln_pitch.set_data(t_arr, ph_arr[:,1])
    ln_yaw.set_data(t_arr, ph_arr[:,2])
    ax_phi.set_xlim(t_arr[0], max(t_arr[-1], t_arr[0]+10))
    ax_phi.set_ylim(-Y_MAX*1.2, Y_MAX*1.2)

    ln_bt_r.set_data(t_arr, bt_arr[:,0])
    ln_be_r.set_data(t_arr, be_arr[:,0])
    ln_bt_p.set_data(t_arr, bt_arr[:,1])
    ln_be_p.set_data(t_arr, be_arr[:,1])
    ax_b.set_xlim(t_arr[0], max(t_arr[-1], t_arr[0]+10))
    ax_b.relim(); ax_b.autoscale_view()

    bnd_clip = np.clip(bd_arr, t_arr[0], t_arr[-1] + 120)
    ln_bnd.set_data(t_arr, bnd_clip)
    ln_now.set_data([t_arr[0], t_arr[-1]], [t_arr[-1], t_arr[-1]])
    ax_bnd.set_xlim(t_arr[0], max(t_arr[-1], t_arr[0]+10))
    ax_bnd.set_ylim(t_arr[0], t_arr[-1] + 60)

    # ── Titre + status ──
    reta_str = "🟢 RETA ON" if reta_on else "🔴 RETA OFF"
    gps_str  = "GPS ✓" if gps_on else "GPS ✗"
    if sim.ruptured:
        reta_str = "💥 RUPTURE"
    title_txt.set_text(f"RETA Drone Interactif  —  {reta_str}  |  {gps_str}  |  t = {sim.t:.1f}s")

    b_est_now = np.array([float(sim.x_k[i][1]) for i in range(3)])
    b_qual    = np.abs(b_est_now) / np.maximum(np.abs(sim.b_true), 1e-6) * 100
    rem       = Y_MAX - np.abs(sim.phi).max()
    z_max     = np.abs(sim.b_true - b_est_now).max()
    t_rup_est = sim.t + rem / max(z_max, 1e-6) if rem > 0 else sim.t

    status_lines = [
        f"Roll  : {sim.phi[0]:+5.1f}°",
        f"Pitch : {sim.phi[1]:+5.1f}°",
        f"Yaw   : {sim.phi[2]:+5.1f}°",
        f"",
        f"Pos  ({sim.pos[0]:+.1f}, {sim.pos[1]:+.1f}, {sim.pos[2]:.1f}m)",
        f"",
        f"Biais vrai  : {sim.b_true[0]:.3f} °/s",
        f"Biais estimé: {b_est_now[0]:.3f} °/s",
        f"Précision   : {b_qual[0]:.0f}%",
        f"",
        f"Marge Y_max : {rem:.1f}°",
        f"t_rup prédit: {t_rup_est:.0f}s",
    ]
    if sim.ruptured:
        status_lines.append("\n⚠️  RUPTURE RETA")
    status_txt.set_text("\n".join(status_lines))
    status_txt.set_color('#ef4444' if sim.ruptured else '#94a3b8')


ani = anim.FuncAnimation(fig, update, interval=60, cache_frame_data=False)
plt.show()
