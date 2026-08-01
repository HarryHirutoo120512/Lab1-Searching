"""
Tourist Route Planner - BACKEND
================================
Cập nhật: Tự động dịch tọa độ UTM sang WGS84 và mapping địa danh.
Run with:   pip install flask pandas pyproj
            python backend.py
"""

import heapq
import itertools
import math
import time
import pandas as pd
from pyproj import Transformer
from collections import defaultdict, deque
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

# ---------------------------------------------------------------------------
# 1 & 2. GRAPH GENERATION FROM CSV & DYNAMIC POI MAPPING
# ---------------------------------------------------------------------------
NODES = {}               
ADJ = defaultdict(dict)  
POIS = []                

# Thay vì bắt file CSV phải có tên, Backend sẽ tự map 12 điểm du lịch Quận 1
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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))

def build_graph_from_csv():
    print("Loading graph from CSV files...")
    # Tọa độ trong file CSV đang ở hệ mét (UTM Zone 48N - EPSG:32648)
    # Cần dịch ngược về chuẩn GPS Lat/Lon (WGS84 - EPSG:4326) để Map Frontend hiển thị được
    transformer = Transformer.from_crs("EPSG:32648", "EPSG:4326", always_xy=True)
    
    try:
        nodes_df = pd.read_csv('processed_nodes.csv')
        for _, row in nodes_df.iterrows():
            nid = int(row['id'])
            # row['lat'] đang giữ UTM Y, row['lon'] đang giữ UTM X do osmnx project
            utm_x = float(row['lon'])
            utm_y = float(row['lat'])
            lon_wgs, lat_wgs = transformer.transform(utm_x, utm_y)
            
            NODES[nid] = {
                "id": nid,
                "lat": lat_wgs,
                "lon": lon_wgs,
                "name": None
            }
            
        # Tìm node gần nhất cho từng Landmark để tạo danh sách điểm đến
        for i, (name, lat, lon) in enumerate(LANDMARKS):
            best_id, best_d = None, float('inf')
            for nid, n in NODES.items():
                d = (n['lat'] - lat)**2 + (n['lon'] - lon)**2
                if d < best_d:
                    best_d, best_id = d, nid
            
            if best_id is not None:
                NODES[best_id]['name'] = name
                POIS.append({
                    "poi_id": f"p_{best_id}",
                    "name": name,
                    "lat": NODES[best_id]['lat'],
                    "lon": NODES[best_id]['lon'],
                    "node_id": best_id
                })
                
    except FileNotFoundError:
        print("ERROR: processed_nodes.csv not found!")
        return

    try:
        edges_df = pd.read_csv('processed_edges.csv')
        for _, row in edges_df.iterrows():
            u = int(row['start_node'])
            v = int(row['end_node'])
            
            travel_time = float(row['time'])
            raw_congestion = float(row['congestion'])
            
            # File poi.py tính congestion = travel_time * (1.1 -> 2.0)
            # Ta cần quy đổi nó về thang 1-5 chuẩn theo SDD
            if travel_time > 0:
                factor = raw_congestion / travel_time
                normalized_congestion = max(1.0, min(5.0, (factor - 1.1) / (2.0 - 1.1) * 4.0 + 1.0))
            else:
                normalized_congestion = 1.0
                
            edge_data = {
                "distance": float(row['distance']),
                "travel_time": travel_time,
                "congestion": normalized_congestion, 
                "risk": float(row['risk']),
                "road_type": str(row['road_type']),
                "average_speed": float(row['average_speed'])
            }
            
            ADJ[u][v] = dict(edge_data)
            
            oneway = bool(row['oneway']) if 'oneway' in row and pd.notna(row['oneway']) else False
            if not oneway:
                ADJ[v][u] = dict(edge_data)
                
    except FileNotFoundError:
        print("ERROR: processed_edges.csv not found!")
        return
        
    print(f"Graph loaded: {len(NODES)} nodes, {len(POIS)} POIs.")

def node_display_name(nid):
    n = NODES.get(nid)
    if not n:
        return f"Node {nid}"
    if n["name"]:
        return n["name"]
    return f"Point ({n['lat']:.4f}, {n['lon']:.4f})"

