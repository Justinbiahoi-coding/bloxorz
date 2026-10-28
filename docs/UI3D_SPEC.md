# Đặc tả thiết kế lại UI 3D

Nhánh: `feat/ui3d-redesign`. Cập nhật: 28/10/2026.

Mục tiêu: bản 3D có đủ mọi thứ bản 2D và Youmei đã làm, đáp ứng đủ yêu cầu GUI của đề, với một phong cách thống nhất ăn khớp với đồ họa hiện có (thành phố zombie về đêm, con mèo, thùng rác).

## 1. Tính năng của Youmei: giữ đủ 100%

Chỉ thay giao diện, không bớt tính năng nào.

| # | Tính năng (`feat/advanced-mechanisms`) | Màn hình mới đảm nhận |
|---|---|---|
| Y1 | Menu chính: Tower, Free Play, Algorithms, Exit | Main Menu |
| Y2 | Free Play chia 2 chế độ **Normal** (không ô nâng cao) / **Advanced** (tutorial 54–57 trước, rồi các màn nâng cao) | Level Select |
| Y3 | Chọn màn: Prev/Next, phím ←/→, Enter/Space để bắt đầu, Esc quay lại | Level Select |
| Y4 | Tên tutorial và mẹo cho từng tutorial | Level Select + HUD |
| Y5 | Màn hình "Loading…" khi dựng màn | Loading |
| Y6 | Chơi Free Play: phím mũi tên lăn, Space đổi khối khi tách, R chơi lại, Esc về menu, F toàn màn hình, nhớ trước 1 nước khi đang lăn | Gameplay + HUD |
| Y7 | Hiệu ứng rơi khi lăn ra ngoài | Gameplay |
| Y8 | Màn kết quả thắng/thua: Next Level (khi còn màn), Retry, Main Menu; phím N / R / Enter / Esc | Result |
| Y9 | Sang màn tiếp theo trong cùng chế độ (`next_level`) | Result |
| Y10 | Tower: intro, cutscene thang máy, zombie, game over, R thử lại | Giữ nguyên, chỉ thay HUD |
| Y11 | Logic engine: `attempt_move` (moved/won/fell), `catalog.py`, sửa ô nâng cao | Dùng nguyên, không sửa |

## 2. Tính năng bản 2D cần có trong 3D

| # | Tính năng 2D | Trạng thái 3D hiện tại |
|---|---|---|
| D1 | Algorithms: chọn chế độ, màn, thuật toán | Chỉ có thông báo "chưa có" |
| D2 | Kết quả solver: thời gian, số nút đã duyệt, chi phí lời giải | Chưa có |
| D3 | Phát lại lời giải (S) | Chưa có |
| D4 | Phát lại thứ tự các nút đã duyệt (N) | Chưa có |
| D5 | Chạy lại solver (R) | Chưa có |
| D6 | Gợi ý nước đi (H, dùng UCS; 2D đang tắt) | Chưa có, sẽ thêm |

## 3. Đối chiếu yêu cầu đề (đã đọc lại toàn bộ PDF)

| Mục đề | Yêu cầu | Đã có | Sẽ làm ở UI 3D |
|---|---|---|---|
| 3.1 | GUI hiển thị bàn: floor, void, goal, fragile, switch, bridge | ✅ `floor.py` | Thêm chú giải (legend) các loại ô |
| 3.1 | Khối 3 tư thế, 4 hướng lăn, phát hiện nước sai, thắng | ✅ | — |
| 3.1 | Tách/gộp khối, đổi khối bằng Space | ✅ | Hiện rõ khối đang điều khiển + phím Space trên HUD |
| 3.1 | **Nút New Game, Restart và nút gọi solver** | ❌ chỉ có phím | Thanh công cụ trong game: New Game, Restart, Solve BFS/DFS/UCS/A* |
| 3.1 | Nạp màn từ JSON, dùng chung cho mọi solver | ✅ | — |
| 3.2–3.5 | Mỗi solver ghi **thời gian, bộ nhớ (peak), số nút mở rộng, độ dài lời giải** | ⚠️ thiếu bộ nhớ | Hiện đủ 4 số liệu (cần engine bổ sung peak memory, xem mục 4) |
| 3.3 | DFS hoặc IDS | DFS ✅, IDS ❌ | Menu chỉ hiện thuật toán đã viết; IDS hiện "chưa có" thay vì crash |
| 7 (video) | Chơi tay: lăn, kích switch, thắng/thua | ✅ | — |
| 7 (video) | Chọn màn, chạy BFS/UCS/A*, hiện lời giải, **animate/replay** | ❌ | Phát lại lời giải trên khối 3D, có play/pause/tua/tốc độ |
| 7 (video) | Thấy rõ giao diện, các loại ô, nút điều khiển | — | Legend + thanh công cụ |

