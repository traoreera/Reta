"""
RETA — Simulation Interactive Drone (PyQt5 pur)
================================================
Pilotage clavier :
  ← → : roulis          ↑ ↓ : tangage
  A / D : lacet          W / S : altitude
  ESPACE : RETA ON/OFF   G : GPS ON/OFF   R : Reset

Souris sur la vue 3D : drag pour tourner la caméra
"""

import sys, math
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QSlider, QLabel, QSizePolicy, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QLinearGradient, QPolygonF
)

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSIQUE + KALMAN
# ═══════════════════════════════════════════════════════════════════════════════
DT       = 0.04
Y_MAX    = 20.0
HIST     = 400
TRAIL    = 160
G        = 9.81
R_GPS    = 0.04
Q_ANG    = 1e-5
ALPHA_Q  = 0.3
Q_MIN    = 1e-9
A_KAL    = np.array([[1., -DT], [0., 1.]])
H_KAL    = np.array([[1., 0.]])

rng = np.random.default_rng(7)

class Simulation:
    def __init__(self):
        self.reset()

    def reset(self):
        self.t        = 0.
        self.phi      = np.zeros(3)          # roll pitch yaw [°]
        self.pos      = np.array([0.,0.,5.]) # x y z [m]
        self.vel      = np.zeros(3)
        self.b_true   = np.zeros(3)          # biais gyro vrai [°/s]
        self.x_k      = [np.zeros(2)   for _ in range(3)]
        self.P_k      = [np.eye(2)*0.1 for _ in range(3)]
        self.Q_b      = np.full(3, 1e-4)
        self.Kp       = np.array([7., 7., 3.])
        self.Ki       = np.array([3., 3., 1.])
        self.I_e      = np.zeros(3)
        self.t_gps    = 0.
        self.ruptured = False
        # historiques
        self.h_t      = []
        self.h_phi    = []
        self.h_bt     = []
        self.h_be     = []
        self.h_bound  = []
        self.trail    = []

    def _kalman(self, axis, omega, phi_gps=None):
        x, P, Qb = self.x_k[axis], self.P_k[axis], self.Q_b[axis]
        x = A_KAL @ x + np.array([DT, 0.]) * omega
        P = A_KAL @ P @ A_KAL.T + np.diag([Q_ANG, Qb])
        if phi_gps is not None:
            S  = float(H_KAL @ P @ H_KAL.T) + R_GPS
            K  = (P @ H_KAL.T) / S
            nu = float(phi_gps) - float(H_KAL @ x)
            x  = x + K.flatten() * nu
            P  = (np.eye(2) - np.outer(K.flatten(), H_KAL)) @ P
            if self.reta_on:
                dr = abs(nu) / max(self.t_gps, 0.3)
                qi = max((dr * DT)**2, Q_MIN)
                self.Q_b[axis] = (1-ALPHA_Q)*self.Q_b[axis] + ALPHA_Q*qi
        self.x_k[axis] = x; self.P_k[axis] = P
        return float(x[0]), float(x[1])

    def step(self, cmd, wind, bias_rate, noise_amp, gps_hz):
        if self.ruptured:
            return
        # biais thermique
        for i in range(3):
            drift = np.array([0.04, 0.05, 0.03])[i]
            self.b_true[i] += bias_rate * drift * DT

        noise = rng.standard_normal(3) * noise_amp

        # PI par axe
        u = np.zeros(3)
        for i in range(3):
            e = float(self.x_k[i][0]) - cmd[i]
            self.I_e[i] = np.clip(self.I_e[i] + e*DT, -40, 40)
            u[i] = -(self.Kp[i]*e + self.Ki[i]*self.I_e[i])

        # mesure gyro + physique boucle fermée
        omega = u + self.b_true + noise
        omega[0] += wind * math.sin(self.t * 0.4)
        omega[1] += wind * math.cos(self.t * 0.3)
        self.phi = np.clip(self.phi + omega * DT, -89, 89)

        # GPS
        self.t_gps += DT
        gps_now = self.gps_on and gps_hz > 0 and self.t_gps >= 1./max(gps_hz, 0.01)
        if gps_now: self.t_gps = 0.

        for i in range(3):
            gps_val = self.phi[i] + rng.standard_normal()*math.sqrt(R_GPS) if gps_now else None
            self._kalman(i, u[i]+self.b_true[i]+noise[i], gps_val)

        # position physique
        self.vel[0] += G * math.sin(math.radians(self.phi[1])) * DT
        self.vel[1] -= G * math.sin(math.radians(self.phi[0])) * DT
        self.vel[2] += cmd[3] * DT
        self.vel    *= 0.96
        self.pos    += self.vel * DT
        self.pos[2]  = max(0., self.pos[2])
        self.t      += DT

        be = np.array([float(self.x_k[i][1]) for i in range(3)])
        z  = np.abs(self.b_true - be)
        rem = Y_MAX - np.abs(self.phi).max()
        bnd = self.t + rem/max(z.max(), 1e-9) if rem>0 else self.t

        self.h_t.append(self.t); self.h_phi.append(self.phi.copy())
        self.h_bt.append(self.b_true.copy()); self.h_be.append(be.copy())
        self.h_bound.append(bnd); self.trail.append(self.pos.copy())
        if len(self.h_t) > HIST:
            self.h_t.pop(0); self.h_phi.pop(0); self.h_bt.pop(0)
            self.h_be.pop(0); self.h_bound.pop(0)
        if len(self.trail) > TRAIL: self.trail.pop(0)

        if np.abs(self.phi).max() >= Y_MAX:
            self.ruptured = True

    # drapeaux (modifiés par UI)
    reta_on = True
    gps_on  = True

