# Báo cáo Kiểm kê Dữ liệu (Data Audit) & Quyết định Chốt Phạm vi Mô phỏng

> **Dự án:** Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses (Tái hiện bài báo Rodrigo Furlan de Assis et al., 2026)
> **Giai đoạn:** Giai đoạn 1 – Data audit và chốt phạm vi (theo `SLAP-agentic-architecture Plan.md`)
> **Trạng thái:** Hoàn thành toàn diện, bảo đảm tính có thể tái lập (Reproducible) và toàn vẹn dữ liệu.

---

## 1. Tổng quan Bộ Dữ liệu & Hồ sơ 9 Tệp CSV

Hệ thống đã kiểm kê toàn bộ 9 tệp dữ liệu CSV gốc trong thư mục `data/raw/`:

| Tệp CSV | Số dòng | Số cột | Dung lượng | Dấu phân cách | Khóa chính / Cột đầu | Unique Khóa | Số ô Null | Dòng trùng |
|---|---:|---:|---:|:---:|:---|---:|---:|---:|
| `Storage_Location.csv` | 2,292 | 5 | 72.9 KB | `,` | `originalLocation` | 2,292 | 0 | 0 |
| `Random_Storage.csv` | 2,292 | 19 | 442.2 KB | `,` | `originalLocation` | 2,292 | 0 | 0 |
| `Product.csv` | 208 | 3 | 3.9 KB | `;` | `Reference` | 208 | 0 | 0 |
| `Customer_Order.csv` | 122,370 | 9 | 9.02 MB | `;` | `codCustomer` | 588 | 16 | 2559 |
| `Picking_Wave.csv` | 215,192 | 6 | 9.23 MB | `;` | `waveNumber` | 9,707 | 0 | 102201 |
| `Class_Based_Storage.csv` | 2,341 | 20 | 562.9 KB | `;` | `Location` | 2,341 | 0 | 0 |
| `Dedicated_Storage.csv` | 2,340 | 20 | 558.0 KB | `;` | `Location` | 2,340 | 0 | 0 |
| `Hybrid_Storage.csv` | 2,340 | 20 | 558.0 KB | `;` | `Location` | 2,340 | 0 | 0 |
| `Support_Points_Navigation.csv` | 44 | 2 | 1.1 KB | `;` | `points_specified` | 44 | 0 | 0 |

### Ghi chú quan trọng về tiền xử lý & Đọc file (Loaders):
- **Dấu phân cách (Delimiter):** `Storage_Location.csv` và `Random_Storage.csv` dùng dấu phẩy (`,`); 7 tệp còn lại (`Product`, `Customer_Order`, `Picking_Wave`, `Class_Based_Storage`, `Dedicated_Storage`, `Hybrid_Storage`, `Support_Points_Navigation`) dùng dấu chấm phẩy (`;`).
- **Mã hóa (Encoding):** Tất cả các tệp đều được xử lý chuẩn UTF-8, có cơ chế dự phòng `latin-1` tự động trong `loaders.py`.
- **Giá trị rỗng (Null values):** Chỉ duy nhất `Customer_Order.csv` chứa 16 ô null ở cột `Size (US)`. Tất cả 8 tệp còn lại hoàn toàn không có ô null.

---

## 2. Kiểm kê Bản đồ Vị trí & Tọa độ (`Storage_Location.csv`)

- **Tổng số vị trí:** 2,292 vị trí (`originalLocation` độc nhất: 2,292).
- **Phân bố theo tầng cao `z`:**
  - Tầng `z=1`: **846** vị trí (36.91%)
  - Tầng `z=2`: **846** vị trí (36.91%)
  - Tầng `z=3`: **301** vị trí (13.13%)
  - Tầng `z=4`: **299** vị trí (13.05%)

