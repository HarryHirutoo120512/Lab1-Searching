## UNIVERSITY OF SCIENCE **FACULTY OF INFORMATION TECHNOLOGY** 

**==> picture [256 x 111] intentionally omitted <==**

**Group G10** 

24127039 Phan Quang Hiệp 24127500 Nguyễn Đại Phúc 24127508 Lê Nho Duy Phước 

# **LAB 01 REPORT: Search Algorithms for Vietnamese Traffic Route Optimization** 

COURSE: **INTRODUCTION TO ARTIFICIAL INTELLIGENCE** 

CLASS: **24C03** 

**Instructors:** 

PhD. Bùi Tiến Lên BSc. Võ Nhật Tân 

Ho Chi Minh City, 2026 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **Contents** 

|**1**|**Group Introduction**|**Group Introduction**|||**1**|
|---|---|---|---|---|---|
||1.1|Team Members . . . . . . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|1|
||1.2|Contribution Matrix<br>. . . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|1|
||1.3|Completion Status<br>. . . . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|2|
|**2**|**Problem Context**||||**3**|
|**3**|**Problem Modeling**||||**4**|
||3.1|Description of the Graph Model|.|. . . . . . . . . . . . . . . . . . . . . . .|4|
||3.2|Nodes, Edges, States, and Transition Rules . . . . . . . . . . . . . . . . . .|||5|
|||3.2.1<br>Nodes and edges<br>. . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|5|
|||3.2.2<br>Start state and goal state||. . . . . . . . . . . . . . . . . . . . . . .|5|
|||3.2.3<br>Transition rules . . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|6|
||3.3|Description of Node Attributes|.|. . . . . . . . . . . . . . . . . . . . . . .|6|
||3.4|Description of Edge Attributes .|.|. . . . . . . . . . . . . . . . . . . . . . .|7|
||3.5|Cost Function . . . . . . . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|8|
|**4**|**Dataset**||||**10**|
||4.1|Data Source and Creation Method||. . . . . . . . . . . . . . . . . . . . . .|10|
||4.2|Locations Used . . . . . . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|11|
||4.3|Edge-Attribute Values<br>. . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|12|
|||4.3.1<br>Raw OSM Attributes . .|.|. . . . . . . . . . . . . . . . . . . . . . .|12|
|||4.3.2<br>Road-Type Parameters .|.|. . . . . . . . . . . . . . . . . . . . . . .|13|
|||4.3.3<br>Derived Speed, Time, Congestion, and Risk<br>. . . . . . . . . . . . .|||13|
|||4.3.4<br>Attribute Summary . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|14|
||4.4|Group Assumptions . . . . . . .|.|. . . . . . . . . . . . . . . . . . . . . . .|14|



i 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **1 Group Introduction** 

## **1.1 Team Members** 

Table 1 lists all members of Group G10 and their primary responsibilities in this lab assignment. 

– Table 1: Group G10 Member Information 

|**#**|**Student **|**ID**|**Full Name**|**Primary Role**|
|---|---|---|---|---|
|1|24127039||Phan Quang Hiệp|Backend Algorithms|
|2|24127500||Nguyễn Đại Phúc|Frontend & Integration|
|3|24127508||Lê Nho Duy Phước|Algorithms & Report|



## **1.2 Contribution Matrix** 

Table 2 shows the detailed contribution breakdown. Each member contributed approximately one-third of the total work, with specializations distributed across backend, frontend, and documentation tasks. 

Table 2: Contribution Matrix 

|**Task**|**Hiệp**|**Phúc**|**Phước**|
|---|---|---|---|
|Problem Modeling|✓|✓|✓|
|BFS Implementation|||✓|
|DFS Implementation|✓|||
|UCS Implementation|||✓|
|A* Implementation|||✓|
|IDDFS Implementation|✓|||
|Greedy Best-First Impl.|✓|||
|Bidirectional BFS Impl.||✓||
|IDA* Implementation||✓||
|FastAPI Backend Setup|✓|✓||
|Frontend GUI Design||✓||
|HTML/CSS Layout||✓||
|JavaScript Logic||✓||
|Animation System||✓||
|Integration Testing|✓|✓|✓|
|Technical Report|✓|✓|✓|
|Presentation Slides|✓|✓|✓|
|**Estimated %**|**35%**|**30%**|**35%**|



