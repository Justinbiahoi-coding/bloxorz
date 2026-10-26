# Bloxorz

## Setup

- **Linux / macOS:**
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```

- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

## Run

- **2D UI (Pygame):**
  ```bash
  python main.py
  ```
- **3D UI (Ursina / Panda3D):**
  ```bash
  python main3d.py
  ```

## Test

    pytest

## Documentation

- [UI and engine interaction](../docs/UI_ENGINE_INTERACTION.md)
- [Algorithm implementation guide](../docs/ALGORITHM_IMPLEMENTATION_GUIDE.md)
