"""
Tourist Route Planner - BACKEND
================================
Owns: the graph, the 6 search algorithms, multi-location ordering (Nearest
Neighbor Heuristic), the cost function, statistics, exploration history,
alternative-route generation and route-explanation generation. It has no
knowledge of how anything is displayed (see SDD §1).

Run with:   pip install flask
            python backend.py
Serves on:  http://localhost:5000

NOTE ON DATA ORIGIN (SDD §4.0): a real deployment reads processed_nodes.csv /
processed_edges.csv produced offline by an OSMnx pipeline. Since that raw
OSM extraction can't run in this environment, this file generates a
synthetic-but-structured road network for HCMC District 1 (a grid of streets
over the real District-1 bounding box, with real landmark POIs snapped onto
it) that carries exactly the same fields (distance, travel_time, congestion,
risk, road_type, average_speed) the rest of the system depends on. Swapping
this generator for a real CSV loader later requires touching only
`build_graph()` below - nothing else in the file depends on where NODES/ADJ
came from. Coordinates are exported un-projected (real lat/lon degrees), so
the §4.0 projection pitfall does not apply here.
"""

import heapq
import itertools
import math
import random
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, request

app = Flask(__name__)
random.seed(7)

# ---------------------------------------------------------------------------
# 0. CORS (manual, so this file has no dependency beyond Flask itself)
# ---------------------------------------------------------------------------
@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


# ---------------------------------------------------------------------------
# 1. GRAPH GENERATION  (stand-in for the offline OSMnx pipeline, SDD §4.0)
# ---------------------------------------------------------------------------
# Real District-1, Ho Chi Minh City bounding box
LAT_MIN, LAT_MAX = 10.765, 10.792
LON_MIN, LON_MAX = 106.688, 106.708
GRID_ROWS, GRID_COLS = 10, 10

# Rows/cols treated as major avenues (higher speed, more congestion variance)
PRIMARY_ROWS = {0, 4, 9}
PRIMARY_COLS = {0, 4, 9}

NODES = {}                       # node_id -> {id, r, c, lat, lon, name}
ADJ = defaultdict(dict)          # node_id -> {neighbor_id: edge_attrs}


def node_id(r, c):
    return r * GRID_COLS + c


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def edge_is_primary(n1, n2):
    r1, c1 = NODES[n1]["r"], NODES[n1]["c"]
    r2, c2 = NODES[n2]["r"], NODES[n2]["c"]
    if r1 == r2 and r1 in PRIMARY_ROWS:
        return True
    if c1 == c2 and c1 in PRIMARY_COLS:
        return True
    return False


def make_edge(n1, n2):
    lat1, lon1 = NODES[n1]["lat"], NODES[n1]["lon"]
    lat2, lon2 = NODES[n2]["lat"], NODES[n2]["lon"]
    dist = haversine(lat1, lon1, lat2, lon2) * random.uniform(1.0, 1.15)

    if edge_is_primary(n1, n2):
        road_type = "primary"
    else:
        road_type = random.choices(["secondary", "tertiary", "residential"], weights=[45, 35, 20])[0]

    base_speed = {"primary": 45, "secondary": 32, "tertiary": 26, "residential": 18}[road_type]
    speed = max(8.0, base_speed + random.uniform(-3, 3))

    congestion_weights = {
        "primary": [5, 10, 25, 35, 25],
        "secondary": [10, 25, 30, 25, 10],
        "tertiary": [25, 30, 25, 15, 5],
        "residential": [35, 30, 20, 10, 5],
    }[road_type]
    congestion = random.choices([1, 2, 3, 4, 5], weights=congestion_weights)[0]

    risk_range = {
        "primary": (0.0, 0.25),
        "secondary": (0.1, 0.4),
        "tertiary": (0.2, 0.5),
        "residential": (0.2, 0.6),
    }[road_type]
    risk = random.uniform(*risk_range)

    speed_mps = speed * 1000.0 / 3600.0
    base_time = dist / speed_mps
    congestion_multiplier = 1 + (congestion - 1) * 0.18
    travel_time = base_time * congestion_multiplier

    return {
        "distance": dist,
        "travel_time": travel_time,
        "congestion": congestion,
        "risk": risk,
        "road_type": road_type,
        "average_speed": speed,
    }