1 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **1.3 Completion Status** 

Table 3 summarizes the completion status of each lab requirement specified in the assignment brief. 

Table 3: Lab Requirement Completion Status 

|**Requirement**|**Status**|**Notes**|
|---|---|---|
|Implement BFS|Done|Fully functional|
|Implement DFS|Done|Fully functional|
|Implement UCS|Done|Fully functional|
|Implement A*|Done|Manhattan heuristic|
|Implement Greedy Best-First|Done|Manhattan heuristic|
|Implement IDDFS|Done|Iterative deepening|
|Implement Bidirectional BFS|Done|Two-frontier approach|
|Implement IDA*|Done|Threshold-based|
|GUI Visualization|Done|Step-by-step animation|
|Algorithm Comparison|Done|Table & charts|
|Technical Report|Done|This document|



2 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **2 Problem Context** 

Our team chose to develop a tourist route planner for visiting multiple landmarks in Ho Chi Minh City. Initially, we intended to map the entire metropolitan area. However, we quickly discovered that the city’s complete traffic network comprises millions of nodes and edges. Processing this enormous dataset would require substantial computational infrastructure, making the experimental phase practically overkill given our current hardware constraints as undergraduate students. To ensure our project remains feasible without sacrificing the authenticity of the problem, we made the strategic decision to shrink the geographic scope strictly to District 1. This central district is an ideal representative subset of the broader city. It features a dense concentration of historical and cultural attractions, paired with highly complex traffic patterns that include one-way streets, varying road types, and frequent rush-hour congestion. By confining our map to District 1, we retain the real-world traffic dynamics necessary to rigorously evaluate our search algorithms. It provides a perfectly balanced environment to demonstrate multi-location route optimization effectively, keeping the project challenging yet computationally manageable. 

When tourists visit a busy urban center like District 1 for the first time, they naturally lack the local knowledge needed to navigate effectively. It is incredibly difficult to determine which paths are the fastest or least affected by rush-hour congestion. This challenge multiplies when travelers want to visit several landmarks within a limited timeframe. Trying to manually compare different route options is not only frustrating and time-consuming but also prone to errors. Furthermore, standard navigation apps simply give a final answer without explaining how the system explored the possibilities. This creates a real-world need for a smart tourism system that systematically explores routes while allowing users to understand the underlying choices. 

Route optimization directly tackles these travel challenges by removing the guesswork and inefficiency from urban navigation. By calculating the most efficient visiting order, a well-optimized path significantly cuts down travel time and prevents frustrating backtracking. This allows visitors to comfortably experience more landmarks during their trip, directly boosting the overall quality of their journey. Beyond helping tourists, this optimization process serves as a practical foundation for our technical evaluation. By applying various artificial intelligence search algorithms to our District 1 map data, we can clearly observe how different strategies explore the network. It provides a concrete way to analyze algorithmic efficiency, convergence speed, and final route quality in a highly realistic setting. 

3 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **3 Problem Modeling** 

## **3.1 Description of the Graph Model** 

The routing area is the road map of District 1, Ho Chi Minh City. For search purposes, the visual map is abstracted as a **weighted, directed graph** 

**==> picture [258 x 13] intentionally omitted <==**

where _V_ = _VN ∪ VP ∪ VS_ contains road-network, POI (point of interest), and snapped POI nodes, while _E_ is the set of directly traversable road segments between routable nodes. This abstraction retains information that affects route selection and map rendering, including road-centerline geometry, while omitting unnecessary visual details such as building outlines and decorative map features. 

A vertex belongs to one of three categories. A road-network node represents a place where road connectivity changes, such as an intersection, junction, or the terminal point of an alley. A POI node preserves the actual geographic coordinates and identity of a destination. Because a POI may not lie directly on a modeled road, a corresponding snapped POI node is placed on the nearest suitable road segment to provide a routable access point. A continuous road section between adjacent routable nodes is represented by an edge. 

