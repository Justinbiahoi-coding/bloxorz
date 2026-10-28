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
7. **Giao diện 3D đang được thiết kế lại** trên `feat/ui3d-redesign`. Các file `ui3d/app.py`, `ui3d/free_play.py` sẽ được viết lại, giữ nguyên tính năng. Ai cần sửa các file này thì báo trước để tránh conflict.
