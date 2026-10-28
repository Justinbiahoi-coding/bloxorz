# Hướng dẫn merge các nhánh

Cập nhật: 28/10/2026. Dành cho người phụ trách merge vào `main`.

## Các nhánh liên quan

| Nhánh | Nội dung | Trạng thái |
|---|---|---|
| `main` | Engine, UI 2D, UI 3D (tháp), DFS + A* | Nhánh chính |
| `fix/cross-platform-setup` | Sửa cài đặt: `pygame-ce`, `pygame-menu-ce`, ghim `ursina==5.2.0`, `launcher.py` tự cài thư viện, file chạy `Play 2D/3D` (.bat, .command), sửa font 3D trên Windows, nút Exit 2D | Chưa merge |
| `feat/bfs-ucs` | BFS, UCS và test | Chưa merge |
| `feat/advanced-mechanisms` | Sửa logic ô nâng cao, `catalog.py`, tutorial 54–57, menu 3D, Free Play 2D/3D | Chưa merge |
| `feat/ui3d-redesign` | Đã chứa sẵn 3 nhánh trên (conflict đã xử lý) + thiết kế lại toàn bộ UI 3D | Đang làm |

## Conflict và cách xử lý

`feat/bfs-ucs` merge sạch, không conflict.

`feat/advanced-mechanisms` conflict với `fix/cross-platform-setup` ở đúng 3 file, đều là file cấu hình hoặc tài liệu:

| File | Cách xử lý |
|---|---|
| `requirements.txt` | Giữ bản `fix/cross-platform-setup`: `pygame-ce`, `pygame-menu-ce`, `ursina==5.2.0`, `panda3d-gltf`, `screeninfo`, `pytest` |
| `Source/requirements.txt` | Như trên |
| `Source/README.md` | Gộp: lấy phần Requirements, Run, Manual setup của `fix/cross-platform-setup`, rồi nối mục **Free Play** và 2 link tài liệu (`ADVANCED_MECHANICS.md`, `SOLVER_IMPLEMENTATION.md`) của `feat/advanced-mechanisms` |

Git tự gộp đúng, không cần sửa tay:
- `Source/ui3d/__init__.py`: giữ cả sửa font (`FONT`) lẫn menu `App3D`.
- `Source/ui/app.py`: nút Exit gọi `self._quit()` trên code đã viết lại của nhánh.

Kết quả sau khi gộp đủ 3 nhánh: 87 test pass. Test fail duy nhất là `test_all_algorithms_solve_level_one`, vì **chưa nhánh nào viết IDS** (`iterative_deepening_search`).

## Thứ tự merge đề xuất

Cách 1, từng nhánh một:
1. `fix/cross-platform-setup`
2. `feat/bfs-ucs`
3. `feat/advanced-mechanisms` (xử lý 3 file như bảng trên)
4. `feat/ui3d-redesign`: phần conflict đã giải giống hệt nên bước này không cần sửa lại

Cách 2: chỉ merge `feat/ui3d-redesign` khi đã xong, vì nhánh này chứa cả 3 nhánh kia.

## Quy ước cho cả nhóm

1. **Không đổi lại `pygame` / `pygame-menu`** trong `requirements.txt`. Máy dùng Python 3.14 sẽ không cài được. Code vẫn `import pygame`, `import pygame_menu` như cũ.
2. **Giữ `ursina==5.2.0`.** Bản 8.x crash khi tạo `Text`.
3. **Đường dẫn file trong bản 3D** (font, model, ảnh): dùng `FONT` trong `ui3d/world.py` hoặc bọc bằng `Filename.fromOsSpecific(str(path))`. Truyền thẳng `str(path)` sẽ lỗi trên Windows.
4. **Giữ `bootstrap(__file__)` ở đầu `main.py` và `main3d.py`.** Đây là phần tự cài thư viện cho người chấm.
5. **Không dùng `pygame_menu.events.EXIT`.** Nó thoát với mã 1.
6. **Không commit `.venv/`.**
7. **Giao diện 3D đã được thiết kế lại** trên `feat/ui3d-redesign`. Ai sửa các file dưới đây trên nhánh khác thì báo trước để tránh conflict.

## Các file 3D đã bị chỉnh trên `feat/ui3d-redesign`

| File | Chủ cũ | Thay đổi |
|---|---|---|
| `ui3d/app.py`, `ui3d/free_play.py` | Youmei | Viết lại phần giao diện, giữ đủ tính năng: 2 bộ màn, tutorial, mẹo, Next / Retry, nhớ trước 1 nước, phím tắt |
| `ui3d/game.py` | Justin | HUD mới (`hud.py`), Esc mở Pause, H gợi ý, Solve, `menu_hold` cho màn tiêu đề, `on_finish` khi lên tới mái |
| `ui3d/intro.py` | Justin | Tiêu đề kiểu mới, ẩn nút Enter Building khi menu mở, giới hạn dt, lớp phủ theo tỉ lệ cửa sổ thật |
| `ui3d/world.py` | Justin | Bật âm thanh (OpenAL); **sửa lỗi** `lights()` lưu màu gốc bằng tham chiếu sống nên ánh sáng cộng dồn mỗi lần dựng lại intro |
| `ui3d/block.py` | Justin | Hệ số `SPEED` cho tốc độ lăn (Settings) |
| `ui3d/floor.py` | Justin | Free Play và Lab dùng chung tầng như tháp: có đồ đạc và thang máy ở ô đích (bỏ ô đích riêng của Free Play) |
| `ui3d/__init__.py` | Justin | Gọi `loadfast.install()`: Ursina 5.2 quét lại cả thư mục assets mỗi lần nạp model, làm tháp mất vài chục giây để dựng |
| `engine/solver.py` | (solver) | Đo peak memory, thêm `expanded`, `solution_length` |

File mới: `ui3d/loadfast.py`, `ui3d/theme.py`, `icons.py`, `widgets.py`, `hud.py`, `controls.py`, `autoplay.py`, `settings.py`, `audio.py`, `screens/*`, font tĩnh `assets/fonts/Fredoka-*.ttf`, `tools/make_font_weights.py`.
