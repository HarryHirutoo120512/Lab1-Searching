"""
Pydantic request/response models for the FastAPI backend.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SearchRequest(BaseModel):
    algorithm: str  # bfs, dfs, ucs, astar, gbfs, bidirectional
    start_node: int
    destinations: List[int]  # 1 = single-location, 2+ = multi-location


class RouteStats(BaseModel):
    total_distance: float
    total_time: float
    total_congestion: float
    total_risk: float
    total_cost: float
    expanded_nodes: int
    execution_time: float  # ms


class ExplorationStep(BaseModel):
    node: int
    frontier: List[int]
    direction: Optional[str] = None  # for bidirectional


class CongestedSegment(BaseModel):
    name: str
    road_type: str
    congestion: float
    average_speed: float
    distance: float


class EdgeDetail(BaseModel):
    from_node: int
    to_node: int
    distance: float
    time: float
    congestion: float
    risk: float
    road_type: str
    street_name: str
    average_speed: float
    max_speed: float


class SingleRouteResult(BaseModel):
    path: List[int]
    explored: List[Dict[str, Any]]
    stats: RouteStats
    edge_details: List[Dict[str, Any]]


class SearchResponse(BaseModel):
    # Both routes are always present for comparison
    shortest_result: SingleRouteResult
    fastest_result: SingleRouteResult
    explanation: str
    congested_segments_shortest: List[CongestedSegment]
    congested_segments_fastest: List[CongestedSegment]
    algorithm_info: Dict[str, Any]


class MultiLegResult(BaseModel):
    visiting_order: List[int]
    legs: List[SingleRouteResult]
    total_stats: RouteStats
    explanation: str


class LocationItem(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
