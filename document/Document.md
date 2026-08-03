# Software Design Document — Tourist Route Planner

**Project:** Tourist Route Planner (Ho Chi Minh City) — AI Search Lab
**Purpose of this document:** define the system architecture as two independent parts — Backend and Frontend — describe what each part owns, and specify exactly what data crosses the boundary between them.
**Note on Data Origin:** The backend repository also houses the offline data preprocessing pipeline (OSMnx script) responsible for extracting real-world Ho Chi Minh City traffic data into the processed CSV files used by the system.
**Out of scope:** any implementation-level detail (function names, code structure, libraries). This document describes responsibilities and behavior only.

---

## 1. System overview

The system is split into two independent parts that communicate over a request/response API:

- **Backend** — owns the graph, the search algorithms, the multi-location ordering logic, and all computation (statistics, exploration history, alternative-route generation, route explanation). It has no knowledge of how anything is displayed.
- **Frontend** — owns everything the user sees and interacts with: the map, the input controls, the animation, and the statistics/explanation display. It has no knowledge of how a route or an itinerary is computed; it only knows how to ask for one and how to render whatever it receives back.

The two parts never share memory or internal state. Every interaction is a single request from the Frontend followed by a single response from the Backend. This separation is intentional: it matches the assignment's split between "backend responsible for loading the graph and performing route search" and "GUI responsible for display," and it means either side could be replaced independently (e.g., swapping the map library, or swapping an algorithm's internal implementation) without touching the other.

---

## 2. Routing behavior: single-location and multi-location

The system supports two routing behaviors, sharing the same underlying search algorithms but differing in how many destinations are given and how the final route is assembled. **There is no explicit mode switch presented to the user or sent to the backend as a separate field** — see §4.3 for why, and §5.1 for how the backend tells the two cases apart from the request shape alone.

### 2.1 Single-location route search

The user selects one start location and exactly one destination. The backend runs whichever of the six implemented search algorithms (BFS, DFS, UCS, A*, Greedy Best-First Search, or Bidirectional Search) the user selected, under the user's chosen optimization criterion, and returns a single route between the two points.

### 2.2 Multi-location route optimization

The user selects one starting location and two or more tourist destinations, added incrementally (§4.3), with no particular order implied by the order they were added in. The system must then decide two separate things: **in what order** to visit the destinations, and **what detailed route** to take between each consecutive pair. These are treated as two distinct steps rather than one combined search:

1. **Determine the visiting order — Nearest Neighbor Heuristic.** Starting from the user's chosen start location, the system repeatedly selects the nearest unvisited destination as the next stop, moves to it, and repeats until every destination has been visited. "Nearest" is measured the same way distance is measured elsewhere in the system (straight-line or graph distance, consistent with the heuristic already used by A*/GBFS), not by running a full route search for every candidate at every step. The result of this step is an ordered sequence of destinations — the visiting order — not yet a detailed road-level route.
2. **Determine the detailed route for each leg — the selected search algorithm.** Once the visiting order is fixed, the backend invokes the search algorithm the user selected (A* is the preferred default, but any of the six supported algorithms may be used if explicitly chosen) once for every consecutive pair of locations in that order, exactly as it would for a single-location search between those two points.
3. **Assemble the itinerary.** The individual leg routes are concatenated, in visiting order, into one continuous itinerary, and the per-leg statistics are summed into itinerary-wide totals.

This two-step design keeps the ordering decision (a discrete combinatorial problem, effectively a small Traveling-Salesman-style question) separate from the routing decision (a graph-search problem the system already solves for single-location mode), so the same six algorithm implementations serve both modes without modification.

### 2.3 Why the Nearest Neighbor Heuristic was selected

Ordering an arbitrary number of tourist destinations exactly optimally is a Traveling-Salesman-Problem-style combinatorial problem, whose exact solution methods (e.g., brute-force enumeration, dynamic programming) become impractical as the number of destinations grows. Since the assignment explicitly allows an approximate method for this part of the project (§4.5, "brute force for a small number of locations, nearest neighbor heuristic, dynamic programming, genetic algorithm, simulated annealing, or another appropriate heuristic method"), the Nearest Neighbor Heuristic was chosen as the method that best matches the practical needs of a tourist route planner over the alternatives:

- **Simple to implement.** The rule is a single, repeated decision — "go to the nearest place you haven't visited yet" — with no tuning parameters, population sizes, or cooling schedules to configure, unlike genetic algorithms or simulated annealing.
- **Fast execution.** Determining the full visiting order for *k* destinations requires on the order of *k²* distance comparisons, which is negligible next to the cost of the subsequent graph searches themselves, and stays fast even as the number of tourist stops grows.
- **Suitable for tourist route planning.** A tourist choosing several attractions in a city is well served by a "visit whatever is closest next" strategy, since it mirrors how a person would plan a walking or driving day intuitively, and it avoids implausible-looking itineraries that backtrack across the city.
- **Scalable to many destinations.** Because the heuristic's cost grows only quadratically and requires no global search over all possible orderings, it remains usable even if a future version of the system allows a large number of selected destinations, which an exact method would not.

### 2.4 Limitation of the Nearest Neighbor Heuristic

The heuristic does not guarantee the globally optimal visiting order — greedily choosing the nearest next destination at each step can lead to an itinerary that is worse overall than a different ordering would have been (a classic failure mode of nearest-neighbor construction in TSP-style problems, where an early greedy choice strands a later destination far out of the way). It provides an **approximate but practical** solution rather than a provably optimal one. This limitation must be stated explicitly wherever the multi-location result is presented — in the statistics panel and in the technical report's algorithm-comparison section — consistent with the assignment's requirement that the group state clearly whether the selected multi-location method guarantees optimality or only approximates it.

The report's Multi-location Optimization section (assignment §4.9h) explicitly asks for a **comparison between the original visiting order and the optimized visiting order**. "Original" here means the order the user happened to add the destinations in (which the frontend naturally has, even though the backend treats the destination set as unordered for computation) — the backend does not need to preserve or return this separately; the frontend already knows the order it sent, and the report comparison can be produced by running the same itinerary computation once on that original order and once on the Nearest-Neighbor order, and comparing the two resulting totals.

---

## 3. Cost function and statistics

The assignment (§4.3) requires the cost of a road segment to combine four factors with group-chosen weights:

> Cost = α × Distance + β × Time + γ × Congestion + δ × Risk

All three optimization criteria the system exposes are built on this same formula, not three unrelated formulas:

| Optimization criterion | Effective weights |
|---|---|
| Distance | α = 1, β = γ = δ = 0 |
| Time | β = 1, α = γ = δ = 0 |
| Hybrid cost | α, β, γ, δ all non-zero, as designed and justified by the group in the report's Cost Function section |

Framing all three modes as special cases of one weighted formula (rather than "hybrid" being a separate, differently-defined calculation) keeps the backend's cost-evaluation logic single and consistent, and keeps the report's explanation of the weights applicable to every mode, not just the hybrid one.

Because Distance, Time, Congestion, and Risk are on different numeric scales (meters, seconds, a 1–5 level, and a risk penalty respectively), they must be normalized onto a comparable scale before the weighted sum is computed — this normalization step and the chosen weight values are exactly what the report's Cost Function section (assignment §4.3) is required to explain, so this document does not redefine it, only confirms the backend uses that same definition rather than inventing a second one.

**Total route cost** — the scalar value actually produced by this formula for a given route — is a required, separate statistic (assignment §4.7 lists "total route cost" alongside total distance and total estimated time as distinct outputs). It is reported in addition to, not instead of, the raw distance/time/congestion/risk totals, since a route search under "Distance" mode still has a well-defined hybrid cost value even though it wasn't the criterion being optimized.

---

## 4. Backend responsibilities

The backend is responsible for the full lifecycle of a route search or a multi-location itinerary, end to end, and for packaging the result in a form the frontend can render without any additional computation.

