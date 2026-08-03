# **Lab 1: Search Algorithms for Vietnamese Traffic Route Optimization** 

## **1 General Requirements** 

-  Complete the project according to the course guidelines. 

-  Each group must consist of **3 to 5 students** . 

-  Each group must appoint **one representative** to submit the project. 

-  The submission must be packaged in a single ZIP file named **[GroupID].zip** , including: 

   - **Source code link** : **[GroupID - SC].txt** 

   - **Technical report** : **[GroupID - Report].pdf** 

   - **Presentation slides** : **[GroupID - Slide].pptx** or **[GroupID - Slide].pdf** 

   - **Demo video link** : **[GroupID - Video].txt** 

   - **Dataset or data description** : **[GroupID - Data].zip** or **[GroupID - Data].txt** 

## **2 Project Context** 

Traffic congestion is a common problem in large Vietnamese cities such as Ho Chi Minh City, Ha Noi, Da Nang, and Can Tho. During rush hours, routes that are shortest in distance may not be the fastest or most suitable in practice. Factors such as traffic density, one-way streets, road types, construction areas, flooding, traffic lights, and vehicle restrictions may significantly affect travel time. 

In this project, each group must develop an application that helps users find an optimal route between locations in a Vietnamese urban traffic context. The project must not only find a path, but also explain why the path is selected and how different search algorithms behave. 

## **3 Objectives** 

The objectives of this lab are as follows: 

-  Apply AI search algorithms to solve a real-world-inspired route optimization problem. 


-  Model Vietnamese urban traffic as a graph-based search problem. 

-  Find the shortest or optimal route between two selected locations. 

-  Optimize the visiting order when multiple locations are given. 

-  Analyze and compare the advantages and disadvantages of different search algorithms. 

-  Develop a graphical user interface (GUI) to visually demonstrate how the algorithms operate. 

-  Explain the selected route based on distance, estimated time, traffic congestion, and total cost. 

-  Practice problem analysis, system design, implementation, experimental evaluation, and technical report writing. 

## **4 Project Requirements** 

## **4.1 Problem Scenario** 

Each group must build a route optimization application in the context of a Vietnamese city or urban area. The group may choose one of the following scenarios: 

-  A delivery application that helps a shipper deliver packages to multiple locations in Ho Chi Minh City. 

-  A navigation system that suggests routes avoiding traffic congestion during rush hours in Ha Noi. 

-  An ambulance route planner that finds the fastest path to a hospital. 

-  A school bus or student shuttle route optimizer. 

-  A tourist route planner for visiting multiple landmarks in Da Nang, Hue, or Ho Chi Minh City. 

-  A truck delivery planner that avoids restricted roads, small alleys, or highly congested areas. 

-  Other realistic Vietnamese traffic-related scenarios approved by the instructor. 

**Note:** The selected scenario must be clearly connected to a real traffic problem in Vietnam. A purely abstract maze or grid without Vietnamese traffic context is not sufficient. 


## **4.2 Problem Modeling** 

The traffic network must be modeled as a graph: 

-  Each **node** represents a location, intersection, landmark, school, hospital, bus station, warehouse, or district. 

-  Each **edge** represents a road segment connecting two locations. 

-  Each edge must have attributes such as: 

   - distance, 

   - estimated travel time, 

   - traffic congestion level, 

   - road type, 

   - direction, for example one-way or two-way, 

   - optional risk factors such as flooding, construction, or narrow roads. 

The project must support at least two types of route optimization: 

1. **Two-location route search** : Given a start location and a destination, find the shortest or optimal path. 

2. **Multi-location route optimization** : Given a start location and several locations to visit, suggest an efficient visiting order and route. 

## **4.3 Cost Function** 

The project must not use physical distance as the only optimization criterion. Each group must design a cost function that reflects traffic conditions in Vietnam. 

For example, the cost of a road segment can be defined as: 

_Cost_ = _α × Distance_ + _β × Time_ + _γ × Congestion_ + _δ × Risk_ 

where: 

-  **Distance** : length of the road segment. 

-  **Time** : estimated travel time based on speed and traffic condition. 

-  **Congestion** : traffic level, for example from 1 to 5. 

