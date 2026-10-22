# SLAP Agentic Architecture Simulation

Tái hiện nghiên cứu: **Rodrigo Furlan de Assis et al. (2026)**, *"Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses"*, Procedia CIRP, 146, 643–648. DOI: [10.1016/j.procir.2026.03.258](https://doi.org/10.1016/j.procir.2026.03.258).

---

## 1. Giới thiệu dự án

Mục tiêu của dự án là xây dựng một mô phỏng có thể tái lập (reproducible simulation) cho bài toán **Storage Location Assignment Problem (SLAP)** trong kho picker-to-part vận hành theo chính sách *random storage*, so sánh ba chế độ tự chủ lũy tiến:
1. **Heuristic Agent:** Tối thiểu hóa mức tăng Mixing Index ($\Delta MI$) kết hợp thưởng độ tương thích size.
2. **Supervised Agent:** Tái sử dụng logic heuristic kết hợp cơ chế kiểm duyệt tự động (auto-approve khi $\Delta MI \le 0$; chuyển sang `pending_manual` khi cần xác nhận của người vận hành).
3. **Adaptive Agent:** Đánh giá vị trí theo hàm utility đa tiêu chí ($U_l = w^T x_l$) và học cập nhật trọng số online qua gradient descent dựa trên reward quan sát được.

---

## 2. Cấu trúc thư mục dự án (Project Structure)

Dự án được xây dựng bám sát theo **Mục 5 - Kiến trúc chương trình đề xuất** trong [SLAP-agentic-architecture Plan.md](SLAP-agentic-architecture%20Plan.md):

```text
slap-agentic-architecture/
├── README.md
├── requirements.txt
├── configs/
│   ├── base.yaml                    # Tham số mô phỏng chính thức (paper & giả định)
│   └── sensitivity.yaml             # Cấu hình 8 kịch bản phân tích độ nhạy (S1 - S8)
├── data/
│   ├── raw/                         # 9 CSV gốc từ kho dữ liệu; không chỉnh sửa trực tiếp
│   ├── interim/                     # CSV trung gian chuẩn hóa, mapping vị trí / SKU
│   └── processed/                   # State snapshot và luồng sự kiện 10.000 inbound_events.csv
├── src/
│   ├── __init__.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loaders.py               # Xử lý delimiter/encoding từng file CSV
│   │   ├── cleaning.py              # Trim chuỗi, parse 18 ô (Reference;Size), chuẩn hóa số
│   │   ├── validation.py            # Kiểm tra ràng buộc khóa, null, capacity, SKU catalog
│   │   └── event_generator.py       # Sinh chuỗi 10.000 inbound events tái lập (seed cố định)
│   ├── model/
│   │   ├── __init__.py
│   │   ├── warehouse_state.py       # Biểu diễn trạng thái kho (LocationState, WarehouseState)
│   │   ├── metrics.py               # Tính toán MI, Delta MI, Critical Rate (>0.8), SKU Dispersion
│   │   └── allocation.py            # Đánh giá phân bổ đơn vị trí và chia lô (split look-ahead)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py            # Vòng lặp Perception -> Decision -> Action thống nhất
│   │   ├── heuristic_agent.py       # Heuristic Agent (greedy score)
│   │   ├── supervised_agent.py      # Supervised Agent (approval gate)
│   │   └── adaptive_agent.py        # Adaptive Agent (multi-criteria utility & online learning)
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── runner.py                # Chạy một agent trên event stream
│   │   ├── experiment.py            # Điều phối chạy so sánh 3 mode trên cùng điều kiện
│   │   └── logging.py               # Ghi ActionLog chi tiết và metric snapshots định kỳ
│   └── reporting/
│       ├── __init__.py
│       ├── tables.py                # Xuất bảng tổng hợp kết quả (table_final_metrics.csv)
│       ├── plots.py                 # Vẽ biểu đồ MI, cumulative actions, critical locations
│       └── summary.py               # Tổng hợp so sánh với mốc công bố trong paper
├── tests/
│   ├── __init__.py
│   ├── test_data_validation.py      # Kiểm tra parser và validation logic
│   ├── test_mixing_index.py         # Kiểm thử các ca biên của Mixing Index (0, 0.5, 17/18, ...)
│   ├── test_capacity_constraints.py # Kiểm tra ràng buộc sức chứa (18 slot), giải phóng 20%
│   ├── test_allocation.py           # Kiểm thử phân bổ đơn vị trí và split allocation
│   └── test_reproducibility.py      # Kiểm thử tính tất định và khả năng tái lập của event stream
├── outputs/
│   ├── logs/                        # File log chi tiết từng action của từng agent
│   ├── metrics/                     # Chuỗi giá trị MI và snapshot theo thời gian
│   ├── figures/                     # Đồ thị so sánh xuất bản (fig_mi_over_time.png, ...)
│   └── tables/                      # Bảng kết quả định lượng cuối kỳ
└── notebooks/
    ├── 01_data_audit.ipynb          # Kiểm kê dữ liệu, đối chiếu baseline theo tầng z
    └── 02_result_analysis.ipynb     # Phân tích đường cong hội tụ và đối chiếu paper
```

---

## 3. Cài đặt môi trường

Yêu cầu: Python 3.10 trở lên.

```bash
# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

---

## 4. Chạy kiểm thử (Unit Tests)

Bộ unit test được thiết kế theo **Mục 8** của Kế hoạch:
- Kiểm thử các đặc tính toán học của Mixing Index.
- Kiểm thử tính bất biến về sức chứa vị trí ($\le 18$) và không âm kho.
- Kiểm thử phân bổ đơn và phân bổ chia lô (split look-ahead).
- Kiểm thử tính tất định của Heuristic Agent và tính tái lập của Event Generator.

Chạy toàn bộ unit test:

```bash
pytest tests/ -v
```

---

## 5. Các mốc kết quả đối chiếu với Paper

| Cấu hình | MI trung bình sau 10.000 sự kiện (Paper) | Tỷ lệ vị trí có MI > 0,8 (Paper) |
|---|---:|---:|
| **Baseline – Random** | 0,918 | 100,00% |
| **Heuristic** | 0,830 | 99,66% |
| **Supervised** | 0,884 | 99,71% |
| **Adaptive** | 0,822 | 99,48% |

> **Lưu ý triển khai:** Dữ liệu thực tế có 600 vị trí ở phạm vi $z \in \{3, 4\}$ với dải size $4 - 16$ và MI ban đầu $\approx 0,9136$ (sát nhất với mô tả paper). Chi tiết các giả định chuyển đổi được quy định tại `configs/base.yaml` và `configs/sensitivity.yaml`.
