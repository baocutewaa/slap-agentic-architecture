# Báo cáo Giai đoạn 2: Chuẩn hóa Snapshot & Khởi tạo Trạng thái Kho (Warehouse State)

> **Dự án:** Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses (Assis et al., 2026)  
> **Giai đoạn:** Giai đoạn 2 – Chuẩn hóa snapshot và tạo state (theo `SLAP-agentic-architecture Plan.md`)  
> **Trạng thái:** Hoàn thành toàn diện, bảo đảm tính có thể tái lập (Reproducible) với seed cố định, tuân thủ nghiêm ngặt mọi ràng buộc vật lý kho.

---

## 1. Tổng quan Mục tiêu Giai đoạn 2

Giai đoạn 2 chuyển đổi snapshot thô sang mô hình trạng thái kho động học chuẩn mực phục vụ mô phỏng chuỗi thời gian:
1. **Chuẩn hóa Cấu trúc Bảng Ô Lưu trữ (Long Format Normalization):** Tách cấu trúc 18 cột (`col_1`…`col_18`) thành bản ghi từng ô độc lập (`location_id`, `slot_id`, `Reference`, `size`, `x`, `y`, `z`).
2. **Thiết lập Ràng buộc Sức chứa Thiết kế ($C_l = 18$):** Đảm bảo bất biến vật lý không một vị trí nào vượt quá 18 ô và số lượng tồn kho luôn không âm ($\sum_i n_{i,l,t} \le 18, \forall l$).
3. **Mô hình hóa Giải phóng Dung lượng Kho (20% Capacity Evacuation):** Tạo không gian trống tiếp nhận chuỗi 10.000 kiện hàng nhập theo đúng quy trình của bài báo, bảo đảm tính phân bố đồng đều ngẫu nhiên bằng `seed=42`.
4. **Phân tích Biến thiên Entropi Trạng thái Ban đầu:** Đo lường chính xác độ dịch chuyển Mixing Index từ trạng thái đầy 100% (*Paper-like Baseline MI*) sang trạng thái khởi đầu mô phỏng $t=0$ (*Initial Simulation MI*).
5. **Đóng gói Trạng thái Trung gian & Tối ưu Nạp Dữ liệu:** Lưu trữ toàn bộ dữ liệu sạch trong `data/interim/` và `data/processed/`, triệt tiêu chi phí đọc lại file thô trong quá trình chạy thuật toán.

---

## 2. Kết quả Chuẩn hóa Snapshot Dạng Dài (Long Format)

Toàn bộ các tệp snapshot đã được phân rã thành định dạng bảng dài phục vụ truy vấn vector hóa:

- `data/interim/random_storage_long_z34.csv`: **600 vị trí × 18 slots = 10.800 ô** (Phạm vi mô phỏng chính).
- `data/interim/random_storage_long_z3.csv`: **301 vị trí × 18 slots = 5.418 ô** (Phạm vi phân tích độ nhạy 1).
- `data/interim/random_storage_long_z4.csv`: **299 vị trí × 18 slots = 5.382 ô** (Phạm vi phân tích độ nhạy 2).
- `data/interim/random_storage_long_all.csv`: **2.292 vị trí × 18 slots = 41.256 ô** (Toàn bộ kho hàng).

Mỗi bản ghi ô lưu trữ bao gồm 7 trường thuộc tính chuẩn hóa:
$$\text{SlotRecord} = \big(\text{location\_id}, \text{slot\_id}, \text{sku}, \text{size}, x, y, z\big)$$

---

## 3. Giải phóng Ngẫu nhiên 20% Dung lượng & Kiểm định Nhị thức

