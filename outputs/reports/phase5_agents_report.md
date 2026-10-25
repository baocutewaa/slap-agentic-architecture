# Báo cáo Giai đoạn 5: Triển khai Ba Chế độ Quyết định (Heuristic, Supervised, Adaptive)

> **Dự án:** Agentic Architecture for Progressive Autonomous Storage Location Assignment in Warehouses (Assis et al., 2026)  
> **Giai đoạn:** Giai đoạn 5 – Triển khai ba mode (theo `SLAP-agentic-architecture Plan.md`)  
> **Trạng thái:** Hoàn thành toàn diện, 100% unit tests đạt chuẩn (53/53 passed), đã thực thi và kết xuất trực quan đầy đủ trong notebook, biểu đồ và báo cáo kỹ thuật.

---

## 1. Tổng quan Mục tiêu Giai đoạn 5

Giai đoạn 5 hiện thực hóa kiến trúc ra quyết định trung tâm (*Central Agent Architecture*) cho bài toán phân bổ vị trí lưu trữ hàng hóa (SLAP). Hệ thống triển khai thống nhất ba chế độ tự chủ lũy tiến (*progressive autonomy*) theo đúng mô tả của bài báo:

1. **Chế độ 1 – Heuristic Agent:** Ra quyết định tham lam (*greedy*) dựa trên việc cực tiểu hóa mức tăng độ hỗn tạp $\Delta MI$, kết hợp điểm thưởng tương thích kích cỡ $\gamma$ và cơ chế nhìn trước chia lô (*Look-Ahead Split*).
2. **Chế độ 2 – Supervised Agent:** Kế thừa bộ đánh giá của Heuristic nhưng thiết lập cổng an toàn tự động (*Safety Approval Gate*). Chỉ tự động thực thi các hành động gom hàng không làm tăng hỗn tạp kho ($\Delta MI \le 0$); các trường hợp còn lại ($\Delta MI > 0$) chuyển sang trạng thái chờ giám sát (*pending_manual*) và bảo toàn trạng thái kho tuyệt đối.
3. **Chế độ 3 – Adaptive Agent:** Mô hình hóa hàm lợi ích đa tiêu chí $U_l = w^T x_l$ trên vector đặc trưng 6 chiều, tích hợp cơ chế khám phá $\epsilon$-greedy và thuật toán học trực tuyến (*online learning*) cập nhật trọng số theo đạo hàm gradient sau mỗi sự kiện nhập hàng.

---

## 2. Kiến trúc Vòng lặp Agentic Thống nhất (Unified Lifecycle)

Tất cả các agent đều kế thừa từ lớp cơ sở [`BaseAgent`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/base_agent.py#L36-L107), vận hành theo chu trình 7 bước khép kín và có thể kiểm toán toàn diện:

$$\text{Perception} \longrightarrow \text{Candidate Set} \longrightarrow \text{Evaluation} \longrightarrow \text{Decision} \longrightarrow \text{Supervision} \longrightarrow \text{Action} \longrightarrow \text{Learning}$$

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CHU TRÌNH RA QUYẾT ĐỊNH AGENTIC                        │
└─────────────────────────────────────────────────────────────────────────────┘
  1. PERCEPTION   : Đọc trạng thái kho hiện tại, dung lượng trống, SKU & size
  2. CANDIDATES   : Tạo tập ứng viên khả thi (vị trí đơn + cặp chia lô Top-30)
  3. EVALUATION   : Tính ΔMI, Score (Heuristic/Supervised) hoặc Utility (Adaptive)
  4. DECISION     : Chọn phương án tối ưu (hoặc ε-greedy exploration ở Adaptive)
  5. SUPERVISION  : Cổng giám sát (chỉ kích hoạt ở Supervised: Auto-approve vs Pending)
  6. ACTION       : Cập nhật nguyên tử vào kho nếu thực thi; giữ nguyên nếu Pending
  7. LEARNING     : Cập nhật trọng số online theo reward r_t (chỉ có ở Adaptive)
  8. LOGGING      : Ghi nhật ký đầy đủ (ActionDecision, weights, mi_before/after)
```

---

## 3. Chi tiết Cài đặt Ba Chế độ Quyết định

### 3.1. Chế độ 1 – Heuristic Agent
Cài đặt tại [`src/agents/heuristic_agent.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/heuristic_agent.py):
- **Hàm mục tiêu:** Tối đa hóa điểm số Heuristic:
  $$Score_l = -\Delta MI_l + \gamma \cdot \mathbb{1}(s_t \text{ đã có tại } l)$$
  Trong đó $\gamma = 0.1$ là hệ số thưởng khi kích cỡ $s_t$ đã tồn tại trong vị trí.