-  **Risk** : penalty for flooding, construction, difficult intersections, narrow roads, or unsafe areas. 

-  _α, β, γ, δ_ : weights designed by the group. 


Each group must explain: 

-  why the chosen cost function is reasonable, 

-  how the weights are selected, 

-  how traffic congestion affects the final route, 

-  and how the route changes under different traffic conditions. 

## **4.4 Dataset Requirements** 

Each group may use one of the following data approaches: 

## 1. **Simulated Vietnamese traffic data** 

-  Create a graph with at least **20 nodes** and **30 edges** . 

-  Nodes should represent real or realistic Vietnamese locations. 

-  Edges should include distance, estimated time, congestion level, and road type. 

## 2. **Simplified real-world data** 

-  Use map data, public map sources, or manually collected road information. 

-  Convert the data into a graph representation suitable for search algorithms. 

-  The group may simplify the map if the original data is too complex. 

## 3. **Hybrid data** 

-  Use real Vietnamese locations and manually add simulated traffic conditions. 

-  This approach is recommended for balancing realism and implementation difficulty. 

The dataset must be included in the submission or clearly described in the report. 

## **4.5 Algorithms to Implement** 

At minimum, the project must implement and compare the following algorithms for route search between two locations: 

-  Breadth-First Search (BFS) 

-  Depth-First Search (DFS) 

-  Uniform Cost Search (UCS) 

-  A* Search 


In addition, each group must implement at least **two more search or optimization algorithms** . Suggested algorithms include: 

-  Dijkstra’s Algorithm 

-  Greedy Best-First Search 

-  Bidirectional Search 

-  Iterative Deepening A* (IDA*) 

-  Beam Search 

-  Hill Climbing 

-  Simulated Annealing 

-  Genetic Algorithm 

-  Ant Colony Optimization 

-  Nearest Neighbor heuristic for multi-location routing 

-  Dynamic Programming for small-scale Traveling Salesman Problem 

For the multi-location route optimization problem, the group must apply at least one suitable method, such as: 

-  brute force for a small number of locations, 

-  nearest neighbor heuristic, 

-  dynamic programming, 

-  genetic algorithm, 

-  simulated annealing, 

-  or another appropriate heuristic method. 

**Important:** The group must clearly state whether the selected algorithm guarantees an optimal solution or only provides an approximate solution. 


## **4.6 Heuristic Design** 

For heuristic-based algorithms such as A* Search or Greedy Best-First Search, each group must design and explain a heuristic function. Examples: 

-  straight-line distance between two locations, 

-  estimated travel time based on average speed, 

-  distance plus traffic penalty, 

-  district-level or zone-level estimation. 

The report must explain whether the heuristic is admissible, consistent, or only practically useful. 

## **4.7 Graphical User Interface** 

The project must include a visual and user-friendly GUI. The interface may be developed using tools such as **Tkinter** , **Pygame** , **PyQt** , or a **web-based interface** using HTML, CSS, JavaScript, React, Flask, or similar technologies. 

The GUI must satisfy the following requirements: 

-  Display the traffic graph, city map, or simplified road network. 

-  Allow users to select: 

   - start location, 

   - destination, 

   - optional intermediate locations, 

   - algorithm to run, 

   - optimization criterion. 

-  Visually display the search process step by step, for example by highlighting visited nodes, frontier nodes, and the final route. 

-  Display detailed output, including: 

   - path found, 

   - visiting order for multiple locations, 

   - number of explored nodes, 

   - total distance, 

   - total estimated time, 

   - total route cost, 

   - processing time, 

   - traffic or congestion explanation, 

   - and other relevant performance metrics. 

-  Provide a short explanation of why the selected route is considered optimal or nearoptimal. 

## **4.8 Route Explanation Requirement** 

The project must include an explanation component. The system should not only output a path, but also explain the result in a human-understandable way. For example: 

The route A _→_ C _→_ F _→_ H is selected because it has the lowest total cost. Although route A _→_ B _→_ H is shorter in distance, it passes through a highly congested area during rush hour. Therefore, its estimated travel time and congestion penalty are higher. 

The explanation should include: 

-  why the selected route was chosen, 

-  whether it is shortest by distance, fastest by time, or best by total cost, 

