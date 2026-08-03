# 🗺️ Ho Chi Minh Tourist Route Planner

**CSC14003 - Lab 01: Searching Algorithms in Artificial Intelligence**

Ứng dụng web tương tác hỗ trợ lập lộ trình du lịch tối ưu tại Quận 1, Thành phố Hồ Chí Minh. Ứng dụng tích hợp bản đồ **MapLibre GL JS** sắc nét, phía backend là **FastAPI (Python)** chạy các thuật toán tìm kiếm đường đi cổ điển dựa trên 2 tiêu chí đánh giá đường đi: **Shortest (Ngắn nhất)** và **Fastest (Nhanh nhất)**.

---

## 🌟 Tính năng nổi bật

1. **Đa dạng thuật toán tìm kiếm**:
   - `BFS` (Breadth-First Search)
   - `DFS` (Depth-First Search)
   - `UCS` (Uniform Cost Search)
   - `A* Search`
   - `Greedy BFS` (Greedy Best-First Search)
   - `Bidirectional Search` (Tìm kiếm hai chiều)

2. **So sánh đường đi 2 tiêu chí đồng thời**:
   - Chạy thuật toán song song cho 2 cấu hình trọng số: **Shortest** (ưu tiên khoảng cách) và **Fastest** (ưu tiên thời gian di chuyển, né tránh kẹt xe).
   - Đánh giá hàm Heuristic chuẩn hóa **Min-Max Normalization** trên tất cả các thuộc tính đường (`distance`, `time`, `congestion`, `risk`).

3. **Giao diện hiện đại & Bản đồ sống động**:
   - Sử dụng **MapLibre GL JS** với basemap CARTO Voyager nhẹ nhàng, mượt mà.
   - **Vector SVG Pins**: Đỉnh Marker thẳng đứng chỉ chính xác vị trí vật lý thực tế của địa điểm (POI).
   - **Mũi tên định hướng (Road Direction Vectors)**: Vẽ mũi tên chỉ hướng di chuyển dọc theo các tuyến đường và lộ trình trên bản đồ.

4. **Thuyết minh & Chỉ dẫn đường đi từng bước (Turn-by-Turn Navigation)**:
   - Thuyết minh so sánh lý do chọn đường ngắn vs đường nhanh bằng ngôn ngữ tự nhiên.
   - Danh sách chỉ dẫn đường đi từng bước kiểu Google Maps (*Đi thẳng, Rẽ trái, Rẽ phải, Bạn đã tới địa điểm...*).

5. **Hỗ trợ lộ trình đa điểm (Multi-location Routing)**:
   - Tự động sắp xếp thứ tự tham quan tối ưu giữa nhiều địa điểm bằng giải thuật **Nearest Neighbor Heuristic**.

6. **Chế độ Debug mạng lưới (Network Debug Overlay)**:
   - Nút bật/tắt vẽ toàn bộ các Node và Edge trong đồ thị lên bản đồ kèm Legend phân loại đường đi.

---

## 📁 Cấu trúc thư mục project

```
CSC14003-Lab01-Searching/
├── backend/
│   ├── app.py           # FastAPI Web Server & API Endpoints
│   ├── graph.py         # Cấu trúc dữ liệu Đồ thị & Đọc CSV
│   ├── algorithms.py    # Cài đặt các thuật toán tìm kiếm (BFS, DFS, UCS, A*, Greedy, Bidi)
│   ├── cost.py          # Chuẩn hóa Min-Max & Tính chi phí cạnh (Shortest / Fastest)
│   ├── explanation.py   # Máy phát thuyết minh lộ trình & Chỉ dẫn rẽ từng bước
│   ├── poi.py           # Script trích xuất dữ liệu OSMnx & tạo dataset đường phố
│   └── requirements.txt # Danh sách thư viện Python cần thiết
├── frontend/
│   ├── src/
│   │   ├── components/  # Các React component (MapView, ControlPanel, StatsPanel,...)
│   │   ├── App.jsx      # Component chính của ứng dụng
│   │   ├── App.css      # Hệ thống Style Glassmorphism
│   │   └── main.jsx
│   ├── package.json     # Khai báo phụ thuộc Node.js (React, MapLibre GL)
│   └── vite.config.js
├── processed_nodes.csv  # Dataset danh sách các Node (Intersection, Physical POI, Snap POI)
├── processed_edges.csv  # Dataset các Edge chứa đường cong hình học LineString WGS84
├── .gitignore
└── README.md
```

---

## 🛠️ Yêu cầu môi trường (Prerequisites)

- **Python**: 3.9+ 
- **Node.js**: 18+ & **npm**

---

## 🚀 Hướng dẫn cài đặt & Chạy ứng dụng

### 1. Khởi chạy Backend (FastAPI)

Mở một cửa sổ Terminal tại thư mục gốc của project:

```bash
# 1. Chuyển vào thư mục backend
cd backend

# 2. Cài đặt các thư viện Python
pip install -r requirements.txt

# 3. Khởi chạy Uvicorn Server
uvicorn app:app --reload --port 8000
```
Server Backend sẽ lắng nghe tại: `http://localhost:8000`.

*(Tùy chọn)* Nếu muốn tải lại dữ liệu bản đồ mới nhất từ OpenStreetMap (OSMnx):
```bash
python poi.py
```

---

### 2. Khởi chạy Frontend (React + Vite)

Mở một cửa sổ Terminal khác tại thư mục gốc của project:

```bash
# 1. Chuyển vào thư mục frontend
cd frontend

# 2. Cài đặt các gói phụ thuộc Node
npm install

# 3. Khởi chạy Web Server phát triển
npm run dev
```

Truy cập ứng dụng tại trình duyệt: **`http://localhost:5173`**.

---

## 🎮 Hướng dẫn sử dụng

1. **Chọn điểm xuất phát (Start Location)**: Click chọn địa điểm từ bảng điều khiển bên trái.
2. **Chọn điểm đến (Destinations)**: Nhấp chọn 1 hoặc nhiều điểm đến mong muốn.
3. **Chọn Thuật toán (Algorithm)**: Lựa chọn một trong 6 thuật toán tìm kiếm (`A*`, `UCS`, `BFS`, `DFS`, `Greedy BFS`, `Bidirectional`).
4. **Bấm "Find Route"**:
   - Bản đồ hiển thị đồng thời 2 tuyến đường: **🔵 Đường Ngắn nhất (Xanh)** và **🔴 Đường Nhanh nhất (Đỏ)** kèm mũi tên hướng đi.
   - Bảng thống kê so sánh thời gian, khoảng cách, mức độ kẹt xe, số nút đã duyệt.
   - Bảng thuyết minh giải thích sự khác biệt giữa 2 tuyến đường.
   - Tab chỉ dẫn di chuyển từng bước (*Turn-by-Turn Navigation*).
5. **Chế độ Debug**: Tích chọn checkbox **"Debug Network"** trên góc bản đồ để xem toàn bộ mạng lưới giao thông đường phố cùng chú thích Legend.

---

## 📄 Giấy phép & Tác giả

* Đồ án học thuật môn **CSC14003 - Trí tuệ Nhân tạo / AI**.
* Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM.
