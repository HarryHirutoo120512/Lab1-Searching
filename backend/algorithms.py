"""
Search algorithms — BFS, DFS, UCS, A*, Greedy Best-First, Bidirectional BFS.

Each function returns:
    path        – list of node IDs from start to goal
    explored    – ordered list of exploration steps for animation
    stats       – dict with performance / route metrics
"""

import heapq
import time
from collections import deque
from typing import Callable, Dict, List, Optional, Tuple

from graph import Graph
from cost import NormBounds, edge_cost, heuristic_cost


# ── Result structure ───────────────────────────────────────────────────

def _build_result(
    path: List[int],
    explored: List[dict],
    graph: Graph,
    weights: Tuple[float, float, float, float],
    start_time: float,
    expanded_count: int,
) -> dict:
    """Assemble the standard result dict from a found path."""
    elapsed = time.perf_counter() - start_time

    total_distance = 0.0
    total_time = 0.0
    total_congestion = 0.0
    total_risk = 0.0
    total_cost = 0.0
    edge_details = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        # Find the edge u → v
        edge = _find_edge(graph, u, v)
        if edge:
            total_distance += edge["distance"]
            total_time += edge["time"] + edge["congestion"]  # actual travel time
            total_congestion += edge["congestion"]
            total_risk += edge["risk"]
            total_cost += edge_cost(edge, weights, graph.bounds)
            edge_details.append({
                "from": u,
                "to": v,
                "distance": edge["distance"],
                "time": edge["time"],
                "congestion": edge["congestion"],
                "risk": edge["risk"],
                "road_type": edge["road_type"],
                "street_name": edge.get("street_name", ""),
                "average_speed": edge["average_speed"],
                "max_speed": edge["max_speed"],
                "geometry": edge.get("geometry", []),
            })

    return {
        "path": path,
        "explored": explored,
        "edge_details": edge_details,
        "stats": {
            "total_distance": round(total_distance, 2),
            "total_time": round(total_time, 2),
            "total_congestion": round(total_congestion, 2),
            "total_risk": round(total_risk, 4),
            "total_cost": round(total_cost, 6),
            "expanded_nodes": expanded_count,
            "execution_time": round(elapsed * 1000, 2),  # ms
        },
    }


def _find_edge(graph: Graph, u: int, v: int) -> Optional[dict]:
    """Find the edge from u to v."""
    for neighbour, edge in graph.neighbours(u):
        if neighbour == v:
            return edge
    return None


def _no_path_result(explored, start_time, expanded_count):
    """Return when no path exists."""
    return {
        "path": [],
        "explored": explored,
        "edge_details": [],
        "stats": {
            "total_distance": 0,
            "total_time": 0,
            "total_congestion": 0,
            "total_risk": 0,
            "total_cost": 0,
            "expanded_nodes": expanded_count,
            "execution_time": round((time.perf_counter() - start_time) * 1000, 2),
        },
    }


# ── BFS ────────────────────────────────────────────────────────────────

def bfs(
    graph: Graph,
    start: int,
    goal: int,
    weights: Tuple[float, float, float, float],
) -> dict:
    t0 = time.perf_counter()
    explored_list = []
    visited = set()
    parent = {start: None}
    queue = deque([start])
    visited.add(start)
    expanded = 0

    while queue:
        node = queue.popleft()
        expanded += 1
        frontier_snapshot = list(queue)
        explored_list.append({
            "node": node,
            "parent": parent.get(node),
            "frontier": frontier_snapshot[:50],  # cap for payload size
        })

        if node == goal:
            path = _reconstruct(parent, goal)
            return _build_result(path, explored_list, graph, weights, t0, expanded)

        for neighbour, _ in graph.neighbours(node):
            if neighbour not in visited:
                visited.add(neighbour)
                parent[neighbour] = node
                queue.append(neighbour)

    return _no_path_result(explored_list, t0, expanded)


# ── DFS ────────────────────────────────────────────────────────────────

def dfs(
    graph: Graph,
    start: int,
    goal: int,
    weights: Tuple[float, float, float, float],
) -> dict:
    t0 = time.perf_counter()
    explored_list = []
    visited = set()
    parent = {start: None}
    stack = [start]
    expanded = 0

    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        expanded += 1
        explored_list.append({
            "node": node,
            "parent": parent.get(node),
            "frontier": stack[-50:],
        })

        if node == goal:
            path = _reconstruct(parent, goal)
            return _build_result(path, explored_list, graph, weights, t0, expanded)

        for neighbour, _ in graph.neighbours(node):
            if neighbour not in visited:
                parent[neighbour] = node
                stack.append(neighbour)

    return _no_path_result(explored_list, t0, expanded)


