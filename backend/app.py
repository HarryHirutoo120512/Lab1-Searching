"""
FastAPI backend — Tourist Route Planner.

Endpoints:
    GET  /api/locations   — POI list
    GET  /api/network     — full node/edge data for map rendering
    POST /api/search      — run search with both criteria, return comparison
"""

import os
import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from graph import Graph
from algorithms import ALGORITHMS, ALGORITHM_PROPERTIES
from explanation import compare_routes, generate_multi_route_explanation, generate_turn_by_turn_directions
from cost import SHORTEST_WEIGHTS, FASTEST_WEIGHTS, edge_cost

# ── Init ───────────────────────────────────────────────────────────────

app = FastAPI(title="Tourist Route Planner API", version="1.0.0")

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load graph once on startup
graph = Graph()
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@app.on_event("startup")
def startup():
    graph.load(DATA_DIR)
    pois = graph.get_pois()
    print(f"Graph loaded: {len(graph.nodes)} nodes, {sum(len(v) for v in graph.adj.values())} edges")
    print(f"POIs: {len(pois)}")


# ── Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/locations")
def get_locations():
    """Return all POI locations (snap_poi nodes with names)."""
    pois = graph.get_pois()
    # Also include all nodes so the user can click any node
    return {
        "pois": pois,
        "total_nodes": len(graph.nodes),
    }


@app.get("/api/network")
def get_network():
    """Return the full road network as GeoJSON-ready data with accurate edge geometries."""
    nodes = graph.get_all_nodes()
    edges = graph.get_all_edges()

    # Convert edges to GeoJSON features for MapLibre
    edge_features = []
    for e in edges:
        coords = e.get("geometry")
        if not coords:
            coords = [
                [e.get("start_lon", 0), e.get("start_lat", 0)],
                [e.get("end_lon", 0), e.get("end_lat", 0)],
            ]

        edge_features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
            "properties": {
                "start_node": e["start_node"],
                "end_node": e["end_node"],
                "road_type": e["road_type"],
                "distance": e["distance"],
            },
        })

    node_features = []
    for n in nodes:
        node_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [n["lon"], n["lat"]],
            },
            "properties": {
                "id": n["id"],
                "type": n["type"],
                "name": n.get("name", ""),
            },
        })

    return {
        "edges": {
            "type": "FeatureCollection",
            "features": edge_features,
        },
        "nodes": {
            "type": "FeatureCollection",
            "features": node_features,
        },
        "bounds": {
            "d_min": graph.bounds.d_min,
            "d_max": graph.bounds.d_max,
            "t_min": graph.bounds.t_min,
            "t_max": graph.bounds.t_max,
        },
    }


def _resolve_node(nid: int) -> int:
    """Resolve physical POI node ID to its routable road snap_id."""
    if nid is None:
        return None
    node = graph.get_node(nid)
    if node and "snap_id" in node:
        return node["snap_id"]
    return nid