### Phát hiện Tọa độ Trùng (Duplicate Coordinates):
> [!WARNING]
> Phát hiện 2 vị trí có cùng tọa độ 3D `(x, y, z)` trong kho:
> - Vị trí `K-23-30` (position `102, 810, 3`): tọa độ `(102.0, 810.0, 3.0)`
> - Vị trí `K-23-40` (position `102, 810, 3`): tọa độ `(102.0, 810.0, 3.0)`
> **Xử lý:** Đối với bài toán SLAP dựa trên Mixing Index, hai vị trí này hoàn toàn độc lập về định danh `originalLocation` và sức chứa (mỗi vị trí 18 ô riêng biệt). Sự trùng lặp tọa độ không ảnh hưởng đến Mixing Index hay phân bổ hàng nhập. Trong trường hợp mở rộng tính toán đường đi picker, cần gán offset hoặc tách biệt nút đồ thị.

---

## 3. Kiểm kê Danh mục Sản phẩm (`Product.csv`)

- **Tổng số SKU (`Reference`):** **208** mã sản phẩm duy nhất.
- **Phân loại ABC (`ABCCOD`):**
  - Nhóm **A**: **44** SKU (21.2%)
  - Nhóm **B**: **70** SKU (33.7%)
  - Nhóm **C**: **94** SKU (45.2%)
- **Khu vực (`Sector`):** 100% SKU thuộc sector **`PF`** (208 dòng).
- **Kiểm tra tương thích Danh mục:** Tất cả 208 mã SKU xuất hiện trong `Random_Storage.csv` đều tồn tại chính xác 100% trong `Product.csv`.

---

## 4. Phân tích Chi tiết Snapshot Kho & Tính toán Mixing Index Baseline

Theo công thức Mixing Index (MI) của Assis et al. (2026):

$$
MI_l(S_t) = \begin{cases} 1 - \dfrac{\max_i n_{i,l,t}}{\sum_i n_{i,l,t}}, & \text{nếu vị trí có hàng} \\ 0, & \text{nếu vị trí trống} \end{cases}
$$

Bảng kiểm kê Mixing Index và đặc trưng hàng hóa theo từng phạm vi tầng cao `z`:

| Phạm vi Không gian | Bộ lọc tầng `z` | Số vị trí | Tổng số ô (slots) | Số SKU | Dải Size quan sát | MI Baseline trung bình | Tỷ lệ vị trí có MI > 0.8 |
|---|:---:|---:|---:|---:|:---:|---:|---:|
| **All Levels (z in {1, 2, 3, 4})** | `1, 2, 3, 4` | 2,292 | 41,256 | 208 | `4.0 - 280.0` | **0.4362** | **47.69%** |
| **Level z=1** | `[1]` | 846 | 15,228 | 208 | `4.0 - 235.0` | **0.2692** | **29.43%** |
| **Level z=2** | `[2]` | 846 | 15,228 | 208 | `4.0 - 280.0` | **0.2646** | **28.96%** |
| **Level z=3** | `[3]` | 301 | 5,418 | 208 | `4.0 - 16.0` | **0.9131** | **99.67%** |
| **Level z=4** | `[4]` | 299 | 5,382 | 208 | `4.0 - 16.0` | **0.9142** | **100.00%** |
| **Candidate Scope (z in {3, 4})** | `[3, 4]` | 600 | 10,800 | 208 | `4.0 - 16.0` | **0.9136** | **99.83%** |

### Phân tích Khoa học & Nguyên nhân Sai khác giữa các Tầng:
1. **Tầng `z=1` và `z=2` (Kho chứa chuyên dụng/Dedicated):**
   - MI trung bình chỉ đạt xấp xỉ **0.2692** (`z=1`) và **0.2646** (`z=2`).
   - Tỷ lệ vị trí có `MI > 0.8` chỉ là **29.43%** và **28.96%**.
   - Dải size chứa các giá trị ngoại lai lớn như **235.0, 260.0, 280.0** (quy ước cỡ giày mm/châu Á hoặc đơn vị kích thước thùng hàng khác).
   - Thực tế vận hành cho thấy 2 tầng dưới được tổ chức theo cơ chế phân bổ tập trung (mỗi vị trí hầu như chỉ chứa 1 hoặc rất ít SKU), không phản ánh tính chất *Random Storage* được mô tả trong bài báo.

