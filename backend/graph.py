"""
Graph loading and in-memory representation.

Reads processed_nodes.csv and processed_edges.csv, builds an adjacency-list
graph, and precomputes min-max normalisation bounds.
"""

import csv
import os
from typing import Dict, List, Optional, Tuple

from cost import NormBounds, compute_norm_bounds


class Graph:
    """
    In-memory directed graph with node/edge attributes.
    Loaded once on backend startup.
    """

    def __init__(self):
        # node_id -> {lat, lon, type, name}
        self.nodes: Dict[int, dict] = {}
        # node_id -> [(neighbour_id, edge_dict), ...]
        self.adj: Dict[int, List[Tuple[int, dict]]] = {}
        # Precomputed normalisation bounds
        self.bounds: NormBounds = NormBounds()
        # POI list (snap_poi nodes only)
        self._pois: Optional[List[dict]] = None

    # ── Loading ────────────────────────────────────────────────────────

    def load(self, data_dir: str):
        """Load from CSV files in *data_dir*."""
        nodes_path = os.path.join(data_dir, "processed_nodes.csv")
        edges_path = os.path.join(data_dir, "processed_edges.csv")

        self._load_nodes(nodes_path)
        self._load_edges(edges_path)
        self._compute_bounds()

    def _load_nodes(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                nid = int(row["id"])
                snap_id = int(row["snap_id"]) if row.get("snap_id") else nid
                self.nodes[nid] = {
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "type": row["type"],
                    "name": row.get("name", ""),
                    "snap_id": snap_id,
                }
                if nid not in self.adj:
                    self.adj[nid] = []

    def _load_edges(self, path: str):
        import json
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                u = int(row["start_node"])
                v = int(row["end_node"])
                geom_str = row.get("geometry", "")
                geometry = []
                if geom_str:
                    try:
                        geometry = json.loads(geom_str)
                    except Exception:
                        geometry = []

                if not geometry:
                    u_node = self.nodes.get(u, {})
                    v_node = self.nodes.get(v, {})
                    geometry = [
                        [u_node.get("lon", 0), u_node.get("lat", 0)],
                        [v_node.get("lon", 0), v_node.get("lat", 0)],
                    ]

                edge = {
                    "start_node": u,
                    "end_node": v,
                    "distance": float(row["distance"]),
                    "road_type": row["road_type"],
                    "max_speed": float(row["max_speed"]),
                    "average_speed": float(row["average_speed"]),
                    "time": float(row["time"]),
                    "congestion": float(row["congestion"]),
                    "risk": float(row["risk"]),
                    "street_name": row.get("street_name", ""),
                    "oneway": row.get("oneway", "False") == "True",
                    "geometry": geometry,
                }
                if u not in self.adj:
                    self.adj[u] = []
                self.adj[u].append((v, edge))

    def _compute_bounds(self):
        """Precompute normalisation bounds from all edges."""
        all_edges = []
        for neighbours in self.adj.values():
            for _, edge in neighbours:
                all_edges.append(edge)
        self.bounds = compute_norm_bounds(all_edges)

    # ── Accessors ──────────────────────────────────────────────────────

    def neighbours(self, node_id: int) -> List[Tuple[int, dict]]:
        """Return list of (neighbour_id, edge_dict)."""
        return self.adj.get(node_id, [])

    def get_node(self, node_id: int) -> Optional[dict]:
        return self.nodes.get(node_id)

    def get_pois(self) -> List[dict]:
        """Return list of POI nodes with physical lat/lon and snap_id for routing."""
        if self._pois is None:
            self._pois = []
            for nid, data in self.nodes.items():
                if (data["type"] == "poi" or data["type"] == "snap_poi") and data.get("name"):
                    self._pois.append({
                        "id": nid,
                        "snap_id": data.get("snap_id", nid),
                        "name": data["name"],
                        "lat": data["lat"],
                        "lon": data["lon"],
                        "type": data["type"],
                    })

            has_physical_pois = any(p["type"] == "poi" for p in self._pois)
            if has_physical_pois:
                self._pois = [p for p in self._pois if p["type"] == "poi"]

        return self._pois

    def get_all_nodes(self) -> List[dict]:
        """Return all nodes for network rendering."""
        result = []
        for nid, data in self.nodes.items():
            result.append({"id": nid, **data})
        return result

    def get_all_edges(self) -> List[dict]:
        """Return all edges for network rendering."""
        result = []
        for neighbours in self.adj.values():
            for _, edge in neighbours:
                u_node = self.nodes.get(edge["start_node"], {})
                v_node = self.nodes.get(edge["end_node"], {})
                result.append({
                    **edge,
                    "start_lat": u_node.get("lat", 0),
                    "start_lon": u_node.get("lon", 0),
                    "end_lat": v_node.get("lat", 0),
                    "end_lon": v_node.get("lon", 0),
                })
        return result

    def nearest_node(self, lat: float, lon: float) -> int:
        """Find the node closest to given WGS84 coordinates."""
        import math
        best_id = -1
        best_dist = float("inf")
        for nid, data in self.nodes.items():
            dlat = data["lat"] - lat
            dlon = data["lon"] - lon
            d = math.sqrt(dlat ** 2 + dlon ** 2)
            if d < best_dist:
                best_dist = d
                best_id = nid
        return best_id