## 4. Ngoài phạm vi UI nhưng UI phụ thuộc

Những mục này thuộc phần solver/engine của thành viên khác. UI sẽ xử lý an toàn khi chưa có.

| Vấn đề | Ảnh hưởng | Đề xuất |
|---|---|---|
| Chưa đo **peak memory** | Đề bắt buộc ghi lại | Thêm `tracemalloc` vào `solve_problem` trong `engine/solver.py`, trả về `peak_memory_kb` trong `SolveResult` (sửa nhỏ, mình có thể làm nếu nhóm đồng ý) |
| Chưa có **IDS** | Menu có mục "Iterative DFS" sẽ crash | UI bắt `NotImplementedError` và hiện "Not implemented" |
| **UCS** đang dùng chi phí 1 mỗi bước, nên kết quả giống hệt BFS | Đề nói chi phí đều thì UCS vô nghĩa | Người làm solver định nghĩa `path_cost` riêng |
| `explored` của DFS/A* chứa `State`, còn của BFS/UCS chứa `Node` | Đếm vẫn đúng; UI đọc được cả hai | Nên thống nhất một kiểu |

Thời gian đo trên máy này: chậm nhất là DFS ở màn 43, mất 0,67 s. Lời giải dài nhất là 106 bước (BFS, màn 46). Peak memory khoảng 6 MB. Không cần chạy luồng nền, chỉ cần một khung "Solving…".

## 5. Hệ thống thiết kế

Hướng thẩm mỹ (duyệt lại 28/10): **bảng điều khiển thang máy** trong thành phố low-poly. Nút chữ nhật vát góc nhẹ, mặt xám than/xám xanh, có chiều sâu (mặt nút nằm trên một cạnh tối, khi nhấn thì lún xuống). Vàng ấm chỉ dành cho hành động chính và mục đang chọn. Nguồn: `ui3d/theme.py`. Ảnh mẫu: `docs/ui3d_widgets_preview.png`, `docs/ui3d_main_menu_preview.png`.

### Màu chính

| Token | RGB | Dùng cho |
|---|---|---|
| `FACE` / `FACE_HOVER` / `FACE_PRESS` | 38,43,52 / 52,59,71 / 29,33,40 | Mặt nút phụ theo trạng thái |
| `EDGE`, `RIM` | 15,17,22 · 74,81,95 | Cạnh dưới (độ sâu), viền |
| `GOLD` / `GOLD_HOVER` / `GOLD_PRESS` | 240,182,74 / 250,202,108 / 196,146,56 | Nút chính, mục đang chọn |
| `GOLD_RIM` | 255,214,128 | Viền focus |
| `PANEL`, `PANEL_RIM` | 21,24,30 a236 · 62,68,80 | Bảng |
| `DONE_FACE`, `GREEN` | 46,68,52 · 150,212,150 | Level đã hoàn thành |
| `OFF_FACE`, `OFF_TEXT` | 64,68,76 · 118,122,130 | Disabled, level khóa |
| `ORANGE` | 255,146,96 | Chữ cảnh báo (nút danger) |
| `TEXT`, `MUTED`, `INK` | 236,232,224 · 150,156,168 · 34,26,14 | Chữ thường, chữ phụ, chữ trên nền vàng |

### Chữ
Fredoka là font biến thiên, Panda3D chỉ đọc được bản Light (300) nên chữ mảnh. `tools/make_font_weights.py` tách ra 3 bản tĩnh:
- `Fredoka-BoldCondensed` (700, hẹp 80): tiêu đề, số lớn.
- `Fredoka-SemiBold` (600): nút, nhãn, phím tắt.
- `Fredoka-Medium` (500): chữ thường, font mặc định của bản 3D.