# ── UCS ────────────────────────────────────────────────────────────────

def ucs(
    graph: Graph,
    start: int,
    goal: int,
    weights: Tuple[float, float, float, float],
) -> dict:
    t0 = time.perf_counter()
    explored_list = []
    dist = {start: 0.0}
    parent = {start: None}
    pq = [(0.0, start)]
    visited = set()
    expanded = 0
    counter = 0

    while pq:
        cost_so_far, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        expanded += 1
        explored_list.append({"node": node, "parent": parent.get(node), "frontier": [n for _, n in pq[:50]]})

        if node == goal:
            path = _reconstruct(parent, goal)
            return _build_result(path, explored_list, graph, weights, t0, expanded)

        for neighbour, edge in graph.neighbours(node):
            if neighbour in visited:
                continue
            ec = edge_cost(edge, weights, graph.bounds)
            new_cost = cost_so_far + ec
            if neighbour not in dist or new_cost < dist[neighbour]:
                dist[neighbour] = new_cost
                parent[neighbour] = node
                counter += 1
                heapq.heappush(pq, (new_cost, neighbour))

    return _no_path_result(explored_list, t0, expanded)


# ── A* ─────────────────────────────────────────────────────────────────

def astar(
    graph: Graph,
    start: int,
    goal: int,
    weights: Tuple[float, float, float, float],
) -> dict:
    t0 = time.perf_counter()
    explored_list = []
    goal_node = graph.get_node(goal)
    if goal_node is None:
        return _no_path_result([], t0, 0)

    g = {start: 0.0}
    parent = {start: None}

    start_node = graph.get_node(start)
    h0 = heuristic_cost(
        start_node["lat"], start_node["lon"],
        goal_node["lat"], goal_node["lon"],
        weights, graph.bounds,
    )
    pq = [(h0, 0, start)]  # (f, tiebreaker, node)
    visited = set()
    expanded = 0
    counter = 0

    while pq:
        f_val, _, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        expanded += 1
        explored_list.append({"node": node, "parent": parent.get(node), "frontier": [n for _, _, n in pq[:50]]})

        if node == goal:
            path = _reconstruct(parent, goal)
            return _build_result(path, explored_list, graph, weights, t0, expanded)

        for neighbour, edge in graph.neighbours(node):
            if neighbour in visited:
                continue
            ec = edge_cost(edge, weights, graph.bounds)
            new_g = g[node] + ec
            if neighbour not in g or new_g < g[neighbour]:
                g[neighbour] = new_g
                parent[neighbour] = node
                n_node = graph.get_node(neighbour)
                h = heuristic_cost(
                    n_node["lat"], n_node["lon"],
                    goal_node["lat"], goal_node["lon"],
                    weights, graph.bounds,
                )
                counter += 1
                heapq.heappush(pq, (new_g + h, counter, neighbour))

    return _no_path_result(explored_list, t0, expanded)


# ── Greedy Best-First Search ──────────────────────────────────────────

def gbfs(
    graph: Graph,
    start: int,
    goal: int,
    weights: Tuple[float, float, float, float],
) -> dict:
    t0 = time.perf_counter()
    explored_list = []
    goal_node = graph.get_node(goal)
    if goal_node is None:
        return _no_path_result([], t0, 0)

    parent = {start: None}
    start_node = graph.get_node(start)
    h0 = heuristic_cost(
        start_node["lat"], start_node["lon"],
        goal_node["lat"], goal_node["lon"],
        weights, graph.bounds,
    )
    pq = [(h0, 0, start)]
    visited = set()
    expanded = 0
    counter = 0

    while pq:
        _, _, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)
        expanded += 1
        explored_list.append({"node": node, "parent": parent.get(node), "frontier": [n for _, _, n in pq[:50]]})

        if node == goal:
            path = _reconstruct(parent, goal)
            return _build_result(path, explored_list, graph, weights, t0, expanded)

        for neighbour, edge in graph.neighbours(node):
            if neighbour not in visited:
                parent[neighbour] = node
                n_node = graph.get_node(neighbour)
                h = heuristic_cost(
                    n_node["lat"], n_node["lon"],
                    goal_node["lat"], goal_node["lon"],
                    weights, graph.bounds,
                )
                counter += 1
                heapq.heappush(pq, (h, counter, neighbour))

    return _no_path_result(explored_list, t0, expanded)


