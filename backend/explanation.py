"""Route comparison, natural-language explanation, and turn-by-turn directions."""
import math
from graph import Graph
from cost import SHORTEST_WEIGHTS, FASTEST_WEIGHTS, edge_cost
from algorithms import ALGORITHMS, ALGORITHM_PROPERTIES

# ── Formatting helpers ────────────────────────────────────────────────

def _fmt_time(s):
    if s < 60: return f"{s:.0f}s"
    m, s = int(s // 60), int(s % 60)
    if m < 60: return f"{m}m {s}s"
    return f"{m // 60}h {m % 60}m"

def _fmt_dist(m):
    return f"{m / 1000:.2f} km" if m >= 1000 else f"{m:.0f} m"

# ── Internal analysis helpers ─────────────────────────────────────────

def _top_congested(edges, n=3):
    """Return top-n congested segments from edge list."""
    return [{"name": e["street_name"] or e["road_type"], "road_type": e["road_type"],
             "congestion": e["congestion"], "average_speed": e["average_speed"]}
            for e in sorted(edges, key=lambda e: e["congestion"], reverse=True)[:n]
            if e["congestion"] > 0]

def _street_summary(edges):
    """'via A → B → C' from unique street names (fallback to road types)."""
    names = list(dict.fromkeys(e.get("street_name", "") for e in edges if e.get("street_name")))
    if not names:
        names = list(dict.fromkeys(e.get("road_type", "") for e in edges if e.get("road_type")))
    return " → ".join(names[:5])

# ── Single-pair comparison ────────────────────────────────────────────

def compare_routes(graph, algorithm_key, start, goal):
    algo_fn, algo_info = ALGORITHMS[algorithm_key], ALGORITHM_PROPERTIES[algorithm_key]
    shortest = algo_fn(graph, start, goal, SHORTEST_WEIGHTS)
    fastest  = algo_fn(graph, start, goal, FASTEST_WEIGHTS)
    cs = _top_congested(shortest.get("edge_details", []))
    cf = _top_congested(fastest.get("edge_details", []))
    return {
        "shortest_result": shortest, "fastest_result": fastest,
        "explanation": _build_explanation(shortest, fastest, cs, cf, algo_info),
        "congested_segments_shortest": cs, "congested_segments_fastest": cf,
        "algorithm_info": algo_info,
    }

def _build_explanation(shortest, fastest, cs, cf, info):
    ss, fs = shortest["stats"], fastest["stats"]
    sd, fd, st, ft = ss["total_distance"], fs["total_distance"], ss["total_time"], fs["total_time"]
    sc, fc = ss["total_congestion"], fs["total_congestion"]
    sv, fv = _street_summary(shortest.get("edge_details", [])), _street_summary(fastest.get("edge_details", []))
    dd, td = abs(sd - fd), abs(st - ft)

    opt = "guarantees an optimal solution" if info["optimal"] else "does not guarantee optimality"
    p = [f"Both routes were computed using **{info['name']}**, which {opt}."]

    if shortest["path"] == fastest["path"]:
        p.append(f"\nBoth criteria produce the **same route** "
                 f"(distance: {_fmt_dist(sd)}, time: {_fmt_time(st)}).")
        return "\n".join(p)

    p.append(f"\n**Distance comparison:** Shortest{f'  (via {sv})' if sv else ''}: "
             f"**{_fmt_dist(sd)}** | Fastest{f'  (via {fv})' if fv else ''}: "
             f"**{_fmt_dist(fd)}** (Δ {_fmt_dist(dd)})")

    if st > ft:
        p.append(f"\n**Time comparison:** Shortest takes **{_fmt_time(st)}** — "
                 f"**{_fmt_time(td)} slower** than Fastest ({_fmt_time(ft)}).")
    elif ft > st:
        p.append(f"\n**Time comparison:** Shortest is also faster: "
                 f"**{_fmt_time(st)}** vs **{_fmt_time(ft)}**.")
    else:
        p.append(f"\n**Time comparison:** Both ≈ {_fmt_time(st)}.")

    if cs and st > ft:
        p.append("\n**Why Shortest is slower:**")
        for s in cs:
            p.append(f"  • **{s['name']}** ({s['road_type']}): delay {_fmt_time(s['congestion'])}, "
                     f"avg {s['average_speed']:.0f} km/h")

    cd = sc - fc
    if cf and cd > 0:
        p.append(f"\n**Fastest avoids** {_fmt_time(cd)} of congestion.")
    elif cf and cd < 0:
        p.append(f"\n**Trade-off:** Fastest has {_fmt_time(-cd)} more congestion "
                 f"but higher base speeds → still faster overall.")

    p.append("\n**Summary:**")
    if sd < fd and st > ft:
        p.append(f"Shortest saves {_fmt_dist(dd)}; Fastest saves {_fmt_time(td)}. "
                 f"Choose by priority: distance vs. time.")
    elif sd < fd:
        p.append(f"Shortest is both shorter ({_fmt_dist(dd)} less) and equally fast or faster.")
    else:
        p.append(f"Fastest is **{_fmt_dist(abs(fd-sd))}** "
                 f"{'shorter' if fd<sd else 'longer'} and "
                 f"**{_fmt_time(abs(ft-st))}** {'faster' if ft<st else 'slower'}.")
    return "\n".join(p)

# ── Multi-location explanation ────────────────────────────────────────

def generate_multi_route_explanation(ts, tf, legs_s, legs_f, names, info):
    sd, fd = ts["total_distance"], tf["total_distance"]
    st, ft = ts["total_time"], tf["total_time"]
    sc, fc = ts["total_congestion"], tf["total_congestion"]
    dd, td = abs(sd - fd), abs(st - ft)
    an = info.get("name", "Search Algorithm")

    p = [f"Multi-location tour: **{len(names)} stops** ({' → '.join(names)}). "
         f"Order: Nearest Neighbor; routing: **{an}**."]
    p.append(f"\n**Distance:** Shortest **{_fmt_dist(sd)}** | Fastest **{_fmt_dist(fd)}** (Δ {_fmt_dist(dd)})")

    if st > ft:
        p.append(f"\n**Time:** Fastest completes in **{_fmt_time(ft)}**, saving **{_fmt_time(td)}**.")
    elif ft > st:
        p.append(f"\n**Time:** Shortest is faster: **{_fmt_time(st)}** vs **{_fmt_time(ft)}**.")
    else:
        p.append(f"\n**Time:** Both ≈ {_fmt_time(st)}.")

    if sc > fc and st > ft:
        p.append(f"\n**Congestion:** Fastest avoids **{_fmt_time(sc - fc)}** of delay.")

    p.append("\n**Summary:**")
    if sd < fd and st > ft:
        p.append(f"Shortest saves {_fmt_dist(dd)}; Fastest saves {_fmt_time(td)}.")
    elif sd < fd:
        p.append("Shortest is both shorter and equally fast or faster.")
    else:
        p.append("Fastest provides the best balance of time and distance.")
    return "\n".join(p)

# ── Bearing calculation ───────────────────────────────────────────────

def _bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def _edge_bearing(graph, edge, pos="end"):
    """Bearing at the start or end of an edge, using geometry if available."""
    geom = edge.get("geometry", [])
    if geom and len(geom) >= 2:
        (p1, p2) = (geom[-2], geom[-1]) if pos == "end" else (geom[0], geom[1])
        if abs(p1[0]-p2[0]) > 1e-7 or abs(p1[1]-p2[1]) > 1e-7:
            return _bearing(p1[1], p1[0], p2[1], p2[0])
    uid = edge.get("from", edge.get("start_node"))
    vid = edge.get("to",   edge.get("end_node"))
    u, v = (graph.get_node(uid) if uid else None), (graph.get_node(vid) if vid else None)
    return _bearing(u["lat"], u["lon"], v["lat"], v["lon"]) if u and v else 0.0

# ── Turn-by-turn directions ──────────────────────────────────────────

def generate_turn_by_turn_directions(graph, edge_details, destinations_info=None, start_info=None):
    if not edge_details: return []
    legs = edge_details if isinstance(edge_details[0], list) else [edge_details]
    steps = []

    if start_info and start_info.get("name"):
        steps.append({"icon": "start", "text": f"Bắt đầu từ: {start_info['name']}",
                       "distance": 0, "poi": start_info["name"]})

    for li, leg in enumerate(legs):
        if not leg: continue
        # Group consecutive edges sharing the same street
        groups, cur = [], None
        for e in leg:
            st = e.get("street_name") or e.get("road_type") or "đường không tên"
            d  = e.get("distance", 0)
            uid = e.get("from", e.get("start_node"))
            vid = e.get("to",   e.get("end_node"))
            if cur and cur["street"] == st:
                cur["distance"] += d; cur["edges"].append(e); cur["end"] = vid
            else:
                if cur: groups.append(cur)
                cur = {"street": st, "distance": d, "edges": [e], "start": uid, "end": vid}
        if cur: groups.append(cur)
        if not groups: continue

        # First segment is always "go straight"
        g0 = groups[0]
        rd = round(g0["distance"])
        steps.append({"icon": "straight",
                       "text": f"Đi thẳng trên {g0['street']} ({_fmt_dist(rd)})" if rd > 0 else f"Đi thẳng trên {g0['street']}",
                       "distance": rd, "street": g0["street"]})

        # Subsequent segments: compute turn angle
        for i in range(1, len(groups)):
            gp, gc = groups[i-1], groups[i]
            st, d = gc["street"], round(gc["distance"])
            angle = (_edge_bearing(graph, gc["edges"][0], "start")
                     - _edge_bearing(graph, gp["edges"][-1], "end") + 540) % 360 - 180

            if   angle >  20 and angle <=  135: icon, act = "turn-right", f"Rẽ phải vào {st}"
            elif angle >  135:                  icon, act = "u-turn",     f"Quay đầu vào {st}"
            elif angle < -20 and angle >= -135: icon, act = "turn-left",  f"Rẽ trái vào {st}"
            elif angle < -135:                  icon, act = "u-turn",     f"Quay đầu vào {st}"
            else:                               icon, act = "straight",   f"Đi thẳng tiếp trên {st}"

            steps.append({"icon": icon,
                           "text": f"{act} ({_fmt_dist(d)})" if d > 0 else act,
                           "distance": d, "street": st})

        # Arrival
        if destinations_info and li < len(destinations_info):
            pn = destinations_info[li].get("name", "Điểm đến")
            if len(legs) > 1 and li < len(legs) - 1:
                steps.append({"icon": "arrive", "text": f"Bạn đã tới điểm dừng {li+1}: {pn}", "distance": 0, "poi": pn})
            else:
                steps.append({"icon": "arrive", "text": f"Bạn đã tới đích: {pn}", "distance": 0, "poi": pn})

    return steps