The graph is directed because legal travel may differ by direction. A two-way road is represented by two opposite directed edges, whereas a one-way road is represented by only one edge. The graph is weighted because each edge carries quantitative attributes used to evaluate the suitability of a route. 

Table 4: Information retained by the District 1 graph abstraction. 

|**Map element**|**Graph representation**|**Information preserved**|
|---|---|---|
|Intersection or road end|Network node _v ∈VN_|Road topology and available|
|||movement directions|
|Real-world destination|POI node _v ∈VP_|Actual coordinates, name,|
|||and destination identity|
|POI projection onto a road|Snapped POI node _v ∈VS_|Routable access point|
|||associated with the original|
|||POI|
|Traversable road segment|Directed edge (_u, v_)_∈E_|Permitted direction,|
|||centerline geometry, and|
|||travel-related attributes|
|Two-way road|Two edges (_u, v_) and (_v, u_)|Independent travel in both|
|||directions|
|One-way road|One edge in the permitted|Legal direction of movement|
||direction||
|Unrelated visual detail|Omitted|No effect on connectivity,|
|||cost, or road-centerline|
|||geometry|



4 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **3.2 Nodes, Edges, States, and Transition Rules** 

## **3.2.1 Nodes and edges** 

The complete node set is partitioned into three disjoint subsets: 

**==> picture [380 x 13] intentionally omitted <==**

where _VN_ contains road-network nodes, _VP_ contains POI nodes at their actual coordinates, and _VS_ contains snapped POI nodes inserted on the road network. Search algorithms expand only routable nodes in _VN ∪ VS_ . Each POI node _p ∈ VP_ is associated with one snapped node _σ_ ( _p_ ) _∈ VS_ , which connects the destination to the searchable topology. 

Each searchable edge _e_ = ( _u, v_ ) _∈ E_ connects routable nodes _u, v ∈ VN ∪ VS_ and represents direct travel without passing through another decision node. The outgoingneighbor function is defined as 

**==> picture [309 x 13] intentionally omitted <==**

The branching factor at _u_ is therefore the number of legally reachable neighbors in Succ( _u_ ), not the number of roads that merely appear to touch _u_ on the visual map. 

## **3.2.2 Start state and goal state** 

For a single-destination search, a state is the current routable node _n ∈ VN ∪ VS_ . The initial state is 

**==> picture [255 x 13] intentionally omitted <==**

and the goal test is 

**==> picture [290 x 13] intentionally omitted <==**

If the user selects a POI _p ∈ VP_ , the search goal is its associated snapped node _n_ goal = _σ_ ( _p_ ) _∈ VS_ . Reaching this snapped node means that the algorithm has found the road-network access point for the POI. 

The model also supports a route containing several required destinations. Let _D ⊆ VS_ be the set of snapped nodes associated with the selected POIs. In that case, a state must record both the current routable node and the destinations already visited: 

**==> picture [286 x 13] intentionally omitted <==**

The initial state is ( _n_ start _, S_ 0), where _S_ 0 contains the start node only if it is itself a required destination. The multi-destination goal test is 

**==> picture [291 x 13] intentionally omitted <==**

5 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

The set _S_ must be included because the current node alone does not contain enough information in a multi-destination search. For example, the algorithm may reach the same road node _n_ in two cases: state ( _n, {A}_ ) has visited only destination _A_ , whereas state ( _n, {A, B}_ ) has already visited both _A_ and _B_ . Although both states are currently at _n_ , they have different remaining destinations and may require different next routes. They must therefore be treated as distinct search states. 

## **3.2.3 Transition rules** 

From a single-destination state _u_ , an action selects one node _v ∈_ Succ( _u_ ). The transition function is 

**==> picture [258 x 13] intentionally omitted <==**

For a multi-destination state ( _u, S_ ), the corresponding transition is 

**==> picture [314 x 16] intentionally omitted <==**

A transition from _u_ to _v_ is valid only when all of the following conditions hold: 

1. A directed edge ( _u, v_ ) exists in the graph. 

2. The edge is available for travel; closed or inaccessible segments are excluded from the current graph. 

3. The move respects the direction represented by the edge. 

4. The search strategy’s duplicate-state policy permits the resulting state to be inserted into the frontier. 

