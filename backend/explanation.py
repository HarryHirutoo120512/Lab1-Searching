"""
Route comparison and natural-language explanation generator.

Runs the same algorithm with Shortest and Fastest weights, then
produces a human-readable explanation of why one route beats the
other for each criterion.
"""

from typing import Tuple, List

from graph import Graph
from cost import (
    SHORTEST_WEIGHTS, FASTEST_WEIGHTS,
    edge_cost, NormBounds,
)
from algorithms import ALGORITHMS, ALGORITHM_PROPERTIES


def _format_time(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = int(minutes // 60)
    mins = minutes % 60
    return f"{hours}h {mins}m"


def _format_distance(metres: float) -> str:
    """Format metres into km or m."""
    if metres >= 1000:
        return f"{metres / 1000:.2f} km"
    return f"{metres:.0f} m"


def _identify_congested_segments(edge_details: list, top_n: int = 3) -> list:
    """Find the most congested segments in a route."""
    if not edge_details:
        return []
    sorted_edges = sorted(edge_details, key=lambda e: e["congestion"], reverse=True)
    result = []
    for e in sorted_edges[:top_n]:
        if e["congestion"] > 0:
            name = e["street_name"] or e["road_type"]
            result.append({
                "name": name,
                "road_type": e["road_type"],
                "congestion": e["congestion"],
                "average_speed": e["average_speed"],
                "distance": e["distance"],
            })
    return result


def _get_route_street_summary(edge_details: list) -> str:
    """Build a short 'via X → Y → Z' summary from edge details."""
    street_names = []
    for e in edge_details:
        name = e.get("street_name", "")
        if name and name not in street_names:
            street_names.append(name)
    if not street_names:
        # Fall back to road types
        road_types = []
        for e in edge_details:
            rt = e.get("road_type", "")
            if rt and rt not in road_types:
                road_types.append(rt)
        return " → ".join(road_types[:5])
    return " → ".join(street_names[:5])


def compare_routes(
    graph: Graph,
    algorithm_key: str,
    start: int,
    goal: int,
) -> dict:
    """
    Run the algorithm with both weight tuples and produce a comparison.

    Returns:
        {
            "shortest_result": {...},
            "fastest_result": {...},
            "explanation": str,
            "congested_segments_shortest": [...],
            "congested_segments_fastest": [...],
        }
    """
    algo_fn = ALGORITHMS[algorithm_key]
    algo_info = ALGORITHM_PROPERTIES[algorithm_key]

    # Run with Shortest weights
    shortest_result = algo_fn(graph, start, goal, SHORTEST_WEIGHTS)
    # Run with Fastest weights
    fastest_result = algo_fn(graph, start, goal, FASTEST_WEIGHTS)

    # Identify congested segments in each route
    cong_shortest = _identify_congested_segments(shortest_result.get("edge_details", []))
    cong_fastest = _identify_congested_segments(fastest_result.get("edge_details", []))

    # Build explanation
    explanation = _generate_explanation(
        shortest_result, fastest_result,
        cong_shortest, cong_fastest,
        algo_info,
    )

    return {
        "shortest_result": shortest_result,
        "fastest_result": fastest_result,
        "explanation": explanation,
        "congested_segments_shortest": cong_shortest,
        "congested_segments_fastest": cong_fastest,
        "algorithm_info": algo_info,
    }


def _generate_explanation(
    shortest: dict,
    fastest: dict,
    cong_shortest: list,
    cong_fastest: list,
    algo_info: dict,
) -> str:
    """
    Generate a natural-language explanation comparing the two routes.
    """
    s_stats = shortest["stats"]
    f_stats = fastest["stats"]

    s_dist = s_stats["total_distance"]
    f_dist = f_stats["total_distance"]
    s_time = s_stats["total_time"]
    f_time = f_stats["total_time"]
    s_cong = s_stats["total_congestion"]
    f_cong = f_stats["total_congestion"]

    # Route summaries
    s_via = _get_route_street_summary(shortest.get("edge_details", []))
    f_via = _get_route_street_summary(fastest.get("edge_details", []))

    parts = []

    # 1. Algorithm info
    algo_name = algo_info["name"]
    optimality = "guarantees an optimal solution" if algo_info["optimal"] else "does not guarantee optimality"
    parts.append(
        f"Both routes were computed using **{algo_name}**, which {optimality}."
    )

    # 2. Check if routes are identical
    if shortest["path"] == fastest["path"]:
        parts.append(
            f"\nBoth the Shortest and Fastest criteria produce the **same route** "
            f"(distance: {_format_distance(s_dist)}, travel time: {_format_time(s_time)}). "
            f"This means the physically shortest path also happens to be the fastest, "
            f"with no high-congestion segments forcing a detour."
        )
        return "\n".join(parts)

    # 3. Distance comparison
    dist_diff = abs(s_dist - f_dist)
    parts.append(
        f"\n**Distance comparison:** "
        f"The Shortest route{'  (via ' + s_via + ')' if s_via else ''} covers "
        f"**{_format_distance(s_dist)}**, "
        f"while the Fastest route{'  (via ' + f_via + ')' if f_via else ''} covers "
        f"**{_format_distance(f_dist)}** "
        f"(difference: {_format_distance(dist_diff)})."
    )

    # 4. Time comparison
    time_diff = abs(s_time - f_time)
    if s_time > f_time:
        parts.append(
            f"\n**Time comparison:** Despite being shorter in distance, the Shortest route "
            f"takes **{_format_time(s_time)}** — that is **{_format_time(time_diff)} slower** "
            f"than the Fastest route ({_format_time(f_time)})."
        )
    elif f_time > s_time:
        parts.append(
            f"\n**Time comparison:** The Shortest route is also faster at "
            f"**{_format_time(s_time)}** vs. **{_format_time(f_time)}** for the Fastest route."
        )
    else:
        parts.append(
            f"\n**Time comparison:** Both routes take approximately the same time "
            f"({_format_time(s_time)})."
        )

    # 5. Congestion analysis — why the Shortest route is slow
    if cong_shortest and s_time > f_time:
        parts.append("\n**Why the Shortest route is slower:**")
        for seg in cong_shortest:
            parts.append(
                f"  • **{seg['name']}** ({seg['road_type']}): "
                f"congestion delay of {_format_time(seg['congestion'])}, "
                f"average speed only {seg['average_speed']:.0f} km/h"
            )
        parts.append(
            "These congested segments increase the total travel time significantly, "
            "even though the route is physically shorter."
        )

    # 6. Congestion analysis — what the Fastest route avoids
    if cong_fastest:
        cong_diff = s_cong - f_cong
        if cong_diff > 0:
            parts.append(
                f"\n**Why the Fastest route is better for speed:** "
                f"It avoids {_format_time(cong_diff)} of congestion delay by routing "
                f"around the most congested segments."
            )
        elif cong_diff < 0:
            parts.append(
                f"\n**Trade-off in the Fastest route:** "
                f"It encounters {_format_time(abs(cong_diff))} more congestion, "
                f"but the segments it uses have higher base speeds, "
                f"resulting in a shorter overall travel time."
            )

    # 7. Recommendation
    parts.append("\n**Summary:**")
    if s_dist < f_dist and s_time > f_time:
        parts.append(
            f"While the Shortest route saves {_format_distance(dist_diff)} in distance, "
            f"the Fastest route saves {_format_time(time_diff)} in travel time by "
            f"avoiding congested segments. Choose the **Shortest route** if minimising "
            f"distance matters most (e.g., walking), or the **Fastest route** if you "
            f"want to arrive sooner."
        )
    elif s_dist < f_dist and s_time <= f_time:
        parts.append(
            f"The Shortest route is both shorter ({_format_distance(dist_diff)} less) "
            f"and equally fast or faster. It is the better choice for both criteria."
        )
    else:
        parts.append(
            f"The Fastest route is **{_format_distance(abs(f_dist - s_dist))}** "
            f"{'shorter' if f_dist < s_dist else 'longer'} and "
            f"**{_format_time(abs(f_time - s_time))}** "
            f"{'faster' if f_time < s_time else 'slower'}."
        )

    return "\n".join(parts)


def generate_multi_route_explanation(
    total_stats_s: dict,
    total_stats_f: dict,
    legs_s: list,
    legs_f: list,
    visiting_order_names: list,
    algo_info: dict,
) -> str:
    """Generate detailed natural language comparison explanation for multi-location search."""
    s_dist = total_stats_s["total_distance"]
    f_dist = total_stats_f["total_distance"]
    s_time = total_stats_s["total_time"]
    f_time = total_stats_f["total_time"]
    s_cong = total_stats_s["total_congestion"]
    f_cong = total_stats_f["total_congestion"]

    algo_name = algo_info.get("name", "Search Algorithm")
    parts = []

    parts.append(
        f"Multi-location tour visiting **{len(visiting_order_names)} destinations** in order: "
        f"{' → '.join(visiting_order_names)}. "
        f"The order was determined using the Nearest Neighbor Heuristic, "
        f"and each leg was routed using **{algo_name}**."
    )

    dist_diff = abs(s_dist - f_dist)
    time_diff = abs(s_time - f_time)

    parts.append(
        f"\n**Distance Comparison:** "
        f"The Shortest route tour covers **{_format_distance(s_dist)}**, "
        f"while the Fastest route tour covers **{_format_distance(f_dist)}** "
        f"({_format_distance(dist_diff)} difference)."
    )

    if s_time > f_time:
        parts.append(
            f"\n**Time Comparison:** The Fastest route tour completes in **{_format_time(f_time)}**, "
            f"saving **{_format_time(time_diff)}** compared to the Shortest route tour ({_format_time(s_time)})."
        )
    elif f_time > s_time:
        parts.append(
            f"\n**Time Comparison:** The Shortest route tour is also faster at "
            f"**{_format_time(s_time)}** vs. **{_format_time(f_time)}** for the Fastest route tour."
        )
    else:
        parts.append(
            f"\n**Time Comparison:** Both tour routes take approximately the same time "
            f"({_format_time(s_time)})."
        )

    if s_cong > f_cong and s_time > f_time:
        parts.append(
            f"\n**Congestion Avoidance:** The Fastest route tour avoids "
            f"**{_format_time(s_cong - f_cong)}** of traffic congestion delay by choosing higher-speed avenues."
        )

    parts.append("\n**Summary:**")
    if s_dist < f_dist and s_time > f_time:
        parts.append(
            f"Choose the **Shortest route tour** if you want to minimise total travel distance "
            f"({_format_distance(dist_diff)} less), or the **Fastest route tour** if you want to arrive "
            f"{_format_time(time_diff)} faster across all destinations."
        )
    elif s_dist < f_dist and s_time <= f_time:
        parts.append(
            f"The Shortest route tour is both shorter and equally fast or faster across all stops."
        )
    else:
        parts.append(
            f"The Fastest route tour provides the best balance of travel time and distance."
        )

    return "\n".join(parts)


import math

def _calculate_bearing(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    initial_bearing = math.atan2(x, y)
    return (math.degrees(initial_bearing) + 360) % 360


def generate_turn_by_turn_directions(graph: Graph, edge_details: list, destinations_info: list = None) -> list:
    """
    Generate step-by-step turn-by-turn navigation instructions (like Google Maps).
    """
    if not edge_details:
        return []

    # Group consecutive edges with the same street_name
    grouped = []
    curr_group = None

    for edge in edge_details:
        street = edge.get("street_name") or edge.get("road_type") or "đường không tên"
        dist = edge.get("distance", 0)
        u_node = graph.get_node(edge.get("start_node", 0))
        v_node = graph.get_node(edge.get("end_node", 0))

        if curr_group and curr_group["street"] == street:
            curr_group["distance"] += dist
            curr_group["edges"].append(edge)
            if v_node:
                curr_group["end_coord"] = (v_node["lat"], v_node["lon"])
        else:
            if curr_group:
                grouped.append(curr_group)
            curr_group = {
                "street": street,
                "distance": dist,
                "edges": [edge],
                "start_coord": (u_node["lat"], u_node["lon"]) if u_node else (0, 0),
                "end_coord": (v_node["lat"], v_node["lon"]) if v_node else (0, 0),
            }
    if curr_group:
        grouped.append(curr_group)

    steps = []
    if not grouped:
        return []

    first_street = grouped[0]["street"]
    first_dist = round(grouped[0]["distance"])
    steps.append({
        "icon": "straight",
        "text": f"Đi thẳng trên {first_street} ({_format_distance(first_dist)})",
        "distance": first_dist,
        "street": first_street,
    })

    dest_idx = 0

    for i in range(1, len(grouped)):
        g_curr = grouped[i]
        g_prev = grouped[i - 1]
        street = g_curr["street"]
        dist = round(g_curr["distance"])

        b_prev = _calculate_bearing(
            g_prev["start_coord"][0], g_prev["start_coord"][1],
            g_prev["end_coord"][0], g_prev["end_coord"][1]
        )
        b_curr = _calculate_bearing(
            g_curr["start_coord"][0], g_curr["start_coord"][1],
            g_curr["end_coord"][0], g_curr["end_coord"][1]
        )

        angle = (b_curr - b_prev + 540) % 360 - 180

        if angle > 35 and angle <= 135:
            icon = "turn-right"
            action = f"Rẽ phải vào {street}"
        elif angle > 135:
            icon = "u-turn"
            action = f"Quay đầu vào {street}"
        elif angle < -35 and angle >= -135:
            icon = "turn-left"
            action = f"Rẽ trái vào {street}"
        elif angle < -135:
            icon = "u-turn"
            action = f"Quay đầu vào {street}"
        else:
            icon = "straight"
            action = f"Đi thẳng tiếp trên {street}"

        steps.append({
            "icon": icon,
            "text": f"{action} ({_format_distance(dist)})" if dist > 0 else action,
            "distance": dist,
            "street": street,
        })

        if destinations_info and dest_idx < len(destinations_info):
            last_edge_v = g_curr["edges"][-1].get("end_node")
            target_poi = destinations_info[dest_idx]
            if last_edge_v == target_poi.get("snap_id") or last_edge_v == target_poi.get("id"):
                steps.append({
                    "icon": "arrive",
                    "text": f"📍 Bạn đã tới địa điểm: {target_poi.get('name', 'Điểm đến')}",
                    "distance": 0,
                    "poi": target_poi.get("name"),
                })
                dest_idx += 1

    if destinations_info and dest_idx < len(destinations_info):
        final_poi = destinations_info[-1]
        steps.append({
            "icon": "arrive",
            "text": f"🏁 Bạn đã tới đích: {final_poi.get('name', 'Điểm đến')}",
            "distance": 0,
            "poi": final_poi.get("name"),
        })

    return steps