2. **Tầng `z=3` và `z=4` (Kho chứa ngẫu nhiên chuẩn / Random Storage):**
   - MI trung bình đạt **0.9131** (`z=3`) và **0.9142** (`z=4`).
   - Tỷ lệ vị trí có `MI > 0.8` đạt **99.67%** (`z=3`) và **100.00%** (`z=4`).
   - Toàn bộ dải size nằm chính xác tuyệt đối trong khoảng **`[4.0, 16.0]`**, hoàn toàn trùng khớp với bài báo Assis et al. (2026).
   - Khi kết hợp **`z in {3, 4}`**: ta có **600 vị trí**, **10.800 ô**, **208 SKU**, MI baseline trung bình là **0.9136**, tỷ lệ critical là **99.83%**.

---

## 5. Quyết định Chốt Phạm vi Mô phỏng (Scope Determination)

### Bảng Đối chiếu Chỉ số: Bài báo gốc vs. Dữ liệu thực tế

| Tiêu chí | Báo cáo trong Bài báo Paper | Dữ liệu Toàn bộ Kho (All z) | Đề xuất Chốt: Phạm vi Chính `z in {3, 4}` | Sai khác & Giải trình |
|---|---:|---:|---:|:---|
| **Số vị trí lưu trữ** | 847 | 2.292 | **600** | Dữ liệu thực tế chia thành 846 (z=1), 846 (z=2), 301 (z=3), 299 (z=4). Không tự ý gán vị trí giả. |
| **Số SKU độc nhất** | 209 | 208 | **208** | Thiếu 1 SKU so với bài báo; giữ nguyên 208 SKU thực tế, không sinh dữ liệu ảo. |
| **Sức chứa mỗi vị trí** | 18 | 18 | **18** | Khớp chính xác 100%. |
| **Dải Size sản phẩm** | 4 – 16 | 4 – 280 | **4 – 16** | Khớp chính xác 100% với dải của bài báo. |
| **MI Baseline (Random)** | **0.918** | 0.4362 | **0.9136** | Chênh lệch chỉ 0.0044 (0.48%), cực kỳ tiệm cận baseline paper. |
| **Tỷ lệ vị trí MI > 0.8** | **100.00%** | 47.69% | **99.83%** | Tiệm cận mức 100% của bài báo (599/600 vị trí). |

> [!IMPORTANT]
> **KẾT LUẬN CHỐT PHẠM VI (SCOPE DECISION):**
> 1. **Phạm vi chính thức của mô phỏng (Primary Simulation Universe):** Sử dụng tập hợp vị trí thuộc tầng **`z in {3, 4}`** (gồm 600 vị trí, 10.800 ô lưu trữ, 208 SKU). Đây là tập con duy nhất thỏa mãn đồng thời: dải size `[4, 16]`, MI baseline tiệm cận `0.918` và tỷ lệ vị trí hỗn tạp cao tiệm cận `100%`.
> 2. **Phạm vi phân tích độ nhạy (Sensitivity Scopes):** Thiết lập thêm 2 kịch bản chạy độc lập trên **`z=3`** (301 vị trí) và **`z=4`** (299 vị trí) nhằm kiểm chứng tính vững của thuật toán trước quy mô tầng kho.
> 3. **Tính trung thực khoa học:** Trong mọi báo cáo và ấn phẩm, khẳng định rõ đây là *closest matching subset from the provided files* (600 vị trí, 208 SKU), không sửa đổi nhân tạo để cố tình làm khớp con số 847 vị trí hay 209 SKU của bài báo.

---

## 6. Kiểm kê Bổ sung: Giao dịch Đơn hàng, Lấy hàng và Các Snapshot Chính sách

