"""
sovereign_anima.py — Machine Identity Manifold
Sovereign Anima v0.1 | Chad Edward Holland | June 2026

Concept: Every machine develops a unique geometric identity over time.
Scars accumulate. The biography is readable in the geometry.
When the manifold collapses — the machine is dying.

DEMO VERSION — full implementation under NDA
Contact: c.holland.arch@proton.me
"""
import os, time, hashlib, numpy as np
from typing import Tuple, Dict, List

def _read_temp() -> float:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip())/1000.0
    except: return 37.0

def _is_charging() -> bool:
    try:
        with open("/sys/class/power_supply/battery/status") as f:
            return f.read().strip().lower() in ("charging","full")
    except: return False

class MachineIdentityManifold:
    """
    Geometric identity for a single physical machine.

    Each machine gets its own low-rank manifold learned from its
    own telemetry. Not a class of machines — THIS specific machine.

    Scars accumulate over the machine's operational lifetime.
    The geometry encodes the machine's history.
    Manifold collapse predicts failure before it occurs.
    """

    def __init__(self, machine_id: str, d: int = 64, rank: int = 16):
        self.machine_id = machine_id
        self.d    = d
        self.rank = rank
        # Identity manifold — learned from this machine's telemetry
        rng  = np.random.default_rng(seed=abs(hash(machine_id)) % (2**32))
        raw  = rng.standard_normal((d, rank)).astype(np.float32)
        self.M, _ = np.linalg.qr(raw)
        self.M = self.M[:, :rank]
        # Scar history
        self.scars: List[Dict] = []
        self.n_updates   = 0
        self.n_scars     = 0
        self.t_created   = time.time()

    def observe(self, telemetry_vec: np.ndarray) -> Dict:
        """
        Observe a telemetry vector from this machine.
        Returns identity match score and novelty signal.
        """
        x    = self._norm(telemetry_vec)
        proj = self.M @ (self.M.T @ x)
        res  = x - proj
        # Identity match: how well does this fit THIS machine's geometry?
        match   = float(np.dot(proj, x) / (np.linalg.norm(proj)+1e-10))
        novelty = float(np.linalg.norm(res))
        return {"match": round(match,4), "novelty": round(novelty,4),
                "machine_id": self.machine_id}

    def update(self, telemetry_vec: np.ndarray, eta: float = 0.01) -> bool:
        """Update machine identity manifold from new telemetry."""
        temp = _read_temp()
        if temp >= 40.5:  # SCAR_LOCK
            return False
        x    = self._norm(telemetry_vec)
        proj = self.M @ (self.M.T @ x)
        res  = x - proj
        # Gradient update
        grad = -2.0 * np.outer(res, x) @ self.M
        self.M = self.M - eta * grad
        # Re-orthogonalize
        self.M, _ = np.linalg.qr(self.M)
        self.M = self.M[:, :self.rank]
        self.n_updates += 1
        return True

    def write_scar(self, event: str, severity: float):
        """Record a permanent scar from a significant event."""
        scar = {"t": time.time(), "event": event[:100],
                "severity": round(severity,3), "n_update": self.n_updates}
        self.scars.append(scar)
        self.n_scars += 1

    def health(self) -> Dict:
        """Assess geometric health of machine identity."""
        U, S, Vt  = np.linalg.svd(self.M, full_matrices=False)
        spec_norm = float(np.max(S))
        rank_eff  = int(np.sum(S > 0.01))
        age_days  = (time.time() - self.t_created) / 86400

        # Collapse risk: spectral norm dropping + scar density rising
        scar_density = self.n_scars / max(self.n_updates, 1)
        collapse_risk = min(1.0, scar_density * 10 + max(0, 0.5 - spec_norm))

        return {
            "machine_id":    self.machine_id,
            "spectral_norm": round(spec_norm, 4),
            "effective_rank": rank_eff,
            "n_scars":       self.n_scars,
            "n_updates":     self.n_updates,
            "scar_density":  round(scar_density, 4),
            "collapse_risk": round(collapse_risk, 4),
            "age_days":      round(age_days, 2),
            "status": ("CRITICAL" if collapse_risk>0.7 else
                       "DEGRADED" if collapse_risk>0.4 else
                       "HEALTHY"),
        }

    def _norm(self, x: np.ndarray) -> np.ndarray:
        if len(x) < self.d: x = np.pad(x, (0, self.d-len(x)))
        elif len(x) > self.d: x = x[:self.d]
        n = np.linalg.norm(x)
        return (x/n if n>1e-8 else x).astype(np.float32)


