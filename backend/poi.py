"""
Data Preprocessing Pipeline — Tourist Route Planner
Downloads District 1 HCMC road network from OSM, snaps POIs to edges,
derives deterministic traffic attributes, and exports to CSV.

Key fixes over original:
  - Exports WGS84 lat/lon from the *unprojected* graph (not UTM metres)
  - Stores POI name on every snap_poi node
  - Uses deterministic congestion/risk from Report Table 7 formulas
"""

import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString

# ── OSMnx config ───────────────────────────────────────────────────────
ox.settings.use_cache = True
ox.settings.log_console = True

# ── Road-type parameter tables (Report Table 7) ───────────────────────
# α(q): speed multiplier   ρ(q): risk score
ROAD_TYPE_PARAMS = {
    "trunk":         {"alpha": 0.45, "rho": 0.9},
    "trunk_link":    {"alpha": 0.45, "rho": 0.9},
    "primary":       {"alpha": 0.50, "rho": 0.8},
    "primary_link":  {"alpha": 0.50, "rho": 0.8},
    "secondary":     {"alpha": 0.60, "rho": 0.6},
    "secondary_link":{"alpha": 0.60, "rho": 0.6},
    "tertiary":      {"alpha": 0.65, "rho": 0.5},
    "tertiary_link": {"alpha": 0.65, "rho": 0.5},
    "residential":   {"alpha": 0.75, "rho": 0.3},
    "living_street": {"alpha": 0.85, "rho": 0.1},
}
DEFAULT_PARAMS = {"alpha": 0.75, "rho": 0.3}


def split_line_at_distance(line, distance):
    """Split a LineString at a given distance along it, preserving curvature."""
    if distance <= 0.0 or distance >= line.length:
        return [line]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        p_geom = Point(p)
        pd_val = line.project(p_geom)
        if pd_val == distance:
            return [LineString(coords[: i + 1]), LineString(coords[i:])]
        if pd_val > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:]),
            ]
    return [line]