The final condition is algorithm-dependent. For example, graph-search variants of BFS and UCS avoid expanding an already settled state, while DFS and IDDFS must prevent cycles along the current search path. This policy affects how the state space is explored but does not change the underlying road graph. 

## **3.3 Description of Node Attributes** 

Each node _v ∈ V_ stores the attribute tuple 

**==> picture [347 x 16] intentionally omitted <==**

6 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

Table 5: Attributes stored for each graph node. 

|**Attribute**|**Meaning**|**Role in the model**|
|---|---|---|
|`id`|Unique node identifier|Supports graph indexing, adjacency lookup,|
|||state comparison, and path reconstruction.|
|`lat`|Geographic latitude in|Defines the north–south position used for|
||decimal degrees|display, POI snapping, and spatial lookup.|
|`lon`|Geographic longitude in|Defines the east–west position used for|
||decimal degrees|display, POI snapping, and spatial lookup.|
|`type`|One of `network`, `poi`, or|Determines the node’s structural and routing|
||`snap_poi`|role.|
|`name`|Human-readable road-node|Identifies POIs in input and output; it may|
||or place name|be empty for network nodes.|



The `network` type includes intersections, connectivity changes, and terminal road points such as the ends of alleys. These nodes form the original road topology. A `poi` node records the actual coordinates and name of a real-world destination but is not assumed to be located on a traversable road. A `snap_poi` node is the projection of a POI onto the nearest suitable road segment. It is inserted into the routable topology so that a search algorithm can find the POI’s access point and then associate that result with the original POI. 

## **3.4 Description of Edge Attributes** 

Each directed edge _e_ has an attribute vector 

**==> picture [374 x 15] intentionally omitted <==**

whose components describe travel along that road segment. The attributes are properties of a directed edge rather than of a pair of physical locations; opposite directions of the same road may therefore have different values. The geometry attribute is preserved for visualization and spatial processing even though it is not included in the numerical pathcost function. 

7 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

Table 6: Semantic edge attributes used by the routing model. 

|**Attribute**|**Meaning**|**Role in route evaluation**|
|---|---|---|
|_d_(_e_): distance|Physical length of the road|Measures how far the traveler must move|
|(m)|segment|and forms the distance component of the|
|||cost.|
|_t_(_e_): travel time|Minimum traversal time|Favors routes that can reach the|
|(s)|derived from distance and|destination sooner.|
||maximum speed||
|_c_(_e_): congestion|Additional travel time|Penalizes segments whose practical travel|
|delay (s)|caused by the difference|time is substantially longer than their|
||between average and|free-flow travel time.|
||maximum speed||
|_r_(_e_): risk|Numerical risk score derived|Penalizes road classes associated with less|
|(dimensionless,|from the road type|suitable or less reliable travel.|
|0–1)|||
|_q_(_e_): road type|Category describing the|Provides the source value from which the|
|(categorical)|road class|risk score is determined.|
|_v_avg(_e_): average|Expected practical speed on|Used with maximum speed to calculate the|
|speed (km/h)|the segment|congestion delay.|
|_v_max(_e_):|Legal or design speed|Provides a reference bound and supports|
|maximum speed|associated with the segment|validation of the average speed estimate.|
|(km/h)|||
|_γ_(_e_): geometry|Ordered centerline|Preserves intermediate shape points so|
|(LineString)|coordinates of the road|curved edges can be rendered accurately on|
||segment|the map; it does not directly affect path|
|||cost.|



## **3.5 Cost Function** 

The quality of a route depends on several criteria with different units. Adding raw metres, seconds, and risk scores directly would make the result depend mainly on whichever attribute has the largest numerical scale. Each component is therefore normalized before combination. For an attribute _x ∈{d, t, c, r}_ , define 

**==> picture [325 x 28] intentionally omitted <==**

where _x_ min and _x_ max are reference bounds for that attribute over the modeled District 1 network. If an attribute is constant, its normalized value is defined as zero because it cannot distinguish between routes. 

The cost of traversing edge _e_ is 

**==> picture [336 x 16] intentionally omitted <==**

subject to 

**==> picture [346 x 13] intentionally omitted <==**

8 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

The components have the following interpretations: 