@app.post("/api/search")
def search(request: dict):
    """
    Run search algorithm with both Shortest and Fastest weights.
    Returns both routes + comparison explanation.
    """
    algorithm = request.get("algorithm", "astar")
    start_node_raw = request.get("start_node")
    destinations_raw = request.get("destinations", [])

    start_node = _resolve_node(start_node_raw)
    destinations = [_resolve_node(d) for d in destinations_raw if d is not None]

    # Validate
    if algorithm not in ALGORITHMS:
        raise HTTPException(400, f"Unknown algorithm: {algorithm}. Available: {list(ALGORITHMS.keys())}")
    if start_node is None:
        raise HTTPException(400, "start_node is required")
    if not destinations:
        raise HTTPException(400, "At least one destination is required")
    if start_node not in graph.nodes:
        raise HTTPException(400, f"Start node {start_node} not found in graph")
    for d in destinations:
        if d not in graph.nodes:
            raise HTTPException(400, f"Destination node {d} not found in graph")

    # Single-location search: compare both criteria
    if len(destinations) == 1:
        goal = destinations[0]
        result = compare_routes(graph, algorithm, start_node, goal)

        # Format path coordinates for frontend rendering
        result["shortest_result"]["path_coords"] = _path_to_coords(result["shortest_result"]["path"])
        result["fastest_result"]["path_coords"] = _path_to_coords(result["fastest_result"]["path"])
        result["legs_shortest"] = [result["shortest_result"]]
        result["legs_fastest"] = [result["fastest_result"]]

        # Generate turn-by-turn directions
        dest_node = graph.get_node(goal)
        dest_info = [{"id": goal, "snap_id": goal, "name": dest_node.get("name", "Điểm đến")}] if dest_node else []
        start_node_obj = graph.get_node(start_node_raw) or graph.get_node(start_node)
        start_info = {"id": start_node, "name": start_node_obj.get("name", "Điểm xuất phát")} if start_node_obj else None

        result["shortest_result"]["directions"] = generate_turn_by_turn_directions(
            graph, result["shortest_result"].get("edge_details", []), dest_info, start_info
        )
        result["fastest_result"]["directions"] = generate_turn_by_turn_directions(
            graph, result["fastest_result"].get("edge_details", []), dest_info, start_info
        )

        return result

    # Multi-location: Nearest Neighbor Heuristic for ordering
    else:
        return _multi_location_search(algorithm, start_node, destinations)


def _path_to_coords(path: List[int]) -> list:
    """
    Convert a list of node IDs to [[lon, lat], ...] for map rendering,
    following the detailed intermediate curve points of each edge.
    """
    if not path:
        return []
    if len(path) == 1:
        n = graph.get_node(path[0])
        return [[n["lon"], n["lat"]]] if n else []

    coords = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        u_node = graph.get_node(u)
        v_node = graph.get_node(v)
        if not u_node or not v_node:
            continue

        edge = None
        for nbr, e_dict in graph.neighbours(u):
            if nbr == v:
                edge = e_dict
                break

        if edge and edge.get("geometry"):
            pts = edge["geometry"]
            first_pt = pts[0]
            d_u = (first_pt[0] - u_node["lon"]) ** 2 + (first_pt[1] - u_node["lat"]) ** 2
            d_v = (first_pt[0] - v_node["lon"]) ** 2 + (first_pt[1] - v_node["lat"]) ** 2
            if d_v < d_u:
                pts = pts[::-1]

            if not coords:
                coords.extend(pts)
            else:
                if math.isclose(coords[-1][0], pts[0][0], abs_tol=1e-6) and math.isclose(coords[-1][1], pts[0][1], abs_tol=1e-6):
                    coords.extend(pts[1:])
                else:
                    coords.extend(pts)
        else:
            if not coords:
                coords.append([u_node["lon"], u_node["lat"]])
            coords.append([v_node["lon"], v_node["lat"]])

    return coords