-  which road segments have high congestion, 

-  how the result differs from another possible route, 

-  and whether the algorithm guarantees optimality. 

## **4.9 Technical Report** 

The report must include the following sections: 

## a. **Group Introduction** 

-  Group information: group name, student IDs, and member list. 

-  Specific contributions of each member. 

-  Overall completion level of each project requirement. 

## b. **Problem Context** 

-  Description of the selected Vietnamese traffic scenario. 

-  Explanation of the real-world problem being addressed. 

-  Why route optimization is useful in this context. 

## c. **Problem Modeling** 

-  Description of the graph model. 

-  Definition of nodes, edges, start state, goal state, and transition rules. 

-  Description of edge attributes. 

-  Cost function and explanation of each component. 

## d. **Dataset** 

-  Source of data or data creation method. 

-  List of locations used. 

-  Description of distance, time, congestion, and road-type values. 

-  Any assumptions made by the group. 

## e. **Algorithm Principles** 

-  Theoretical explanation of each implemented algorithm. 

-  Simple examples to illustrate how each algorithm works. 

-  Explanation of the heuristic function if applicable. 

-  Discussion of completeness and optimality. 

## f. **Program Flow** 

-  Flowcharts or diagrams describing the main processing steps. 

-  Explanation of the main modules, functions, and program structure. 

-  Description of how the GUI interacts with the search algorithms. 

## g. **Algorithm Comparison** 

-  A comparison table covering time complexity, memory usage, completeness, and optimality. 

-  Comparison of actual performance on the selected traffic dataset. 

-  Discussion of route quality, number of explored nodes, and processing time. 

-  Analysis of how traffic congestion changes the selected route. 

## h. **Multi-location Optimization** 

-  Description of the multi-location routing problem. 

-  Explanation of the selected method. 

-  Comparison between the original visiting order and optimized visiting order. 

-  Discussion of whether the result is optimal or approximate. 

## i. **Program Instructions** 

-  Installation and setup instructions. 

-  Guidelines for using the GUI. 

-  Example inputs and outputs. 

-  Screenshots of the system. 

## j. **Limitations and Future Work** 

-  Difficulties and challenges encountered during development. 

-  Limitations of the dataset, cost function, and algorithms. 

-  Suggestions for future extensions, such as real-time traffic data, map API integration, or support for multiple vehicles. 

## **4.10 Video Requirement** 

A demonstration video must be submitted together with the project. The video should clearly explain both the implemented system and the search algorithms used. 

## a. **Explanation of Algorithms** 

-  Each implemented algorithm must be explained clearly and step by step. 

-  The group may use a separate illustrative example to explain the algorithm. 

-  The illustrative example must be designed by the group and must not be copied directly from common tutorials, textbooks, online videos, or existing walkthrough materials. 

-  During the explanation, the group should show: 

   - the initial location, 

   - the destination, 

   - the order in which nodes are expanded, 

   - the generated frontier or open list, 

   - the cost values used by UCS, Dijkstra, or A*, 

   - the heuristic values used by A* or Greedy Best-First Search, 

   - and how the final route is obtained. 

## b. **Project Demonstration** 

-  Show the actual implementation of the project in action. 

-  Demonstrate how users select locations and algorithms. 

-  Demonstrate route search between two locations. 

-  Demonstrate route optimization with multiple locations. 

-  Present several test cases under different traffic conditions. 

-  Compare the performance and behavior of different algorithms. 

-  Explain why the final route is selected. 

## **5 Evaluation Criteria** 

|**aluation Criteria**||
|---|---|
|**Criterion**|**Points**|
|Vietnamese traffic context and realistic problem scenario|10|
|Graph modeling, dataset design, and cost function|15|
|Correct implementation of required search algorithms|20|
|Implementation<br>of<br>additional<br>search<br>or<br>optimization<br>algorithms|10|
|Multi-location route optimization|10|
|GUI and visualization of search process|10|
|Route explanation and comparison of alternatives|10|
|Technical report quality|10|
|Demo video quality|5|
|**Total**|**100**|

## **6 Contact** 

If you have any questions regarding the project, please contact: vntan.work@gmail.com 

— — GOOD LUCK! 