sim = Simulation()

# ═══════════════════════════════════════════════════════════════════════════════
# VUE 3D (drone + trajectoire)
# ═══════════════════════════════════════════════════════════════════════════════
def rot3(roll_d, pitch_d, yaw_d):
    r,p,y = math.radians(roll_d), math.radians(pitch_d), math.radians(yaw_d)
    Rx=np.array([[1,0,0],[0,math.cos(r),-math.sin(r)],[0,math.sin(r),math.cos(r)]])
    Ry=np.array([[math.cos(p),0,math.sin(p)],[0,1,0],[-math.sin(p),0,math.cos(p)]])
    Rz=np.array([[math.cos(y),-math.sin(y),0],[math.sin(y),math.cos(y),0],[0,0,1]])
    return Rz@Ry@Rx

class DroneView3D(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(480, 480)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.azim = 35.
        self.elev = 22.
        self._drag_start = None

    def project(self, pt3, cx, cy, scale=60., cam_dist=18.):
        az, el = math.radians(self.azim), math.radians(self.elev)
        # camera basis
        cam = np.array([
            math.sin(az)*math.cos(el),
            math.cos(az)*math.cos(el),
            math.sin(el)
        ]) * cam_dist
        # right, up vectors of camera
        fwd   = -cam / np.linalg.norm(cam)
        world_up = np.array([0.,0.,1.])
        right = np.cross(fwd, world_up); right /= np.linalg.norm(right)
        up    = np.cross(right, fwd)
        # relative to camera
        rel = pt3 - cam
        depth = np.dot(rel, fwd)
        if depth > -0.5: depth = -0.5
        xs = np.dot(rel, right)  / (-depth) * scale * 1.8
        ys = np.dot(rel, up)     / (-depth) * scale * 1.8
        return cx + xs, cy - ys

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        cx, cy = w//2, h//2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # fond dégradé
        grad = QLinearGradient(0,0,0,h)
        grad.setColorAt(0, QColor('#0d1117'))
        grad.setColorAt(1, QColor('#0a0e17'))
        painter.fillRect(0,0,w,h, grad)

        p = sim.pos
        scale = max(30., 140. - p[2]*4)

        # ── sol / grille ──
        grid_range = 8
        for gx in range(-grid_range, grid_range+1):
            for gy in range(-grid_range, grid_range+1):
                if gx == grid_range: continue
                p1 = self.project(np.array([p[0]+gx, p[1]+gy, 0.]), cx,cy,scale)
                p2 = self.project(np.array([p[0]+gx+1, p[1]+gy, 0.]), cx,cy,scale)
                q1 = self.project(np.array([p[0]+gx, p[1]+gy, 0.]), cx,cy,scale)
                q2 = self.project(np.array([p[0]+gx, p[1]+gy+1, 0.]), cx,cy,scale)
                c = QColor('#1a2035') if (gx+gy)%2==0 else QColor('#161c2e')
                painter.setPen(QPen(c, 0.8))
                painter.drawLine(int(p1[0]),int(p1[1]),int(p2[0]),int(p2[1]))
                painter.drawLine(int(q1[0]),int(q1[1]),int(q2[0]),int(q2[1]))

        # ── trajectoire ──
        if len(sim.trail) > 2:
            for i in range(1, len(sim.trail)):
                alpha = int(180 * i / len(sim.trail))
                col = QColor(50,100,200,alpha)
                painter.setPen(QPen(col, 1.5))
                p1 = self.project(sim.trail[i-1], cx,cy,scale)
                p2 = self.project(sim.trail[i],   cx,cy,scale)
                painter.drawLine(int(p1[0]),int(p1[1]),int(p2[0]),int(p2[1]))

        # ── fil de plomb ──
        shadow = self.project(np.array([p[0], p[1], 0.]), cx,cy,scale)
        drone  = self.project(p, cx,cy,scale)
        painter.setPen(QPen(QColor(100,100,150,80), 1, Qt.DashLine))
        painter.drawLine(int(drone[0]),int(drone[1]),int(shadow[0]),int(shadow[1]))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(100,120,200,60))
        painter.drawEllipse(int(shadow[0])-8,int(shadow[1])-4,16,8)

        # ── drone ──
        R = rot3(*sim.phi)
        arm = 0.7
        angles = [45,135,225,315]
        tips = []
        for ang in angles:
            local = arm*np.array([math.cos(math.radians(ang)),
                                   math.sin(math.radians(ang)), 0.])
            world = p + R @ local
            tips.append(world)

        # bras
        if sim.ruptured:
            drone_col = QColor('#ef4444')
        elif np.abs(sim.phi).max() > Y_MAX*0.7:
            drone_col = QColor('#f97316')
        elif np.abs(sim.phi).max() > Y_MAX*0.4:
            drone_col = QColor('#eab308')
        elif sim.reta_on:
            drone_col = QColor('#22d3ee')
        else:
            drone_col = QColor('#94a3b8')

        painter.setPen(QPen(drone_col, 4, Qt.SolidLine, Qt.RoundCap))
        dc = self.project(p, cx,cy,scale)
        for tip in tips:
            tc = self.project(tip, cx,cy,scale)
            painter.drawLine(int(dc[0]),int(dc[1]),int(tc[0]),int(tc[1]))

        # rotors (ellipses aplaties en perspective)
        rv = 0.22
        n_rot = 18
        for tip in tips:
            pts = []
            for k in range(n_rot+1):
                ang = 2*math.pi*k/n_rot
                local = np.array([rv*math.cos(ang), rv*math.sin(ang), 0.])
                world_pt = tip + R @ local
                sc = self.project(world_pt, cx,cy,scale)
                pts.append(QPointF(sc[0], sc[1]))
            poly = QPolygonF(pts)
            rotor_col = QColor(drone_col.red(), drone_col.green(), drone_col.blue(), 110)
            painter.setPen(QPen(rotor_col, 1.5))
            painter.setBrush(QColor(drone_col.red(),drone_col.green(),drone_col.blue(),30))
            painter.drawPolygon(poly)

        # corps central
        painter.setPen(Qt.NoPen)
        painter.setBrush(drone_col)
        painter.drawEllipse(int(dc[0])-7,int(dc[1])-7,14,14)

        # indicateur de nez
        nose_world = p + R @ np.array([arm*1.1, 0., 0.1])
        nc = self.project(nose_world, cx,cy,scale)
        painter.setPen(QPen(QColor('#ffffff'), 2.5))
        painter.drawLine(int(dc[0]),int(dc[1]),int(nc[0]),int(nc[1]))

        # ── overlay texte ──
        painter.setPen(QColor('#64748b'))
        painter.setFont(QFont('Courier New', 9))
        be = np.array([float(sim.x_k[i][1]) for i in range(3)])
        bq = np.abs(be)/np.maximum(np.abs(sim.b_true),1e-4)*100
        lines = [
            f"t       {sim.t:7.1f} s",
            f"Roll   {sim.phi[0]:+7.1f} °",
            f"Pitch  {sim.phi[1]:+7.1f} °",
            f"Yaw    {sim.phi[2]:+7.1f} °",
            f"",
            f"X {sim.pos[0]:+5.1f}m  Y {sim.pos[1]:+5.1f}m",
            f"Z {sim.pos[2]:5.1f}m",
            f"",
            f"Biais  {sim.b_true[0]*1000:+5.1f} m°/s",
            f"Estimé {be[0]*1000:+5.1f} m°/s",
            f"Qualité {bq[0]:.0f}%",
        ]
        if sim.ruptured:
            painter.setFont(QFont('Courier New', 12, QFont.Bold))
            painter.setPen(QColor('#ef4444'))
            painter.drawText(cx-60, cy-10, "⚠ RUPTURE RETA")
        for i, line in enumerate(lines):
            painter.setPen(QColor('#64748b'))
            painter.setFont(QFont('Courier New', 9))
            painter.drawText(8, 18+i*16, line)

        # ── RETA status badge ──
        reta_col = QColor('#22d3ee') if sim.reta_on else QColor('#ef4444')
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(reta_col.red(),reta_col.green(),reta_col.blue(),40))
        painter.drawRoundedRect(w-110,8,102,22,6,6)
        painter.setPen(reta_col)
        painter.setFont(QFont('Courier New', 9, QFont.Bold))
        txt = "● RETA ON" if sim.reta_on else "● RETA OFF"
        painter.drawText(w-106,23, txt)

        gps_col = QColor('#22d3ee') if sim.gps_on else QColor('#f97316')
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(gps_col.red(),gps_col.green(),gps_col.blue(),40))
        painter.drawRoundedRect(w-110,34,102,22,6,6)
        painter.setPen(gps_col)
        painter.drawText(w-106,49, "● GPS ON" if sim.gps_on else "● GPS OFF")

        painter.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start = (e.x(), e.y(), self.azim, self.elev)

    def mouseMoveEvent(self, e):
        if self._drag_start:
            dx = e.x() - self._drag_start[0]
            dy = e.y() - self._drag_start[1]
            self.azim = self._drag_start[2] - dx * 0.5
            self.elev = max(5., min(80., self._drag_start[3] - dy * 0.4))

    def mouseReleaseEvent(self, e):
        self._drag_start = None