def build_graph():
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            nid = node_id(r, c)
            lat = LAT_MIN + (LAT_MAX - LAT_MIN) * r / (GRID_ROWS - 1)
            lon = LON_MIN + (LON_MAX - LON_MIN) * c / (GRID_COLS - 1)
            NODES[nid] = {"id": nid, "r": r, "c": c, "lat": lat, "lon": lon, "name": None}

    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            nid = node_id(r, c)
            if c + 1 < GRID_COLS:
                n2 = node_id(r, c + 1)
                e = make_edge(nid, n2)
                ADJ[nid][n2] = dict(e)
                ADJ[n2][nid] = dict(e)
            if r + 1 < GRID_ROWS:
                n2 = node_id(r + 1, c)
                e = make_edge(nid, n2)
                ADJ[nid][n2] = dict(e)
                ADJ[n2][nid] = dict(e)

    # A few diagonal shortcuts so alternative routes are visually distinct
    for r in range(GRID_ROWS - 1):
        for c in range(GRID_COLS - 1):
            if random.random() < 0.15:
                n1, n2 = node_id(r, c), node_id(r + 1, c + 1)
                e = make_edge(n1, n2)
                ADJ[n1][n2] = dict(e)
                ADJ[n2][n1] = dict(e)


build_graph()

# ---------------------------------------------------------------------------
# 2. Named tourist points of interest, snapped onto the graph
# ---------------------------------------------------------------------------
LANDMARKS = [
    ("Notre-Dame Cathedral Basilica", 10.7797, 106.6990),
    ("Saigon Central Post Office", 10.7798, 106.6997),
    ("Independence (Reunification) Palace", 10.7772, 106.6953),
    ("Ben Thanh Market", 10.7720, 106.6980),
    ("Bitexco Financial Tower", 10.7716, 106.7040),
    ("War Remnants Museum", 10.7797, 106.6917),
    ("Saigon Opera House", 10.7765, 106.7031),
    ("Nguyen Hue Walking Street", 10.7745, 106.7030),
    ("Bui Vien Walking Street", 10.7679, 106.6935),
    ("Turtle Lake (Ho Con Rua)", 10.7822, 106.6949),
    ("Jade Emperor Pagoda", 10.7896, 106.6923),
    ("Saigon Zoo & Botanical Garden", 10.7877, 106.7053),
]


def find_nearest_node(lat, lon):
    best, best_d = None, float("inf")
    for n in NODES.values():
        d = haversine(lat, lon, n["lat"], n["lon"])
        if d < best_d:
            best_d, best = d, n["id"]
    return best


POIS = []
for i, (name, lat, lon) in enumerate(LANDMARKS):
    nid = find_nearest_node(lat, lon)
    node = NODES[nid]
    POIS.append({"poi_id": f"p{i + 1}", "name": name, "lat": node["lat"], "lon": node["lon"], "node_id": nid})
    if NODES[nid]["name"] is None:
        NODES[nid]["name"] = name


def node_display_name(nid):
    for p in POIS:
        if p["node_id"] == nid:
            return p["name"]
    n = NODES[nid]
    return f"Point ({n['lat']:.4f}, {n['lon']:.4f})"


# ---------------------------------------------------------------------------
# 3. COST FUNCTION  (SDD §3: Cost = a*Distance + b*Time + g*Congestion + d*Risk)
# ---------------------------------------------------------------------------
ALPHA, BETA, GAMMA, DELTA = 0.35, 0.30, 0.20, 0.15  # hybrid weights (sum = 1)


def edge_cost(e, mode):
    if mode == "distance":
        return e["distance"]
    if mode == "time":
        return e["travel_time"]
    # hybrid: normalize onto comparable scales, then weighted sum
    nd = e["distance"] / 1000.0        # km
    nt = e["travel_time"] / 60.0       # minutes
    nc = e["congestion"]               # already 1-5
    nr = e["risk"] * 5.0               # 0-5 scale
    return ALPHA * nd + BETA * nt + GAMMA * nc + DELTA * nr


MAX_SPEED_MPS = 45 * 1000.0 / 3600.0


def heuristic(n, goal, mode):
    d = haversine(NODES[n]["lat"], NODES[n]["lon"], NODES[goal]["lat"], NODES[goal]["lon"])
    if mode == "distance":
        return d
    if mode == "time":
        return d / MAX_SPEED_MPS
    return ALPHA * (d / 1000.0)  # admissible lower bound for hybrid mode