- _wdd_[�] ( _e_ ) is the distance component. A larger _wd_ gives greater preference to physically shorter routes. 

- _wt_[�] _t_ ( _e_ ) is the travel-time component. A larger _wt_ favors routes expected to be completed sooner. 

- 

- • _wcc_ ( _e_ ) is the congestion component. A larger _wc_ avoids roads with a larger estimated congestion delay. 

- 

- • _wrr_ ( _e_ ) is the risk component. A larger _wr_ more strongly penalizes road types assigned a high risk score by _ρ_ . 

For a path _P_ = _⟨e_ 1 _, e_ 2 _, . . . , ek⟩_ , the accumulated path cost is 

**==> picture [273 x 36] intentionally omitted <==**

Different routing preferences are represented by changing the weights rather than changing the graph. For example, a shortest-distance configuration sets _wd_ close to one, a fastestroute configuration emphasizes _wt_ , and a risk-aware configuration assigns more weight to congestion and road-type risk. Because all edge costs are nonnegative, the model is compatible with UCS and with A* when the heuristic is admissible with respect to the selected weighted cost. 

9 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **4 Dataset** 

## **4.1 Data Source and Creation Method** 

The dataset represents the drivable road network and selected tourist destinations in District 1, Ho Chi Minh City. Its primary source is OpenStreetMap (OSM), and the data are downloaded and processed in Python with the `osmnx` library. OSM is suitable for this project because it provides road geometry, connectivity, direction, road classification, speed-limit tags, and point-of-interest metadata in a common geographic coordinate system. 

The dataset is created through the following pipeline: 

1. **Download the study boundary.** The place name `District 1, Ho Chi Minh City, Vietnam` is geocoded to obtain the study-area polygon. 

2. **Download the road network.** The function `osmnx.graph_from_place()` is used with `network_type="drive"` . The returned directed `MultiDiGraph` preserves legal driving direction, including one-way streets. 

3. **Simplify and project the graph.** OSMnx removes intermediate non-junction nodes while preserving curved road shapes in edge LineString geometry, then projects the graph to a metric coordinate system. 

4. **Extract POIs.** The OSMnx function `features_from_place()` obtains features carrying an OSM `tourism` tag. The returned features are filtered by the value of that field. This project retains destination-oriented values such as `museum` , `attraction` , `gallery` , `artwork` , `viewpoint` , and `information` . Features whose `tourism` value is outside the accepted set, or whose geometry is missing, are excluded. Each retained feature is stored as a `poi` node at its actual OSM coordinates. 

5. **Connect POIs to the road network.** For each POI, the nearest suitable drivable edge is located with OSMnx spatial nearest-edge tools. The POI is projected onto that edge, the edge is split at the projected position, and a `snap_poi` node is inserted. This node provides the routable access point used by the search algorithms while the original POI node preserves the destination’s actual position and name. 

6. **Derive edge attributes.** OSMnx supplies segment length and OSM tags such as `highway` , `oneway` , and `maxspeed` , as well as the edge `geometry` . Missing speed limits are replaced by road-type defaults. Ideal time, simulated congestion delay, and risk are then calculated consistently for every directed edge. 

7. **Export the processed data.** Nodes are exported with `id` , `lat` , `lon` , `type` , and `name` . Edges are exported with `id` , `start_node` , `end_node` , `oneway` , `geometry` , `distance` , `road_type` , `max_speed` , `average_speed` , `time` , `congestion` , and `risk` . 

Figure 1 visualizes the extracted District 1 road network using the OSM `highway` classification. The preserved edge geometry allows curved and irregular road segments to follow their actual map shapes instead of being displayed as straight connections between nodes. 

10 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

**==> picture [309 x 417] intentionally omitted <==**

Figure 1: District 1 road-network edges colored by OSM road type. 

## **4.2 Locations Used** 

The POI dataset contains all valid features inside District 1 whose `tourism` value belongs to the accepted destination set, including values such as `museum` and `attraction` . Thus, POI creation is based on a reproducible tag filter rather than a manually chosen coordinate list. The exact locations used by the application are therefore the POI records returned by the OSM query and retained after filtering. No location name or coordinate is manually invented for this report. Because OSM can change over time, the resulting list belongs to the downloaded dataset snapshot rather than being fixed in the document. Each retained record preserves its OSM identifier, name, `tourism` value, latitude, longitude, and geometry. 

