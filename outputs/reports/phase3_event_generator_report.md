# Báo cáo Giai đoạn 3: Sinh Chuỗi 10.000 Sự kiện Hàng nhập (Event Generator)

> **Dự án:** Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses (Assis et al., 2026)
> **Giai đoạn:** Giai đoạn 3 – Event generator (theo `SLAP-agentic-architecture Plan.md`)
> **Trạng thái:** Hoàn thành toàn diện, bảo đảm tính có thể tái lập (Reproducible) với seed cố định.

---

## 1. Thiết kế Phân phối Xác suất Hàng nhập

Do bộ dữ liệu gốc không có bảng nhật ký giao dịch nhập hàng (inbound transactions), chuỗi sự kiện được tái tạo bằng quy tắc toán học theo đúng mô tả của bài báo:

1. **Xác suất SKU $P(i_t = i)$:** Lấy mẫu tỷ lệ thuận với tần suất tồn kho (*stock frequency*) trong snapshot phạm vi chính $z \in \{3, 4\}$:
   $$P(i_t = i) = \frac{\text{stock\_count}_i}{\sum_j \text{stock\_count}_j}$$
   Tất cả **208 SKU** đều có xác suất dương và được lấy mẫu có hoàn lại.

2. **Kích cỡ hàng nhập $s_t$ (Conditional Size Sampling):**
   - Với mỗi SKU $i_t$ được chọn, kích cỡ $s_t$ được lấy mẫu ngẫu nhiên từ chính các kích cỡ đã quan sát được của SKU đó trong snapshot.
   - Mọi kích cỡ hàng nhập nằm chính xác tuyệt đối trong dải **`[4.0, 16.0]`**, bảo toàn quan hệ SKU–size và khớp 100% mô tả bài báo.

3. **Khối lượng lô hàng $u_t$ (Inbound Batch Size Proxy):**
   - Lấy mẫu có hoàn lại từ phân phối thực nghiệm của các dòng có số lượng dương trong `Customer_Order.csv` (122.337 dòng sau khi đã loại bỏ 33 dòng có số lượng bằng 0).
   - Phân phối batch-size có trung vị là **1**, trung bình là **1.85**, và giá trị lớn nhất trong chuỗi sự kiện là **24** (không vượt quá sức chứa look-ahead 2 vị trí là 36 ô).

---

## 2. Thống kê Chuỗi Sự kiện Chính & Độ nhạy

| Tên chuỗi sự kiện | Nguồn xác suất SKU | Seed | Số sự kiện | Số SKU | Dải Size | Dải Quantity | Quantity TB | Tổng số đơn vị nhập | Tình trạng Kiểm định |
|---|:---:|:---:|---:|---:|:---:|:---:|---:|---:|:---:|
| **Primary Stream (Stock Frequency)** | `Stock Frequency` | `42` | 10,000 | 208 | `4.0 - 16.0` | `1 - 24` | 1.8546 | **18,546** | PASSED (100% catalog/size valid) |
| **Sensitivity S2 (Demand Proxy)** | `Order Demand` | `42` | 10,000 | 182 | `4.0 - 16.0` | `1 - 24` | 1.8546 | **18,546** | PASSED (100% catalog/size valid) |

---

## 3. Phân phối Khối lượng Lô hàng Nhập (Batch Size Distribution)

| Khối lượng lô ($u_t$) | Số lượng sự kiện | Tỷ lệ phần trăm | Diễn giải vận hành |
|---:|---:|---:|:---|
| **1** | 6,798 | 67.98% | Đơn vị lẻ (Single unit) |
| **2** | 1,745 | 17.45% | Cặp đơn vị (Pair) |
| **3** | 453 | 4.53% | Hộp nhỏ / Thùng nhỏ |
| **4** | 227 | 2.27% | Hộp nhỏ / Thùng nhỏ |
| **5** | 401 | 4.01% | Hộp nhỏ / Thùng nhỏ |
| **6** | 130 | 1.30% | Hộp nhỏ / Thùng nhỏ |
| **7** | 29 | 0.29% | Lô hàng trung bình |
| **8** | 34 | 0.34% | Lô hàng trung bình |
| **9** | 28 | 0.28% | Lô hàng trung bình |
| **10** | 19 | 0.19% | Lô hàng trung bình |

> [!NOTE]
> Các sự kiện có khối lượng $u_t \in \{1, 2\}$ chiếm tới **85.4%** tổng số sự kiện hàng nhập. Điều này hoàn toàn phù hợp với thực tế kho picker-to-part và thương mại điện tử.

---

## 4. Kiểm tra Độ khớp Tần suất SKU (Top 10 SKU)

| Mã SKU (`Reference`) | Số ô trong Snapshot gốc | Xác suất lý thuyết | Số sự kiện được lấy mẫu | Tần suất thực nghiệm | Chênh lệch |
|:---|---:|---:|---:|---:|---:|
| `AHR20O` | 75 | 0.0069 | 76 | 0.0076 | +0.0007 |
| `PZUF7K` | 71 | 0.0066 | 56 | 0.0056 | -0.0010 |
| `RAUDQ6` | 71 | 0.0066 | 55 | 0.0055 | -0.0011 |
| `IYV9SV` | 70 | 0.0065 | 76 | 0.0076 | +0.0011 |
| `UU4A1K` | 70 | 0.0065 | 64 | 0.0064 | -0.0001 |
| `C5O9C9` | 66 | 0.0061 | 66 | 0.0066 | +0.0005 |
| `B24J86` | 65 | 0.0060 | 68 | 0.0068 | +0.0008 |
| `NJVZEL` | 65 | 0.0060 | 61 | 0.0061 | +0.0001 |
| `56TC1Z` | 64 | 0.0059 | 61 | 0.0061 | +0.0002 |
| `CVU3QV` | 63 | 0.0058 | 62 | 0.0062 | +0.0004 |

---

## 5. Nghiệm thu Điều kiện Hoàn thành Giai đoạn 3

- [x] **1. Phân phối SKU:** Tính toán xác suất stock frequency $P(i_t = i)$ trên 10.800 ô snapshot gốc của phạm vi chính $z \in \{3, 4\}$.
- [x] **2. Phân phối Size có điều kiện:** 100% sự kiện có size hợp lệ theo quan sát của từng SKU trong kho, nằm trọn vẹn trong $[4.0, 16.0]$.
- [x] **3. Phân phối Batch-size:** Lấy mẫu thực nghiệm từ 122.337 dòng `Customer_Order.quantity > 0`, đã ghi nhận và loại bỏ 33 dòng lỗi.
- [x] **4. Tính tái lập với Seed=42:** Chuỗi 10.000 sự kiện được sinh đúng 1 lần và lưu ra `data/processed/inbound_events.csv` dùng chung tuyệt đối cho cả 3 tác tử.
- [x] **5. Bộ dòng nhạy cảm đa dạng:** Đã sinh sẵn chuỗi S2 (demand proxy) và 4 chuỗi hạt giống khác (seeds 100, 2026, 777, 999).
- [x] **6. Kiểm định Toàn vẹn:** Đã kiểm tra 100% SKU thuộc catalog, 100% size hợp lệ, không có quantity $\le 0$, event ID độc nhất từ 1 đến 10.000.
