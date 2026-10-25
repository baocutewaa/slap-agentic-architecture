# Báo cáo Kiểm kê Dữ liệu (Data Audit) & Quyết định Chốt Phạm vi Mô phỏng

> **Dự án:** Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses (Tái hiện bài báo Rodrigo Furlan de Assis et al., 2026)  
> **Giai đoạn:** Giai đoạn 1 – Data audit và chốt phạm vi (theo `SLAP-agentic-architecture Plan.md`)  
> **Trạng thái:** Hoàn thành toàn diện, bảo đảm tính có thể tái lập (Reproducible), toàn vẹn dữ liệu và đối chiếu minh bạch với bài báo gốc.

---

## 1. Tổng quan Bộ Dữ liệu & Hồ sơ 9 Tệp CSV

Hệ thống đã xây dựng bộ nạp chuyên biệt (`src/data/loaders.py`) để kiểm kê toàn bộ 9 tệp dữ liệu CSV gốc trong thư mục `data/raw/`, tự động nhận diện định dạng dấu phân cách và mã hóa:

| Tệp CSV | Số dòng | Số cột | Dung lượng | Dấu phân cách | Khóa chính / Cột đầu | Unique Khóa | Số ô Null | Dòng trùng |
|---|---:|---:|---:|:---:|:---|---:|---:|---:|
| `Storage_Location.csv` | 2,292 | 5 | 72.9 KB | `,` | `originalLocation` | 2,292 | 0 | 0 |
| `Random_Storage.csv` | 2,292 | 19 | 442.2 KB | `,` | `originalLocation` | 2,292 | 0 | 0 |
| `Product.csv` | 208 | 3 | 3.9 KB | `;` | `Reference` | 208 | 0 | 0 |
| `Customer_Order.csv` | 122,370 | 9 | 9.02 MB | `;` | `codCustomer` | 588 | 16 | 2,559 |
| `Picking_Wave.csv` | 215,192 | 6 | 9.23 MB | `;` | `waveNumber` | 9,707 | 0 | 102,201 |
| `Class_Based_Storage.csv` | 2,341 | 20 | 562.9 KB | `;` | `Location` | 2,341 | 0 | 0 |
| `Dedicated_Storage.csv` | 2,340 | 20 | 558.0 KB | `;` | `Location` | 2,340 | 0 | 0 |
| `Hybrid_Storage.csv` | 2,340 | 20 | 558.0 KB | `;` | `Location` | 2,340 | 0 | 0 |
| `Support_Points_Navigation.csv` | 44 | 2 | 1.1 KB | `;` | `points_specified` | 44 | 0 | 0 |

### Quy tắc Tiền xử lý & Kiểm soát Toàn vẹn (Data Engineering Standards):
- **Dấu phân cách (Delimiter):** `Storage_Location.csv` và `Random_Storage.csv` dùng dấu phẩy (`,`); 7 tệp còn lại dùng dấu chấm phẩy (`;`).
- **Mã hóa (Encoding):** Tự động xử lý UTF-8 với cơ chế fallback sang `latin-1`.
- **Giá trị rỗng (Null values):** Chỉ duy nhất `Customer_Order.csv` chứa 16 ô null ở cột `Size (US)`. Tất cả 8 tệp còn lại hoàn toàn không có ô null.
- **Tính duy nhất:** Khóa chính `originalLocation` trong `Storage_Location.csv` và `Random_Storage.csv` đạt tỷ lệ duy nhất 100% (2.292/2.292).

---

## 2. Kiểm kê Bản đồ Vị trí & Phân tích Không gian 3D

- **Tổng số vị trí:** 2.292 vị trí lưu trữ.
- **Phân bố theo tầng cao $z$:**
  - Tầng $z=1$: **846** vị trí (36.91%)
  - Tầng $z=2$: **846** vị trí (36.91%)
  - Tầng $z=3$: **301** vị trí (13.13%)
  - Tầng $z=4$: **299** vị trí (13.05%)
- **Tập hợp tầng trên $z \in \{3, 4\}$:** Gồm **600 vị trí** (26.18% tổng kho).