Figure 2 shows the POI connection process. The red points are the original POIs at their actual coordinates. The blue points are the corresponding `snap_poi` nodes placed on the nearest suitable road, which makes the destinations reachable by graph-search algorithms. 

11 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

**==> picture [219 x 295] intentionally omitted <==**

- (a) Original POIs before road-network snapping. 

**==> picture [219 x 295] intentionally omitted <==**

(b) Original POIs and their routable snapped nodes. 

Figure 2: Connecting real POI coordinates to the searchable road network. 

## **4.3 Edge-Attribute Values** 

Each directed edge combines values obtained from OSM, parameters configured by road type, and values derived from those inputs. Opposite directions of the same physical road remain separate edges and may have different tags or speeds. The attributes are introduced below in dependency order so that every derived value is defined only after its required inputs. 

## **4.3.1 Raw OSM Attributes** 

Four values are obtained directly from the OSM road graph: 

- The **distance** _d_ ( _e_ ) is the OSMnx edge `length` , measured in metres from the road geometry. 

- The **road type** _q_ ( _e_ ) is the categorical OSM `highway` tag, such as `primary` , `secondary` , `residential` , or `service` . 

- The **maximum speed** _v_ max( _e_ ) is measured in km/h. It is read from the OSM `maxspeed` tag when available; otherwise, a default for the corresponding road type is used. 

- The **geometry** _γ_ ( _e_ ) is the ordered centerline geometry of the edge, normally represented as a LineString of coordinate pairs. It preserves intermediate shape points so that curved road segments can be drawn accurately on the map. If an edge has no explicit LineString, a straight segment between its start and end nodes is used. 

12 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **4.3.2 Road-Type Parameters** 

Each road type _q_ determines two configuration parameters. The multiplier _α_ ( _q_ ), where 0 _< α_ ( _q_ ) _≤_ 1, controls the simulated average speed. The function _ρ_ ( _q_ ) assigns a dimensionless risk score from 0 to 1. 

Larger roads receive smaller speed multipliers because their nominal maximum speeds are less representative of movement in dense Vietnamese traffic. They also receive higher risk scores because of heavy vehicles, mixed traffic, higher speeds, and more severe collision potential. Smaller local roads have lower maximum speeds and therefore receive multipliers closer to one and lower severity-based risk scores. 

Table 7: Road-type mapping for simulated speed and risk. 

|**OSM road type** _q_|**_α_(****_q_)**|**_ρ_(****_q_)**|**Interpretation**|
|---|---|---|---|
|`motorway`|0.40|1.0|Highest risk because of high speeds, heavy container|
||||trucks, and the potential severity of collisions.|
|`trunk`|0.45|0.9|National or major interurban road with heavy vehicles,|
||||high speed, and substantial accident severity.|
|`primary`|0.50|0.8|Major arterial road with dense mixed traffic, buses, cars,|
||||motorcycles, and complex intersections.|
|`secondary`|0.60|0.6|Standard urban road with moderate risk from cross-traffic,|
||||merging, and frequent stopping.|
|`tertiary`|0.65|0.5|Smaller city street with lower speed but continued inter-|
||||action with crossing and merging traffic.|
|`unclassified`|0.75|0.3|Minor local road whose lower speed reduces severe-accident|
||||risk despite less predictable movement.|
|`residential`|0.75|0.3|Neighborhood road or alley with slow traffic, pedestrians,|
||||parked motorcycles, and local access activity.|
|`living_street`|0.85|0.1|Very-low-speed shared space with minimal vehicle risk un-|
||||der the assumed access restrictions.|
|`pedestrian`|0.90|0.1|Walking-oriented space with the lowest modeled vehicle|
||||risk and only explicitly permitted vehicle access.|



The mapping intentionally assigns the highest risk to `motorway` and `trunk` , followed by `primary` , `secondary` , and `tertiary` . Local and shared-space roads receive lower scores because their lower operating speeds reduce the expected severity of an accident. 

