"""
MCP RETA Memory — Serveur de mémoire contextuelle RETA pour LLM.

Valide end-to-end :
  - Kalman v1.3 (adaptatif Q, R)
  - PI v1.2 gradient (Kp, Ki auto)
  - ConversationMemory (O(n + k·s))
  - Fusion de référentiels (⊕)
  - Navigation O(1) entre états passés
  - Compression 2020× vs mémoire classique

Lancer :
  uv run python simulations/mcp_reta_memory.py

Tester avec le client MCP ou Claude Desktop (ajouter dans settings.json) :
  {
    "mcpServers": {
      "reta-memory": {
        "command": "uv",
        "args": ["run", "python", "simulations/mcp_reta_memory.py"]
      }
    }
  }
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# Ajouter le root du projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Persistance fichier ───────────────────────────────────────────────────────

STORE_PATH = Path(__file__).parent / "reta_store.json"


def _load_store() -> dict:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"sessions": {}, "referentiels": {}}


def _save_store(sessions: dict, referentiels: dict) -> None:
    data = {
        "saved_at": datetime.utcnow().isoformat(),
        "sessions": {
            sid: {
                "session_id":  mem.session_id,
                "n_tokens":    mem.n_tokens,
                "y_current":   mem.y_current,
                "signatures": [
                    {
                        "turn_id":   s.turn_id,
                        "tour_type": s.tour_type,
                        "eps":       s.eps,
                        "z_mean":    s.z_mean,
                        "delta_y":   s.delta_y,
                        "ts":        s.ts.isoformat(),
                        "label":     s.label,
                    }
                    for s in mem.signatures
                ],
            }
            for sid, mem in sessions.items()
        },
        "referentiels": {
            lbl: ref.encode() | {"version": ref.version}
            for lbl, ref in referentiels.items()
        },
    }
    STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _restore(store: dict) -> tuple[dict, dict]:
    """Recharge sessions et référentiels depuis le store JSON."""
    sessions: dict[str, ConversationMemory] = {}
    referentiels: dict[str, RETAReferential] = {}
    # Sessions restaurées après import des classes (appelé plus bas)
    return sessions, referentiels

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from reta import RETAReferential, KalmanAdaptive, fusion, navigate
from reta.llm import (
    TurnSignature, ConversationMemory,
    compression_ratio, reconstruction_error, efficiency_eta,
    reconstruct_at, reconstruct_trajectory,
    merge_memories, to_prompt_context, efficiency_report,
    needs_checkpoint,
)
from reta.pi import PIRegulator

# ── État global du serveur ────────────────────────────────────────────────────

P_INF  = 0.4316   # variance Kalman convergée (doc efficience §3)
EPS    = 0.5858   # perturbation minimale RETA (2 − √2)

# Chargement initial depuis le fichier
_store = _load_store()
_sessions: dict[str, ConversationMemory] = {}
_referentiels: dict[str, RETAReferential] = {}

def _init_from_store(store: dict) -> None:
    """Recharge l'état persisté au démarrage."""
    for sid, s in store.get("sessions", {}).items():
        mem = ConversationMemory(session_id=sid, n_tokens=s["n_tokens"])
        mem.y_current = s["y_current"]
        for sig_d in s["signatures"]:
            sig = TurnSignature(
                turn_id=sig_d["turn_id"],
                tour_type=sig_d["tour_type"],
                eps=sig_d["eps"],
                z_mean=sig_d["z_mean"],
                delta_y=sig_d["delta_y"],
                ts=datetime.fromisoformat(sig_d["ts"]),
                label=sig_d["label"],
            )
            mem.signatures.append(sig)
        _sessions[sid] = mem

    for lbl, payload in store.get("referentiels", {}).items():
        _referentiels[lbl] = RETAReferential.from_encoded(payload)

app = Server("reta-memory")