# ---------------------------------------------------------------------------
# 4. SEARCH ALGORITHMS
#    Each returns (path, exploration_order, frontier_snapshots)
# ---------------------------------------------------------------------------
def reconstruct(came_from, start, goal):
    if goal not in came_from:
        return None
    path, n = [], goal
    while n is not None:
        path.append(n)
        n = came_from[n]
    path.reverse()
    return path if path[0] == start else None


def bfs(start, goal):
    frontier = deque([start])
    came_from = {start: None}
    visited = {start}
    exploration, snapshots = [], []
    while frontier:
        snapshots.append(list(frontier))
        current = frontier.popleft()
        exploration.append(current)
        if current == goal:
            break
        for nbr in ADJ[current]:
            if nbr not in visited:
                visited.add(nbr)
                came_from[nbr] = current
                frontier.append(nbr)
    return reconstruct(came_from, start, goal), exploration, snapshots


def dfs(start, goal):
    stack = [start]
    came_from = {start: None}
    visited = {start}
    exploration, snapshots = [], []
    while stack:
        snapshots.append(list(stack))
        current = stack.pop()
        exploration.append(current)
        if current == goal:
            break
        for nbr in reversed(list(ADJ[current].keys())):
            if nbr not in visited:
                visited.add(nbr)
                came_from[nbr] = current
                stack.append(nbr)
    return reconstruct(came_from, start, goal), exploration, snapshots


def ucs(start, goal, mode):
    counter = itertools.count()
    heap = [(0.0, next(counter), start)]
    came_from = {start: None}
    cost_so_far = {start: 0.0}
    closed = set()
    exploration, snapshots = [], []
    while heap:
        snapshots.append([n for _, _, n in heap])
        cur_cost, _, current = heapq.heappop(heap)
        if current in closed:
            continue
        closed.add(current)
        exploration.append(current)
        if current == goal:
            break
        for nbr, e in ADJ[current].items():
            new_cost = cost_so_far[current] + edge_cost(e, mode)
            if nbr not in cost_so_far or new_cost < cost_so_far[nbr]:
                cost_so_far[nbr] = new_cost
                came_from[nbr] = current
                heapq.heappush(heap, (new_cost, next(counter), nbr))
    return reconstruct(came_from, start, goal), exploration, snapshots


def astar(start, goal, mode):
    counter = itertools.count()
    heap = [(heuristic(start, goal, mode), next(counter), start)]
    came_from = {start: None}
    cost_so_far = {start: 0.0}
    closed = set()
    exploration, snapshots = [], []
    while heap:
        snapshots.append([n for _, _, n in heap])
        _, _, current = heapq.heappop(heap)
        if current in closed:
            continue
        closed.add(current)
        exploration.append(current)
        if current == goal:
            break
        for nbr, e in ADJ[current].items():
            new_cost = cost_so_far[current] + edge_cost(e, mode)
            if nbr not in cost_so_far or new_cost < cost_so_far[nbr]:
                cost_so_far[nbr] = new_cost
                came_from[nbr] = current
                heapq.heappush(heap, (new_cost + heuristic(nbr, goal, mode), next(counter), nbr))
    return reconstruct(came_from, start, goal), exploration, snapshots


def gbfs(start, goal, mode):
    counter = itertools.count()
    heap = [(heuristic(start, goal, mode), next(counter), start)]
    came_from = {start: None}
    visited = set()
    exploration, snapshots = [], []
    while heap:
        snapshots.append([n for _, _, n in heap])
        _, _, current = heapq.heappop(heap)
        if current in visited:
            continue
        visited.add(current)
        exploration.append(current)
        if current == goal:
            break
        for nbr in ADJ[current]:
            if nbr not in visited and nbr not in came_from:
                came_from[nbr] = current
                heapq.heappush(heap, (heuristic(nbr, goal, mode), next(counter), nbr))
    return reconstruct(came_from, start, goal), exploration, snapshots