| Responsibility | Description |
|---|---|
| **Loading the processed graph** | Reads `processed_nodes.csv` and `processed_edges.csv` once, builds the in-memory graph, and keeps it resident for the lifetime of the running backend process — the graph is not reloaded on every request. |
| **Inferring single- vs. multi-location behavior** | Determined from the request shape alone (§5.1): exactly one destination runs the single-location behavior of §2.1; two or more destinations run the multi-location behavior of §2.2. No separate mode flag exists to get out of sync with the actual destination count. |
| **Executing search algorithms** | Runs whichever of the six required algorithms the request specifies, using the optimization criterion (distance / time / hybrid cost) also specified in the request. |
| **Recording every exploration step** | While an algorithm runs, the backend records the order in which nodes are expanded and the state of the frontier at each step. This history is not a byproduct — it is a first-class output the frontend animation depends on. |
| **Computing path statistics** | For a returned route, the backend computes total distance, total travel time, total congestion, total risk, **total route cost** (§3), number of expanded nodes, and execution time. |
| **Determining the primary route (single-location mode)** | The route actually produced by the requested algorithm under the requested optimization criterion. |
| **Determining an alternative route (single-location mode)** | A second, valid start-to-goal route that differs from the primary route. It does not need to be optimal — its only requirement is that it is a genuinely different, legal path between the same two locations, so the user has something meaningful to compare the primary route against. |
| **Producing the route explanation (single-location mode)** | A human-readable justification of why the primary route was chosen over the alternative (§4.1 below), built from the statistics and, critically, the individual edge attributes of both routes. |
| **Exposing the API** | All of the above is only reachable through a defined set of endpoints; the backend does not assume anything about who is calling it or how the response will be displayed. |

### 4.0 Data Preprocessing Pipeline (Offline)

Although the search algorithms run in real-time, the backend repository explicitly includes the offline data extraction script. This script is responsible for:
- Downloading the actual OpenStreetMap network for District 1, Ho Chi Minh City using `osmnx`.
- Identifying Tourist Points of Interest (POIs) and snapping them correctly to the road network (adding routing nodes and splitting edges).
- Generating simulated traffic conditions (time, congestion, risk) to fulfill the assignment's "Hybrid data" requirement.
- Exporting the final graph to `processed_nodes.csv` and `processed_edges.csv`.

**Execution:** This script is run *offline* by the developers to generate the dataset. The backend API server does not run this script on every user request; it only reads the resulting CSV files on startup. Keeping this script in the backend folder ensures data reproducibility and documents exactly how the dataset is modeled.

**⚠ Known data-compatibility risk to resolve before frontend integration:** the current pipeline calls `ox.project_graph()` to get a metric (meter-based) coordinate system for accurate distance calculations, but then exports the node coordinates from that *projected* graph directly into the `lat`/`lon` columns of `processed_nodes.csv`. Projected coordinates are not geographic latitude/longitude — they are typically large UTM-style meter values (e.g., `1192794`, `687303`), not values in the expected `~10.7x`, `~106.6x` range for Ho Chi Minh City. A Google-Maps-style frontend (§6) places markers using real WGS84 latitude/longitude in degrees, so if this is not corrected, every marker and every route drawn on the map will be positioned incorrectly. The fix is to export `lat`/`lon` from the **original, unprojected** graph (before `ox.project_graph()` is applied), while continuing to use the projected graph only internally for computing `distance`/`length` in meters — the two coordinate systems serve different purposes and neither should be discarded, but they must not be exported under the same two columns. This should be verified and corrected in the preprocessing script before any frontend map work begins.

### 4.1 Route Explanation (assignment §4.8) — a required output, not an optional add-on

Assignment §4.8 states plainly: *"The project must include an explanation component. The system should not only output a path, but also explain the result in a human-understandable way."* This is graded as its own line item ("Route explanation and comparison of alternatives — 10 points"), so it is treated here as a first-class backend responsibility with its own dedicated response field and its own dedicated frontend panel (§5, §6.2) — not something folded silently into the statistics display.

The assignment's own example makes clear the explanation is not a repeated printout of the statistics panel, but a *causal* paragraph:

> "The route A → C → F → H is selected because it has the lowest total cost. Although route A → B → H is shorter in distance, it passes through a highly congested area during rush hour. Therefore, its estimated travel time and congestion penalty are higher."

Assignment §4.8 lists five things the explanation must contain. Each is addressed explicitly by this architecture:

| §4.8 requirement | How this architecture produces it |
|---|---|
| **Why the selected route was chosen** | The backend compares the primary route's total cost (§3) against the alternative's, and states the primary route as the winner on whichever criterion the user selected — this is the opening sentence of the explanation, mirroring "...is selected because it has the lowest total cost" in the assignment's example. |
| **Whether it is shortest by distance, fastest by time, or best by total cost** | Determined directly from the `Optimization mode` the user selected for the request (§6.1) — the explanation always names this criterion explicitly rather than leaving it implicit. |
| **Which road segments have high congestion** | The backend walks the edge-level attributes of the *alternative* route (the one not chosen) and identifies specific segments with high `congestion` or low `average_speed`, naming them by road name/type — see the numbered steps below. This is the step most architectures skip by only comparing totals; it is deliberately called out here because it is what makes the explanation causal rather than descriptive. |
| **How the result differs from another possible route** | This is precisely the role of the alternative route (§4.2) — the explanation is always a comparison between the primary and the alternative, never the primary route described in isolation. |
| **Whether the algorithm guarantees optimality** | Looked up from the fixed optimal/approximate classification of the algorithm actually used (the same classification already established for BFS/DFS/UCS/A*/GBFS/Bidirectional in the report's Algorithm Principles section, and for the Nearest Neighbor Heuristic in §2.4) — never re-derived per request, since it is a property of the algorithm, not of any particular run. |

Producing the "which road segments have high congestion" requirement specifically requires the explanation logic to go one level below the summary statistics:

1. Compute the summary comparison (total distance, time, congestion, risk, and cost for both the primary and the alternative route).
2. Walk the **edge-level attributes** of the alternative route and identify which specific road segments are responsible for it losing on the selected criterion — for example, a segment whose `average_speed` is markedly lower than the rest of the route, or whose `congestion` value is high. Because `processed_edges.csv` already stores `road_type` and `average_speed` per segment (§4.0), this is a lookup over data already present, not a new computation.
3. Name those segments by their road name/type in the explanation text, rather than only reporting that "the total time is higher" — e.g., "...because it passes through [road name/type], which has a low average speed of [value] km/h, raising the estimated travel time by [delta] despite the shorter distance."

This is what distinguishes the explanation component from simply re-displaying the statistics panel: it points at the cause, not only the effect — and it is why "Route explanation" appears in §6.2 as its own response field, and why the frontend has a dedicated explanation panel (§5) rather than a line inside the statistics table.


### 4.2 On the alternative route

Three ways of obtaining a valid non-optimal alternative are worth considering; the team should pick one and record the choice (and the reasoning) in the report, rather than leaving it implicit:

- **Different algorithm, same criterion** — run a second algorithm (e.g., if the primary route came from A*, run DFS or GBFS instead) over the same start/goal/criterion. Simple to justify, and it also gives a concrete second data point for the algorithm-comparison section of the report.
- **Same algorithm, penalized primary edges** — re-run the same algorithm after temporarily increasing the cost of the edges used by the primary route, forcing the search to route around them. Produces a route that is meaningfully different in shape, not just marginally different in cost.
- **Same algorithm, different optimization criterion** — e.g., primary route optimizes hybrid cost, alternative optimizes pure distance (or vice versa). This pairs naturally with the route-explanation example already required by §4.8 and with §4.1 above, since the two routes are then directly comparable on the criterion the primary route deliberately traded away.

Any of the three satisfies the stated requirement ("does not need to be optimal, but must be a valid route"); the second option produces the most visually distinct alternative, which is likely to matter more for the animation than for the report text. This mechanism applies to single-location mode only; multi-location itineraries are not currently required to have a secondary alternative itinerary (see §4.4).

### 4.3 On exploration history

Because the frontend must animate the search rather than only display the final answer, the backend cannot treat exploration order as an implementation detail — it has to be captured deliberately, in a form ordered exactly the way the algorithm expanded nodes, and returned in full as part of the response. Recomputing this on the frontend is not possible without duplicating the search logic, so this history must originate entirely from the backend.

### 4.4 Multi-location responsibilities

When the request contains two or more destinations (§4 table, "Inferring single- vs. multi-location behavior"), the backend additionally handles:

| Responsibility | Description |
|---|---|
| **Receiving multiple destinations** | Accepting the list of tourist destinations selected by the user, in addition to the single start location. |
| **Determining the visiting order** | Applying the Nearest Neighbor Heuristic (§2.2) starting from the start location to produce an ordered sequence covering every requested destination exactly once. |
| **Repeatedly invoking the selected search algorithm** | Calling the same single-location search logic once per consecutive pair in the visiting order (start → destination 1, destination 1 → destination 2, and so on), using the algorithm and optimization criterion the user selected. |
| **Merging subpaths into one itinerary** | Concatenating the individual leg routes, in visiting order, into a single continuous route with no gaps or overlaps at the junctions between legs. |
| **Calculating itinerary-wide totals** | Summing distance, travel time, congestion, risk, and total cost (§3) across all legs to produce the totals for the complete trip, in addition to (not instead of) the per-leg statistics. |

Exploration history is still recorded per leg (§4.3), so the frontend can optionally animate each leg's search individually, in visiting order, rather than only animating the single-location case.

---

## 5. Frontend responsibilities

The frontend is responsible for everything the user directly experiences, and for translating user actions into a single, well-formed request to the backend.

| Responsibility | Description |
|---|---|
| **Rendering the interactive map** | An interactive base map showing the road network, supporting zoom and pan, in a style of interaction similar to Google Maps (click, drag, scroll-to-zoom) — not necessarily matching its visual design. |
| **Displaying nodes and edges** | Drawing the underlying road network (or a simplified version of it) on top of the base map so the graph structure is visible, not just an abstract search result. |
| **Collecting user input** | Start location and destination(s), chosen either by clicking on the map or by searching for a named location; algorithm selection; optimization-criterion selection; and the Search / Reset actions. |
| **Sending requests to the backend** | Packaging the current selections into a single request once the user presses Search. |
| **Animating exploration** | Replaying the exploration history returned by the backend, progressively marking nodes as visited and distinguishing frontier nodes visually, so the search appears to spread outward from the start node rather than appearing all at once. |
| **Drawing the primary path** | Highlighting the final algorithm-returned route in a color distinct from both the exploration animation and the alternative route. |
| **Drawing the alternative path** | Highlighting the second, non-optimal route in its own distinct color, drawn so both routes can be visually compared at the same time. |
| **Highlighting the congested segments named in the explanation** | Visually marking, on the alternative path, the specific road segments identified by the backend's explanation (§4.1) as high-congestion or low-speed — so the "which road segments have high congestion" requirement is shown on the map itself, not only stated in the explanation text. |
| **Displaying statistics** | Presenting algorithm name, total distance, total travel time, congestion value, risk value, **total route cost**, expanded nodes, and execution time in a dedicated panel. |
| **Displaying the route explanation** | Rendering the causal, human-readable explanation text (§4.1 / assignment §4.8) in its own dedicated panel, distinct from the statistics panel — since the explanation is a required, separately-graded output, not a caption on the numbers. |

### 5.1 On animation ownership

Since the backend already returns the complete, ordered exploration history in one response (see §4.3), the animation itself — the timing, the pacing, play/pause, replay — is entirely a frontend concern. The frontend does not ask the backend "what happened at step N"; it already has every step and simply reveals them over time. This keeps the interaction to a single request/response cycle per search, rather than the frontend polling the backend repeatedly while an animation plays.

### 5.2 On location selection

Supporting both click-to-select and search-to-select on the map means the frontend needs a way to translate a click into "the nearest valid node" and to translate a typed query into a matching named location — both are frontend-side lookups against the location list the backend exposes (see §6), not new computation the backend needs to perform beyond serving that list.

### 5.3 Multi-destination interface — Google-Maps-style, no explicit mode switch

Rather than asking the user to declare "single" or "multi" mode up front, the interface grows the same way Google Maps' own directions panel does, so the interaction style is already familiar and requires no explanation:

| Interface element | Behavior |
|---|---|
| **Default state** | The panel shows exactly two input rows: **Start** and **Destination**. This is indistinguishable from a single-location search until the user does something more. |
| **"Add destination" affordance** | A small "+ Add destination" link/button sits directly beneath the Destination row, identical in placement and purpose to Google Maps'. Clicking it appends a new destination input row below the existing ones. |
| **Growing the list** | Each click of "+ Add destination" appends one more row; there is no fixed cap presented to the user other than a sensible practical limit (documented, not hard-blocked, since the Nearest Neighbor Heuristic stays fast regardless — §2.3). |
| **Removing a destination** | Every destination row (but not the Start row) carries its own small "×" remove control, so any single destination can be deleted without disturbing the others. |
| **Implicit behavior determination** | The interface itself never asks the user to choose a "mode." Whether the resulting search is single-location or multi-location follows purely from how many destination rows are filled in when Search is pressed — one filled destination row sends the single-location request shape (§6.1); two or more send the multi-location shape. This mirrors exactly how the backend infers behavior from request shape (§4, "Inferring single- vs. multi-location behavior"), so frontend and backend never need to agree on a separate mode value. |
| **Simple, button-driven list management** | The destination list is built and edited entirely through the "+ Add destination" and "×" remove controls described above — no other interaction is available or needed to manage it. Rows are simply listed in the order they were added. Keeping list management to these two buttons avoids adding interaction complexity to the interface beyond what the project needs to demonstrate. |
| **Auto-reorder after search** | Once a multi-location search returns, the frontend re-orders the physical input rows on screen to match the Nearest-Neighbor-optimized visiting order returned by the backend, so the input list and the numbered map markers (§5.4) always agree with each other after a search completes. |

### 5.4 Multi-location result display

Once a multi-location search returns, in addition to the interface behavior in §5.3:

| Responsibility | Description |
|---|---|
| **Visualizing the complete itinerary** | Drawing every leg of the returned itinerary on the map as one continuous, visually connected route, using the same primary-path styling already established for single-location mode. |
| **Numbering the visiting order** | Marking each destination on the map with its position in the visiting order (1, 2, 3, ...) as determined by the backend, so the Nearest-Neighbor-derived sequence is immediately readable rather than implied only by the drawn line. |
| **Displaying total statistics** | Presenting the itinerary-wide totals (total distance, total time, total congestion, total risk, total cost) for the whole trip, distinguished from — and in addition to — any per-leg statistics the interface chooses to also expose. |

---

## 6. Communication contract

The frontend and backend exchange exactly two kinds of messages: a **search request** (frontend → backend) and a **search response** (backend → frontend). A third, lighter exchange supplies the location list used for search-to-select and for populating the base map.

### 6.1 Frontend → Backend (search request)

| Field | Meaning |
|---|---|
| Selected algorithm | Which of the six algorithms to run for each route leg |
| Start node | The node the user selected as the origin |
| Destination list | One or more destination nodes, in the order the rows currently appear in the interface (§5.3) — a list with exactly one entry is a single-location request; a list with two or more entries is a multi-location request |
| Optimization mode | Distance, time, or hybrid cost |

There is no separate "mode" field (§2, §5.3): the backend infers single- vs. multi-location behavior purely from the length of the destination list. In multi-location mode the list's order is not treated as a constraint — the backend is solely responsible for producing the visiting order via the Nearest Neighbor Heuristic (§2.2).

### 6.2 Backend → Frontend (search response)

| Field | Meaning | Consumed by | Applies when |
|---|---|---|---|
| Exploration sequence | The ordered list of nodes as they were expanded during a search | Animation (§5, "Animating exploration") | Always (per leg if multi-location) |
| Explored-node markers | Which nodes had been fully explored at each point in the sequence | Animation (visited-node styling) | Always |
| Frontier updates | Which nodes were in the frontier at each point in the sequence | Animation (frontier-node styling) | Always |
| Primary path | The route actually returned by the requested algorithm | Path rendering (§5, "Drawing the primary path") | Destination list has 1 entry |
| Alternative path | The second, valid, non-optimal route (§4.2) | Path rendering (§5, "Drawing the alternative path") | Destination list has 1 entry |
| Congested segments | The specific edges of the alternative path identified as high-congestion/low-speed, with their road name/type (§4.1) | Map highlighting (§5, "Highlighting the congested segments named in the explanation") | Destination list has 1 entry |
| Route explanation | The human-readable, causally-specific justification text (§4.1) | Statistics/explanation panel | Destination list has 1 entry |
| Visiting order | The ordered list of destination nodes determined by the Nearest Neighbor Heuristic | Destination numbering and row auto-reorder (§5.3–5.4) | Destination list has 2+ entries |
| Leg paths | The detailed route for each consecutive pair in the visiting order | Itinerary rendering (§5.4) | Destination list has 2+ entries |
| Complete itinerary | All leg paths concatenated into one continuous route | Itinerary rendering (§5.4) | Destination list has 2+ entries |
| Statistics | Distance, time, congestion, risk, **total cost** (§3), expanded-node count, execution time — per route (1 destination) or per leg plus itinerary-wide totals (2+ destinations) | Statistics panel | Always |

The response is a single payload containing all of the above at once for the relevant case — the backend does not stream steps individually. This keeps the contract to one round trip per search and lets the frontend replay, pause, or restart the animation freely without needing to talk to the backend again.

### 6.3 Location list (supporting exchange)

Separately from the search flow, the backend exposes the list of named locations (tourist points of interest) with their coordinates, so the frontend can populate the search-to-select control and place markers on the base map before any search is run. This exchange has no request parameters beyond asking for the list, and its response is simply the set of locations available to choose from. This list must use the corrected, unprojected geographic coordinates (§4.0 known risk) — a location list expressed in projected meters would misplace every marker on the base map.

### 6.4 Interaction sequence

1. Frontend requests the location list and the base network on load, and renders the initial map.
2. User selects a start location and fills in one destination row, or clicks "+ Add destination" repeatedly to add more (§5.3) — no explicit mode choice is made at any point.
3. User selects an algorithm and an optimization mode, then presses Search. Frontend sends the search request (§6.1) with however many destinations are currently filled in.
4. Backend inspects the destination list length and runs either the single-location behavior (§2.1, §4.1–4.2) or the multi-location behavior (§2.2, §4.4), then returns everything as one search response (§6.2).
5. Frontend replays the exploration sequence as an animation; if the response was single-location, it draws the primary and alternative paths and populates the explanation panel; if multi-location, it re-orders the destination rows to match the returned visiting order, numbers each marker, draws the full itinerary, and populates the itinerary-wide statistics.
6. User presses Reset. Frontend clears the map state and the destination row list, and returns to step 2 without contacting the backend.

---

## 7. Non-functional notes

- **Statelessness:** the backend does not need to remember anything between requests beyond the graph itself. Each search request — regardless of destination count — is self-contained and independent of any previous one, which keeps the API simple and avoids session-management concerns.
- **Single round trip:** returning the full exploration history and, for 2+ destinations, the full itinerary up front (rather than the frontend requesting step-by-step or leg-by-leg updates) trades a larger single response for a much simpler interaction model and a smoother, restartable animation.
- **Negligible ordering cost:** the Nearest Neighbor Heuristic's own cost (quadratic in the number of destinations) is negligible compared to the cost of the subsequent graph searches, so adding the ordering step does not materially change the backend's response-time characteristics.
- **Independent evolution:** because the contract in §6 is the only thing shared between the two parts, the map library, the animation style, or the internal search/ordering implementation can each change independently as long as the request/response fields in §6.1–6.2 stay the same.

---

## 8. Suggested build order (for a 3-person team)

| Order | Task | Depends on |
|---|---|---|
| 1 | Data Preprocessing Pipeline: finalize the OSMnx script, **fixing the projected-vs-geographic coordinate export issue (§4.0)** before it blocks frontend work, to generate `processed_nodes.csv` and `processed_edges.csv` | None |
| 1b | Graph loading: build the class to read the generated CSVs into an in-memory graph | (1) |
| 2 | The six search algorithms, each producing statistics (including total cost, §3) and an exploration history | (1b) |
| 3 | Alternative-route generation strategy for single-destination requests (§4.2) | (2) |
| 4 | Route explanation generation, including the edge-level causal reasoning (§4.1) | (2)(3) |
| 5 | Nearest Neighbor Heuristic ordering module for multi-destination requests (§2.2) | (1b) |
| 6 | Multi-destination leg execution, merging, and itinerary-wide statistics (§4.4) | (2)(5) |
| 7 | API layer exposing the location list and the search endpoint (single vs. multi inferred from request shape, §6.1) | (1)–(6) |
| 8 | Base map rendering, location selection, the growing destination-row control panel (§5.3) | (7) for the location list only — can start in parallel with (2)–(6) |
| 9 | Exploration animation (visited/frontier styling, replay of the exploration sequence, per leg for 2+ destinations) | (7) |
| 10 | Primary/alternative path rendering and statistics/explanation panel (1 destination) | (7) |
| 11 | Itinerary rendering, destination numbering, row auto-reorder, and total-statistics panel (2+ destinations) | (7) |

This keeps the two parts genuinely independent during development: the frontend team can build and test steps 8–11 against a stub search response shaped like §6.2, without waiting for the backend's algorithms or ordering logic to be finished, as long as the field list in §6.2 is agreed on first.