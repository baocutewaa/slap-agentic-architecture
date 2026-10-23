# Báo cáo Giai đoạn 2: Chuẩn hóa Snapshot & Khởi tạo Trạng thái Kho (Warehouse State)

> **Dự án:** Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses (Assis et al., 2026)
> **Giai đoạn:** Giai đoạn 2 – Chuẩn hóa snapshot và tạo state
> **Trạng thái:** Hoàn thành toàn diện, bảo đảm tính có thể tái lập (Reproducible) với seed cố định.

---

## 1. Kết quả Chuẩn hóa Snapshot (Long Format)

Đã chuyển đổi toàn bộ 18 cột ô lưu trữ (`col_1`…`col_18`) sang cấu trúc dữ liệu chuẩn (`originalLocation`, `slot_id`, `Reference`, `size`, `x`, `y`, `z`):

- `data/interim/random_storage_long_all.csv`: 2.292 vị trí × 18 slots = **41.256 ô**.
- `data/interim/random_storage_long_z34.csv`: 600 vị trí × 18 slots = **10.800 ô** (Phạm vi chính).
- `data/interim/random_storage_long_z3.csv`: 301 vị trí × 18 slots = **5.418 ô** (Sensitivity 1).
- `data/interim/random_storage_long_z4.csv`: 299 vị trí × 18 slots = **5.382 ô** (Sensitivity 2).

Toàn bộ các lần chạy thuật toán tiếp theo sẽ nạp trực tiếp từ `data/interim/` mà không cần đọc lại file thô.

---

## 2. Giải phóng Khoảng 20% Dung lượng (Capacity Release)

Theo mô tả của bài báo, trạng thái ban đầu của mô phỏng cần giải phóng khoảng 20% dung lượng kho để tiếp nhận chuỗi 10.000 kiện hàng nhập:

- **Quy trình tái lập:** Sử dụng thuật toán chọn ngẫu nhiên chính xác 20% số slot đang chứa hàng với `seed=42`.
- **Số ô giải phóng:** Đúng **2,160 / 10,800 ô** (20.0%).
- **Dung lượng còn trống sau giải phóng:** **2,160 ô** (Tỷ lệ lấp đầy: **80.0%**).
- **Tệp lưu trữ vết giải phóng:** `data/processed/released_slots_z34_seed42.csv` ghi nhận chính xác từng ô (`originalLocation`, `slot_id`, `Reference`, `size`).

---

## 3. Biến thiên Mixing Index: Trước vs. Sau Giải phóng Dung lượng

| Phạm vi Không gian | Số vị trí | Tổng sức chứa | Số đơn vị Trước giải phóng | Baseline MI Trước | Critical Rate Trước | Số ô Đã giải phóng | Số đơn vị Sau giải phóng | Initial MI Sau giải phóng | Critical Rate Sau | Biến thiên MI (ΔMI) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Candidate Scope (z in {3, 4})** | 600 | 10,800 | 10,800 | **0.9136** | 99.83% | 2,160 | 8,640 | **0.9015** | 98.83% | -0.0121 |
| **Sensitivity Scope (z=3)** | 301 | 5,418 | 5,418 | **0.9131** | 99.67% | 1,084 | 4,334 | **0.9013** | 99.34% | -0.0117 |
| **Sensitivity Scope (z=4)** | 299 | 5,382 | 5,382 | **0.9142** | 100.00% | 1,076 | 4,306 | **0.9046** | 99.67% | -0.0096 |
| **Full Warehouse (z in {1..4})** | 2,292 | 41,256 | 41,256 | **0.4362** | 47.69% | 8,251 | 33,005 | **0.4300** | 47.60% | -0.0062 |

### Ghi chú phân biệt hai chỉ số quan trọng:
1. **`Paper-like Baseline MI` (0.9136):** Là Mixing Index trên toàn bộ snapshot kho ban đầu khi còn đầy 100% (10.800 ô có hàng). Chỉ số này dùng để đối chiếu với con số `0.918` mà paper báo cáo cho trạng thái *Baseline - Random*.
2. **`Initial Simulation MI` (0.9015):** Là Mixing Index tại thời điểm $t=0$ ngay sau khi giải phóng 20% dung lượng (8.640 ô có hàng). Đây là điểm xuất phát chính xác cho cả 3 tác tử: Heuristic, Supervised, và Adaptive.

---

## 4. Nghiệm thu Điều kiện Hoàn thành Giai đoạn 2

- [x] **1. Parse 18 cột:** Đã chuyển đổi sang long format đầy đủ `location_id`, `slot_id`, `Reference`, `size`, `x`, `y`, `z`.
- [x] **2. Lọc phạm vi:** Đã tạo phạm vi chính `z in {3, 4}` (600 vị trí) và hai sensitivity `z=3` (301 vị trí), `z=4` (299 vị trí).
- [x] **3. Ràng buộc Capacity 18:** Đã cấu hình và kiểm chứng: không có vị trí nào vượt quá 18 ô, không có tồn kho âm.
- [x] **4. Lưu Snapshot Chuẩn hóa:** Đã lưu 4 tệp trong `data/interim/` sẵn sàng phục vụ mô phỏng tốc độ cao.
- [x] **5. Baseline MI trước giải phóng:** Đã tính và ghi nhận đầy đủ theo từng vị trí và toàn kho.
- [x] **6. Trạng thái sau giải phóng 20%:** Đã giải phóng 2.160 ô bằng `seed=42`, lưu danh sách slot trống tại `data/processed/released_slots_z34_seed42.csv` và snapshot tại `data/processed/initial_state_z34_after_release.csv`.