- **Tập ứng viên:** Đánh giá cả các vị trí đơn lẻ thỏa mãn sức chứa $a_{l,t} \ge u_t$ và các cặp chia lô nhìn trước (Look-Ahead Split) trong tập Top-30 ứng viên tiềm năng nhất.
- **Thực thi:** Lựa chọn ứng viên có điểm số cao nhất và thực thi giao dịch nguyên tử vào kho thông qua `apply_action`.

### 3.2. Chế độ 2 – Supervised Agent
Cài đặt tại [`src/agents/supervised_agent.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/supervised_agent.py):
- **Cổng an toàn tự chủ:**
  $$\text{Quyết định} = \begin{cases} \text{Auto-Approved (Executed)}, & \text{nếu } \Delta MI_l \le 0 \text{ (Gom hàng / Bảo toàn)} \\ \text{Pending Manual (No State Change)}, & \text{nếu } \Delta MI_l > 0 \text{ (Tăng hỗn tạp)} \end{cases}$$
- **Đảm bảo bất biến:** Khi hành động ở trạng thái `pending_manual`, kho hàng **không bị thay đổi dù chỉ 1 slot**. Số lượng hàng tồn, dung lượng trống và chỉ số MI toàn kho được bảo lưu hoàn hảo.
- **Phân tích độ nhạy (Sensitivity):** Hỗ trợ tham số cấu hình `operator_fallback = "always_approve"` nhằm mô phỏng kịch bản người vận hành phê duyệt tất cả các đề xuất khả thi.

### 3.3. Chế độ 3 – Adaptive Agent
Cài đặt tại [`src/agents/adaptive_agent.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/adaptive_agent.py):
- **Hàm Utility Đa tiêu chí Tuyến tính:**
  $$U_l = w^T x_l = \sum_{k=1}^6 w_k x_{l,k}$$
- **Vector Đặc trưng 6 Chiều ($x_l$):**
  $$x_l = \left[ -\Delta MI_l,\; \mathbb{1}(i_t \in l),\; \mathbb{1}(s_t \text{ tương thích}),\; \frac{a_{l,t}}{C_l},\; 1 - MI_l^{before},\; \text{Dispersion}(i_t) \right]$$
  Đối với phân bổ chia lô, các chiều được tổng hợp có trọng số theo tỷ lệ số lượng: $x_k^{split} = \frac{q_1}{u_t} x_k(l_1) + \frac{q_2}{u_t} x_k(l_2)$.
- **Chiến lược Lựa chọn $\epsilon$-greedy:**
  - Với xác suất $1 - \epsilon$ ($\epsilon = 0.1$ theo tham số bài báo): Chọn ứng viên có Utility cao nhất.
  - Với xác suất $\epsilon$: Chọn ngẫu nhiên một ứng viên trong Top-$K$ ($K=30$) để duy trì khả năng khám phá (*exploration*).
- **Học Trực tuyến (Online Gradient Update):**
  Sau khi thực thi hành động, quan sát phần thưởng $r_t = \overline{MI}_{before} - \overline{MI}_{after}$ và cập nhật trọng số:
  $$w \leftarrow w - \eta \left[ 2 (\hat{U}_t - r_t) \bar{x}_t + \lambda w \right]$$
  với tốc độ học $\eta = 0.05$, hệ số chính quy hóa $\lambda = 0.01$, $\bar{x}_t = x_t / (\|x_t\|_2 + 10^{-8})$, sau đó chuẩn hóa vector trọng số $\|w\|_2 = 1$ để tránh bùng nổ thang đo.