### 6.1. Dữ liệu Đơn hàng Khách hàng (`Customer_Order.csv`)
- **Tổng số dòng:** 122,370
- **Số đơn hàng (`orderNumber`):** 32,634
- **Số đợt (`waveNumber`):** 9,784
- **Khoảng thời gian tạo đơn:** từ `2023-01-05 07:42:00` đến `2023-10-19 07:18:00` (tháng 1 đến tháng 10 năm 2023).
- **Kiểm tra chất lượng số lượng (Quantity):**
  - Số dòng có `quantity <= 0`: **33** dòng (tất cả đều có quantity = 0). Cần lọc bỏ các dòng này khi sinh phân phối batch-size.
  - Số dòng có `quantity > 36`: duy nhất **1** dòng (giá trị max = 120).
  - Số dòng khuyết `Size (US)`: **16** dòng.
  - Kích cỡ `Size (US)` trong file order có chứa 41,549 dòng với giá trị > 16 (do mã hóa quy ước cỡ số khác). Do đó, **không lấy size trực tiếp từ `Customer_Order.csv` mà lấy size từ snapshot kho trong phạm vi `z in (3, 4)`** để đảm bảo đúng dải 4–16.

### 6.2. Dữ liệu Đợt Lấy hàng (`Picking_Wave.csv`)
- **Tổng số dòng:** 215,192
- **Số đợt (`waveNumber`):** 9,707
- **Số mã tham chiếu (`reference`):** 198
- **Đặc điểm `quantityToPick (units)`:** **100% dòng đều có quantity = 1** (215,192 dòng).
- **Kết luận:** Tệp này ghi nhận từng đơn vị lấy hàng đơn lẻ, do đó **không thể sử dụng làm phân phối batch-size hàng nhập**.

### 6.3. So sánh các Snapshot Chính sách Lưu trữ Khác

| Tệp Snapshot Chính sách | Số vị trí | Số ô / vị trí | Vị trí thừa so với Random_Storage | Vị trí thiếu so với Random_Storage | Số SKU | SKU thừa so với Product Catalog |
|---|---:|---:|---:|---:|---:|---:|
| `Dedicated_Storage.csv` | 2,340 | 18 | **+48** | 0 | 208 | **+0** |
| `Hybrid_Storage.csv` | 2,340 | 18 | **+48** | 0 | 208 | **+0** |
| `Class_Based_Storage.csv` | 2,341 | 18 | **+49** | 0 | 317 | **+109** |

#### Nhận xét:
- `Dedicated_Storage` và `Hybrid_Storage` đều chứa 2.340 vị trí (nhiều hơn `Random_Storage` đúng 48 vị trí: `E-25-10`, `E-25-20`, `F-25-10`...). 48 vị trí này cũng không có trong `Storage_Location.csv`.
- `Class_Based_Storage` chứa 2.341 vị trí (nhiều hơn 49 vị trí) và chứa tới **317 SKU** (thừa 109 SKU so với danh mục `Product.csv`).
- **Kết luận:** Các snapshot chính sách này không cùng không gian vị trí và mã hàng với `Random_Storage`, do đó **không được dùng trực tiếp làm đối chứng baseline** trong thí nghiệm cốt lõi của bài báo.

---

## 7. Nghiệm thu Điều kiện Hoàn thành Giai đoạn 1

- [x] **1. Loaders:** Đã xây dựng `src/data/loaders.py` và `src/data/audit.py` hỗ trợ đầy đủ encoding và delimiter của 9 tệp CSV.
- [x] **2. Data Profile:** Đã xuất `outputs/tables/data_profile.csv` với đầy đủ row count, nulls, duplicates, column metrics.
- [x] **3. Không gian Vị trí & z:** Đã join `Random_Storage` với `Storage_Location` để phân tầng z và phát hiện cặp tọa độ trùng `K-23-30` & `K-23-40`.
- [x] **4. Baseline MI:** Đã tính MI baseline và critical percentage trên tất cả các tầng (All z, z=1, z=2, z=3, z=4, z in {3,4}) và xuất `outputs/tables/baseline_mi_by_scope.csv`.
- [x] **5. Kiểm tra Reference:** Đã đối chiếu 100% SKU giữa `Random_Storage` và `Product.csv` (208 SKU khớp tuyệt đối), ghi nhận 109 SKU ngoại lai trong `Class_Based_Storage`.
- [x] **6. Báo cáo & Chốt Phạm vi:** Đã hoàn thành báo cáo kiểm kê toàn diện `data_audit.md`, chốt phạm vi chính `z in {3, 4}` với cơ sở toán học và thực nghiệm vững chắc, sẵn sàng chuyển tiếp sang Giai đoạn 2.