Theo bài báo của Assis et al. (2026), để mô phỏng quá trình tiếp nhận 10.000 kiện hàng nhập theo thời gian, kho hàng cần được giải phóng khoảng 20% dung lượng từ snapshot ban đầu:
- **Thuật toán giải phóng:** Lấy mẫu ngẫu nhiên không hoàn lại chính xác $20.0\%$ số ô đang chứa hàng trên toàn bộ 600 vị trí với `seed=42`.
- **Số ô giải phóng thực tế:** Đúng **2,160 / 10,800 ô** (tỷ lệ giải phóng: **20.00%**).
- **Dung lượng còn trống sau giải phóng:** Đúng **2,160 ô** (tỷ lệ lấp đầy: **80.00%**, số lượng hàng còn lại: **8,640 ô**).
- **Vết giải phóng chi tiết:** Toàn bộ 2.160 ô giải phóng được lưu vết tại [`data/processed/released_slots_z34_seed42.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/data/processed/released_slots_z34_seed42.csv) và ghi nhật ký tại [`outputs/logs/phase2_state_release_log.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/logs/phase2_state_release_log.csv).

### Kiểm định Tính ngẫu nhiên Đồng đều (Binomial Verification):
Về mặt lý thuyết xác suất, khi giải phóng ngẫu nhiên độc lập $20\%$ trên $10.800$ ô của $600$ vị trí ($n=18$ ô/vị trí, $p=0.20$), số ô trống $K_l$ tại mỗi vị trí phải tuân theo phân phối nhị thức:
$$K_l \sim B(n=18, p=0.20), \qquad \mathbb{E}[K_l] = 18 \times 0.20 = 3.60 \text{ slots}, \qquad \text{Var}(K_l) = 18 \times 0.2 \times 0.8 = 2.88$$

Thực nghiệm cho thấy phân phối số ô giải phóng thực tế bám sát phân phối nhị thức lý thuyết:
- Giá trị trung bình thực nghiệm: **3.60 slots/vị trí**.
- Độ lệch chuẩn thực nghiệm: **1.69 slots** ($\sigma^2 \approx 2.86$).
- Khoảng biến thiên thực tế: từ **0 đến 9 ô trống/vị trí** (không có vị trí nào bị làm trống hoàn toàn hay vượt quá 18 ô).

![Kiểm định Phân phối Giải phóng Dung lượng Kho](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_capacity_release_distribution.png)

*Hình 2.1: (a) So sánh tần suất thực nghiệm số ô giải phóng trên mỗi vị trí so với phân phối nhị thức lý thuyết $B(18, 0.20)$; (b) Hàm phân phối tích lũy thực nghiệm (ECDF) của dung lượng giải phóng.*

---

## 4. Biến thiên Mixing Index: Trước vs. Sau Giải phóng Dung lượng

Bảng đối chiếu Mixing Index và sức chứa kho trước và sau khi giải phóng 20% dung lượng:

| Phạm vi Không gian | Số vị trí | Tổng sức chứa | Số đơn vị Trước giải phóng | Baseline MI Trước | Critical Rate Trước | Số ô Đã giải phóng | Số đơn vị Sau giải phóng | Initial MI Sau giải phóng | Critical Rate Sau | Biến thiên MI ($\Delta MI$) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Candidate Scope ($z \in \{3, 4\}$)** | **600** | **10,800** | **10,800** | **0.9136** | **99.83%** | **2,160** | **8,640** | **0.9015** | **98.83%** | **-0.0121** |
| **Sensitivity Scope ($z=3$)** | 301 | 5,418 | 5,418 | 0.9131 | 99.67% | 1,084 | 4,334 | 0.9013 | 99.34% | -0.0117 |
| **Sensitivity Scope ($z=4$)** | 299 | 5,382 | 5,382 | 0.9142 | 100.00% | 1,076 | 4,306 | 0.9046 | 99.67% | -0.0096 |
| **Full Warehouse ($z \in \{1..4\}$)** | 2,292 | 41,256 | 41,256 | 0.4362 | 47.69% | 8,251 | 33,005 | 0.4300 | 47.60% | -0.0062 |