def bidirectional(start, goal, mode):
    if start == goal:
        return [start], [start], [[start]]
    counter = itertools.count()
    heap_f = [(0.0, next(counter), start)]
    heap_b = [(0.0, next(counter), goal)]
    cost_f, cost_b = {start: 0.0}, {goal: 0.0}
    came_f, came_b = {start: None}, {goal: None}
    closed_f, closed_b = set(), set()
    exploration, snapshots = [], []
    best, best_cost = None, float("inf")

    while heap_f and heap_b:
        snapshots.append([n for _, _, n in heap_f] + [n for _, _, n in heap_b])

        _, _, cur_f = heapq.heappop(heap_f)
        if cur_f not in closed_f:
            closed_f.add(cur_f)
            exploration.append(cur_f)
            if cur_f in closed_b and cost_f[cur_f] + cost_b[cur_f] < best_cost:
                best_cost, best = cost_f[cur_f] + cost_b[cur_f], cur_f
            for nbr, e in ADJ[cur_f].items():
                nc = cost_f[cur_f] + edge_cost(e, mode)
                if nbr not in cost_f or nc < cost_f[nbr]:
                    cost_f[nbr] = nc
                    came_f[nbr] = cur_f
                    heapq.heappush(heap_f, (nc, next(counter), nbr))

        if heap_b:
            _, _, cur_b = heapq.heappop(heap_b)
            if cur_b not in closed_b:
                closed_b.add(cur_b)
                exploration.append(cur_b)
                if cur_b in closed_f and cost_f[cur_b] + cost_b[cur_b] < best_cost:
                    best_cost, best = cost_f[cur_b] + cost_b[cur_b], cur_b
                for nbr, e in ADJ[cur_b].items():
                    nc = cost_b[cur_b] + edge_cost(e, mode)
                    if nbr not in cost_b or nc < cost_b[nbr]:
                        cost_b[nbr] = nc
                        came_b[nbr] = cur_b
                        heapq.heappush(heap_b, (nc, next(counter), nbr))

        if best is not None:
            top_f = heap_f[0][0] if heap_f else float("inf")
            top_b = heap_b[0][0] if heap_b else float("inf")
            if top_f + top_b >= best_cost:
                break

    if best is None:
        return None, exploration, snapshots

    path_f = []
    n = best
    while n is not None:
        path_f.append(n)
        n = came_f[n]
    path_f.reverse()
    path_b = []
    n = came_b[best]
    while n is not None:
        path_b.append(n)
        n = came_b[n]
    return path_f + path_b, exploration, snapshots


ALGO_NAMES = {
    "bfs": "Breadth-First Search",
    "dfs": "Depth-First Search",
    "ucs": "Uniform Cost Search",
    "astar": "A* Search",
    "gbfs": "Greedy Best-First Search",
    "bidirectional": "Bidirectional Search",
}

ALGORITHM_OPTIMALITY = {
    "bfs": {"optimal": False, "reason": "BFS only guarantees the fewest road segments (hops), not the lowest cost under the selected optimization criterion."},
    "dfs": {"optimal": False, "reason": "DFS explores depth-first and stops at the first path it finds, with no guarantee of minimal cost."},
    "ucs": {"optimal": True, "reason": "UCS always expands the lowest cumulative-cost frontier node first, which guarantees the optimal path for the selected criterion."},
    "astar": {"optimal": True, "reason": "A* combines true path cost with an admissible (never-overestimating) heuristic, which guarantees optimality."},
    "gbfs": {"optimal": False, "reason": "GBFS expands whichever node looks closest to the goal and ignores the cost already paid, so it can miss the optimal path."},
    "bidirectional": {"optimal": True, "reason": "This implementation runs cost-based (Dijkstra-style) search from both ends and proves optimality at the meeting point."},
}


def run_search(algorithm, start, goal, mode):
    t0 = time.perf_counter()
    if algorithm == "bfs":
        path, exp, front = bfs(start, goal)
    elif algorithm == "dfs":
        path, exp, front = dfs(start, goal)
    elif algorithm == "ucs":
        path, exp, front = ucs(start, goal, mode)
    elif algorithm == "astar":
        path, exp, front = astar(start, goal, mode)
    elif algorithm == "gbfs":
        path, exp, front = gbfs(start, goal, mode)
    elif algorithm == "bidirectional":
        path, exp, front = bidirectional(start, goal, mode)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    exec_ms = (time.perf_counter() - t0) * 1000.0
    return path, exp, front, exec_ms