def get_road_type(highway_val):
    """Normalise the highway tag (may be a list after simplification)."""
    if isinstance(highway_val, list):
        return highway_val[0]
    return highway_val if highway_val else "unclassified"


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    place_name = "District 1, Ho Chi Minh City, Vietnam"

    # ── Step 1–2: Download road network ────────────────────────────────
    print("[1/7] Downloading road network ...")
    G = ox.graph_from_place(place_name, network_type="drive", simplify=False)

    # ── Step 3: Simplify and project ───────────────────────────────────
    print("[2/7] Simplifying graph ...")
    G = ox.simplify_graph(G)
    # Keep unprojected G for WGS84 coordinate export
    G_unprojected = G.copy()
    G_proj = ox.project_graph(G)

    # ── Step 4: Extract POIs ───────────────────────────────────────────
    print("[3/7] Extracting POIs ...")
    tags = {
        "tourism": [
            "museum", "attraction", "gallery",
            "artwork", "viewpoint", "information",
        ]
    }
    pois = ox.features_from_place(place_name, tags=tags)
    pois = pois[pois.geometry.notnull()]
    pois_proj = pois.to_crs(G_proj.graph["crs"]).copy()
    # Convert polygons to centroids
    pois_proj["geometry"] = pois_proj.centroid

    # ── Step 5: Snap POIs to road network ──────────────────────────────
    print("[4/7] Snapping POIs to road network ...")
    new_node_id = max(G_proj.nodes) + 1
    snapped_info = []  # (poi_name, proj_node_id, snap_geom_proj)

    for idx, row in pois_proj.iterrows():
        poi_geom = row["geometry"]
        # Extract POI name from OSM data (checking name, name:vi, name:en, alt_name, official_name)
        poi_name = None
        for name_col in ["name", "name:vi", "name:en", "alt_name", "official_name"]:
            val = row.get(name_col, None)
            if val is not None and not (isinstance(val, float) and np.isnan(val)):
                if isinstance(val, list):
                    val = val[0]
                poi_name = str(val).strip()
                if poi_name:
                    break

        # Skip unnamed generic POIs (e.g. unlabelled info boards, artworks without a title)
        if not poi_name:
            continue

        # Get physical WGS84 POI coordinates (using centroid for Polygons/MultiPolygons)
        orig_poi_wgs = pois.loc[idx]["geometry"].centroid
        poi_node_id = new_node_id
        new_node_id += 1

        try:
            u, v, key = ox.distance.nearest_edges(G_proj, poi_geom.x, poi_geom.y)
        except Exception:
            continue

        edge_data = G_proj.get_edge_data(u, v, key)
        if edge_data is None:
            continue
        edge_data = edge_data.copy()

        # Get edge geometry
        if "geometry" in edge_data:
            line = edge_data["geometry"]
        else:
            line = LineString([
                (G_proj.nodes[u]["x"], G_proj.nodes[u]["y"]),
                (G_proj.nodes[v]["x"], G_proj.nodes[v]["y"]),
            ])

        proj_dist = line.project(poi_geom)
        snap_geom = line.interpolate(proj_dist)

        # Determine snap_node_id on road network
        if proj_dist < 1.0:
            snap_node_id = u
            G_proj.nodes[u]["type"] = "snap_poi"
            G_proj.nodes[u]["poi_name"] = poi_name
            G_proj.nodes[u]["snap_id"] = u
            G_unprojected.nodes[u]["type"] = "snap_poi"
            G_unprojected.nodes[u]["poi_name"] = poi_name
            G_unprojected.nodes[u]["snap_id"] = u
        elif proj_dist > line.length - 1.0:
            snap_node_id = v
            G_proj.nodes[v]["type"] = "snap_poi"
            G_proj.nodes[v]["poi_name"] = poi_name
            G_proj.nodes[v]["snap_id"] = v
            G_unprojected.nodes[v]["type"] = "snap_poi"
            G_unprojected.nodes[v]["poi_name"] = poi_name
            G_unprojected.nodes[v]["snap_id"] = v
        else:
            snap_node_id = new_node_id
            new_node_id += 1

            split_lines = split_line_at_distance(line, proj_dist)
            if len(split_lines) != 2:
                continue

            line1, line2 = split_lines

            u_unproj_data = G_unprojected.nodes[u]
            v_unproj_data = G_unprojected.nodes[v]
            if G_unprojected.has_edge(u, v):
                unproj_edge = G_unprojected.get_edge_data(u, v)
                if isinstance(unproj_edge, dict) and 0 in unproj_edge:
                    unproj_edge_data = unproj_edge[0]
                else:
                    unproj_edge_data = unproj_edge
                if "geometry" in unproj_edge_data:
                    unproj_line = unproj_edge_data["geometry"]
                else:
                    unproj_line = LineString([
                        (u_unproj_data["x"], u_unproj_data["y"]),
                        (v_unproj_data["x"], v_unproj_data["y"]),
                    ])
                frac = proj_dist / line.length if line.length > 0 else 0
                wgs_snap = unproj_line.interpolate(frac, normalized=True)
                wgs_x, wgs_y = wgs_snap.x, wgs_snap.y
            else:
                frac = proj_dist / line.length if line.length > 0 else 0
                wgs_x = u_unproj_data["x"] + frac * (v_unproj_data["x"] - u_unproj_data["x"])
                wgs_y = u_unproj_data["y"] + frac * (v_unproj_data["y"] - u_unproj_data["y"])

            G_proj.add_node(
                snap_node_id,
                x=snap_geom.x, y=snap_geom.y,
                type="snap_poi", poi_name=poi_name, snap_id=snap_node_id,
            )

            G_unprojected.add_node(
                snap_node_id,
                x=wgs_x, y=wgs_y,
                type="snap_poi", poi_name=poi_name, snap_id=snap_node_id,
            )

            len1, len2 = line1.length, line2.length
            edge_data1 = edge_data.copy()
            edge_data1.update({"length": len1, "geometry": line1})
            edge_data2 = edge_data.copy()
            edge_data2.update({"length": len2, "geometry": line2})

            G_proj.add_edge(u, snap_node_id, **edge_data1)
            G_proj.add_edge(snap_node_id, v, **edge_data2)

            if G_proj.has_edge(v, u):
                rev_keys = list(G_proj[v][u].keys())
                for rk in rev_keys:
                    rev_data = G_proj.get_edge_data(v, u, rk).copy()
                    if "geometry" in rev_data:
                        rev_line = rev_data["geometry"]
                    else:
                        rev_line = LineString([
                            (G_proj.nodes[v]["x"], G_proj.nodes[v]["y"]),
                            (G_proj.nodes[u]["x"], G_proj.nodes[u]["y"]),
                        ])
                    rev_proj = rev_line.project(snap_geom)
                    rev_splits = split_line_at_distance(rev_line, rev_proj)
                    if len(rev_splits) == 2:
                        rl1, rl2 = rev_splits
                        rd1 = rev_data.copy()
                        rd1.update({"length": rl1.length, "geometry": rl1})
                        rd2 = rev_data.copy()
                        rd2.update({"length": rl2.length, "geometry": rl2})
                        G_proj.add_edge(v, snap_node_id, **rd1)
                        G_proj.add_edge(snap_node_id, u, **rd2)
                        G_proj.remove_edge(v, u, rk)

            if G_proj.has_edge(u, v, key):
                G_proj.remove_edge(u, v, key)

        # Add physical POI node storing exact landmark coordinates
        G_unprojected.add_node(
            poi_node_id,
            x=orig_poi_wgs.x, y=orig_poi_wgs.y,
            type="poi", poi_name=poi_name, snap_id=snap_node_id,
        )
        snapped_info.append((poi_name, poi_node_id, snap_node_id))

    print(f"    -> Snapped {len(snapped_info)} POIs")

    # ── Step 6: Derive edge attributes (deterministic) ─────────────────
    print("[5/7] Deriving edge attributes ...")
    G_proj = ox.add_edge_speeds(G_proj)
    G_proj = ox.add_edge_travel_times(G_proj)

    for u, v, key, data in G_proj.edges(keys=True, data=True):
        rt = get_road_type(data.get("highway", "unclassified"))
        params = ROAD_TYPE_PARAMS.get(rt, DEFAULT_PARAMS)
        alpha = params["alpha"]
        rho = params["rho"]

        v_max = data.get("speed_kph", 40.0)
        v_avg = alpha * v_max
        dist = data.get("length", 0.0)

        ideal_time = (dist / (v_max / 3.6)) if v_max > 0 else 0.0
        actual_time = (dist / (v_avg / 3.6)) if v_avg > 0 else 0.0
        congestion = max(0.0, actual_time - ideal_time)

        data["road_type"] = rt
        data["distance"] = dist
        data["max_speed"] = v_max
        data["average_speed"] = v_avg
        data["time"] = ideal_time
        data["congestion"] = congestion
        data["risk"] = rho

    # ── Tag node types ─────────────────────────────────────────────────
    for n, data in G_proj.nodes(data=True):
        if "type" not in data:
            data["type"] = "network_grid"

    for n, data in G_unprojected.nodes(data=True):
        if "type" not in data:
            data["type"] = "network_grid"

    # ── Step 7: Export to CSV ──────────────────────────────────────────
    print("[6/7] Exporting to CSV ...")

    node_rows = []
    for node_id, data in G_unprojected.nodes(data=True):
        node_type = data.get("type", "network_grid")
        if node_id in G_proj.nodes:
            proj_data = G_proj.nodes[node_id]
            if proj_data.get("type") == "snap_poi":
                node_type = "snap_poi"

        poi_name = data.get("poi_name", "")
        if not poi_name and node_id in G_proj.nodes:
            poi_name = G_proj.nodes[node_id].get("poi_name", "")

        snap_id = data.get("snap_id", node_id)

        node_rows.append({
            "id": node_id,
            "lat": data.get("y", data.get("lat", 0)),
            "lon": data.get("x", data.get("lon", 0)),
            "type": node_type,
            "name": poi_name if poi_name else "",
            "snap_id": snap_id,
        })

    nodes_df = pd.DataFrame(node_rows)
    nodes_df.set_index("id", inplace=True)

    # --- Edges: unproject to WGS84 to export accurate curved geometries ---
    import json
    G_wgs = ox.project_graph(G_proj, to_crs="EPSG:4326")

    edge_rows = []
    edge_id = 0
    for u, v, key, data in G_wgs.edges(keys=True, data=True):
        geom = data.get("geometry", None)
        if geom is not None:
            coords = [[round(float(c[0]), 6), round(float(c[1]), 6)] for c in geom.coords]
        else:
            u_node = G_wgs.nodes[u]
            v_node = G_wgs.nodes[v]
            coords = [
                [round(float(u_node["x"]), 6), round(float(u_node["y"]), 6)],
                [round(float(v_node["x"]), 6), round(float(v_node["y"]), 6)],
            ]

        geom_json = json.dumps(coords)

        # Get the street name for explanation purposes
        street_name = data.get("name", "")
        if isinstance(street_name, list):
            street_name = street_name[0] if street_name else ""
        if isinstance(street_name, float) and np.isnan(street_name):
            street_name = ""

        edge_rows.append({
            "id": edge_id,
            "start_node": u,
            "end_node": v,
            "oneway": data.get("oneway", False),
            "distance": data.get("distance", 0),
            "road_type": data.get("road_type", "unclassified"),
            "max_speed": data.get("max_speed", 40),
            "average_speed": data.get("average_speed", 30),
            "time": data.get("time", 0),
            "congestion": data.get("congestion", 0),
            "risk": data.get("risk", 0.3),
            "street_name": street_name,
            "geometry": geom_json,
        })
        edge_id += 1

    edges_df = pd.DataFrame(edge_rows)
    edges_df.set_index("id", inplace=True)

    # Save to project root (one level up from backend/)
    import os
    out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_path = os.path.join(out_dir, "processed_nodes.csv")
    edges_path = os.path.join(out_dir, "processed_edges.csv")

    nodes_df.to_csv(nodes_path)
    edges_df.to_csv(edges_path)

    # Print summary
    snap_count = len(nodes_df[nodes_df["type"] == "snap_poi"])
    print(f"[7/7] Pipeline complete!")
    print(f"    -> Nodes: {len(nodes_df)} ({snap_count} snap_poi)")
    print(f"    -> Edges: {len(edges_df)}")
    print(f"    -> Saved to {nodes_path}")
    print(f"    -> Saved to {edges_path}")

    # Verify WGS84 range
    lat_range = (nodes_df["lat"].min(), nodes_df["lat"].max())
    lon_range = (nodes_df["lon"].min(), nodes_df["lon"].max())
    print(f"    -> Lat range: {lat_range[0]:.4f} - {lat_range[1]:.4f}")
    print(f"    -> Lon range: {lon_range[0]:.4f} - {lon_range[1]:.4f}")
    if lat_range[0] > 100 or lon_range[0] > 1000:
        print("    [WARNING] Coordinates look like projected (UTM), not WGS84!")
    else:
        print("    [OK] Coordinates are in WGS84 range")


if __name__ == "__main__":
    main()
