# USDT ⇄ INR  P2P Trading Calculator — Windows App

A professional dark-themed desktop trading calculator built with
Python + CustomTkinter. Zero web browser required.

---

## 📁 Files

```
p2p-calc-win/
├── main.py          ← Complete application (single file)
├── requirements.txt ← Python dependencies
├── p2pcalc.spec     ← PyInstaller build config
├── build.bat        ← One-click build → EXE
├── run.bat          ← One-click run in dev mode
└── README.md        ← This file
```

---

## ⚡ Quick Start — Run Directly (No Build Needed)

### Requirements
- Windows 10 / 11
- Python 3.10+  →  https://python.org/downloads
  ✓ Check "Add Python to PATH" during install

### Steps
```
1. Double-click  run.bat
   — or —
   pip install customtkinter requests
   python main.py
```

---

## 📦 Build a Standalone EXE

Produces a single `P2PCalc.exe` that runs on any Windows PC
without Python installed.

```
1. Double-click  build.bat
2. Wait ~60 seconds
3. Your EXE is at:  dist\P2PCalc.exe
```

You can share `dist\P2PCalc.exe` directly — no installation needed.

### Manual build command
```batch
pip install customtkinter requests pyinstaller
pyinstaller p2pcalc.spec --noconfirm
```

---

## 🔑 Update the API Key

Open `main.py`, find line near the top:

```python
API_KEY = "c5hxf2wjnat9kpi92qk6"
```

Replace with your new key from: https://freecryptoapi.com/panel

---

## ✨ Features

| Feature | Details |
|---|---|
| **Live Rate** | 4-tier: FreeCryptoAPI → FreeCryptoAPI×FX → CoinGecko → ExchangeRate |
| **Modes** | Buy→Sell and Sell→Buy |
| **Amount input** | Toggle between INR and USDT |
| **Fee control** | Slider + +/− stepper, 0–100% |
| **Results** | USDT, Net selling value, P/L, Return % |
| **Breakeven** | Min sell rate to recover capital |
| **Profit chart** | Canvas curve — profit vs sell rate ±5–10% |
| **Projections tab** | Per trade, Daily, Weekly, Monthly, Yearly, Volume |
| **Persistence** | Settings saved to AppData\Roaming\P2PCalc\settings.json |
| **UI** | Dark fintech theme, 1080×760 resizable, 2-column layout |

---

## 🎨 Adding a Custom Icon

1. Create a 256×256 `.ico` file (use https://convertio.co/png-ico)
2. Place it at `assets/icon.ico`
3. In `p2pcalc.spec`, uncomment: `icon='assets/icon.ico'`
4. Rebuild with `build.bat`

---

## 🛠 Tech Stack

| Library | Purpose |
|---|---|
| `customtkinter` | Modern dark-themed UI widgets |
| `tkinter` (built-in) | Window, canvas (chart), layout |
| `requests` | HTTP for live rate fetching |
| `pyinstaller` | Package to single `.exe` |
| `threading` | Non-blocking API calls |
| `json` + `os` | Settings persistence |

---

## ⚠ Disclaimer

For informational purposes only.
Not financial advice. Verify all rates before executing trades.