# ---------------------------------------------------------------------------
# 5. STATISTICS  (SDD §3 / §4: distance, time, congestion, risk, total cost)
# ---------------------------------------------------------------------------
def compute_stats(path, mode):
    if not path or len(path) < 1:
        return None
    total_distance = total_time = total_congestion = total_risk = total_cost = 0.0
    edges_detail = []
    for i in range(len(path) - 1):
        n1, n2 = path[i], path[i + 1]
        e = ADJ[n1][n2]
        total_distance += e["distance"]
        total_time += e["travel_time"]
        total_congestion += e["congestion"]
        total_risk += e["risk"]
        total_cost += edge_cost(e, "hybrid")  # total route cost is always the hybrid formula (SDD §3)
        edges_detail.append({"from": n1, "to": n2, **e})
    return {
        "distance_m": round(total_distance, 1),
        "time_s": round(total_time, 1),
        "congestion_total": round(total_congestion, 2),
        "risk_total": round(total_risk, 3),
        "total_cost": round(total_cost, 3),
        "edges": edges_detail,
    }


# ---------------------------------------------------------------------------
# 6. ALTERNATIVE ROUTE  (SDD §4.2: same algorithm family, penalized primary edges)
# ---------------------------------------------------------------------------
def generate_alternative(start, goal, mode, primary_path):
    if not primary_path or len(primary_path) < 2:
        return None
    penalty = 6.0
    pairs = list(zip(primary_path, primary_path[1:]))
    for n1, n2 in pairs:
        ADJ[n1][n2]["distance"] *= penalty
        ADJ[n1][n2]["travel_time"] *= penalty
        ADJ[n2][n1]["distance"] *= penalty
        ADJ[n2][n1]["travel_time"] *= penalty
    try:
        alt_path, _, _ = ucs(start, goal, mode)
    finally:
        for n1, n2 in pairs:
            ADJ[n1][n2]["distance"] /= penalty
            ADJ[n1][n2]["travel_time"] /= penalty
            ADJ[n2][n1]["distance"] /= penalty
            ADJ[n2][n1]["travel_time"] /= penalty

    if not alt_path or alt_path == primary_path:
        fallback, _, _ = dfs(start, goal)
        if fallback and fallback != primary_path:
            return fallback
        return None
    return alt_path


# ---------------------------------------------------------------------------
# 7. ROUTE EXPLANATION  (SDD §4.1 / assignment §4.8)
# ---------------------------------------------------------------------------
MODE_LABEL = {"distance": "total distance", "time": "total travel time", "hybrid": "total route cost"}
STAT_KEY = {"distance": "distance_m", "time": "time_s", "hybrid": "total_cost"}
STAT_UNIT = {"distance": "m", "time": "s", "hybrid": "cost units"}


def build_explanation(algorithm, mode, primary_stats, alt_stats):
    key = STAT_KEY[mode]
    unit = STAT_UNIT[mode]
    optimality = ALGORITHM_OPTIMALITY[algorithm]

    primary_val = primary_stats[key]
    alt_val = alt_stats[key] if alt_stats else None

    if alt_stats is None:
        text = (
            f"The route returned by {ALGO_NAMES[algorithm]} has a {MODE_LABEL[mode]} of "
            f"{primary_val:.1f} {unit}, and no valid alternative route could be found for comparison."
        )
    elif primary_val < alt_val:
        text = (
            f"The route returned by {ALGO_NAMES[algorithm]} is the better choice here: it has the lower "
            f"{MODE_LABEL[mode]} of the two routes considered ({primary_val:.1f} {unit} versus "
            f"{alt_val:.1f} {unit} for the alternative route)."
        )
    elif primary_val > alt_val:
        text = (
            f"The route returned by {ALGO_NAMES[algorithm]} actually has a higher {MODE_LABEL[mode]} than the "
            f"alternative route it is being compared against ({primary_val:.1f} {unit} versus {alt_val:.1f} {unit}). "
            f"This is possible because {optimality['reason']} If a guaranteed lowest-cost route is required, "
            f"use UCS, A*, or Bidirectional Search instead."
        )
    else:
        text = (
            f"The route returned by {ALGO_NAMES[algorithm]} ties the alternative route on {MODE_LABEL[mode]} "
            f"({primary_val:.1f} {unit} each), so the two are equivalent on the selected criterion."
        )

    if alt_stats:
        congested = [e for e in alt_stats["edges"] if e["congestion"] >= 4 or e["average_speed"] < 22]
        if congested:
            examples = "; ".join(
                f"a {e['road_type']} segment (congestion {e['congestion']}/5, avg speed {e['average_speed']:.0f} km/h)"
                for e in congested[:3]
            )
            text += (
                f" The alternative route passes through {len(congested)} congested/slow segment(s), including "
                f"{examples}, which raises its estimated travel time and risk."
            )
        else:
            text += " The alternative route does not pass through any notably congested segments."

    text += (
        f" {ALGO_NAMES[algorithm]} "
        + ("guarantees" if optimality["optimal"] else "does not guarantee")
        + f" that the returned route is optimal for the selected criterion: {optimality['reason']}"
    )
    return text