def _multi_location_search(algorithm: str, start: int, destinations: List[int]) -> dict:
    """
    Multi-location routing using Nearest Neighbor Heuristic.
    Uses the Shortest criteria for ordering, then routes each leg.
    Returns a unified response with combined shortest_result and fastest_result
    so the frontend renders them using the same code path as single-location.
    """
    algo_fn = ALGORITHMS[algorithm]
    algo_info = ALGORITHM_PROPERTIES[algorithm]

    # Nearest Neighbor ordering
    unvisited = set(destinations)
    visiting_order = []
    current = start

    while unvisited:
        nearest = min(unvisited, key=lambda d: _haversine(current, d))
        visiting_order.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    # Route each leg with both criteria
    legs_shortest = []
    legs_fastest = []
    sequence = [start] + visiting_order

    total_stats_s = {"total_distance": 0, "total_time": 0, "total_congestion": 0, "total_risk": 0, "total_cost": 0, "expanded_nodes": 0, "execution_time": 0}
    total_stats_f = {"total_distance": 0, "total_time": 0, "total_congestion": 0, "total_risk": 0, "total_cost": 0, "expanded_nodes": 0, "execution_time": 0}

    combined_path_s = []
    combined_path_f = []
    combined_coords_s = []
    combined_coords_f = []
    combined_explored_s = []
    combined_explored_f = []
    combined_edge_details_s = []
    combined_edge_details_f = []

    for i in range(len(sequence) - 1):
        u, v = sequence[i], sequence[i + 1]
        s_result = algo_fn(graph, u, v, SHORTEST_WEIGHTS)
        f_result = algo_fn(graph, u, v, FASTEST_WEIGHTS)

        s_coords = _path_to_coords(s_result["path"])
        f_coords = _path_to_coords(f_result["path"])
        s_result["path_coords"] = s_coords
        f_result["path_coords"] = f_coords

        legs_shortest.append(s_result)
        legs_fastest.append(f_result)

        # Combine paths (skip first node of subsequent legs to avoid duplication)
        if i == 0:
            combined_path_s.extend(s_result["path"])
            combined_path_f.extend(f_result["path"])
            combined_coords_s.extend(s_coords)
            combined_coords_f.extend(f_coords)
        else:
            combined_path_s.extend(s_result["path"][1:])
            combined_path_f.extend(f_result["path"][1:])
            combined_coords_s.extend(s_coords[1:])
            combined_coords_f.extend(f_coords[1:])

        combined_explored_s.extend(s_result.get("explored", []))
        combined_explored_f.extend(f_result.get("explored", []))
        combined_edge_details_s.extend(s_result.get("edge_details", []))
        combined_edge_details_f.extend(f_result.get("edge_details", []))

        for key in total_stats_s:
            total_stats_s[key] += s_result["stats"].get(key, 0)
            total_stats_f[key] += f_result["stats"].get(key, 0)

    # Round totals
    for key in total_stats_s:
        total_stats_s[key] = round(total_stats_s[key], 4)
        total_stats_f[key] = round(total_stats_f[key], 4)

    # Build destination names info for directions and explanation
    visiting_order_names = []
    dest_infos = []
    for nid in visiting_order:
        n_info = graph.get_node(nid)
        name = n_info.get("name", f"Location {nid}") if n_info else f"Location {nid}"
        visiting_order_names.append(name)
        dest_infos.append({"id": nid, "snap_id": nid, "name": name})

    explanation_multi = generate_multi_route_explanation(
        total_stats_s, total_stats_f, legs_shortest, legs_fastest, visiting_order_names, algo_info
    )

    legs_edge_details_s = [leg.get("edge_details", []) for leg in legs_shortest]
    legs_edge_details_f = [leg.get("edge_details", []) for leg in legs_fastest]

    start_node_obj = graph.get_node(start)
    start_info = {"id": start, "name": start_node_obj.get("name", "Điểm xuất phát")} if start_node_obj else None

    directions_s = generate_turn_by_turn_directions(graph, legs_edge_details_s, dest_infos, start_info)
    directions_f = generate_turn_by_turn_directions(graph, legs_edge_details_f, dest_infos, start_info)

    return {
        "visiting_order": visiting_order,
        "shortest_result": {
            "path": combined_path_s,
            "path_coords": combined_coords_s,
            "explored": combined_explored_s,
            "edge_details": combined_edge_details_s,
            "stats": total_stats_s,
            "directions": directions_s,
        },
        "fastest_result": {
            "path": combined_path_f,
            "path_coords": combined_coords_f,
            "explored": combined_explored_f,
            "edge_details": combined_edge_details_f,
            "stats": total_stats_f,
            "directions": directions_f,
        },
        "legs_shortest": legs_shortest,
        "legs_fastest": legs_fastest,
        "algorithm_info": algo_info,
        "explanation": explanation_multi,
    }


def _haversine(node_a: int, node_b: int) -> float:
    """Haversine distance between two graph nodes."""
    a = graph.get_node(node_a)
    b = graph.get_node(node_b)
    if not a or not b:
        return float("inf")

    R = 6_371_000
    phi1, phi2 = math.radians(a["lat"]), math.radians(b["lat"])
    dphi = math.radians(b["lat"] - a["lat"])
    dlam = math.radians(b["lon"] - a["lon"])
    x = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))