Mỗi font có một độ phân giải glyph cố định (`theme.RESOLUTION`) để tiêu đề lớn không bị mờ.

Fredoka **không có** `← ↑ → ↓ ▶ ■ ✓ ⏸`; các icon này vẽ bằng mesh trong `ui3d/icons.py`.

### Thành phần (`ui3d/widgets.py`)
- `UIButton`: các kiểu `primary` / `secondary` / `quiet` (Exit) / `danger`; 5 trạng thái normal, hover, focus (viền vàng + mũi tên chỉ), pressed (lún xuống), disabled. Chữ tự thu nhỏ để không bị cắt.
- `back_button`, `icon_button` (pause, restart), `Stepper`, `Tabs`.
- `LevelTile`: completed (xanh + dấu check), selected (viền và số vàng), available, locked (mờ + ổ khóa, không chọn được).
- `Slider` (kéo chuột, bấm, hoặc ←/→), `Checkbox`, `ProgressBar`.
- `Panel`, `Modal`, `ConfirmDialog` (Esc hủy, Enter xác nhận, kiểu danger thì focus mặc định ở Cancel).
- `HUDBar` (dải gọn ở mép trên trái), `KeyHint`, `StatCard`, `Toast` (nhiều toast xếp chồng, không đè nhau).
- `FocusGroup`: điều khiển bàn phím cho mọi thành phần trên, kể cả lưới ô level.

### Tương tác và kiểm tra
- Chuột và bàn phím dùng được ở mọi màn: ↑/↓ (hoặc ←/→) chọn, Enter bấm, Esc quay lại.
- HUD trong màn chơi nằm gọn ở mép, không che bàn cờ. Số liệu thuật toán chỉ hiện trong chế độ Algorithms.
- Mỗi màn được chụp kiểm tra ở 1280×720 và 1920×1080.

## 6. Các màn hình

Chữ trong game giữ tiếng Anh như bản hiện có.

### 6.1 Main Menu (= cảnh cuối intro của Justin)
Luồng: mở game → Loading → intro của Justin (bấm phím bất kỳ để bỏ qua) → dừng ở cảnh cuối: tiêu đề BLOXORZ TOWER trên cửa tòa tháp. Bảng menu đứng ở góc phải dưới, đúng chỗ nút "Enter Building" cũ.

- **Tower:** đi tiếp đúng đoạn của Justin, cái thùng lăn vào sảnh.
- **Free Play / Algorithms / Settings:** mở màn tương ứng.
- **Exit / Esc:** hộp thoại xác nhận.
- **Về menu sau khi chơi:** dựng lại cảnh và vào thẳng cảnh cuối, không chiếu lại cả đoạn intro.

Code: `ui3d/app.py` (`main_menu`, `_enter_tower`), `ui3d/screens/main_menu.py`. Phần sửa vào code của Justin chỉ gồm:
- `TowerGame.menu_hold`: giữ intro ở cảnh tiêu đề trong lúc menu mở.
- `Intro.show_button`, `Intro.at_title`.
- Tiêu đề intro đổi sang font BoldCondensed, chữ "TOWER" màu vàng.
- `Intro.step` giới hạn dt để intro không nhảy cóc khi game khựng lúc tải.
- Lớp vignette và hạt nhiễu tự giãn theo tỉ lệ cửa sổ thật.

### 6.2 Level Select (Free Play và Algorithms dùng chung)
```
  FREE PLAY                                  [ Normal | Advanced ]
  ┌─────────────────────────┐   ┌──────────────────────────────┐
  │   ‹   Tutorial 1  ›     │   │                              │
  │        Fragile          │   │   (bản xem trước 3D của màn)  │
  │  tiles: ■fragile ■bridge│   │                              │
  │  "Fragile tiles break…" │   └──────────────────────────────┘
  │  [ Start ]   [ Back ]   │
  └─────────────────────────┘
```

