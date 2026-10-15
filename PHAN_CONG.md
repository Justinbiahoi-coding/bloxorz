# Phân công 5 người – Làm sản phẩm Bloxorz Solver

Phạm vi: chỉ phần **sản phẩm** (game, GUI, solver, thực nghiệm). Báo cáo và video chia sau.

Nguyên tắc: mỗi người **sở hữu một module**, ít đụng file của nhau để tránh conflict git. Mọi người đều phải hiểu toàn bộ project (đề có thể vấn đáp ngẫu nhiên).

## Hợp đồng giao diện (chốt ngày 1, không tự ý đổi)

Engine cung cấp, solver và GUI chỉ dùng các hàm này:

```python
Stage            # tải từ JSON: lưới, start, goal, fragile, bridges, switches
State            # bất biến, hashable: vị trí + tư thế khối (hoặc 2 khối khi split),
                 # khối đang điều khiển, trạng thái đóng/mở của mọi cầu
initial_state(stage) -> State
successors(stage, state) -> list[(move, State, cost)]   # chỉ nước hợp lệ
is_goal(stage, state) -> bool
```

Solver nhận `(stage)` và trả `SolveResult(path, time, peak_memory, expanded, length)`.

## Phân công

| # | Vai trò | Việc chính | File sở hữu |
|---|---|---|---|
| 1 | **Engine lõi** (trưởng kỹ thuật) | State, bảng chuyển tư thế, hợp lệ/void, thắng, bộ nạp JSON, unit test bảng chuyển. **Chốt hợp đồng giao diện trong 2 ngày đầu.** | `bloxorz/state.py`, `bloxorz/stage.py`, `tests/test_core.py` |
| 2 | **Ô nâng cao** | Fragile, bridge (toggle/permanent), soft/heavy/split switch, tách và gộp khối, đổi khối điều khiển. Tích hợp vào `successors`. Phối hợp với #1 vì cùng đụng hàm chuyển trạng thái. | `bloxorz/tiles.py`, `tests/test_advanced.py` |
| 3 | **GUI** | pygame: vẽ bàn và các loại ô, khối ở 3 tư thế, chơi tay bằng phím, nút New Game / Restart / Solve BFS-DFS-UCS-A*, animate lời giải, hiển thị thắng/thua. | `main.py`, `bloxorz/gui.py` |
| 4 | **Solver cơ bản** | BFS, DFS (hoặc IDS), UCS với hàm chi phí không đồng đều. Khung đo thời gian, peak memory (`tracemalloc`), số nút mở rộng, độ dài lời giải dùng chung cho cả 4 solver. | `bloxorz/solvers/base.py`, `bfs.py`, `dfs.py`, `ucs.py` |
| 5 | **A\* + Thực nghiệm** | A* và heuristic (admissible theo hàm chi phí của #4). Thiết kế bộ màn test cố định 4 nhóm độ khó, script chạy thực nghiệm, xuất bảng số liệu và biểu đồ. | `bloxorz/solvers/astar.py`, `experiments.py`, `stages/*.json` |

## Tiến độ

| Giai đoạn | Mốc |
|---|---|
| Đầu | #1 xong lõi và hợp đồng giao diện (ngày 2). #2 bắt đầu fragile và bridge. #3 dựng GUI với màn mẫu. #4 viết BFS trước, rồi DFS/UCS. #5 thiết kế màn test và nghiên cứu heuristic. |
| Giữa | #2 xong 3 loại switch và split. #3 nối nút Solve và animate. #4 xong 3 solver và khung đo. #5 xong A*. Tích hợp, chạy thử toàn bộ. |
| Cuối | #5 chạy thực nghiệm trên bộ test cố định. Cả nhóm sửa lỗi và ôn vấn đáp. |

## Quy ước làm việc
- Mỗi người một nhánh `feature/<tên>`, merge vào `main` qua pull request, ít nhất một người khác xem.
- Đổi hợp đồng giao diện phải báo cả nhóm.
- Mỗi người tự giải thích được code của mình và cách nó khớp với module khác.
