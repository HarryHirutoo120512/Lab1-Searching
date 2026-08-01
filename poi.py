import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from shapely.geometry import Point, LineString

# Cấu hình OSMnx
ox.settings.use_cache = True
ox.settings.log_console = True

# Hàm hỗ trợ: Cắt LineString tại một khoảng cách xác định để giữ nguyên độ cong
def split_line_at_distance(line, distance):
    if distance <= 0.0 or distance >= line.length:
        return [line]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        p_geom = Point(p)
        pd = line.project(p_geom)
        if pd == distance:
            return [LineString(coords[:i+1]), LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [LineString(coords[:i] + [(cp.x, cp.y)]), LineString([(cp.x, cp.y)] + coords[i:])]
    return [line]

def main():
    # ==========================================
    # BƯỚC 1 & 2: Download the study boundary & road network
    # ==========================================
    place_name = "District 1, Ho Chi Minh City, Vietnam"
    print("B1 & B2: Downloading graph...")
    G = ox.graph_from_place(place_name, network_type="all", simplify=False)
    
    # ==========================================
    # BƯỚC 3: Simplify and project the graph
    # ==========================================
    print("B3: Simplifying and projecting graph...")
    G = ox.simplify_graph(G)
    G_proj = ox.project_graph(G)

    # --- VẼ ẢNH 1 (Kết quả Bước 3) ---
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Trích xuất edges để phân loại màu theo type
    edges = ox.graph_to_gdfs(G_proj, nodes=False)
    
    # Xử lý trường hợp 'highway' là list (do simplify gộp cạnh)
    edges['hw_type'] = edges['highway'].apply(lambda x: x[0] if isinstance(x, list) else x)
    unique_types = edges['hw_type'].unique()
    
    # Tạo bảng màu
    cmap = plt.get_cmap('tab20')
    color_map = {hw: cmap(i / len(unique_types)) for i, hw in enumerate(unique_types)}
    ec = edges['hw_type'].map(color_map)
    
    ox.plot_graph(G_proj, ax=ax, node_size=0, edge_color=ec, edge_linewidth=0.5, show=False, close=False)
    
    # Thêm Legend
    legend_elements = [mlines.Line2D([0], [0], color=color_map[hw], lw=2, label=hw) for hw in unique_types]
    ax.legend(handles=legend_elements, loc='upper left', title="Road Types", fontsize=8, title_fontsize=10)
    
    plt.savefig("D:/Picture_1_Graph_By_Type.png", dpi=300, bbox_inches='tight')
    plt.close()

    # ==========================================
    # BƯỚC 4: Extract POIs
    # ==========================================
    print("B4: Extracting POIs...")
    tags = {"tourism": ["museum", "attraction", "gallery", "artwork", "viewpoint", "information"]}
    pois = ox.features_from_place(place_name, tags=tags)
    
    # Loại bỏ các POI không có hình học hợp lệ và đưa về chung hệ tọa độ (metric CRS)
    pois = pois[pois.geometry.notnull()]
    pois_proj = pois.to_crs(G_proj.graph['crs']).copy()
    
    # Chuyển đổi Polygon/Multipolygon thành Point (Tâm)
    pois_proj['geometry'] = pois_proj.centroid

    # --- VẼ ẢNH 2 (Kết quả Bước 4) ---
    fig, ax = plt.subplots(figsize=(10, 10))
    # Vẽ graph trơn (plain edges), node mạng lưới màu xám nhạt
    ox.plot_graph(G_proj, ax=ax, node_color='#CCCCCC', node_size=5, edge_color='#999999', edge_linewidth=0.5, show=False, close=False)
    # Overlay POIs màu đỏ đặc trưng
    pois_proj.plot(ax=ax, color='red', markersize=1, zorder=5, label='Original POIs')
    ax.legend(loc='upper right')
    plt.savefig("D:/Picture_2_Graph_With_POIs.png", dpi=300, bbox_inches='tight')
    plt.close()

    # ==========================================
    # BƯỚC 5: Connect POIs to the road network (Snapping & Splitting)
    # ==========================================
    print("B5: Snapping POIs and splitting edges...")
    snapped_pois = []
    
    # Tạo node ID mới bắt đầu từ giá trị lớn hơn max node ID hiện tại
    new_node_id = max(G_proj.nodes) + 1
    
    for idx, row in pois_proj.iterrows():
        poi_geom = row['geometry']
        
        # Tìm cạnh gần nhất trên đồ thị hiện hành
        try:
            u, v, key = ox.distance.nearest_edges(G_proj, poi_geom.x, poi_geom.y)
        except Exception:
            continue
            
        edge_data = G_proj.get_edge_data(u, v, key).copy()
        
        # Lấy LineString gốc (nếu không có, tạo đường thẳng nối u-v)
        if 'geometry' in edge_data:
            line = edge_data['geometry']
        else:
            line = LineString([(G_proj.nodes[u]['x'], G_proj.nodes[u]['y']),
                               (G_proj.nodes[v]['x'], G_proj.nodes[v]['y'])])
        
        # Tính hình chiếu của POI lên cạnh
        proj_dist = line.project(poi_geom)
        snap_geom = line.interpolate(proj_dist)
        snapped_pois.append(snap_geom)
        
        # Nếu điểm snap quá sát node u hoặc v (ví dụ < 1 mét), bỏ qua split để tránh lỗi topology
        if proj_dist < 1.0 or proj_dist > line.length - 1.0:
            continue
            
        # Tách cạnh thành 2 đoạn giữ nguyên độ cong
        split_lines = split_line_at_distance(line, proj_dist)
        if len(split_lines) == 2:
            line1, line2 = split_lines
            
            # Thêm node snap vào graph
            G_proj.add_node(new_node_id, x=snap_geom.x, y=snap_geom.y, type='snap_poi')
            
            # Tính toán lại chiều dài tỷ lệ cho 2 đoạn mới
            len1, len2 = line1.length, line2.length
            
            # Thêm 2 cạnh mới (thừa kế attributes, cập nhật length và geometry)
            edge_data1 = edge_data.copy()
            edge_data1.update({'length': len1, 'geometry': line1})
            edge_data2 = edge_data.copy()
            edge_data2.update({'length': len2, 'geometry': line2})
            
            G_proj.add_edge(u, new_node_id, **edge_data1)
            G_proj.add_edge(new_node_id, v, **edge_data2)
            
            # Xóa cạnh cũ
            G_proj.remove_edge(u, v, key)
            new_node_id += 1

    snapped_gdf = gpd.GeoDataFrame(geometry=snapped_pois, crs=G_proj.graph['crs'])

    # --- VẼ ẢNH 3 (Kết quả Bước 5) ---
    fig, ax = plt.subplots(figsize=(10, 10))
    # Vẽ graph với các node mới
    ox.plot_graph(G_proj, ax=ax, node_color='#CCCCCC', node_size=5, edge_color='#999999', edge_linewidth=0.5, show=False, close=False)
    
    # Lọc node màu đặc trưng:
    nodes_df = ox.graph_to_gdfs(G_proj, edges=False)
    snap_nodes = nodes_df[nodes_df['type'] == 'snap_poi']
    
    pois_proj.plot(ax=ax, color='red', markersize=1, zorder=6, label='Original POIs')
    snap_nodes.plot(ax=ax, color='blue', markersize=1, zorder=5, label='Snapped POI Nodes (Routable)')
    
    ax.legend(loc='upper right')
    plt.savefig("D:/Picture_3_Graph_Snapped_POIs.png", dpi=300, bbox_inches='tight')
    plt.close()

    # ==========================================
    # BƯỚC 6: Derive edge attributes
    # ==========================================
    print("B6: Deriving attributes...")
    # Thêm default maxspeed dựa trên OSM highway tags
    G_proj = ox.add_edge_speeds(G_proj) 
    G_proj = ox.add_edge_travel_times(G_proj) # Tính toán thời gian lý tưởng (time)
    
    # Dummy calculation cho congestion và risk (để demo format dữ liệu đầu ra)
    for u, v, key, data in G_proj.edges(keys=True, data=True):
        data['congestion'] = data.get('travel_time', 0) * np.random.uniform(1.1, 2.0)
        data['risk'] = np.random.uniform(0.1, 1.0)
        data['average_speed'] = data.get('speed_kph', 40) * 0.8
        data['road_type'] = data.get('highway', 'unclassified')
        data['distance'] = data.get('length', 0)
        if isinstance(data['road_type'], list): 
            data['road_type'] = data['road_type'][0]

    for n, data in G_proj.nodes(data=True):
        if 'type' not in data:
            data['type'] = 'network_grid'
        data['lat'] = data.get('y')
        data['lon'] = data.get('x')

    # ==========================================
    # BƯỚC 7: Export the processed data
    # ==========================================
    print("B7: Exporting to CSV...")
    nodes_export, edges_export = ox.graph_to_gdfs(G_proj)
    
    # Format đúng cột như mô tả của đề bài
    nodes_final = nodes_export[['lat', 'lon', 'type']].copy()
    nodes_final['name'] = nodes_export.get('name', 'N/A')
    nodes_final.index.name = 'id'
    
    # Cần reset_index cho edges để lấy start_node, end_node (u, v)
    edges_export = edges_export.reset_index()
    edges_final = edges_export[['u', 'v', 'oneway', 'geometry', 'distance', 'road_type', 'speed_kph', 'average_speed', 'travel_time', 'congestion', 'risk']].copy()
    edges_final.rename(columns={'u': 'start_node', 'v': 'end_node', 'speed_kph': 'max_speed', 'travel_time': 'time'}, inplace=True)
    edges_final.index.name = 'id'
    
    nodes_final.to_csv("processed_nodes.csv")
    edges_final.to_csv("processed_edges.csv")
    print("Pipeline completed successfully!")

if __name__ == "__main__":
    main()