# ═══════════════════════════════════════════════════════════════════════════════
# WIDGET COURBE GÉNÉRIQUE
# ═══════════════════════════════════════════════════════════════════════════════
class PlotWidget(QWidget):
    def __init__(self, title, ylabel, ymin, ymax):
        super().__init__()
        self.title = title; self.ylabel = ylabel
        self.ymin = ymin; self.ymax = ymax
        self.series = []   # list of (array_ref, color, label, style)
        self.hlines = []   # list of (y_value, color, style)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def add_series(self, getter, color, label='', dash=False):
        self.series.append((getter, QColor(color), label, dash))

    def add_hline(self, y, color, dash=True):
        self.hlines.append((y, QColor(color), dash))

    def paintEvent(self, event):
        if not sim.h_t:
            return
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 48, 12, 22, 28
        pw, ph = w-pad_l-pad_r, h-pad_t-pad_b

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(0,0,w,h, QColor('#0d1117'))

        # grille
        t_arr = np.array(sim.h_t)
        t0, t1 = t_arr[0], max(t_arr[-1], t_arr[0]+1)
        ys = np.linspace(self.ymin, self.ymax, 5)
        for y in ys:
            sy = pad_t + ph*(1-(y-self.ymin)/(self.ymax-self.ymin))
            painter.setPen(QPen(QColor('#1e293b'), 1))
            painter.drawLine(pad_l, int(sy), pad_l+pw, int(sy))
            painter.setPen(QColor('#475569'))
            painter.setFont(QFont('Courier New', 8))
            painter.drawText(2, int(sy)+4, f"{y:.0f}")

        # hlines
        for y_val, col, dash in self.hlines:
            sy = pad_t + ph*(1-(y_val-self.ymin)/(self.ymax-self.ymin))
            pen = QPen(col, 1, Qt.DashLine if dash else Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(pad_l, int(sy), pad_l+pw, int(sy))

        # titres
        painter.setPen(QColor('#94a3b8'))
        painter.setFont(QFont('Courier New', 8, QFont.Bold))
        painter.drawText(pad_l, 14, self.title)

        # légende
        lx = pad_l + pw - 5
        for getter, col, label, dash in reversed(self.series):
            if label:
                pen = QPen(col, 2, Qt.DashLine if dash else Qt.SolidLine)
                painter.setPen(pen)
                tw = len(label)*6 + 22
                lx -= tw
                painter.drawLine(lx, 12, lx+16, 12)
                painter.setPen(col)
                painter.setFont(QFont('Courier New', 8))
                painter.drawText(lx+18, 16, label)

        # séries
        def sx(t):
            return pad_l + pw*(t-t0)/(t1-t0)
        def sy(y):
            return pad_t + ph*(1-(np.clip(y,self.ymin,self.ymax)-self.ymin)/(self.ymax-self.ymin))

        for getter, col, label, dash in self.series:
            data = np.array(getter())
            if len(data) < 2: continue
            path = QPainterPath()
            path.moveTo(sx(t_arr[0]), sy(data[0]))
            for i in range(1, len(data)):
                path.lineTo(sx(t_arr[i]), sy(data[i]))
            pen = QPen(col, 1.8, Qt.DashLine if dash else Qt.SolidLine)
            painter.setPen(pen)
            painter.drawPath(path)

        # axe X (temps)
        painter.setPen(QColor('#334155'))
        painter.drawLine(pad_l, h-pad_b, pad_l+pw, h-pad_b)
        painter.setPen(QColor('#475569'))
        painter.setFont(QFont('Courier New', 8))
        for tv in np.linspace(t0, t1, 5):
            sx_v = int(sx(tv))
            painter.drawText(sx_v-12, h-8, f"{tv:.0f}s")

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# FENÊTRE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════
KEYS = set()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RETA — Simulation Drone Interactif")
        self.setStyleSheet("background:#0a0e17; color:#e2e8f0;")
        self.resize(1280, 820)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(6,6,6,6)
        root.setSpacing(6)

        # ── Vue 3D ──
        self.view3d = DroneView3D()
        self.view3d.setMinimumWidth(460)
        root.addWidget(self.view3d, 5)

        # ── Droite : courbes + contrôles ──
        right = QVBoxLayout()
        right.setSpacing(4)
        root.addLayout(right, 4)

        # Courbe angles
        self.plt_phi = PlotWidget("Angles Roll/Pitch/Yaw", "°", -Y_MAX*1.3, Y_MAX*1.3)
        self.plt_phi.add_series(lambda: [v[0] for v in sim.h_phi], '#ef4444', 'Roll')
        self.plt_phi.add_series(lambda: [v[1] for v in sim.h_phi], '#22d3ee', 'Pitch')
        self.plt_phi.add_series(lambda: [v[2] for v in sim.h_phi], '#a78bfa', 'Yaw')
        self.plt_phi.add_hline( Y_MAX, '#ef4444'); self.plt_phi.add_hline(-Y_MAX, '#ef4444')
        right.addWidget(self.plt_phi, 3)

        # Courbe biais
        self.plt_b = PlotWidget("Biais Gyro : Vrai vs Estimé", "°/s", -0.05, 0.5)
        self.plt_b.add_series(lambda: [v[0] for v in sim.h_bt], '#ef4444', 'b_true', dash=True)
        self.plt_b.add_series(lambda: [v[0] for v in sim.h_be], '#ef4444', 'b_est')
        self.plt_b.add_series(lambda: [v[1] for v in sim.h_bt], '#22d3ee', '', dash=True)
        self.plt_b.add_series(lambda: [v[1] for v in sim.h_be], '#22d3ee', '')
        right.addWidget(self.plt_b, 2)

        # Courbe bound RETA
        self.plt_bnd = PlotWidget("Prédiction t_rupture (RETA)", "s", 0, 1)
        self.plt_bnd.add_series(lambda: sim.h_bound, '#facc15', 't_rup prédit')
        self.plt_bnd.add_series(lambda: sim.h_t,     '#475569', 't actuel', dash=True)
        right.addWidget(self.plt_bnd, 2)

        # Courbe position
        self.plt_pos = PlotWidget("Position X/Y/Z", "m", -20, 20)
        self.plt_pos.add_series(lambda: [v[0] for v in sim.trail], '#f97316', 'X')
        self.plt_pos.add_series(lambda: [v[1] for v in sim.trail], '#4ade80', 'Y')
        self.plt_pos.add_series(lambda: [v[2] for v in sim.trail], '#60a5fa', 'Z')
        right.addWidget(self.plt_pos, 2)

        # ── Contrôles ──
        ctrl_panel = self._build_controls()
        right.addWidget(ctrl_panel)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)   # 25 fps

    def _build_controls(self):
        panel = QFrame()
        panel.setStyleSheet("background:#111827; border-radius:6px;")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(8,6,8,6)
        vl.setSpacing(4)

        # Boutons
        btn_row = QHBoxLayout()
        self.btn_reta  = self._btn("RETA ON",  '#1b4332', self.toggle_reta)
        self.btn_gps   = self._btn("GPS ON",   '#1b3a5c', self.toggle_gps)
        self.btn_reset = self._btn("RESET",    '#4a1942', self.do_reset)
        for b in [self.btn_reta, self.btn_gps, self.btn_reset]:
            btn_row.addWidget(b)
        vl.addLayout(btn_row)

        # Sliders
        sliders = [
            ("Vent",   0, 300, 30,  "vent"),
            ("Biais",  5, 500, 100, "bias"),
            ("GPS Hz", 0, 100, 20,  "gps"),
            ("Bruit",  0, 100, 5,   "noise"),
        ]
        grid = QGridLayout()
        self.sl = {}
        for row,(name,vmin,vmax,vinit,key) in enumerate(sliders):
            lbl = QLabel(name)
            lbl.setStyleSheet("color:#94a3b8; font:8pt 'Courier New';")
            lbl.setFixedWidth(46)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(vmin,vmax); sl.setValue(vinit)
            sl.setStyleSheet("QSlider::groove:horizontal{height:4px;background:#1e293b;border-radius:2px;}"
                             "QSlider::handle:horizontal{width:10px;height:10px;margin:-3px 0;background:#22d3ee;border-radius:5px;}")
            val_lbl = QLabel(f"{vinit/100:.2f}")
            val_lbl.setStyleSheet("color:#64748b; font:8pt 'Courier New';")
            val_lbl.setFixedWidth(38)
            sl.valueChanged.connect(lambda v,vl=val_lbl: vl.setText(f"{v/100:.2f}"))
            self.sl[key] = sl
            grid.addWidget(lbl, row//2, (row%2)*3)
            grid.addWidget(sl,  row//2, (row%2)*3+1)
            grid.addWidget(val_lbl, row//2, (row%2)*3+2)
        vl.addLayout(grid)

        # Aide clavier
        hint = QLabel("← → : Roulis   ↑ ↓ : Tangage   A D : Lacet   W S : Altitude   ESPACE : RETA   G : GPS   R : Reset")
        hint.setStyleSheet("color:#334155; font:8pt 'Courier New';")
        hint.setAlignment(Qt.AlignCenter)
        vl.addWidget(hint)
        return panel

    def _btn(self, text, bg, cb):
        b = QPushButton(text)
        b.setStyleSheet(f"QPushButton{{background:{bg};color:#e2e8f0;border-radius:4px;"
                        f"padding:5px 10px;font:9pt 'Courier New';border:none;}}"
                        f"QPushButton:hover{{background:#374151;}}")
        b.clicked.connect(cb)
        return b

    def _tick(self):
        # cmd depuis clavier
        cmd = np.zeros(4)
        if Qt.Key_Right in KEYS: cmd[0] += 10
        if Qt.Key_Left  in KEYS: cmd[0] -= 10
        if Qt.Key_Down  in KEYS: cmd[1] += 10
        if Qt.Key_Up    in KEYS: cmd[1] -= 10
        if Qt.Key_D     in KEYS: cmd[2] += 5
        if Qt.Key_A     in KEYS: cmd[2] -= 5
        if Qt.Key_W     in KEYS: cmd[3]  = 3.
        if Qt.Key_S     in KEYS: cmd[3]  = -3.

        wind  = self.sl['vent'].value()  / 100.
        bias  = self.sl['bias'].value()  / 100.
        gps   = self.sl['gps'].value()   / 100.
        noise = self.sl['noise'].value() / 100.

        for _ in range(2):
            sim.step(cmd, wind, bias, noise, gps)

        # auto-scale bound plot
        if sim.h_bound:
            tmax = max(sim.h_bound[-1], sim.h_t[-1]+20) if sim.h_t else 30
            tmin = sim.h_t[0] if sim.h_t else 0
            self.plt_bnd.ymin = tmin
            self.plt_bnd.ymax = min(tmax, sim.h_t[-1]+120) if sim.h_t else tmax

        # auto-scale biais
        if sim.h_bt:
            mx = max(0.05, np.array(sim.h_bt).max()*1.2)
            self.plt_b.ymin = -0.005; self.plt_b.ymax = mx

        # auto-scale position
        if sim.trail:
            tr = np.array(sim.trail)
            mx = max(5., float(np.abs(tr).max())*1.2)
            self.plt_pos.ymin = -mx; self.plt_pos.ymax = mx

        self.view3d.update()
        self.plt_phi.update()
        self.plt_b.update()
        self.plt_bnd.update()
        self.plt_pos.update()

    def keyPressEvent(self, e):
        KEYS.add(e.key())
        if e.key() == Qt.Key_Space:  self.toggle_reta()
        if e.key() == Qt.Key_G:      self.toggle_gps()
        if e.key() == Qt.Key_R:      self.do_reset()

    def keyReleaseEvent(self, e):
        KEYS.discard(e.key())

    def toggle_reta(self):
        sim.reta_on = not sim.reta_on
        on = sim.reta_on
        self.btn_reta.setText("RETA ON" if on else "RETA OFF")
        self.btn_reta.setStyleSheet(
            f"QPushButton{{background:{'#1b4332' if on else '#7f1d1d'};"
            "color:#e2e8f0;border-radius:4px;padding:5px 10px;font:9pt 'Courier New';border:none;}}"
            "QPushButton:hover{background:#374151;}")

    def toggle_gps(self):
        sim.gps_on = not sim.gps_on
        on = sim.gps_on
        self.btn_gps.setText("GPS ON" if on else "GPS OFF ⚠")
        self.btn_gps.setStyleSheet(
            f"QPushButton{{background:{'#1b3a5c' if on else '#78350f'};"
            "color:#e2e8f0;border-radius:4px;padding:5px 10px;font:9pt 'Courier New';border:none;}}"
            "QPushButton:hover{background:#374151;}")

    def do_reset(self):
        KEYS.clear()
        sim.reset()
        sim.reta_on = True; sim.gps_on = True
        self.btn_reta.setText("RETA ON")
        self.btn_gps.setText("GPS ON")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