build_graph_from_csv()

# ---------------------------------------------------------------------------
# 3. COST FUNCTION
# ---------------------------------------------------------------------------
ALPHA, BETA, GAMMA, DELTA = 0.35, 0.30, 0.20, 0.15  

def edge_cost(e, mode):
    if mode == "distance":
        return e["distance"]
    if mode == "time":
        return e["travel_time"]
    nd = e["distance"] / 1000.0        
    nt = e["travel_time"] / 60.0       
    nc = e["congestion"]               
    nr = e["risk"] * 5.0               
    return ALPHA * nd + BETA * nt + GAMMA * nc + DELTA * nr

MAX_SPEED_MPS = 45 * 1000.0 / 3600.0

def heuristic(n, goal, mode):
    d = haversine(NODES[n]["lat"], NODES[n]["lon"], NODES[goal]["lat"], NODES[goal]["lon"])
    if mode == "distance":
        return d
    if mode == "time":
        return d / MAX_SPEED_MPS
    return ALPHA * (d / 1000.0)  

# ---------------------------------------------------------------------------
# 4. SEARCH ALGORITHMS
# ---------------------------------------------------------------------------
def reconstruct(came_from, start, goal):
    if goal not in came_from: return None
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
        if current == goal: break
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
        if current == goal: break
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
        if current in closed: continue
        closed.add(current)
        exploration.append(current)
        if current == goal: break
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
        if current in closed: continue
        closed.add(current)
        exploration.append(current)
        if current == goal: break
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
        if current in visited: continue
        visited.add(current)
        exploration.append(current)
        if current == goal: break
        for nbr in ADJ[current]:
            if nbr not in visited and nbr not in came_from:
                came_from[nbr] = current
                heapq.heappush(heap, (heuristic(nbr, goal, mode), next(counter), nbr))
    return reconstruct(came_from, start, goal), exploration, snapshots

def bidirectional(start, goal, mode):
    if start == goal: return [start], [start], [[start]]
    counter = itertools.count()
    heap_f, heap_b = [(0.0, next(counter), start)], [(0.0, next(counter), goal)]
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
                    cost_f[nbr] = nc; came_f[nbr] = cur_f
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
                        cost_b[nbr] = nc; came_b[nbr] = cur_b
                        heapq.heappush(heap_b, (nc, next(counter), nbr))

        if best is not None:
            top_f = heap_f[0][0] if heap_f else float("inf")
            top_b = heap_b[0][0] if heap_b else float("inf")
            if top_f + top_b >= best_cost: break

    if best is None: return None, exploration, snapshots
    path_f = []
    n = best
    while n is not None: path_f.append(n); n = came_f[n]
    path_f.reverse()
    path_b = []
    n = came_b[best]
    while n is not None: path_b.append(n); n = came_b[n]
    return path_f + path_b, exploration, snapshots

ALGO_NAMES = {
    "bfs": "Breadth-First Search", "dfs": "Depth-First Search", "ucs": "Uniform Cost Search",
    "astar": "A* Search", "gbfs": "Greedy Best-First Search", "bidirectional": "Bidirectional Search",
}

ALGORITHM_OPTIMALITY = {
    "bfs": {"optimal": False, "reason": "BFS only guarantees fewest hops, not lowest cost."},
    "dfs": {"optimal": False, "reason": "DFS stops at the first path found."},
    "ucs": {"optimal": True, "reason": "UCS always expands lowest cumulative-cost node."},
    "astar": {"optimal": True, "reason": "A* combines true path cost with an admissible heuristic."},
    "gbfs": {"optimal": False, "reason": "GBFS ignores cost already paid."},
    "bidirectional": {"optimal": True, "reason": "Runs cost-based search from both ends."},
}

def run_search(algorithm, start, goal, mode):
    t0 = time.perf_counter()
    if algorithm == "bfs": path, exp, front = bfs(start, goal)
    elif algorithm == "dfs": path, exp, front = dfs(start, goal)
    elif algorithm == "ucs": path, exp, front = ucs(start, goal, mode)
    elif algorithm == "astar": path, exp, front = astar(start, goal, mode)
    elif algorithm == "gbfs": path, exp, front = gbfs(start, goal, mode)
    elif algorithm == "bidirectional": path, exp, front = bidirectional(start, goal, mode)
    else: raise ValueError(f"Unknown algorithm: {algorithm}")
    exec_ms = (time.perf_counter() - t0) * 1000.0
    return path, exp, front, exec_ms