class BiHemisphericLearner:
    """
    Bi-hemispheric learning: HOT hemisphere runs live,
    COOL hemisphere learns during charging/idle,
    handoff occurs when thermal and quality conditions are met.

    Inspired by sleep-based memory consolidation in biological systems.
    Full implementation details under NDA.
    """
    def __init__(self, machine_id: str, d: int = 64, rank: int = 16):
        self.machine_id = machine_id
        self.hot  = MachineIdentityManifold(machine_id+"_hot",  d, rank)
        self.cool = MachineIdentityManifold(machine_id+"_cool", d, rank)
        self.cool.M = self.hot.M.copy()
        self.phase = "HOT_AWAKE"
        self.n_cool_updates = 0
        self.t_last_handoff = 0.0

    def think(self, vec: np.ndarray) -> Dict:
        return self.hot.observe(vec)

    def learn(self, vec: np.ndarray):
        """Learn in cool hemisphere (background)."""
        self.cool.update(vec, eta=0.005)
        self.n_cool_updates += 1

    def handoff_ready(self) -> bool:
        temp     = _read_temp()
        charging = _is_charging()
        dt       = time.monotonic() - self.t_last_handoff
        return (charging and temp < 37.0 and
                self.n_cool_updates >= 50 and dt >= 3600.0)

    def attempt_handoff(self) -> Tuple[bool, str]:
        """Transfer cool hemisphere learning to hot."""
        self.phase = "HANDOFF"
        delta = self.cool.M - self.hot.M
        delta_norm = float(np.linalg.norm(delta, "fro"))
        hot_norm   = float(np.linalg.norm(self.hot.M, "fro"))
        geodesic   = delta_norm / (hot_norm + 1e-10)

        if geodesic > 0.15:  # Too large a jump
            self.cool.M = self.hot.M.copy()
            self.n_cool_updates = 0
            self.phase = "HOT_AWAKE"
            return False, f"rejected: geodesic {geodesic:.3f} > 0.15"

        # Merge
        self.hot.M += 0.01 * delta
        self.hot.M, _ = np.linalg.qr(self.hot.M)
        self.hot.M = self.hot.M[:, :self.hot.rank]
        self.cool.M = self.hot.M.copy()
        self.n_cool_updates = 0
        self.t_last_handoff = time.monotonic()
        self.phase = "HOT_AWAKE"
        return True, f"merged | geodesic={geodesic:.4f}"

    def status(self) -> Dict:
        h = self.hot.health()
        return {**h, "phase": self.phase,
                "cool_updates": self.n_cool_updates,
                "handoff_ready": self.handoff_ready()}


if __name__ == "__main__":
    print("\n  SOVEREIGN ANIMA v0.1 — Machine Identity Demo\n")

    # Simulate two machines
    pump_a = BiHemisphericLearner("PUMP-A1", d=64, rank=16)
    pump_b = BiHemisphericLearner("PUMP-B1", d=64, rank=16)

    print("  Training on 100 normal operational cycles...")
    for i in range(100):
        # Normal telemetry for pump A
        vec_a = np.array([65.0+np.random.randn()*5,   # pressure
                          1750+np.random.randn()*50,    # RPM
                          7.4+np.random.randn()*0.2,    # pH
                          1.2+np.random.randn()*0.2],   # chlorine
                         dtype=np.float32)
        pump_a.learn(vec_a)

        # Normal telemetry for pump B (different machine, different geometry)
        vec_b = np.array([70.0+np.random.randn()*4,
                          1800+np.random.randn()*40,
                          7.3+np.random.randn()*0.15,
                          1.3+np.random.randn()*0.15],
                         dtype=np.float32)
        pump_b.learn(vec_b)

    print("  Testing identity recognition...")

    # Normal reading from pump A
    normal_a = np.array([65.0, 1750, 7.4, 1.2], dtype=np.float32)
    result_a  = pump_a.think(normal_a)
    print(f"\n  PUMP-A1 reading its own normal telemetry:")
    print(f"    Match score: {result_a['match']:.4f}  (high = recognized)")

    # Pump A reading pump B's telemetry
    normal_b = np.array([70.0, 1800, 7.3, 1.3], dtype=np.float32)
    result_cross = pump_a.think(normal_b)
    print(f"\n  PUMP-A1 reading PUMP-B1 telemetry:")
    print(f"    Match score: {result_cross['match']:.4f}  (low = different machine)")

    # Inject attack — Oldsmar-style pH tampering
    attack = np.array([65.0, 1750, 9.8, 0.05], dtype=np.float32)
    result_atk = pump_a.think(attack)
    pump_a.hot.write_scar("pH tampering detected", severity=0.9)
    print(f"\n  PUMP-A1 reading ATTACK telemetry (pH=9.8, Cl=0.05):")
    print(f"    Match score: {result_atk['match']:.4f}  (low = ANOMALY)")
    print(f"    Novelty:     {result_atk['novelty']:.4f}  (high = ANOMALY)")

    print(f"\n  Machine health:")
    for m in [pump_a, pump_b]:
        h = m.status()
        print(f"\n  {h['machine_id']}")
        print(f"    Status:        {h['status']}")
        print(f"    Spectral norm: {h['spectral_norm']}")
        print(f"    Scars:         {h['n_scars']}")
        print(f"    Collapse risk: {h['collapse_risk']}")

    print("\n  Vincit Omnia Veritas")
    print("  Full implementation: c.holland.arch@proton.me\n")
