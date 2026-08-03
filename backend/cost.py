"""
Cost function module — weight tuples and min-max normalisation.

Two search criteria:
  • Shortest — emphasises physical distance
  • Fastest  — emphasises travel time + congestion avoidance
"""

from dataclasses import dataclass
from typing import Dict, Tuple

# ── Weight tuples ──────────────────────────────────────────────────────
# (w_distance, w_time, w_congestion, w_risk)
SHORTEST_WEIGHTS = (0.7, 0.1, 0.1, 0.1)
FASTEST_WEIGHTS  = (0.1, 0.5, 0.3, 0.1)

CRITERIA = {
    "shortest": SHORTEST_WEIGHTS,
    "fastest":  FASTEST_WEIGHTS,
}


@dataclass
class NormBounds:
    """Global min/max for each raw feature, computed once on graph load."""
    d_min: float = 0.0
    d_max: float = 1.0
    t_min: float = 0.0
    t_max: float = 1.0
    c_min: float = 0.0
    c_max: float = 1.0
    r_min: float = 0.0
    r_max: float = 1.0


def compute_norm_bounds(edges: list) -> NormBounds:
    """
    Compute min-max bounds across all edges.
    *edges* is a list of dicts, each with keys: distance, time, congestion, risk.
    """
    if not edges:
        return NormBounds()

    distances   = [e["distance"]   for e in edges]
    times       = [e["time"]       for e in edges]
    congestions = [e["congestion"] for e in edges]
    risks       = [e["risk"]       for e in edges]

    return NormBounds(
        d_min=min(distances),   d_max=max(distances),
        t_min=min(times),       t_max=max(times),
        c_min=min(congestions),  c_max=max(congestions),
        r_min=min(risks),       r_max=max(risks),
    )


def _normalise(value: float, vmin: float, vmax: float) -> float:
    """Min-max normalisation; returns 0 when range is zero."""
    if vmax == vmin:
        return 0.0
    return (value - vmin) / (vmax - vmin)


def edge_cost(
    edge: dict,
    weights: Tuple[float, float, float, float],
    bounds: NormBounds,
) -> float:
    """
    Weighted normalised cost of a single edge.

    cost = w_d·d̂ + w_t·t̂ + w_c·ĉ + w_r·r̂
    """
    wd, wt, wc, wr = weights

    d_hat = _normalise(edge["distance"],   bounds.d_min, bounds.d_max)
    t_hat = _normalise(edge["time"],       bounds.t_min, bounds.t_max)
    c_hat = _normalise(edge["congestion"], bounds.c_min, bounds.c_max)
    r_hat = _normalise(edge["risk"],       bounds.r_min, bounds.r_max)

    return wd * d_hat + wt * t_hat + wc * c_hat + wr * r_hat


def heuristic_cost(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    weights: Tuple[float, float, float, float],
    bounds: NormBounds,
) -> float:
    """
    Admissible heuristic for A* / GBFS.

    Uses haversine distance normalised by the same distance bounds,
    multiplied by the distance weight.  Since this is a lower bound
    on the true edge cost, it remains admissible.
    """
    import math
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    haversine_m = 2 * R * math.asin(math.sqrt(a))

    # Normalise the haversine distance using global distance bounds
    d_hat = _normalise(haversine_m, bounds.d_min, bounds.d_max)

    # Use the smallest weight to guarantee admissibility
    min_w = min(w for w in weights if w > 0)
    return min_w * d_hat
