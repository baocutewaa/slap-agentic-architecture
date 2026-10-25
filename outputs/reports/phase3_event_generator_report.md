# Báo cáo Giai đoạn 3: Sinh Chuỗi 10.000 Sự kiện Hàng nhập (Event Generator)

> **Dự án:** Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses (Assis et al., 2026)  
> **Giai đoạn:** Giai đoạn 3 – Event generator (theo `SLAP-agentic-architecture Plan.md`)  
> **Trạng thái:** Hoàn thành toàn diện, bảo đảm tính có thể tái lập (Reproducible) với seed cố định, kiểm định thống kê đạt chuẩn tuyệt đối.

---

## 1. Tổng quan Mục tiêu & Khung Sinh Sự kiện Thực nghiệm

Do tập dữ liệu CSV thô không chứa nhật ký các giao dịch hàng nhập thực tế (inbound transactions), Giai đoạn 3 thiết kế một bộ sinh sự kiện Monte Carlo chuẩn xác theo đúng mô hình hóa và giả định của Assis et al. (2026):
1. **Mô hình hóa Chuỗi Sự kiện Hàng nhập Rời rạc theo Thời gian:** Mỗi sự kiện $t \in \{1, \dots, 10.000\}$ là một bộ ba:
   $$E_t = \big(i_t, u_t, s_t\big)$$
   Trong đó: $i_t$ là mã SKU nhập kho; $u_t \in \mathbb{Z}^+$ là số lượng đơn vị của lô hàng (batch size); $s_t \in [4.0, 16.0]$ là thuộc tính kích cỡ của lô hàng.