# ---------------------------------------------------------------------------
# 5. STATISTICS 
# ---------------------------------------------------------------------------
def compute_stats(path, mode):
    if not path or len(path) < 1: return None
    total_distance = total_time = total_congestion = total_risk = total_cost = 0.0
    edges_detail = []
    for i in range(len(path) - 1):
        n1, n2 = path[i], path[i + 1]
        e = ADJ[n1][n2]
        total_distance += e["distance"]
        total_time += e["travel_time"]
        total_congestion += e["congestion"]
        total_risk += e["risk"]
        total_cost += edge_cost(e, "hybrid")  
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
# 6. ALTERNATIVE ROUTE
# ---------------------------------------------------------------------------
def generate_alternative(start, goal, mode, primary_path):
    if not primary_path or len(primary_path) < 2: return None
    penalty = 6.0
    pairs = list(zip(primary_path, primary_path[1:]))
    for n1, n2 in pairs:
        ADJ[n1][n2]["distance"] *= penalty
        ADJ[n1][n2]["travel_time"] *= penalty
        if n1 in ADJ[n2]:
            ADJ[n2][n1]["distance"] *= penalty
            ADJ[n2][n1]["travel_time"] *= penalty
    try:
        alt_path, _, _ = ucs(start, goal, mode)
    finally:
        for n1, n2 in pairs:
            ADJ[n1][n2]["distance"] /= penalty
            ADJ[n1][n2]["travel_time"] /= penalty
            if n1 in ADJ[n2]:
                ADJ[n2][n1]["distance"] /= penalty
                ADJ[n2][n1]["travel_time"] /= penalty

    if not alt_path or alt_path == primary_path:
        fallback, _, _ = dfs(start, goal)
        if fallback and fallback != primary_path: return fallback
        return None
    return alt_path

# ---------------------------------------------------------------------------
# 7. EXPLANATION
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
        text = f"The route returned by {ALGO_NAMES[algorithm]} has a {MODE_LABEL[mode]} of {primary_val:.1f} {unit}."
    elif primary_val < alt_val:
        text = f"The route returned by {ALGO_NAMES[algorithm]} is better ({primary_val:.1f} vs {alt_val:.1f} {unit})."
    else:
        text = f"The route returned by {ALGO_NAMES[algorithm]} has a higher {MODE_LABEL[mode]} ({primary_val:.1f} vs {alt_val:.1f}). This is because {optimality['reason']}"

    if alt_stats:
        congested = [e for e in alt_stats["edges"] if e["congestion"] >= 3.0 or e["average_speed"] < 22]
        if congested:
            examples = "; ".join(f"a {e['road_type']} segment (congestion {e['congestion']:.1f}/5)" for e in congested[:3])
            text += f" The alternative route passes through {len(congested)} congested segment(s), including {examples}."

    return text

def build_multi_explanation(algorithm, mode, order_with_start, legs):
    names = [node_display_name(n) for n in order_with_start]
    total_cost = sum(l["stats"]["total_cost"] for l in legs if l["stats"])
    return (
        "Nearest Neighbor Heuristic determined order: " + " -> ".join(names) + 
        f". {ALGO_NAMES[algorithm]} computed legs for a total cost of {total_cost:.1f}."
    )

# ---------------------------------------------------------------------------
# 8. MULTI-LOCATION
# ---------------------------------------------------------------------------
def nearest_neighbor_order(start, destinations):
    remaining = set(destinations)
    order, current = [], start
    while remaining:
        nxt = min(remaining, key=lambda d: haversine(NODES[current]["lat"], NODES[current]["lon"], NODES[d]["lat"], NODES[d]["lon"]))
        order.append(nxt)
        remaining.remove(nxt)
        current = nxt
    return order