### Phân biệt Hai Chỉ số Nền tảng:
1. **`Paper-like Baseline MI` ($0.9136$):** Là Mixing Index tính trên toàn bộ snapshot kho đầy 100% (10.800 ô có hàng). Chỉ số này dùng để đối chiếu với con số **0.918** mà bài báo công bố cho trạng thái tĩnh ban đầu.
2. **`Initial Simulation MI` ($0.9015$):** Là Mixing Index tại thời điểm xuất phát $t=0$ ngay sau khi giải phóng 20% ô chứa hàng. Đây là điểm mốc chuẩn xác mà cả 3 tác tử **Heuristic, Supervised, và Adaptive** đều bắt đầu vận hành trên cùng một trạng thái.

![Biến thiên Mixing Index Trước vs Sau Giải phóng Dung lượng](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_mi_before_after_release.png)

*Hình 2.2: (a) Biểu đồ phân tán chuyển dịch MI từng vị trí trước vs sau khi giải phóng; (b) Phân phối độ biến thiên cục bộ $\Delta MI$, trung bình giảm nhẹ $-0.0121$ do việc rút ngẫu nhiên làm giảm số lượng SKU khác loại.*

---

## 5. Phân bố Không gian Độ lấp đầy Kho Hàng (Spatial Occupancy)

Bản đồ nhiệt dưới đây minh họa độ lấp đầy thực tế tại từng vị trí lưu trữ theo tọa độ $(x, y)$ trên các giá kệ tầng $z=3$ và $z=4$:
- **Trước giải phóng:** 100% vị trí đều chứa trọn vẹn 18/18 ô (màu xanh đậm đồng nhất).
- **Sau giải phóng:** Độ lấp đầy dao động phân tán đều xung quanh giá trị trung bình 14.4 ô/vị trí (tương ứng 80.0%), không xuất hiện hiện tượng dồn ứ cục bộ hay chỗ trống tập trung ở một khu vực giá kệ.

![Bản đồ Nhiệt Độ lấp đầy Không gian Trước vs Sau Giải phóng](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_spatial_occupancy_map.png)

*Hình 2.3: Bản đồ phân bố không gian độ lấp đầy vị trí lưu trữ: (a) Trước giải phóng (18/18 slots); (b) Sau khi giải phóng ngẫu nhiên 20% dung lượng (trung bình 14.4 slots).*

![So sánh MI qua các Phạm vi Độ nhạy](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_sensitivity_scopes_mi.png)

*Hình 2.4: So sánh Mixing Index trước và sau giải phóng dung lượng qua các phạm vi phân tích độ nhạy.*

---

## 6. Tổng kết Danh mục Kết quả & Hiện vật (Deliverables Giai đoạn 2)

Toàn bộ các đầu ra của Giai đoạn 2 đã được chuẩn hóa và lưu trữ đầy đủ trong thư mục `outputs/`:

| Loại hiện vật | Đường dẫn tệp tin | Mô tả kỹ thuật |
|---|---|---|
| **Báo cáo Kỹ thuật** | [`outputs/reports/phase2_state_report.md`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/reports/phase2_state_report.md) | Báo cáo chi tiết quá trình chuẩn hóa snapshot, giải phóng 20% dung lượng và phân tích biến thiên MI. |
| **Mã nguồn Quản lý Trạng thái** | [`src/model/state_manager.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/model/state_manager.py)<br>[`src/model/warehouse_state.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/model/warehouse_state.py) | Lớp quản lý trạng thái kho `WarehouseState`, cấu trúc slot inventory và cập nhật giao dịch. |
| **Mã nguồn Làm sạch Dữ liệu** | [`src/data/cleaning.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/data/cleaning.py) | Chuyển đổi wide-to-long format và thuật toán giải phóng 20% dung lượng theo seed ngẫu nhiên cố định. |
| **Bộ Kiểm thử Đầy đủ** | [`tests/test_capacity_constraints.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/tests/test_capacity_constraints.py) | 7 unit tests kiểm định ràng buộc sức chứa 18 ô, không âm, giải phóng đúng 2.160 ô và tính bất biến. |
| **Jupyter Notebook Trực quan** | [`notebooks/02_state_initialization.ipynb`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/notebooks/02_state_initialization.ipynb) | Notebook tương tác (~465 KB), hiển thị đầy đủ quy trình giải phóng và biểu đồ trực quan hóa. |
| **Biểu đồ Phân phối Dung lượng Giải phóng** | [`outputs/figures/phase2_capacity_release_distribution.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_capacity_release_distribution.png) | Phân phối số ô giải phóng thực nghiệm so với hàm mật độ nhị thức lý thuyết $B(18, 0.20)$ và ECDF. |
| **Biểu đồ Biến thiên Mixing Index** | [`outputs/figures/phase2_mi_before_after_release.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_mi_before_after_release.png) | Đồ thị phân tán MI cặp trước vs sau giải phóng và phân phối độ dịch chuyển $\Delta MI$ cục bộ. |
| **Biểu đồ Nhiệt Độ lấp đầy Không gian** | [`outputs/figures/phase2_spatial_occupancy_map.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_spatial_occupancy_map.png) | Bản đồ nhiệt 2D thể hiện độ lấp đầy các vị trí kho trên tọa độ $(x, y)$ trước và sau giải phóng. |
| **Biểu đồ So sánh các Phạm vi Độ nhạy** | [`outputs/figures/phase2_sensitivity_scopes_mi.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase2_sensitivity_scopes_mi.png) | So sánh MI trước và sau giải phóng qua 4 phạm vi: $z \in \{3,4\}$, $z=3$, $z=4$, toàn kho. |
| **Bảng Thống kê Từng Vị trí** | [`outputs/tables/location_level_mi_z34.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/location_level_mi_z34.csv) | Bảng dữ liệu chi tiết 600 vị trí: tồn kho, MI trước/sau, $\Delta MI$, số ô giải phóng. |
| **Bảng So sánh Trạng thái Tổng hợp** | [`outputs/tables/snapshot_mi_before_after_release.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/snapshot_mi_before_after_release.csv) | So sánh chỉ số tổng hợp toàn kho trước và sau giải phóng qua các phạm vi phân tích. |
| **Bảng Tổng hợp Sức chứa Kho** | [`outputs/tables/phase2_capacity_summary.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/phase2_capacity_summary.csv) | Tổng hợp sức chứa, tỷ lệ lấp đầy, số ô trống sẵn sàng đón hàng nhập theo từng tầng. |
| **Bảng Chỉ số Trạng thái Định lượng** | [`outputs/metrics/metrics_phase2_state.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/metrics/metrics_phase2_state.csv) | 13 chỉ số đo lường trạng thái cốt lõi (tổng dung lượng, số ô giải phóng, baseline MI 0.9136, initial MI 0.9015). |
| **Nhật ký Giải phóng Dung lượng** | [`outputs/logs/phase2_state_release_log.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/logs/phase2_state_release_log.csv) | Nhật ký mẫu chi tiết thao tác thu hồi từng ô lưu trữ (location_id, slot_id, SKU, size, seed). |
| **Dữ liệu Chuẩn hóa Dạng dài (Interim)** | [`data/interim/random_storage_long_z34.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/data/interim/random_storage_long_z34.csv) | Snapshot chuẩn hóa 10.800 ô lưu trữ phục vụ nạp trạng thái mô phỏng tức thời. |
| **Trạng thái Khởi đầu Mô phỏng (Processed)** | [`data/processed/initial_state_z34_after_release.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/data/processed/initial_state_z34_after_release.csv) | Trạng thái ban đầu chuẩn mực tại $t=0$ gồm 8.640 ô có hàng và 2.160 ô trống dùng chung cho 3 tác tử. |

---

## 7. Sẵn sàng Chuyển giao sang Giai đoạn 3

Trạng thái kho ban đầu đã được thiết lập hoàn chỉnh, bảo đảm tính xác định và tái lập 100%. Nền tảng này sẵn sàng tiếp nhận luồng sự kiện hàng nhập từ **Giai đoạn 3 – Sinh chuỗi 10.000 sự kiện hàng nhập (Event Generator)**.