---

## 4. Kết quả Thử nghiệm Thực tế trên Chuỗi Sự kiện Pilot (50 Events)

Ba chế độ đã được chạy thử nghiệm trên cùng chuỗi 50 sự kiện đầu tiên từ `inbound_events.csv`, bắt đầu từ cùng một snapshot kho thực tế sau giải phóng 20% dung lượng ($z \in \{3, 4\}$, 600 vị trí, $MI_{initial} = 0.9015$).

### 4.1. Bảng Số liệu Đối chiếu Ba Chế độ

| Chỉ số Đánh giá | Heuristic Agent | Supervised Agent (Main) | Adaptive Agent | Ghi chú & Diễn giải |
|---|:---:|:---:|:---:|:---|
| **Số sự kiện xử lý** | 50 | 50 | 50 | Cùng một chuỗi sự kiện pilot |
| **Số hành động thực thi** | **50** (100.0%) | **50** (100.0%) | **50** (100.0%) | Cả 50 sự kiện đều tìm được vị trí gom hàng $\Delta MI \le 0$ |
| **Số hành động Pending** | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | 100% thỏa mãn cổng Auto-approve |
| **Số lần chia lô (Look-Ahead Split)** | **15** lần (30.0%) | **15** lần (30.0%) | **2** lần (4.0%) | Heuristic/Supervised tích cực chia lô để gom hàng |
| **Mixing Index ban đầu** | 0.9015 | 0.9015 | 0.9015 | Trạng thái ban đầu giống hệt nhau |
| **Mixing Index kết thúc** | **0.8926** | **0.8926** | **0.8987** | MI giảm rõ rệt ngay từ 50 sự kiện đầu |
| **Mức giảm MI ($\Delta MI_{global}$)** | **-0.0089** | **-0.0089** | **-0.0028** | Heuristic tập trung 100% vào giảm MI; Adaptive cân bằng đa mục tiêu |
| **Thời gian xử lý trung bình** | **13.54 ms/event** | **14.07 ms/event** | **137.49 ms/event** | Adaptive tính thêm vector 6D & online learning |

> [!NOTE]
> Trong 50 sự kiện đầu tiên, do kho vừa giải phóng 20% capacity (2,160 slots trống), các vị trí có sẵn SKU nhập hàng còn rất nhiều chỗ trống. Cả Heuristic và Supervised đều dễ dàng tìm được các phương án gom hàng đạt $\Delta MI \le 0$, dẫn đến tỷ lệ auto-approved đạt 100% ở pilot. Khi kho dần đầy ở các sự kiện sau (Giai đoạn 6), Supervised sẽ bắt đầu kích hoạt cơ chế `pending_manual` khi hết vị trí gom hàng an toàn.

---

### 4.2. Phân tích Tiến hóa Trọng số của Adaptive Agent

Bắt đầu từ vector trọng số đồng đều đã chuẩn hóa $w_0 = [0.4082, 0.4082, 0.4082, 0.4082, 0.4082, 0.4082]$, qua 50 sự kiện nhập hàng, thuật toán gradient descent online đã điều chỉnh trọng số như sau:

| Chiều Đặc trưng ($x_{l,k}$) | Trọng số Ban đầu $w_0$ | Trọng số Kết thúc $w_{50}$ | Độ Biến thiên $\Delta w$ | Ý nghĩa Vận hành |
|:---|:---:|:---:|:---:|:---|
| **$-\Delta MI_l$ (Lợi ích giảm hỗn tạp)** | 0.4082 | **0.4081** | -0.0001 | Giữ vai trò nền tảng quan trọng |
| **$\mathbb{1}(i_t \in l)$ (Đã có SKU này)** | 0.4082 | **0.4081** | -0.0001 | Khuyến khích gom cụm SKU |
| **$\mathbb{1}(s_t \text{ tương thích})$ (Size phù hợp)** | 0.4082 | **0.4080** | -0.0002 | Trọng số tương thích kích cỡ |
| **$a_{l,t} / C_l$ (Tỷ lệ dung lượng trống)** | 0.4082 | **0.4084** | **+0.0002** | Ưu tiên chọn vị trí còn nhiều sức chứa |
| **$1 - MI_l^{before}$ (Độ thuần nhất)** | 0.4082 | **0.4086** | **+0.0004** | **Tăng mạnh nhất:** Bảo vệ các vị trí thuần nhất |
| **$\text{Dispersion}(i_t)$ (Tỷ lệ phân tán SKU)** | 0.4082 | **0.4083** | **+0.0001** | Hạn chế SKU bị phân tán quá nhiều vị trí |