# ── Bidirectional BFS ──────────────────────────────────────────────────

def bidirectional(
    graph: Graph,
    start: int,
    goal: int,
    weights: Tuple[float, float, float, float],
) -> dict:
    t0 = time.perf_counter()
    explored_list = []
    expanded = 0

    if start == goal:
        return _build_result([start], explored_list, graph, weights, t0, 0)

    # Build reverse adjacency for backward search
    reverse_adj: Dict[int, List[Tuple[int, dict]]] = {}
    for node_id in graph.adj:
        for neighbour, edge in graph.adj[node_id]:
            if neighbour not in reverse_adj:
                reverse_adj[neighbour] = []
            reverse_adj[neighbour].append((node_id, edge))

    parent_fwd = {start: None}
    parent_bwd = {goal: None}
    visited_fwd = {start}
    visited_bwd = {goal}
    queue_fwd = deque([start])
    queue_bwd = deque([goal])

    meeting_node = None

    while queue_fwd or queue_bwd:
        # Forward step
        if queue_fwd:
            node = queue_fwd.popleft()
            expanded += 1
            explored_list.append({
                "node": node,
                "parent": parent_fwd.get(node),
                "frontier": list(queue_fwd)[:30],
                "direction": "forward",
            })

            if node in visited_bwd:
                meeting_node = node
                break

            for neighbour, _ in graph.neighbours(node):
                if neighbour not in visited_fwd:
                    visited_fwd.add(neighbour)
                    parent_fwd[neighbour] = node
                    queue_fwd.append(neighbour)
                    if neighbour in visited_bwd:
                        meeting_node = neighbour
                        break

            if meeting_node is not None:
                break

        # Backward step
        if queue_bwd:
            node = queue_bwd.popleft()
            expanded += 1
            explored_list.append({
                "node": node,
                "parent": parent_bwd.get(node),
                "frontier": list(queue_bwd)[:30],
                "direction": "backward",
            })

            if node in visited_fwd:
                meeting_node = node
                break

            for neighbour, _ in reverse_adj.get(node, []):
                if neighbour not in visited_bwd:
                    visited_bwd.add(neighbour)
                    parent_bwd[neighbour] = node
                    queue_bwd.append(neighbour)
                    if neighbour in visited_fwd:
                        meeting_node = neighbour
                        break

            if meeting_node is not None:
                break

    if meeting_node is None:
        return _no_path_result(explored_list, t0, expanded)

    # Reconstruct forward path: start → meeting
    fwd_path = []
    n = meeting_node
    while n is not None:
        fwd_path.append(n)
        n = parent_fwd.get(n)
    fwd_path.reverse()

    # Reconstruct backward path: meeting → goal
    bwd_path = []
    n = parent_bwd.get(meeting_node)
    while n is not None:
        bwd_path.append(n)
        n = parent_bwd.get(n)

    full_path = fwd_path + bwd_path
    return _build_result(full_path, explored_list, graph, weights, t0, expanded)


# ── Utility ────────────────────────────────────────────────────────────

def _reconstruct(parent: dict, goal: int) -> List[int]:
    path = []
    n = goal
    while n is not None:
        path.append(n)
        n = parent[n]
    path.reverse()
    return path


# ── Algorithm registry ────────────────────────────────────────────────

ALGORITHMS = {
    "bfs": bfs,
    "dfs": dfs,
    "ucs": ucs,
    "astar": astar,
    "gbfs": gbfs,
    "bidirectional": bidirectional,
}

# Optimality classification (for explanation)
ALGORITHM_PROPERTIES = {
    "bfs":           {"name": "Breadth-First Search",       "optimal": False, "complete": True},
    "dfs":           {"name": "Depth-First Search",         "optimal": False, "complete": False},
    "ucs":           {"name": "Uniform Cost Search",        "optimal": True,  "complete": True},
    "astar":         {"name": "A* Search",                  "optimal": True,  "complete": True},
    "gbfs":          {"name": "Greedy Best-First Search",   "optimal": False, "complete": False},
    "bidirectional": {"name": "Bidirectional BFS",          "optimal": False, "complete": True},
}