def run_itinerary(algorithm, start, destinations, mode):
    order = nearest_neighbor_order(start, destinations)
    seq = [start] + order
    legs, full_path = [], []
    totals = {"distance_m": 0.0, "time_s": 0.0, "congestion_total": 0.0, "risk_total": 0.0, "total_cost": 0.0}

    for i in range(len(seq) - 1):
        s, g = seq[i], seq[i + 1]
        path, exp, front, exec_ms = run_search(algorithm, s, g, mode)
        stats = compute_stats(path, mode) if path else None
        legs.append({
            "from": s, "to": g, "path": path, "stats": stats,
            "exploration_sequence": exp, "frontier_snapshots": front,
            "execution_time_ms": exec_ms, "expanded_nodes": len(exp)
        })
        if path:
            full_path.extend(path[1:] if full_path and full_path[-1] == path[0] else path)
            for k in totals: totals[k] += stats[k]
    return order, legs, full_path, totals

# ---------------------------------------------------------------------------
# 9. API
# ---------------------------------------------------------------------------
@app.route("/")
def index(): return jsonify({"status": "ok"})

@app.route("/api/locations")
def api_locations(): return jsonify(POIS)

@app.route("/api/network")
def api_network():
    nodes = [{"id": n["id"], "lat": n["lat"], "lon": n["lon"]} for n in NODES.values()]
    edges, seen = [], set()
    for n1, nbrs in ADJ.items():
        for n2, e in nbrs.items():
            key = tuple(sorted((n1, n2)))
            if key in seen: continue
            seen.add(key)
            edges.append({"from": n1, "to": n2, "road_type": e["road_type"]})
    return jsonify({"nodes": nodes, "edges": edges})

@app.route("/api/search", methods=["POST", "OPTIONS"])
def api_search():
    if request.method == "OPTIONS": return "", 200
    data = request.get_json(force=True, silent=True) or {}
    algorithm = data.get("algorithm", "astar")
    mode = data.get("optimization", "hybrid")

    try:
        start = int(data["start"])
        destinations = [int(d) for d in data["destinations"] if int(d) != start]
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid start or destinations"}), 400

    if len(destinations) == 1:
        goal = destinations[0]
        path, exp, front, exec_ms = run_search(algorithm, start, goal, mode)
        if not path: return jsonify({"error": "No path found"}), 404
        stats = compute_stats(path, mode)
        alt_path = generate_alternative(start, goal, mode, path)
        alt_stats = compute_stats(alt_path, mode) if alt_path else None
        
        congested_segments = []
        if alt_stats:
            for e in alt_stats["edges"]:
                if e["congestion"] >= 3.0 or e["average_speed"] < 22:
                    congested_segments.append({"from": e["from"], "to": e["to"], "road_type": e["road_type"], "congestion": e["congestion"]})

        return jsonify({
            "mode": "single", "algorithm": algorithm, "algorithm_name": ALGO_NAMES[algorithm],
            "optimal_guaranteed": ALGORITHM_OPTIMALITY[algorithm]["optimal"],
            "exploration_sequence": exp, "frontier_snapshots": front,
            "primary_path": path, "alternative_path": alt_path,
            "congested_segments": congested_segments,
            "route_explanation": build_explanation(algorithm, mode, stats, alt_stats),
            "statistics": {**stats, "algorithm": ALGO_NAMES[algorithm], "expanded_nodes": len(exp), "execution_time_ms": exec_ms, "alternative": alt_stats}
        })

    order, legs, full_path, totals = run_itinerary(algorithm, start, destinations, mode)
    if not full_path: return jsonify({"error": "No path found"}), 404
    return jsonify({
        "mode": "multi", "algorithm": algorithm, "algorithm_name": ALGO_NAMES[algorithm],
        "optimal_guaranteed": ALGORITHM_OPTIMALITY[algorithm]["optimal"],
        "visiting_order": order, "legs": legs, "complete_itinerary": full_path,
        "statistics": {**totals, "algorithm": ALGO_NAMES[algorithm], "expanded_nodes": sum(l["expanded_nodes"] for l in legs), "execution_time_ms": sum(l["execution_time_ms"] for l in legs)},
        "route_explanation": build_multi_explanation(algorithm, mode, [start] + order, legs),
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)