### 6.3 Gameplay HUD (Free Play và Tower)
```
 ┌ Tutorial 1 – Fragile ┐                [New] [Restart] [Hint] [Solve ▾] [❚❚]
 │ MOVES 12   ACTIVE: A │
 └──────────────────────┘
          ┌ Fragile tiles break under a standing block… ┐   ← mẹo, không đè tên màn
                                          ┌ legend ┐
                                          │■ floor ■ fragile ■ switch ■ bridge ■ goal│
   ←↑↓→ roll   Space switch cube   R restart   H hint   Esc pause
```
`Solve ▾` mở danh sách BFS / DFS / UCS / A*. Chọn một thuật toán thì giải từ trạng thái hiện tại rồi tự phát lại lời giải ngay trên màn đang chơi.

### 6.4 Pause (Esc)
Resume, Restart, New Game (về chọn màn), Settings, Main Menu.

### 6.5 Result
Thắng: LEVEL CLEARED, số bước. Nếu đã chạy BFS thì kèm "best: N moves". Nút Next / Retry / Menu.
Thua: YOU FELL, nút Retry / Menu.

### 6.6 Algorithms Lab (phần mới lớn nhất)
```
  ALGORITHMS                                           [ Normal | Advanced ]
  ┌ Setup ───────────────┐  ┌──────────────────────────────────────────┐
  │ Level   ‹ Level 12 › │  │                                          │
  │ Algo  [BFS][DFS][UCS]│  │        cảnh 3D của màn, khối đang         │
  │       [A*][IDS]      │  │        phát lại lời giải                  │
  │ [ Run ]  [ Run all ] │  │                                          │
  └──────────────────────┘  │  ▶❚❚  ⏮ ⏭   speed ‹1x›   step 14/31     │
  ┌ Result: BFS ─────────┐  └──────────────────────────────────────────┘
  │ 12.4 ms   3.1 MB     │  ┌ Compare (Run all) ───────────────────────┐
  │ 812 nodes 31 moves   │  │ algo  time   memory  expanded  length    │
  │ [Replay] [Explored]  │  │ BFS   12ms   3.1MB   812       31        │
  └──────────────────────┘  │ A*    4ms    1.2MB   205       31  ▇▇    │
                            └──────────────────────────────────────────┘
```
- **Run**: chạy một thuật toán, hiện 4 số liệu theo đề.
- **Run all**: chạy cả 4 trên cùng màn, hiện bảng so sánh kèm thanh ngang. Có ích cho phần thực nghiệm và video.
- **Replay**: khối 3D lăn theo lời giải. **Explored**: tô sáng lần lượt các ô đã duyệt.

### 6.7 Settings
Fullscreen, tốc độ lăn khối, tốc độ phát lại mặc định, hiện/ẩn dải phím tắt, hiện/ẩn legend. Lưu vào file `settings.json` cạnh game và nhớ qua các lần mở.

## 7. Cấu trúc code dự kiến

```
ui3d/
  theme.py        màu, cỡ chữ, thời gian hiệu ứng
  widgets.py      Panel, MenuButton, Stepper, Tabs, Toggle, Slider, StatCard, KeyHint, Toast, Modal
  hud.py          HUD + thanh công cụ dùng chung cho Free Play và Tower
  screens/
    main_menu.py  level_select.py  pause.py  result.py  settings.py  algorithms.py
  replay.py       phát lại một danh sách State trên Floor + Block có sẵn
  app.py          máy trạng thái chuyển màn (thay App3D hiện tại)
  free_play.py    giữ logic, dùng HUD/Modal mới
```
`game.py` (Tower), `floor.py`, `block.py` cùng phần cảnh, intro, zombie: chỉ thay HUD, không đụng đồ họa.

## 8. Thứ tự triển khai

1. `theme.py` + `widgets.py`, chụp màn hình kiểm tra từng thành phần.
2. Main Menu, Level Select, Loading, Settings.
3. HUD + thanh công cụ + Pause + Result, áp cho Free Play rồi Tower.
4. `replay.py` + Solve trong game.
5. Algorithms Lab: Run, Run all, Replay, Explored.
6. Rà toàn bộ bằng bàn phím và chuột, chạy test, chụp màn hình từng màn.
