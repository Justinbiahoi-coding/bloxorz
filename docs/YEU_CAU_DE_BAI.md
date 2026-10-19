# Project 1 – Bloxorz Solver (CSC14003 – Nhập môn Trí tuệ nhân tạo)

Bài tập **nhóm**, thời lượng khoảng 3 tuần. Nguồn: `AI - Project 1.pdf`.

## 1. Giới thiệu

Bloxorz là game xoay khối 1×1×2 trên sàn gồm các ô vuông. Mục tiêu: làm khối **rơi đứng** vào ô đích (goal hole). Lăn khối ra khỏi bàn là thua.

Game phù hợp để thực hành BFS, DFS, UCS, A*: quan sát đầy đủ (fully observable), xác định (deterministic), và **tư thế khối là một phần của state**, nên rất hợp để thiết kế heuristic admissible.

## 2. Luật chơi

### 2.1 Bố cục
Màn chơi là lưới ô vuông hữu hạn. Mỗi ô là một trong:
- **Floor tile**: ô sàn bình thường, khối đứng được.
- **Empty cell (void)**: không có sàn; nếu bất kỳ phần nào của khối nằm trên void thì khối rơi, nước đi **không hợp lệ**.
- **Goal hole**: ô đích duy nhất; thắng khi khối rơi vào đây.

Khối bắt đầu ở tư thế **đứng** trên một ô xuất phát chỉ định.

### 2.2 Tư thế khối (3 loại)
- **Standing**: chiếm 1 ô (r, c).
- **Lying horizontally**: chiếm (r, c) và (r, c+1).
- **Lying vertically**: chiếm (r, c) và (r+1, c).

### 2.3 Nước đi
Mỗi lượt lăn theo 1 trong 4 hướng: **Up, Down, Left, Right**.
- Khối đứng → lăn thành nằm trên 2 ô theo hướng lăn.
- Khối nằm **dọc theo** hướng lăn → dựng đứng lên 1 ô.
- Khối nằm **vuông góc** hướng lăn → lăn ngang, vẫn nằm, dịch 1 ô.

Nước đi **bất hợp lệ** nếu sau khi lăn, có ô nào của khối là void hoặc nằm ngoài bàn (khối luôn phải được đỡ hoàn toàn bởi ô sàn).

### 2.4 Chiến thắng
Thắng khi khối rơi vào goal hole, chỉ xảy ra khi khối **đứng** trên ô goal. Khối chỉ nằm vắt qua ô goal thì **không** thắng.

### 2.5 Ô nâng cao
- **Fragile tile (ô cam, dễ vỡ)**: chỉ chịu được khi khối đang **nằm**. Khối **đứng** lên thì ô vỡ và khối rơi. Khối được phép nằm vắt qua ô dễ vỡ.
- **Bridge (cầu)**: ô có trạng thái đóng/mở do công tắc điều khiển. Cầu **đóng** = như void; cầu **mở** = như sàn thường. Mỗi công tắc liên kết với một hoặc nhiều cầu.

**3 loại công tắc:**
| Loại | Điều kiện kích hoạt |
|---|---|
| Soft (bát giác/tròn) | Bất kỳ phần nào của khối đè lên, đứng hay nằm đều được |
| Heavy (hình X) | Chỉ khi khối **đứng** trên nó; nằm thì không kích hoạt |
| Split (hình ngoặc "( )") | Chỉ khi khối **đứng** trên nó; dịch chuyển khối đến vị trí định sẵn và **tách thành 2 khối 1×1×1** |

**Hiệu ứng lên cầu** khi công tắc kích hoạt:
- **Toggle**: mỗi lần kích hoạt đảo trạng thái đóng/mở.
- **Permanent**: cầu được đặt cố định ở một trạng thái sau khi kích hoạt.

**Tách khối (block splitting):**
- Hai khối con được điều khiển **từng khối một** (ví dụ chuyển bằng phím cách).
- Hai khối **gộp lại** thành khối 1×1×2 khi nằm ở hai ô kề nhau.
- Một khối con có thể kích hoạt soft switch, nhưng **không** kích hoạt được heavy switch và **không** hoàn thành màn chơi.