def build_multi_explanation(algorithm, mode, order_with_start, legs):
    names = [node_display_name(n) for n in order_with_start]
    total_cost = sum(l["stats"]["total_cost"] for l in legs if l["stats"])
    text = (
        "Starting from your chosen location, the Nearest Neighbor Heuristic determined the visiting order: "
        + " -> ".join(names)
        + f". For each leg, {ALGO_NAMES[algorithm]} computed the {MODE_LABEL[mode]}-optimized route between "
        f"consecutive stops, for a combined total cost of {total_cost:.1f} across the whole itinerary. "
        "Note that the Nearest Neighbor Heuristic provides a fast, practical visiting order but does not "
        "guarantee the globally optimal sequence (a classic limitation of greedy nearest-neighbor "
        "construction in TSP-style problems) - a different ordering could, in principle, produce a shorter "
        "overall itinerary."
    )
    return text


# ---------------------------------------------------------------------------
# 8. MULTI-LOCATION: Nearest Neighbor Heuristic + leg execution  (SDD §2.2, §4.4)
# ---------------------------------------------------------------------------
def nearest_neighbor_order(start, destinations):
    remaining = set(destinations)
    order = []
    current = start
    while remaining:
        nxt = min(
            remaining,
            key=lambda d: haversine(NODES[current]["lat"], NODES[current]["lon"], NODES[d]["lat"], NODES[d]["lon"]),
        )
        order.append(nxt)
        remaining.remove(nxt)
        current = nxt
    return order


def run_itinerary(algorithm, start, destinations, mode):
    order = nearest_neighbor_order(start, destinations)
    seq = [start] + order
    legs = []
    full_path = []
    totals = {"distance_m": 0.0, "time_s": 0.0, "congestion_total": 0.0, "risk_total": 0.0, "total_cost": 0.0}

    for i in range(len(seq) - 1):
        s, g = seq[i], seq[i + 1]
        path, exp, front, exec_ms = run_search(algorithm, s, g, mode)
        stats = compute_stats(path, mode) if path else None
        legs.append(
            {
                "from": s,
                "to": g,
                "path": path,
                "stats": stats,
                "exploration_sequence": exp,
                "frontier_snapshots": front,
                "execution_time_ms": exec_ms,
                "expanded_nodes": len(exp),
            }
        )
        if path:
            if full_path and full_path[-1] == path[0]:
                full_path.extend(path[1:])
            else:
                full_path.extend(path)
            for k in totals:
                totals[k] += stats[k]

    return order, legs, full_path, totals


# ---------------------------------------------------------------------------
# 9. API
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Tourist Route Planner backend is running.",
                     "endpoints": ["/api/locations", "/api/network", "/api/search (POST)"]})


@app.route("/api/locations")
def api_locations():
    return jsonify(POIS)


@app.route("/api/network")
def api_network():
    nodes = [{"id": n["id"], "lat": n["lat"], "lon": n["lon"]} for n in NODES.values()]
    edges, seen = [], set()
    for n1, nbrs in ADJ.items():
        for n2, e in nbrs.items():
            key = tuple(sorted((n1, n2)))
            if key in seen:
                continue
            seen.add(key)
            edges.append({"from": n1, "to": n2, "road_type": e["road_type"]})
    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/search", methods=["POST", "OPTIONS"])