2. **Nguyên tắc "Tái tạo Dữ liệu Dùng chung" (Single Source of Truth):** Toàn bộ chuỗi 10.000 sự kiện được sinh đúng **1 lần duy nhất** với `seed=42` và xuất ra tệp [`data/processed/inbound_events.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/data/processed/inbound_events.csv). Cả ba tác tử Heuristic, Supervised, và Adaptive đều vận hành trên cùng một chuỗi sự kiện này để đảm bảo tính công bằng khoa học trong đối chiếu.
3. **Thiết lập Chuỗi Phân tích Độ nhạy (Sensitivity Streams):** Sinh bổ sung chuỗi nhạy cảm S2 dựa trên xác suất nhu cầu đơn hàng (*Order Demand Proxy*) và các chuỗi với các hạt giống ngẫu nhiên khác nhau (`seed` $\in \{100, 2026, 777, 999\}$).

---

## 2. Thiết kế Toán học Ba Phân phối Thành phần

### 2.1. Xác suất Phân bổ Mã hàng $P(i_t = i)$ (Stock Frequency Prior)
Theo mô tả của bài báo, xác suất một SKU được nhập vào kho tỷ lệ thuận với tần suất tồn kho thực tế của SKU đó trong snapshot phạm vi chính $z \in \{3, 4\}$ (tổng cộng 10.800 ô):

$$P(i_t = i) = \frac{\text{stock\_count}_i}{\sum_{j \in \mathcal{I}} \text{stock\_count}_j}, \qquad \forall i \in \mathcal{I} = \{1, \dots, 208\}$$

- Mọi SKU trong 208 mã sản phẩm đều có xác suất xuất hiện dương ($P(i) > 0$).
- Quá trình lấy mẫu có hoàn lại (sampling with replacement) mô phỏng dòng lưu chuyển hàng hóa liên tục trong chuỗi cung ứng.

### 2.2. Kích cỡ Hàng nhập Có Điều kiện $s_t$ (Conditional Size Sampling)
Thay vì gán kích cỡ ngẫu nhiên tự do, kích cỡ $s_t$ được lấy mẫu có điều kiện phụ thuộc trực tiếp vào mã SKU $i_t$:
$$s_t \sim \text{Uniform}\big(\mathcal{S}_{i_t}\big)$$
Trong đó $\mathcal{S}_{i_t}$ là tập hợp các giá trị kích cỡ thực tế của SKU $i_t$ đã được quan sát trong kho hàng.
- **Bảo toàn ràng buộc vật lý:** 100% các giá trị $s_t$ đều nằm chính xác trong dải chuẩn **`[4.0, 16.0]`**, không có bất kỳ giá trị ngoại lai nào.

### 2.3. Khối lượng Lô hàng Nhập $u_t$ (Inbound Batch Size Proxy)
Khối lượng lô hàng $u_t$ được lấy mẫu có hoàn lại từ phân phối số lượng thực tế của các dòng có số lượng dương trong `Customer_Order.csv` (122.337 dòng hợp lệ, sau khi đã lọc và ghi log loại bỏ 33 dòng lỗi có số lượng bằng 0):
- **Tính thực tế:** Khối lượng tập trung mạnh vào các đơn hàng nhỏ lẻ, phản ánh chân thực luồng hàng thương mại điện tử và bán lẻ picker-to-part.
- **Ràng buộc an toàn:** Giá trị $u_t \le 24$, không vượt quá ngưỡng sức chứa kết hợp tối đa của hai vị trí chia lô ($2 \times 18 = 36$ ô).

---

## 3. Kiểm định Thống kê & Độ khớp Tần suất SKU

Biểu đồ dưới đây đối chiếu giữa phân phối xác suất tồn kho lý thuyết $P(i)$ và tần suất thực nghiệm thu được qua 10.000 sự kiện lấy mẫu:
- Hệ số tương quan xác định tuyến tính đạt **$R^2 = 0.9989$**, khẳng định độ hội tụ mẫu tối ưu của thuật toán Monte Carlo.
- Độ phân kỳ Kullback-Leibler giữa hai phân phối chỉ đạt **$D_{\text{KL}}(P \parallel Q) = 0.0016$ nats**, thể hiện mức sai lệch thông tin gần như triệt tiêu.

![Kiểm định Độ khớp Tần suất SKU Lý thuyết vs Thực nghiệm](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_sku_frequency_empirical_vs_theoretical.png)

*Hình 3.1: (a) Đồ thị phân tán tương quan hồi quy giữa xác suất tồn kho lý thuyết và tần suất thực nghiệm ($R^2 = 0.9989$); (b) Đối chiếu chi tiết 15 SKU có lưu lượng lớn nhất trong kho.*

Bảng thống kê 10 SKU có số lần xuất hiện nhiều nhất trong chuỗi sự kiện chính:

| Mã SKU (`Reference`) | Số ô trong Snapshot gốc | Xác suất lý thuyết $P(i)$ | Số sự kiện lấy mẫu | Tần suất thực nghiệm | Độ lệch ($\Delta P$) |
|:---|---:|---:|---:|---:|---:|
| `AHR20O` | 75 | 0.00694 | 76 | 0.00760 | +0.00066 |
| `PZUF7K` | 71 | 0.00657 | 56 | 0.00560 | -0.00097 |
| `RAUDQ6` | 71 | 0.00657 | 55 | 0.00550 | -0.00107 |
| `IYV9SV` | 70 | 0.00648 | 76 | 0.00760 | +0.00112 |
| `UU4A1K` | 70 | 0.00648 | 64 | 0.00640 | -0.00008 |
| `C5O9C9` | 66 | 0.00611 | 66 | 0.00660 | +0.00049 |
| `B24J86` | 65 | 0.00602 | 68 | 0.00680 | +0.00078 |
| `NJVZEL` | 65 | 0.00602 | 61 | 0.00610 | +0.00008 |
| `56TC1Z` | 64 | 0.00593 | 61 | 0.00610 | +0.00017 |
| `CVU3QV` | 63 | 0.00583 | 62 | 0.00620 | +0.00037 |

---

## 4. Phân tích Phân phối Khối lượng Lô hàng ($u_t$) & Kích cỡ ($s_t$)

Bảng phân bố tần suất khối lượng lô hàng nhập ($u_t$):

| Khối lượng lô ($u_t$) | Số lượng sự kiện | Tỷ lệ phần trăm | Tích lũy (%) | Diễn giải vận hành |
|---:|---:|---:|---:|:---|
| **1** | 6,798 | 67.98% | 67.98% | Đơn vị lẻ (Single unit pick) |
| **2** | 1,745 | 17.45% | 85.43% | Cặp sản phẩm (Pair units) |
| **3** | 453 | 4.53% | 89.96% | Hộp nhỏ đóng gói |
| **4** | 227 | 2.27% | 92.23% | Hộp nhỏ đóng gói |
| **5** | 401 | 4.01% | 96.24% | Hộp nhỏ đóng gói |
| **6** | 130 | 1.30% | 97.54% | Hộp nhỏ đóng gói |
| **7 – 10** | 110 | 1.10% | 98.64% | Lô hàng trung bình |
| **11 – 24** | 136 | 1.36% | 100.00% | Lô hàng lớn (kích hoạt Look-Ahead Split) |

> [!NOTE]
> Các sự kiện có khối lượng $u_t \in \{1, 2\}$ chiếm tới **85.43%** toàn bộ chuỗi sự kiện. Giá trị trung bình khối lượng là **1.8546 đơn vị/sự kiện**, tổng số đơn vị hàng cần phân bổ qua 10.000 sự kiện là **18.546 đơn vị**.

![Phân tích Phân phối Khối lượng Lô hàng Nhập](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_quantity_batch_distribution.png)

*Hình 3.2: (a) Phân phối tần suất khối lượng lô hàng nhập $u_t$; (b) Hàm phân phối tích lũy thực nghiệm (ECDF) thể hiện $85.4\%$ sự kiện có $u_t \le 2$.*

![Phân tích Phân phối Kích cỡ Hàng hóa Có Điều kiện](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_size_distribution_by_sku.png)

*Hình 3.3: (a) Phân phối kích cỡ trên 10.000 sự kiện (100% trong [4.0, 16.0]); (b) Biểu đồ hộp thể hiện phổ kích cỡ đặc trưng của 8 SKU có khối lượng nhập lớn nhất.*

---

## 5. Động lực học Tải việc & Đối chiếu với Chuỗi Độ nhạy S2

- **Độ ổn định của luồng sự kiện:** Đường trung bình trượt 200 sự kiện (rolling average) của khối lượng nhập dao động rất êm dịu quanh trục giá trị trung bình tổng thể $1.85$, không bị hiện tượng đột biến tải (workload spikes).
- **Tốc độ bao phủ danh mục (Catalog Discovery Rate):** Toàn bộ 208 SKU đều được quan sát xuất hiện ít nhất một lần chỉ sau khoảng **600 sự kiện đầu tiên**, đảm bảo các tác tử đều được tôi luyện trên toàn bộ không gian sản phẩm từ rất sớm.
- **So sánh với Chuỗi S2 (Demand Proxy):** Chuỗi S2 (sinh từ tần suất dòng đơn hàng khách) chỉ bao phủ được 182 SKU (87.5% danh mục) do có 26 SKU không có phát sinh đơn bán trong thời gian ghi nhận dữ liệu.

![Động lực học Khối lượng và Tốc độ Khám phá SKU](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_stream_reproducibility_and_sensitivity.png)

*Hình 3.4: (a) Dao động trung bình trượt 200 sự kiện của khối lượng lô hàng; (b) Đường cong tích lũy phát hiện SKU mới qua chuỗi sự kiện.*

---

## 6. Tổng kết Danh mục Kết quả & Hiện vật (Deliverables Giai đoạn 3)

Toàn bộ các hiện vật của Giai đoạn 3 đã được lưu trữ hoàn chỉnh tại các thư mục tương ứng:

| Loại hiện vật | Đường dẫn tệp tin | Mô tả kỹ thuật |
|---|---|---|
| **Báo cáo Kỹ thuật** | [`outputs/reports/phase3_event_generator_report.md`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/reports/phase3_event_generator_report.md) | Báo cáo chi tiết mô hình xác suất sinh sự kiện, kiểm định thống kê và phân tích độ nhạy. |
| **Mã nguồn Sinh Sự kiện** | [`src/data/event_generator.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/data/event_generator.py) | Lớp `EventGenerator` hỗ trợ lấy mẫu Monte Carlo, kích cỡ có điều kiện và cơ chế seed cố định. |
| **Bộ Kiểm thử Đầy đủ** | [`tests/test_reproducibility.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/tests/test_reproducibility.py) | 5 unit tests kiểm tra tính tái lập tuyệt đối của seed, 100% SKU thuộc danh mục và tính hợp lệ của size. |
| **Jupyter Notebook Trực quan** | [`notebooks/03_event_generator.ipynb`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/notebooks/03_event_generator.ipynb) | Notebook tương tác (~363 KB), thực thi sinh chuỗi sự kiện và trực quan hóa phân phối. |
| **Biểu đồ Kiểm định SKU** | [`outputs/figures/phase3_sku_frequency_empirical_vs_theoretical.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_sku_frequency_empirical_vs_theoretical.png) | Tương quan hồi quy xác suất tồn kho lý thuyết vs tần suất thực nghiệm ($R^2 = 0.9989$) và top 15 SKU. |
| **Biểu đồ Khối lượng Lô hàng** | [`outputs/figures/phase3_quantity_batch_distribution.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_quantity_batch_distribution.png) | Phân phối tần suất batch size $u_t$ và hàm phân phối tích lũy ECDF ($85.4\%$ có $u_t \le 2$). |
| **Biểu đồ Phân phối Kích cỡ** | [`outputs/figures/phase3_size_distribution_by_sku.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_size_distribution_by_sku.png) | Phân phối kích cỡ trên toàn bộ 10.000 sự kiện ($[4.0, 16.0]$) và biểu đồ hộp theo SKU. |
| **Biểu đồ Tải việc & Tốc độ Khám phá** | [`outputs/figures/phase3_stream_reproducibility_and_sensitivity.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase3_stream_reproducibility_and_sensitivity.png) | Đường trung bình trượt 200 sự kiện và đường cong tích lũy độ phong phú SKU (bão hòa 208 SKU). |
| **Bảng Tần suất Khối lượng** | [`outputs/tables/event_stream_quantity_distribution.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/event_stream_quantity_distribution.csv) | Tần suất xuất hiện và tỷ lệ phần trăm của từng mức batch size $u_t \in [1, 24]$. |
| **Bảng Thống kê Tổng hợp Stream** | [`outputs/tables/event_stream_summary.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/event_stream_summary.csv) | Chỉ số tóm tắt: 10.000 sự kiện, 18.546 đơn vị, trung bình 1.8546, dải size $[4.0, 16.0]$. |
| **Bảng Tần suất Chi tiết 208 SKU** | [`outputs/tables/event_stream_top_skus.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/event_stream_top_skus.csv) | Bảng dữ liệu 208 SKU: tồn kho gốc, xác suất lý thuyết, số lần lấy mẫu thực nghiệm, sai số. |
| **Bảng So sánh Chuỗi Độ nhạy** | [`outputs/tables/phase3_sensitivity_streams_comparison.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/phase3_sensitivity_streams_comparison.csv) | So sánh các thông số giữa chuỗi chính, chuỗi S2 (Demand Proxy) và các hạt giống seeds khác nhau. |
| **Bảng Chỉ số Đo lường Thống kê** | [`outputs/metrics/metrics_phase3_events.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/metrics/metrics_phase3_events.csv) | 12 chỉ số thống kê định lượng cốt lõi: Chi-squared, $D_{\text{KL}}$, $R^2$, mean/std batch-size, catalog validity. |
| **Nhật ký Giám sát Sinh Chuỗi** | [`outputs/logs/phase3_generation_audit_log.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/logs/phase3_generation_audit_log.csv) | Nhật ký kiểm toán chu kỳ 500 sự kiện xác nhận tính toàn vẹn, tính không âm và biên độ kích cỡ. |
| **Chuỗi Sự kiện Chính (Processed)** | [`data/processed/inbound_events.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/data/processed/inbound_events.csv) | Tệp CSV chuẩn chứa 10.000 dòng sự kiện (Seed=42) được dùng chung tuyệt đối cho 3 tác tử. |
| **Chuỗi Sự kiện Nhu cầu S2** | [`data/processed/inbound_events_demand_proxy_seed42.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/data/processed/inbound_events_demand_proxy_seed42.csv) | Chuỗi 10.000 sự kiện phục vụ phân tích độ nhạy S2 theo nhu cầu đơn hàng của khách. |

---

## 7. Sẵn sàng Chuyển giao sang Giai đoạn 4

Chuỗi sự kiện 10.000 dòng đã được chốt cố định và kiểm định đạt chuẩn 100%. Hệ thống đã hội đủ mọi tiền đề đầu vào để chuyển sang **Giai đoạn 4 – Cài đặt Mixing Index và Allocation Engine**.