Quá trình học diễn ra ổn định tuyệt đối:
- Chuẩn Euclidean $\|w\|_2$ luôn được bảo toàn chính xác bằng **1.0000**.
- Không xuất hiện bất kỳ giá trị `NaN`, `Inf` hay hiện tượng bùng nổ gradient (*gradient explosion*).
- Sai số dự đoán $|\hat{U}_t - r_t|$ có xu hướng hội tụ giảm dần theo thời gian.

---

## 5. Kiểm định Tính Đúng đắn theo Mục 8.3 của Plan

Toàn bộ các kiểm thử bắt buộc tại Mục 8.3 của Plan đã được lập trình thành unit tests trong [`tests/test_agents.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/tests/test_agents.py) và đạt chuẩn **100% (53/53 passed)**:

1. **Tính tất định (Determinism):** Khi tắt yếu tố ngẫu nhiên ($\epsilon = 0$), Heuristic và Adaptive chạy trên cùng trạng thái kho và cùng sự kiện luôn đưa ra **100% quyết định giống hệt nhau** từng slot.
2. **Không vi phạm sức chứa:** Sau mỗi hành động của bất kỳ agent nào, sức chứa từng vị trí $\sum_i n_{i,l} \le 18$ và $free \ge 0$ luôn được bảo đảm tuyệt đối.
3. **Không đọc trước tương lai (Causality Invariant):** Agent chỉ tiếp nhận duy nhất sự kiện hiện tại $e_t$ và trạng thái kho $S_t$; hoàn toàn không truy cập hay biết trước các sự kiện $t+1, \dots, T$.
4. **Bảo toàn trạng thái khi Pending:** Trong chế độ Supervised, khi phát sinh quyết định `pending_manual`, số lượng hàng tồn và cấu trúc slot của kho được chứng minh **bảo toàn nguyên vẹn 100%**.

---

## 6. Danh mục Hiện vật Đã Kết xuất (Deliverables)

| Loại hiện vật | Đường dẫn tệp tin | Mô tả kỹ thuật |
|---|---|---|
| **Lớp Agent Cơ sở** | [`src/agents/base_agent.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/base_agent.py) | Lớp trừu tượng `BaseAgent` với chu trình thống nhất và cấu trúc dữ liệu `ActionDecision`. |
| **Heuristic Agent** | [`src/agents/heuristic_agent.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/heuristic_agent.py) | Cài đặt `HeuristicAgent` tối đa hóa điểm số Heuristic và hỗ trợ Look-Ahead Split. |
| **Supervised Agent** | [`src/agents/supervised_agent.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/supervised_agent.py) | Cài đặt `SupervisedAgent` với cổng an toàn tự chủ $\Delta MI \le 0$ và hỗ trợ `always_approve`. |
| **Adaptive Agent** | [`src/agents/adaptive_agent.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/agents/adaptive_agent.py) | Cài đặt `AdaptiveAgent` với utility đa tiêu chí, chiến lược $\epsilon$-greedy và học trực tuyến online. |
| **Mô phỏng & Logging** | [`src/simulation/runner.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/simulation/runner.py)<br>[`src/simulation/logging.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/src/simulation/logging.py) | Động cơ chạy mô phỏng `SimulationRunner` và bộ ghi nhật ký hành động `SimulationLogger`. |
| **Bộ Kiểm thử Đầy đủ** | [`tests/test_agents.py`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/tests/test_agents.py) | 8 unit tests chuyên sâu cho 3 chế độ agent (nâng tổng số test của dự án lên **53/53 tests passed**). |
| **Jupyter Notebook Trực quan** | [`notebooks/05_agents_implementation.ipynb`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/notebooks/05_agents_implementation.ipynb) | Notebook tương tác hoàn chỉnh (~953 KB), đã pre-execute toàn bộ kết quả, biểu đồ và bảng phân tích. |
| **Đồ thị Heuristic Pilot** | [`outputs/figures/phase5_heuristic_pilot_trajectory.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase5_heuristic_pilot_trajectory.png) | Quỹ đạo Global MI, phân phối $\Delta MI$ và tỷ lệ Single vs Split của Heuristic. |
| **Đồ thị Cổng Giám sát** | [`outputs/figures/phase5_supervised_gate_distribution.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase5_supervised_gate_distribution.png) | Tỷ lệ Auto-Approved vs Pending và so sánh quỹ đạo MI giữa 2 chính sách giám sát. |
| **Đồ thị Học Trực tuyến** | [`outputs/figures/phase5_adaptive_weights_evolution.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase5_adaptive_weights_evolution.png) | Quá trình tiến hóa của 6 trọng số $w$ và tương quan Utility vs $\Delta MI$. |
| **Đồ thị So sánh Đối chiếu** | [`outputs/figures/phase5_cross_agent_comparison.png`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/figures/phase5_cross_agent_comparison.png) | Đồ thị so sánh trực tiếp quỹ đạo MI, trạng thái hành động, runtime và mức giảm hỗn tạp tích lũy. |
| **Bảng Thống kê Tổng hợp** | [`outputs/tables/phase5_pilot_comparison_summary.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/phase5_pilot_comparison_summary.csv) | Bảng dữ liệu số liệu đối chiếu 3 mode trên chuỗi pilot 50 sự kiện. |
| **Bảng Tiến hóa Trọng số Thích nghi** | [`outputs/tables/phase5_adaptive_weights_evolution.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/tables/phase5_adaptive_weights_evolution.csv) | Chi tiết tiến trình biến thiên 6 trọng số $w$ và utility của Adaptive Agent qua từng sự kiện pilot. |
| **Bảng Chỉ số Đo lường So sánh Tác tử** | [`outputs/metrics/metrics_phase5_agents_summary.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/metrics/metrics_phase5_agents_summary.csv) | 24 chỉ số đo lường so sánh đối đầu giữa 3 tác tử (tỷ lệ thực thi, delta MI, runtime trung bình). |
| **Chuỗi Chỉ số Thời gian Từng Agent** | [`outputs/metrics/metrics_heuristic.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/metrics/metrics_heuristic.csv)<br>[`outputs/metrics/metrics_supervised.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/metrics/metrics_supervised.csv)<br>[`outputs/metrics/metrics_adaptive.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/metrics/metrics_adaptive.csv) | Chỉ số giám sát thời gian thực từng bước (Average MI, Critical Locations %, Executed Actions). |
| **Nhật ký Quyết định Chi tiết** | [`outputs/logs/actions_heuristic.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/logs/actions_heuristic.csv)<br>[`outputs/logs/actions_supervised.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/logs/actions_supervised.csv)<br>[`outputs/logs/actions_adaptive.csv`](file:///c:/Users/Admin/Desktop/NCKH/SLAP/slap-agentic-architecture/outputs/logs/actions_adaptive.csv) | Nhật ký từng bước hành động của từng agent (status, allocation, $\Delta MI$, weights, runtime). |

---

## 7. Đánh giá Tính Sẵn sàng cho Giai đoạn 6

Cả ba chế độ quyết định đều đã hoàn thiện, hoạt động ổn định và sẵn sàng cho **Giai đoạn 6 – Chạy thí nghiệm chính**:
- Chạy lần lượt cả 3 chế độ (Heuristic, Supervised, Adaptive) trên toàn bộ chuỗi **10.000 sự kiện** chuẩn (`inbound_events.csv`).
- Thu thập đầy đủ dữ liệu quỹ đạo MI, tỷ lệ vị trí nguy cơ ($MI > 0.8$), và cơ cấu hành động thực thi để chuẩn bị đối chiếu trực tiếp với kết quả công bố của bài báo trong Giai đoạn 7.