### Phát hiện Bất thường Tọa độ Trùng (Duplicate Coordinates):
> [!WARNING]
> Thuật toán kiểm định phát hiện đúng 2 vị trí có cùng tọa độ 3D $(x, y, z)$ trong kho:
> - Vị trí `K-23-30` (position $102, 810, 3$): tọa độ $(102.0, 810.0, 3.0)$
> - Vị trí `K-23-40` (position $102, 810, 3$): tọa độ $(102.0, 810.0, 3.0)$
> **Chiến lược xử lý khoa học:** Cả hai vị trí này hoàn toàn độc lập về định danh `originalLocation` và năng lực chứa hàng ($C_l = 18$ ô riêng biệt). Do đó, chúng được bảo toàn độc lập trong mô phỏng SLAP (đã lập hồ sơ kiểm toán tại [`outputs/tables/phase1_coordinate_duplicate_audit.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/phase1_coordinate_duplicate_audit.csv)). Khi mở rộng sang mô hình định tuyến lấy hàng (picker routing), chỉ cần gán offset hoặc tách nút đồ thị.

![Phân bố Vị trí Kho và Tọa độ Không gian](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase1_warehouse_layout_z_distribution.png)

*Hình 1.1: (a) Phân bố 2.292 vị trí kho theo tầng cao $z$; (b) Bản đồ bố trí tọa độ không gian 2D và điểm phát hiện tọa độ trùng tại Rack 23.*

---

## 3. Kiểm kê Danh mục Sản phẩm & Đối chiếu Mã hàng

- **Tổng số SKU trong danh mục gốc (`Product.csv`):** **208** SKU duy nhất.
- **Phân loại ABC (`ABCCOD`):** Nhóm **A** có 44 SKU (21.2%), Nhóm **B** có 70 SKU (33.7%), Nhóm **C** có 94 SKU (45.2%).
- **Kiểm tra tương thích Danh mục:**
  - 100% SKU xuất hiện trong `Random_Storage.csv` (208 SKU) đều tồn tại chính xác tuyệt đối trong `Product.csv` (độ khớp 100.0%).
  - Ngược lại, snapshot `Class_Based_Storage.csv` chứa tới **317 SKU**, trong đó có **109 SKU ngoại lai** không hề có trong danh mục sản phẩm chuẩn `Product.csv`.

![Phân tích Pareto SKU và Đối chiếu Danh mục Sản phẩm](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase1_sku_pareto_analysis.png)

*Hình 1.2: (a) Biểu đồ Pareto 20 SKU có số lượng tồn lớn nhất trong phạm vi chính $z \in \{3,4\}$; (b) Kết quả đối chiếu danh mục sản phẩm và phát hiện 109 SKU ngoại lai.*

---

## 4. Phân tích Snapshot Kho & Tính toán Mixing Index Baseline

Theo định nghĩa của Assis et al. (2026), chỉ số Mixing Index của vị trí $l$ tại thời điểm $t$ là:

$$MI_l(S_t) = \begin{cases} 1 - \dfrac{\max_i n_{i,l,t}}{\sum_i n_{i,l,t}}, & \text{nếu vị trí có hàng} \\ 0, & \text{nếu vị trí trống} \end{cases}$$

Kết quả đo đạc thực nghiệm trên toàn bộ snapshot kho ban đầu theo từng phạm vi tầng cao:

| Phạm vi Không gian | Bộ lọc tầng $z$ | Số vị trí | Tổng số ô (slots) | Số SKU | Dải Size quan sát | MI Baseline trung bình | Tỷ lệ vị trí có MI > 0.8 |
|---|:---:|---:|---:|---:|:---:|---:|---:|
| **All Levels (z in {1, 2, 3, 4})** | `1, 2, 3, 4` | 2,292 | 41,256 | 208 | `4.0 - 280.0` | **0.4362** | **47.69%** |
| **Level z=1** | `[1]` | 846 | 15,228 | 208 | `4.0 - 235.0` | **0.2692** | **29.43%** |
| **Level z=2** | `[2]` | 846 | 15,228 | 208 | `4.0 - 280.0` | **0.2646** | **28.96%** |
| **Level z=3** | `[3]` | 301 | 5,418 | 208 | `4.0 - 16.0` | **0.9131** | **99.67%** |
| **Level z=4** | `[4]` | 299 | 5,382 | 208 | `4.0 - 16.0` | **0.9142** | **100.00%** |
| **Candidate Scope (z in {3, 4})** | `[3, 4]` | **600** | **10,800** | **208** | **`4.0 - 16.0`** | **0.9136** | **99.83%** |

![Phân phối Mixing Index Baseline qua các Phạm vi Không gian](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase1_baseline_mi_distribution.png)

*Hình 1.3: (a) Hàm mật độ phân phối MI giữa tầng trên $z \in \{3,4\}$ và tầng dưới $z \in \{1,2\}$; (b) Biểu đồ hộp (boxplot) so sánh Mixing Index giữa các phạm vi không gian.*

### Phân tích Khoa học & Bản chất Sự phân tầng:
1. **Tầng dưới ($z=1, 2$):** Có MI trung bình rất thấp ($\sim 0.26$), dải size cực rộng ($4.0 - 280.0$). Tại đây, nhiều vị trí được bố trí theo cụm thuần nhất một loại hàng (single-SKU storage) hoặc ô hàng cồng kềnh, làm triệt tiêu tính ngẫu nhiên hỗn hợp.
2. **Tầng trên ($z=3, 4$):** Có MI trung bình đạt **0.9136**, tỷ lệ vị trí nguy cơ ($MI > 0.8$) đạt **99.83%**, và toàn bộ kích cỡ đều nằm trong dải chuẩn **`[4.0, 16.0]`**. Con số này **trùng khớp mật thiết** với con số **0.918 (100.0% critical)** mà bài báo của Assis et al. (2026) công bố cho cấu hình Baseline – Random!

---

## 5. Quyết định Chốt Phạm vi Mô phỏng (Scope Determination)

### Bảng Đối chiếu Chỉ số: Bài báo gốc vs. Dữ liệu thực tế

| Chỉ số | Bài báo công bố (Assis et al., 2026) | Toàn kho ($z \in \{1..4\}$) | Tầng dưới ($z \in \{1, 2\}$) | Phạm vi đề xuất ($z \in \{3, 4\}$) | Đánh giá độ khớp |
|---|:---:|:---:|:---:|:---:|:---:|
| **Số vị trí kho** | 847 | 2,292 | 1,692 | **600** | Sai khác kích thước kho |
| **Số mã SKU** | 209 | 208 | 208 | **208** | Khớp 99.5% (208 vs 209) |
| **Dải kích cỡ (Size)** | 4 – 16 | 4 – 280 | 4 – 280 | **4 – 16** | **Khớp 100%** |
| **Baseline MI** | **0.918** | 0.4362 | 0.2669 | **0.9136** | **Khớp 99.5%** |
| **Vị trí có MI > 0.8** | **100.00%** | 47.69% | 29.20% | **99.83%** | **Khớp 99.8%** |

> [!IMPORTANT]
> **QUYẾT ĐỊNH CHỐT PHẠM VI (SCOPE DECISION):**
> 1. **Phạm vi chính thức của mô phỏng (Primary Simulation Universe):** Sử dụng tập hợp vị trí thuộc tầng **`z in {3, 4}`** (gồm 600 vị trí, 10.800 ô lưu trữ, 208 SKU). Đây là tập con duy nhất thỏa mãn trọn vẹn: dải size $[4.0, 16.0]$, baseline MI tiệm cận $0.918$ và tỷ lệ vị trí hỗn tạp cao tiệm cận $100\%$.
> 2. **Phạm vi phân tích độ nhạy (Sensitivity Scopes):** Thiết lập thêm 2 kịch bản chạy độc lập trên **`z=3`** (301 vị trí) và **`z=4`** (299 vị trí) nhằm kiểm chứng tính bền vững của thuật toán trước quy mô tầng kho.
> 3. **Nguyên tắc liêm chính học thuật:** Khẳng định minh bạch sai khác $600$ vs $847$ vị trí và $208$ vs $209$ SKU trong bài báo; tuyệt đối không tạo dữ liệu giả để làm khớp hình thức.

---

## 6. Kiểm kê Snapshot Chính sách Lưu trữ Khác

Bảng so sánh cấu trúc giữa 4 snapshot chính sách lưu trữ có sẵn trong dữ liệu:

| Tệp Snapshot Chính sách | Số vị trí | Số ô / vị trí | Vị trí lệch so với Random_Storage | Số SKU | SKU ngoại lai so với Danh mục |
|---|---:|---:|---:|---:|---:|
| `Random_Storage.csv` | 2,292 | 18 | 0 (Gốc) | 208 | 0 (Chuẩn) |
| `Dedicated_Storage.csv` | 2,340 | 18 | **+48 vị trí** | 208 | 0 |
| `Hybrid_Storage.csv` | 2,340 | 18 | **+48 vị trí** | 208 | 0 |
| `Class_Based_Storage.csv` | 2,341 | 18 | **+49 vị trí** | 317 | **+109 SKU ngoại lai** |

![So sánh giữa các Chính sách Lưu trữ](file:///c:/Users/Admin/Desktop/NCKH\SLAP\slap-agentic-architecture\outputs\figures\phase1_storage_policy_comparison.png)

*Hình 1.4: So sánh quy mô vị trí và tính tương thích danh mục sản phẩm giữa 4 snapshot chính sách lưu trữ.*

---

## 7. Tổng kết Danh mục Kết quả & Hiện vật (Deliverables Giai đoạn 1)

Toàn bộ các đầu ra của Giai đoạn 1 đã được kết xuất đầy đủ theo đúng chuẩn cấu trúc của dự án:

| Loại hiện vật | Đường dẫn tệp tin | Mô tả kỹ thuật |
|---|---|---|
| **Báo cáo Kỹ thuật** | [`outputs/reports/phase1_data_audit.md`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/reports/phase1_data_audit.md) | Báo cáo kiểm kê toàn diện 9 tệp dữ liệu, luận chứng khoa học chốt phạm vi mô phỏng $z \in \{3,4\}$. |
| **Mã nguồn Nạp dữ liệu** | [`src/data/loaders.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/data/loaders.py) | Bộ nạp linh hoạt tự động nhận diện dấu phân cách (`,`, `;`) và mã hóa UTF-8/latin-1. |
| **Mã nguồn Kiểm kê** | [`src/data/audit.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/data/audit.py) | Mô-đun tính toán hồ sơ dữ liệu, đối chiếu SKU và tính toán Mixing Index baseline. |
| **Bộ Kiểm thử Đầy đủ** | [`tests/test_data_validation.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/tests/test_data_validation.py) | 10 unit tests kiểm định tính toàn vẹn schema, không gian tọa độ và tính hợp lệ của dữ liệu. |
| **Jupyter Notebook Trực quan** | [`notebooks/01_data_audit.ipynb`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/notebooks/01_data_audit.ipynb) | Notebook phân tích khám phá dữ liệu tương tác (~291 KB), chứa toàn bộ số liệu và trực quan hóa. |
| **Biểu đồ Phân bố Vị trí Kho** | [`outputs/figures/phase1_warehouse_layout_z_distribution.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase1_warehouse_layout_z_distribution.png) | Phân bố vị trí theo tầng $z$ và bản đồ tọa độ 2D phát hiện tọa độ trùng tại $K-23-30$ & $K-23-40$. |
| **Biểu đồ Phân phối MI Baseline** | [`outputs/figures/phase1_baseline_mi_distribution.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase1_baseline_mi_distribution.png) | So sánh hàm mật độ MI giữa tầng $z \in \{3,4\}$ vs $z \in \{1,2\}$ và biểu đồ hộp đa phạm vi. |
| **Biểu đồ Phân tích Pareto SKU** | [`outputs/figures/phase1_sku_pareto_analysis.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase1_sku_pareto_analysis.png) | Biểu đồ Pareto 20 SKU tồn kho lớn nhất và đối chiếu danh mục sản phẩm (208 SKU vs 317 SKU). |
| **Biểu đồ So sánh Chính sách** | [`outputs/figures/phase1_storage_policy_comparison.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase1_storage_policy_comparison.png) | So sánh số lượng vị trí và số lượng mã hàng giữa 4 chính sách lưu trữ trong kho. |
| **Bảng Hồ sơ Dữ liệu** | [`outputs/tables/data_profile.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/data_profile.csv) | Thống kê số dòng, cột, null, duplicates và kích thước của 9 tệp dữ liệu gốc. |
| **Bảng Đo đạc MI theo Tầng** | [`outputs/tables/baseline_mi_by_scope.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/baseline_mi_by_scope.csv) | Chỉ số MI trung bình, critical percentage và dải size theo từng tầng kho. |
| **Bảng Luận chứng Phạm vi** | [`outputs/tables/scope_justification.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/scope_justification.csv) | Bảng so sánh 5 tiêu chí đối chiếu giữa số liệu bài báo và phạm vi dữ liệu $z \in \{3,4\}$. |
| **Bảng Đối chiếu Chính sách** | [`outputs/tables/policy_comparison.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/policy_comparison.csv) | Chi tiết số vị trí và số SKU sai lệch của Dedicated, Hybrid và Class-Based so với Random. |
| **Bảng Kiểm toán Tọa độ Trùng** | [`outputs/tables/phase1_coordinate_duplicate_audit.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/phase1_coordinate_duplicate_audit.csv) | Chi tiết 2 vị trí trùng tọa độ $(102, 810, 3)$ và giải pháp xử lý kỹ thuật độc lập. |
| **Bảng Chỉ số Đo lường Tổng hợp** | [`outputs/metrics/metrics_phase1_audit.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/metrics/metrics_phase1_audit.csv) | 15 chỉ số đo lường định lượng cốt lõi của Giai đoạn 1 (tổng quy mô, độ tương thích danh mục, baseline MI). |
| **Nhật ký Kiểm định Dữ liệu** | [`outputs/logs/phase1_data_audit_log.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/logs/phase1_data_audit_log.csv) | Nhật ký từng bước xác thực cấu trúc, encoding, schema và tính toàn vẹn của 9 tệp dữ liệu. |

---

## 8. Sẵn sàng Chuyển giao sang Giai đoạn 2

Giai đoạn 1 đã hoàn tất 100% mục tiêu, làm rõ cơ sở toán học và chốt tập hợp 600 vị trí tầng $z \in \{3, 4\}$ với độ khớp $99.5\%$ so với bài báo gốc. Hệ thống hoàn toàn sẵn sàng chuyển tiếp sang **Giai đoạn 2 – Chuẩn hóa snapshot và tạo state**.