## 3. Yêu cầu chung
- Mã nguồn bằng **Python**.
- Được dùng thư viện hỗ trợ (GUI, cấu trúc dữ liệu), nhưng **phải tự cài đặt các thuật toán tìm kiếm**.
- Không giới hạn cách tổ chức code, nhưng phải chuyên nghiệp, rõ ràng.

## 3.1 Cài đặt lại game (20 điểm)
**Bắt buộc có GUI** (web hoặc desktop).

**Core mechanics (10đ):** bàn có ô sàn, void, goal; khối 1×1×2 với 3 tư thế; 4 nước lăn với chuyển tư thế đúng; phát hiện nước đi sai (rơi khỏi bàn/qua void); phát hiện thắng (khối đứng ở goal).

**Advanced tiles (10đ):** ô fragile, bridge, đủ 3 loại công tắc (soft, heavy, split, gồm tách/gộp khối và cả hai kiểu hiệu ứng cầu). **Các solver cũng phải xử lý đúng các ô này.**

Lưu ý (F.Y.I.):
- Cài và unit-test sớm bảng chuyển tư thế: mỗi cặp (orientation, direction) ánh xạ xác định sang (orientation, position) mới.
- **State phải gồm trạng thái đóng/mở của mọi cầu**, không chỉ vị trí và tư thế khối. Cùng vị trí khối nhưng khác cấu hình cầu là **state khác nhau**.
- Được tự thiết kế màn chơi hoặc dựng lại màn kinh điển. Cung cấp **định dạng text/JSON đơn giản** để nạp màn, dùng chung cho mọi solver.

GUI phải hiển thị các điều khiển cơ bản (New Game, Restart, nút gọi từng solver).

## 3.2 BFS Solver (10đ)
- Cài solver dùng **Breadth-First Search**.
- Ghi nhận **Search Time, Memory Usage, Expanded Nodes, Solution Length** để phân tích ở phần thực nghiệm. Các solver sau cũng ghi nhận tương tự.

## 3.3 DFS Solver (10đ)
- Cài **Depth-First Search**. Có thể dùng **Iterative Deepening Search (IDS)** thay thế, nhưng phải ghi rõ trong báo cáo.
- Xử lý trạng thái lặp để tránh lặp vô hạn (visited set, hashing...).

## 3.4 UCS Solver (10đ)
- Cài **Uniform-Cost Search**.
- **Trong báo cáo**: định nghĩa và biện minh rõ **hàm chi phí**. Ví dụ mỗi lần lăn cost 1, hoặc chi phí khác nhau (lăn lên ô dễ vỡ "đắt" vì rủi ro, bật công tắc "rẻ"), miễn giải thích hợp lý.
- Nếu mọi nước đi cost 1 thì UCS = BFS; hàm chi phí **không đồng đều** cùng lời giải thích trực giác mới làm bài có ý nghĩa.

## 3.5 A* Solver (10đ)
- Cài **A\*** với **heuristic phù hợp** ước lượng độ gần goal.
- Gợi ý heuristic (không bắt buộc):
  - Khoảng cách Manhattan từ khối đến goal chia 2 (một lần lăn dịch tối đa 2 ô).
  - Thành phần theo tư thế: nếu khối không đứng thì cần ít nhất 1 lần lăn để đứng lên ở goal, cộng penalty nhỏ.
  - Khoảng cách "point-object" nới lỏng: bỏ qua tư thế và ràng buộc void/fragile, coi khối là một điểm trên lưới 4 hướng, lấy đường đi ngắn nhất đến goal làm cận dưới.
- **Trong báo cáo**:
  - Giải thích cách thiết kế heuristic.
  - Thảo luận heuristic có **admissible** (không đánh giá quá chi phí thật còn lại) và/hoặc **consistent**, có lập luận rõ. Heuristic phải admissible **theo hàm chi phí bạn chọn**.