# ── Outils MCP ────────────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="reta_new_session",
            description=(
                "Crée une nouvelle session de mémoire RETA. "
                "Chaque session est une ConversationMemory O(n + k·s)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Identifiant unique de session"},
                    "n_tokens":   {"type": "integer", "default": 1000,
                                   "description": "Taille d'un tour en tokens (doc efficience §1)"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="reta_add_turn",
            description=(
                "Ajoute un tour de conversation à la mémoire RETA. "
                "Types : 'expansion' (+∫z dτ, nouveau contexte), "
                "'contraction' (−∫u dτ, correction PI), "
                "'stabilisation' (Δy→0, confirmation). "
                "Coût : 1 signature de ~15 tokens, jamais O(k)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "content":    {"type": "string",
                                   "description": "Contenu du tour (estimé pour calculer z)"},
                    "tour_type":  {"type": "string", "enum": ["expansion", "contraction", "stabilisation"],
                                   "default": "expansion"},
                    "label":      {"type": "string", "default": ""},
                },
                "required": ["session_id", "content"],
            },
        ),
        Tool(
            name="reta_get_context",
            description=(
                "Retourne le contexte RETA compact pour injection dans le system prompt. "
                "Format : état courant y_k + dernières signatures. "
                "Coût : O(s) tokens au lieu de O(n·k) en classique."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "last_n":     {"type": "integer", "default": 5,
                                   "description": "Nombre de derniers tours à inclure"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="reta_reconstruct",
            description=(
                "Reconstruit l'état de la mémoire au tour j depuis l'état courant k. "
                "Descente par substitution : y_j = y_k − Σ Δy_i (O(k−j) ops). "
                "Erreur garantie ≤ P∞ · (k−j) = 0.4316 · (k−j)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id":  {"type": "string"},
                    "target_turn": {"type": "integer",
                                   "description": "Tour à reconstruire (0 = intention initiale)"},
                },
                "required": ["session_id", "target_turn"],
            },
        ),
        Tool(
            name="reta_fit_referentiel",
            description=(
                "Ajuste un référentiel RETA v1.3 (Chameleon) sur une série numérique. "
                "Kalman adaptatif : Q et R s'auto-calibrent depuis les innovations. "
                "Retourne : phase (BULL/BEAR/NEUTRE), z_last, t_rupture, qualité signal."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "label":   {"type": "string", "description": "Nom du référentiel"},
                    "series":  {"type": "array", "items": {"type": "number"},
                               "description": "Série de prix ou de valeurs"},
                    "version": {"type": "string", "enum": ["v1.1", "v1.2", "v1.3"],
                               "default": "v1.3"},
                },
                "required": ["label", "series"],
            },
        ),
        Tool(
            name="reta_fusion",
            description=(
                "Fusionne deux référentiels RETA avec α ∈ [0,1]. "
                "y_fusion = α·y_A + (1−α)·y_B  (doc fusion_referentiels.md). "
                "Navigation O(1) via Δz = z_B − z_A."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "label_a":     {"type": "string"},
                    "label_b":     {"type": "string"},
                    "alpha":       {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5},
                    "label_out":   {"type": "string", "description": "Nom du référentiel fusionné"},
                },
                "required": ["label_a", "label_b"],
            },
        ),
        Tool(
            name="reta_efficiency",
            description=(
                "Rapport d'efficience RETA vs mémoire classique. "
                "Reproduit le tableau doc efficience_memoire.md §6 : "
                "ratio compression, η_RETA, gain η, erreur reconstruction."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session à analyser (optionnel)"},
                    "n":   {"type": "integer", "default": 1000},
                    "k":   {"type": "integer", "default": 100},
                    "s":   {"type": "integer", "default": 15},
                },
                "required": [],
            },
        ),
        Tool(
            name="reta_list",
            description="Liste toutes les sessions et référentiels actifs.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="reta_reload",
            description=(
                "Recharge l'état depuis le fichier store JSON. "
                "À utiliser si le store a été modifié en dehors du serveur MCP "
                "(script externe, autre process). Fusionne : les nouvelles sessions/référentiels "
                "du fichier sont ajoutés, les existants en mémoire sont mis à jour si le fichier "
                "en a une version plus avancée (k plus grand)."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


# ── Handlers ─────────────────────────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
    except Exception as e:
        result = f"❌ Erreur : {e}"
    return [TextContent(type="text", text=str(result))]


async def _dispatch(name: str, args: dict) -> str:

    # ── reta_new_session ──────────────────────────────────────────────────────
    if name == "reta_new_session":
        sid = args["session_id"]
        _sessions[sid] = ConversationMemory(
            session_id=sid,
            n_tokens=args.get("n_tokens", 1000),
        )
        _save_store(_sessions, _referentiels)
        return (
            f"✅ Session '{sid}' créée.\n"
            f"   Stockage RETA : O(n + k·s) = O({args.get('n_tokens',1000)} + k·15)\n"
            f"   vs classique  : O(n × k)   — avantage dès le tour 2.\n"
            f"   💾 Persisté dans : {STORE_PATH}"
        )

    # ── reta_add_turn ─────────────────────────────────────────────────────────
    elif name == "reta_add_turn":
        sid = args["session_id"]
        if sid not in _sessions:
            return f"❌ Session '{sid}' introuvable. Créer avec reta_new_session."

        mem      = _sessions[sid]
        content  = args["content"]
        typ      = args.get("tour_type", "expansion")
        label    = args.get("label", "")

        # Estimer z depuis le contenu : entropie normalisée → dérive sémantique
        words   = content.split()
        n_words = len(words)
        # z_mean ≈ log(1 + n_words/100) * 0.01 — signal monotone positif
        z_mean  = float(np.log1p(n_words / 100.0) * 0.01)
        eps_i   = max(z_mean * 0.8, 1e-5)
        delta_y = z_mean * 10.0 if typ == "expansion" else z_mean * 5.0

        sig = TurnSignature(
            turn_id   = mem.k + 1,
            tour_type = typ,
            eps       = eps_i,
            z_mean    = z_mean,
            delta_y   = delta_y,
            ts        = datetime.utcnow(),
            label     = label or content[:40],
        )
        mem.add_turn(sig)
        _save_store(_sessions, _referentiels)

        k   = mem.k
        r   = compression_ratio(mem.n_tokens, k) if k > 0 else 1
        err = reconstruction_error(P_INF, k, k - 1) if k > 1 else 0.0
        chk = " ⚠️ checkpoint recommandé" if needs_checkpoint(mem) else ""

        return (
            f"✅ Tour #{k} ajouté [{typ.upper()[:3]}]\n"
            f"   {sig}\n"
            f"   y_current = {mem.y_current:+.5f}\n"
            f"   Compression actuelle : {r:.0f}×  |  "
            f"erreur rec. dernier tour ≤ {err:.4f}{chk}"
        )

    # ── reta_get_context ──────────────────────────────────────────────────────
    elif name == "reta_get_context":
        sid = args["session_id"]
        if sid not in _sessions:
            return f"❌ Session '{sid}' introuvable."
        mem    = _sessions[sid]
        last_n = args.get("last_n", 5)
        return to_prompt_context(mem, P_inf=P_INF, last_n=last_n)

    # ── reta_reconstruct ──────────────────────────────────────────────────────
    elif name == "reta_reconstruct":
        sid = args["session_id"]
        if sid not in _sessions:
            return f"❌ Session '{sid}' introuvable."
        mem    = _sessions[sid]
        target = args["target_turn"]
        k      = mem.k

        y_j  = reconstruct_at(mem, target)
        traj = reconstruct_trajectory(mem)
        err  = reconstruction_error(P_INF, k, target)

        lines = [
            f"🔍 Reconstruction tour {target} depuis k={k}",
            f"   y_{target} = {y_j:+.6f}",
            f"   Erreur garantie ≤ P∞ · (k−j) = {P_INF} × {k-target} = {err:.4f}",
            f"   Coût : {k - target} soustractions (vs relire {k - target} tours en classique)",
            f"\n   Trajectoire complète :",
        ]
        for i, y in enumerate(traj):
            marker = " ← cible" if i == target else (" ← courant" if i == k else "")
            lines.append(f"     y_{i} = {y:+.6f}{marker}")
        return "\n".join(lines)

    # ── reta_fit_referentiel ──────────────────────────────────────────────────
    elif name == "reta_fit_referentiel":
        label   = args["label"]
        series  = np.array(args["series"], dtype=float)
        version = args.get("version", "v1.3")

        ref = RETAReferential(version=version).fit(series)
        _referentiels[label] = ref
        _save_store(_sessions, _referentiels)

        enc = ref.encode()
        kalman_info = ""
        if version == "v1.3" and hasattr(ref, "_kalman"):
            k = ref._kalman
            kalman_info = (
                f"\n   Kalman adaptatif v1.3 :\n"
                f"     R : {ref.R:.2e} → {k.R_current:.2e}  (auto-ajusté)\n"
                f"     Q : {ref.Q:.2e} → {k.Q_current:.2e}  (auto-ajusté)\n"
                f"     Qualité signal : {k.signal_quality:.3f}"
            )

        return (
            f"✅ Référentiel '{label}' ({version}) ajusté sur {len(series)} points\n"
            f"   Phase   : {enc['phase']}\n"
            f"   z_last  : {enc['z_last']:.6f}\n"
            f"   ε       : {enc['eps']:.6f}\n"
            f"   t_rup   : {enc['t_rup']:.1f} barres\n"
            f"   P∞      : {enc['P_inf']:.6f}"
            f"{kalman_info}\n"
            f"   Encodé DB : {json.dumps(enc)}"
        )

    # ── reta_fusion ───────────────────────────────────────────────────────────
    elif name == "reta_fusion":
        la = args["label_a"]
        lb = args["label_b"]
        if la not in _referentiels:
            return f"❌ Référentiel '{la}' introuvable."
        if lb not in _referentiels:
            return f"❌ Référentiel '{lb}' introuvable."

        alpha     = args.get("alpha", 0.5)
        label_out = args.get("label_out", f"{la}⊕{lb}_a{alpha:.2f}")

        A = _referentiels[la]
        B = _referentiels[lb]
        F = fusion(A, B, alpha=alpha)
        _referentiels[label_out] = F
        _save_store(_sessions, _referentiels)

        delta = navigate(A, B)
        enc   = F.encode()

        return (
            f"✅ Fusion '{la}' ⊕ '{lb}' (α={alpha}) → '{label_out}'\n"
            f"   z_fusion = α·z_A + (1−α)·z_B = {enc['z_last']:.6f}\n"
            f"   ε_fusion = {enc['eps']:.6f}  |  t_rup = {enc['t_rup']:.1f}\n"
            f"   Phase fusionnée : {enc['phase']}\n"
            f"   Navigation O(1) A→B : Δz_final = {delta[-1]:.6f}\n"
            f"   (coût : 1 soustraction vs O(n²) transformation matricielle)"
        )

    # ── reta_efficiency ───────────────────────────────────────────────────────
    elif name == "reta_efficiency":
        sid = args.get("session_id")
        n   = args.get("n", 1000)
        s   = args.get("s", 15)

        if sid and sid in _sessions:
            mem = _sessions[sid]
            k   = mem.k if mem.k > 0 else 1
            n   = mem.n_tokens
        else:
            k = args.get("k", 100)

        chk = "⚠️  Checkpoint recommandé (k > 23)" if k > 23 else "✅ Pas de checkpoint nécessaire"
        return efficiency_report(n=n, k=k, P_inf=P_INF, eps=EPS, s=s) + f"\n{chk}"

    # ── reta_list ─────────────────────────────────────────────────────────────
    elif name == "reta_list":
        lines = [f"── Store : {STORE_PATH}  ({'existe' if STORE_PATH.exists() else 'non créé'})"]
        lines.append("── Sessions actives ─────────────────────────────────")
        if not _sessions:
            lines.append("  (aucune)")
        for sid, mem in _sessions.items():
            r = compression_ratio(mem.n_tokens, mem.k) if mem.k > 0 else 1
            lines.append(f"  {sid} : k={mem.k} tours  y={mem.y_current:+.5f}  compression={r:.0f}×")

        lines.append("\n── Référentiels actifs ──────────────────────────────")
        if not _referentiels:
            lines.append("  (aucun)")
        for lbl, ref in _referentiels.items():
            lines.append(f"  {lbl} : {ref}")

        return "\n".join(lines)

    # ── reta_reload ───────────────────────────────────────────────────────────
    elif name == "reta_reload":
        store = _load_store()
        added_s, updated_s, added_r, updated_r = 0, 0, 0, 0

        for sid, s in store.get("sessions", {}).items():
            mem_new = ConversationMemory(session_id=sid, n_tokens=s["n_tokens"])
            mem_new.y_current = s["y_current"]
            for sig_d in s["signatures"]:
                sig = TurnSignature(
                    turn_id=sig_d["turn_id"], tour_type=sig_d["tour_type"],
                    eps=sig_d["eps"], z_mean=sig_d["z_mean"], delta_y=sig_d["delta_y"],
                    ts=datetime.fromisoformat(sig_d["ts"]), label=sig_d["label"],
                )
                mem_new.signatures.append(sig)
            if sid not in _sessions:
                _sessions[sid] = mem_new
                added_s += 1
            elif mem_new.k > _sessions[sid].k:
                _sessions[sid] = mem_new
                updated_s += 1

        for lbl, payload in store.get("referentiels", {}).items():
            ref = RETAReferential.from_encoded(payload)
            if lbl not in _referentiels:
                _referentiels[lbl] = ref
                added_r += 1
            else:
                _referentiels[lbl] = ref
                updated_r += 1

        saved_at = store.get("saved_at", "?")
        return (
            f"🔄 Reload depuis {STORE_PATH}\n"
            f"   Sauvegardé le : {saved_at}\n"
            f"   Sessions  : +{added_s} nouvelles, {updated_s} mises à jour\n"
            f"   Référentiels : +{added_r} nouveaux, {updated_r} mis à jour\n"
            f"   Total en mémoire : {len(_sessions)} sessions, {len(_referentiels)} référentiels"
        )

    return f"❌ Outil inconnu : {name}"


# ── Entrée principale ─────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as streams:
        await app.run(
            streams[0], streams[1],
            app.create_initialization_options(),
        )

if __name__ == "__main__":
    import asyncio
    import sys as _sys
    _init_from_store(_store)
    n_s = len(_sessions)
    n_r = len(_referentiels)
    print(
        f"RETA Memory MCP Server démarré (stdio)\n"
        f"  Store : {STORE_PATH}\n"
        f"  Restauré : {n_s} session(s), {n_r} référentiel(s)",
        file=_sys.stderr,
    )
    asyncio.run(main())