def api_search():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(force=True, silent=True) or {}
    algorithm = data.get("algorithm", "astar")
    mode = data.get("optimization", "hybrid")

    if algorithm not in ALGO_NAMES:
        return jsonify({"error": f"Unknown algorithm '{algorithm}'"}), 400
    if mode not in ("distance", "time", "hybrid"):
        return jsonify({"error": f"Unknown optimization mode '{mode}'"}), 400

    try:
        start = int(data["start"])
        destinations = [int(d) for d in data["destinations"] if int(d) != start]
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Request must include a valid 'start' and a non-empty 'destinations' list"}), 400

    if not destinations:
        return jsonify({"error": "At least one destination is required"}), 400

    # --- Behavior is inferred purely from destination-list length (SDD §4, §5.3, §6.1) ---
    if len(destinations) == 1:
        goal = destinations[0]
        path, exp, front, exec_ms = run_search(algorithm, start, goal, mode)
        if not path:
            return jsonify({"error": "No path found between the selected locations"}), 404

        stats = compute_stats(path, mode)
        alt_path = generate_alternative(start, goal, mode, path)
        alt_stats = compute_stats(alt_path, mode) if alt_path else None

        congested_segments = []
        if alt_stats:
            for e in alt_stats["edges"]:
                if e["congestion"] >= 4 or e["average_speed"] < 22:
                    congested_segments.append(
                        {
                            "from": e["from"],
                            "to": e["to"],
                            "road_type": e["road_type"],
                            "congestion": e["congestion"],
                            "average_speed": round(e["average_speed"], 1),
                        }
                    )

        explanation = build_explanation(algorithm, mode, stats, alt_stats)

        return jsonify(
            {
                "mode": "single",
                "algorithm": algorithm,
                "algorithm_name": ALGO_NAMES[algorithm],
                "optimization": mode,
                "optimal_guaranteed": ALGORITHM_OPTIMALITY[algorithm]["optimal"],
                "exploration_sequence": exp,
                "frontier_snapshots": front,
                "primary_path": path,
                "alternative_path": alt_path,
                "congested_segments": congested_segments,
                "route_explanation": explanation,
                "statistics": {
                    "algorithm": ALGO_NAMES[algorithm],
                    "distance_m": stats["distance_m"],
                    "time_s": stats["time_s"],
                    "congestion_total": stats["congestion_total"],
                    "risk_total": stats["risk_total"],
                    "total_cost": stats["total_cost"],
                    "expanded_nodes": len(exp),
                    "execution_time_ms": round(exec_ms, 3),
                    "alternative": (
                        {
                            "distance_m": alt_stats["distance_m"],
                            "time_s": alt_stats["time_s"],
                            "congestion_total": alt_stats["congestion_total"],
                            "risk_total": alt_stats["risk_total"],
                            "total_cost": alt_stats["total_cost"],
                        }
                        if alt_stats
                        else None
                    ),
                },
            }
        )

    # --- Multi-location itinerary ---
    order, legs, full_path, totals = run_itinerary(algorithm, start, destinations, mode)
    if not full_path:
        return jsonify({"error": "Could not compute an itinerary for the selected destinations"}), 404

    return jsonify(
        {
            "mode": "multi",
            "algorithm": algorithm,
            "algorithm_name": ALGO_NAMES[algorithm],
            "optimization": mode,
            "optimal_guaranteed": ALGORITHM_OPTIMALITY[algorithm]["optimal"],
            "visiting_order": order,
            "legs": [
                {
                    "from": l["from"],
                    "to": l["to"],
                    "path": l["path"],
                    "exploration_sequence": l["exploration_sequence"],
                    "frontier_snapshots": l["frontier_snapshots"],
                    "stats": l["stats"],
                    "execution_time_ms": round(l["execution_time_ms"], 3),
                    "expanded_nodes": l["expanded_nodes"],
                }
                for l in legs
            ],
            "complete_itinerary": full_path,
            "statistics": {
                "algorithm": ALGO_NAMES[algorithm],
                "distance_m": round(totals["distance_m"], 1),
                "time_s": round(totals["time_s"], 1),
                "congestion_total": round(totals["congestion_total"], 2),
                "risk_total": round(totals["risk_total"], 3),
                "total_cost": round(totals["total_cost"], 3),
                "expanded_nodes": sum(l["expanded_nodes"] for l in legs),
                "execution_time_ms": round(sum(l["execution_time_ms"] for l in legs), 3),
            },
            "route_explanation": build_multi_explanation(algorithm, mode, [start] + order, legs),
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