## 3.6 Báo cáo (30 điểm)
File **PDF** được định dạng tốt, gồm:

**Project Planning and Task Distribution**
- Ghi trách nhiệm từng thành viên: task được giao và **phần trăm hoàn thành**.
- Ví dụ: điểm nhóm 9.0, bạn A hoàn thành 90% thì điểm A = 9.0 × 90% = 8.1.
- Đánh giá đóng góp phải **công bằng và chính xác**.

**Algorithm Description (10đ)**
- Giải thích chi tiết từng thuật toán (BFS, DFS/IDS, UCS, A*).
- Mô tả cách hình thức hóa bài toán: biểu diễn state (gồm tư thế và cấu hình cầu), actions, transition model, goal test, hàm chi phí, heuristic, và cách tránh thăm lại state.

**Experiments (20đ)**
- Đánh giá hiệu năng trên nhiều test case (**bộ test cố định**, để so sánh công bằng giữa các thuật toán). Có thể nhóm test theo độ khó (không ô nâng cao; có fragile; có công tắc; kết hợp cả hai), và mô tả rõ các nhóm.
- Mỗi thuật toán đo: thời gian tìm kiếm, bộ nhớ (peak), số nút mở rộng, độ dài lời giải (số nước đi).
- Trình bày: **bảng** tổng hợp số liệu, **biểu đồ** so sánh các thuật toán, và **nhận xét** ưu/nhược điểm từng thuật toán.

**References và Appendix**
- Liệt kê toàn bộ tài liệu tham khảo (bài báo, sách, tutorial, repo GitHub...).
- Appendix, ví dụ: cách dùng Generative AI (LLM) trong bài, các prompt đã dùng.

## 3.7 Video (10 điểm)
Upload video demo lên **YouTube**, đặt **link công khai** trong báo cáo.

**Graphical Interface (5đ):**
- Demo GUI của chương trình.
- Thể hiện rõ bố cục: bàn với các loại ô (floor, void, goal, fragile, switch/bridge), khối ở các tư thế, các nút điều khiển (New Game, Restart, Solve BFS/DFS/UCS/A*).

**Feature Presentation (5đ):**
- Chơi tay: lăn khối, kích hoạt công tắc, thắng/thua màn.
- Chạy solver (chọn màn, chạy BFS/UCS/A*, hiển thị lời giải, có thể animate hoặc replay các nước đi).

Video cần có **phụ đề hoặc thuyết minh** (tiếng Anh hoặc tiếng Việt).

## 4. Nộp bài
- Nộp **mã nguồn + báo cáo** dưới dạng file nén (.zip, .rar), đặt tên theo `StudentID1_StudentID2_...`.
- Nếu file nén lớn hơn **20MB**: upload Google Drive và chia sẻ link.
- **Tuyệt đối không được sửa sau deadline.**

Cấu trúc thư mục mẫu:
```
StudentID1_StudentID2_...
├── Source
│   ├── main.py
│   ├── README.md          (cách chạy code)
│   ├── requirements.txt   (thư viện cần cài)
│   └── ...
└── Report.pdf             (kèm URL video demo)
```

## 5. Lưu ý
- Đây là bài tập **NHÓM**.
- Thời lượng: khoảng 3 tuần.
- **Không cấm** công cụ AI nhưng nên dùng hợp lý. Giảng viên thực hành có quyền phỏng vấn vấn đáp ngẫu nhiên các nhóm để kiểm tra hiểu biết về project.
- Mọi hình thức đạo văn, gian lận, vi phạm liêm chính học thuật sẽ bị **0 điểm cả môn**.

## Bảng điểm tổng hợp
| Hạng mục | Điểm |
|---|---|
| Cài lại game: Core mechanics | 10 |
| Cài lại game: Advanced tiles | 10 |
| BFS Solver | 10 |
| DFS Solver | 10 |
| UCS Solver | 10 |
| A* Solver | 10 |
| Báo cáo (Algorithm Description 10 + Experiments 20) | 30 |
| Video (GUI 5 + Feature 5) | 10 |