## **4.3.3 Derived Speed, Time, Congestion, and Risk** 

The average speed is calculated first because it is required by the congestion formula: 

**==> picture [292 x 15] intentionally omitted <==**

For example, _α_ ( `primary` ) = 0 _._ 50 means that the simulated average speed on a primary road is half of its maximum speed. 

The ideal free-flow travel time is calculated as: 

13 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

**==> picture [300 x 29] intentionally omitted <==**

Congestion is represented as the surplus time caused by traveling at the simulated average speed instead of the maximum speed: 

**==> picture [359 x 29] intentionally omitted <==**

Risk is derived from road type through a fixed mapping: 

**==> picture [266 x 16] intentionally omitted <==**

where _ρ_ supplies the value in Table 7. Both _α_ and _ρ_ are kept separate from the raw OSM attributes so that the simulation assumptions can be changed without downloading the network again. 

## **4.3.4 Attribute Summary** 

Table 8 summarizes the final edge attributes, their dimensions, and their dependencies. 

Table 8: Final edge attributes in dependency order. 

|**Attribute**|**Dimension**|**Source or definition**|
|---|---|---|
|Road type _q_(_e_)|Categorical|OSM `highway` tag|
|Distance _d_(_e_)|m|OSMnx edge `length`|
|Maximum speed _v_max(_e_)|km/h|OSM `maxspeed` or road-type default|
|Average speed _v_avg(_e_)|km/h|_α_(_q_(_e_))_v_max(_e_)|
|Ideal time _t_(_e_)|s|Distance divided by maximum speed|
|Congestion _c_(_e_)|s|Practical traversal time minus ideal time|
|Risk _r_(_e_)|Dimensionless,|Road-type lookup _ρ_(_q_(_e_))|
||0–1||
|Geometry _γ_(_e_)|Spatial|OSMnx edge `geometry`, or a straight line|
||LineString|between endpoint coordinates|



## **4.4 Group Assumptions** 

The dataset and its derived values rely on the following assumptions: 

1. **Ideal travel time.** The baseline travel time for an edge represents optimal free-flow traffic. A vehicle is assumed to maintain the maximum speed assigned to that road type over the entire edge; therefore, ideal time is calculated from distance and maximum speed. 

2. **Congestion as delay.** Congestion is modeled strictly as the additional traversal time beyond the ideal baseline. Average-speed multipliers simulate the effect of road class on practical movement. For example, a multiplier of 0 _._ 50 for a primary road means that its simulated average speed is half its maximum speed, and the difference between the two resulting travel times is recorded as congestion. 

14 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

3. **Risk correlates with infrastructure.** Navigational risks, such as exposure to heavy vehicles or complex intersections, are assumed to be related to physical road design. OSM `highway` classifications are therefore treated as proxies for danger, and a static risk penalty is assigned from road type rather than from real-time incident data. 

4. **Uniform edge conditions.** Distance, road type, speed, risk, and simulated congestion are assumed to remain constant along the full length of a distinct road segment. They also remain unchanged during one route optimization query; temporal fluctuations are outside the scope of the current dataset. 

15 

```
Lab01:SearchAlgorithms
```

```
GroupG10
```

## **Conclusion** 

This lab report presented a comprehensive study of eight classical search algorithms applied to the weighted grid pathfinding problem. Through careful implementation, detailed step-by-step traces on a 5 _×_ 5 reference grid, and experimental evaluation on a 20 _×_ 20 grid, we demonstrated the fundamental trade-offs between completeness, optimality, time complexity, and space complexity that distinguish these algorithms. 

The key insight from our experiments is that no single algorithm dominates all criteria. BFS and IDDFS guarantee finding the shallowest path but ignore edge weights. UCS and A* guarantee optimal weighted paths but may explore more nodes than necessary. Greedy Best-First and IDA* can be remarkably efficient but offer different optimality guarantees. Bidirectional BFS exploits the structure of the search space for improved efficiency. Understanding these trade-offs is essential for selecting the appropriate algorithm for any given real-world application. 

Our web-based visualization tool successfully bridges the gap between theoretical understanding and practical intuition, allowing users to observe how each algorithm explores the search space step by step. 

16 

