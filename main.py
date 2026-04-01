"""
╔══════════════════════════════════════════════════════════════╗
║      USDT ⇄ INR  P2P Trading Calculator  —  Windows App     ║
║      Python 3.10+ · CustomTkinter · Tkinter Canvas          ║
║                                                              ║
║  Live rate : FreeCryptoAPI  (+ 3 fallback tiers)            ║
║  Storage   : JSON file in AppData/Roaming                   ║
║  Chart     : Custom canvas profit curve                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import threading, json, os, math, time
from datetime import datetime
from pathlib import Path

# ── Try to import requests; fallback to urllib ──────────────────
try:
    import requests as _req
    def _get(url, headers=None, timeout=7):
        r = _req.get(url, headers=headers or {}, timeout=timeout)
        r.raise_for_status()
        return r.json()
except ImportError:
    import urllib.request, urllib.error
    def _get(url, headers=None, timeout=7):
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

# ═══════════════════════════════════════════════════════════════
# THEME
# ═══════════════════════════════════════════════════════════════
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

C = {
    "bg_base":    "#060c09",
    "bg_card":    "#0d1510",
    "bg_card2":   "#0f1711",
    "bg_input":   "#0a1209",
    "border":     "#1e2f20",
    "border_hi":  "#2a4230",
    "accent":     "#00e676",
    "accent_d":   "#00b85a",
    "red":        "#ff4d6d",
    "gold":       "#f0b429",
    "white":      "#e8f5eb",
    "sec":        "#7a9c80",
    "muted":      "#3d5c42",
}

FONT_TITLE  = ("Consolas", 9,  "bold")
FONT_MONO   = ("Consolas", 11)
FONT_MONO_L = ("Consolas", 16, "bold")
FONT_MONO_S = ("Consolas", 9)
FONT_BODY   = ("Segoe UI",  10)
FONT_BODY_B = ("Segoe UI",  10, "bold")
FONT_SMALL  = ("Segoe UI",  8)

# ═══════════════════════════════════════════════════════════════
# PERSISTENCE  (AppData\Roaming\P2PCalc\settings.json)
# ═══════════════════════════════════════════════════════════════
def _settings_path():
    base = os.environ.get("APPDATA", str(Path.home()))
    d = Path(base) / "P2PCalc"
    d.mkdir(exist_ok=True)
    return d / "settings.json"

def load_settings():
    try:
        with open(_settings_path()) as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data: dict):
    try:
        with open(_settings_path(), "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# 4-TIER LIVE RATE FETCH
# ═══════════════════════════════════════════════════════════════
API_KEY  = "c5hxf2wjnat9kpi92qk6"
API_BASE = "https://api.freecryptoapi.com/v1"
API_HDR  = {"Authorization": f"Bearer {API_KEY}"}

def fetch_live_rate():
    """
    Returns (rate: float, source: str) or raises RuntimeError if all tiers fail.
    """
    # Tier 1 — FreeCryptoAPI: USDT→INR direct
    try:
        j   = _get(f"{API_BASE}/getDataCurrency?symbol=USDT&currency=INR", headers=API_HDR)
        raw = j[0] if isinstance(j, list) else j
        p   = float(raw.get("price") or raw.get("rate") or raw.get("inr") or 0)
        if p > 0:
            return p, "FreeCryptoAPI"
    except Exception:
        pass

    # Tier 2 — FreeCryptoAPI USD price × ExchangeRate USD/INR
    try:
        j1  = _get(f"{API_BASE}/getData?symbol=USDT", headers=API_HDR)
        raw = j1[0] if isinstance(j1, list) else j1
        usd = float(raw.get("price") or 1)
        j2  = _get("https://api.exchangerate-api.com/v4/latest/USD")
        inr = float(j2["rates"]["INR"])
        if inr > 0:
            return usd * inr, "FreeCryptoAPI × FX"
    except Exception:
        pass

    # Tier 3 — CoinGecko
    try:
        j = _get("https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=inr")
        p = float(j["tether"]["inr"])
        if p > 0:
            return p, "CoinGecko"
    except Exception:
        pass

    # Tier 4 — ExchangeRate-API (USD ≈ USDT)
    try:
        j   = _get("https://api.exchangerate-api.com/v4/latest/USD")
        inr = float(j["rates"]["INR"])
        if inr > 0:
            return inr, "ExchangeRate-API~"
    except Exception:
        pass

    raise RuntimeError("All rate sources failed")

# ═══════════════════════════════════════════════════════════════
# CALCULATION ENGINE
# ═══════════════════════════════════════════════════════════════
def do_calc(amount, amt_mode, mode, buy_rate, sell_rate, fee):
    if not all([amount > 0, buy_rate > 0, sell_rate > 0]):
        return None

    inr = amount * buy_rate if amt_mode == "usdt" else amount

    if mode == "sell":
        # Reverse: user wants to receive <inr> INR → how much to invest
        usdt_needed = inr / sell_rate
        inr = usdt_needed * buy_rate

    usdt      = inr / buy_rate
    gross     = usdt * sell_rate
    fee_amt   = (fee / 100) * gross
    net_sell  = gross - fee_amt
    profit    = net_sell - inr
    pct       = (profit / inr * 100) if inr > 0 else 0
    spread    = sell_rate - buy_rate
    be_rate   = inr / (usdt * (1 - fee / 100)) if usdt > 0 else 0

    return dict(
        inr=inr, usdt=usdt, gross=gross,
        fee_amt=fee_amt, net_sell=net_sell,
        profit=profit, pct=pct,
        spread=spread, be_rate=be_rate,
        buy_rate=buy_rate, sell_rate=sell_rate, fee=fee,
    )

def fmt(n, d=2):
    if n is None or not math.isfinite(n):
        return "—"
    return f"{n:,.{d}f}"

def fmt_inr(n, d=2):
    return "₹" + fmt(n, d)

def fmt_k(n):
    a = abs(n)
    if a >= 1e7:  return f"₹{n/1e7:.2f} Cr"
    if a >= 1e5:  return f"₹{n/1e5:.2f} L"
    if a >= 1e3:  return f"₹{n/1e3:.1f}K"
    return fmt_inr(n, 0)

# ═══════════════════════════════════════════════════════════════
# PROFIT CURVE CANVAS
# ═══════════════════════════════════════════════════════════════
class ProfitChart(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, bg=C["bg_card2"], bd=0, highlightthickness=0, **kw)
        self._result = None
        self.bind("<Configure>", lambda e: self.redraw())

    def update_data(self, result):
        self._result = result
        self.redraw()

    def redraw(self):
        self.delete("all")
        W, H   = self.winfo_width(), self.winfo_height()
        PAD    = 16
        if W < 40 or H < 40:
            return

        r = self._result
        if not r or r["buy_rate"] <= 0:
            self.create_text(W//2, H//2, text="Enter rates to see chart",
                             fill=C["muted"], font=FONT_SMALL)
            self._draw_grid(W, H, PAD)
            return

        STEPS   = 80
        buy     = r["buy_rate"]
        sell    = r["sell_rate"]
        fee     = r["fee"]
        usdt    = r["usdt"]
        inr_amt = r["inr"]
        min_sr  = buy * 0.95
        max_sr  = buy * 1.10

        pts = []
        for i in range(STEPS + 1):
            sr = min_sr + (max_sr - min_sr) * i / STEPS
            p  = usdt * sr * (1 - fee / 100) - inr_amt
            pts.append(p)

        min_p, max_p = min(pts), max(pts)
        rng  = max_p - min_p or 1

        def to_x(i): return PAD + (i / STEPS) * (W - PAD*2)
        def to_y(p): return (H - PAD) - ((p - min_p) / rng) * (H - PAD*2)

        self._draw_grid(W, H, PAD)

        # Zero line
        zy = to_y(0)
        self.create_line(PAD, zy, W-PAD, zy, fill=C["muted"], dash=(4,6), width=1)
        self.create_text(W-PAD-2, zy-6, text="0", fill=C["muted"],
                         font=FONT_SMALL, anchor="e")

        # Current sell-rate position
        curr_i = max(0, min(STEPS, round(((sell - min_sr) / (max_sr - min_sr)) * STEPS)))
        curr_p = usdt * sell * (1 - fee/100) - inr_amt
        curr_y = to_y(curr_p)
        curr_x = to_x(curr_i)
        color  = C["accent"] if curr_p >= 0 else C["red"]

        # Fill polygon
        coords = []
        for i, p in enumerate(pts):
            coords += [to_x(i), to_y(p)]
        coords += [W - PAD, H - PAD, PAD, H - PAD]
        self.create_polygon(*coords, fill=color, stipple="gray25", outline="")

        # Main line
        line_pts = []
        for i, p in enumerate(pts):
            line_pts += [to_x(i), to_y(p)]
        self.create_line(*line_pts, fill=color, width=2, smooth=True)

        # Current dot
        self.create_oval(curr_x-9, curr_y-9, curr_x+9, curr_y+9,
                         fill=color, stipple="gray25", outline="")
        self.create_oval(curr_x-4, curr_y-4, curr_x+4, curr_y+4,
                         fill=color, outline="")

        # Sell rate label
        label = f"₹{sell:.2f}"
        self.create_text(curr_x, curr_y - 14, text=label,
                         fill=color, font=FONT_SMALL)

        # Range labels
        self.create_text(PAD+2, H-4, text=f"₹{min_sr:.0f}", fill=C["muted"],
                         font=FONT_SMALL, anchor="w")
        self.create_text(W-PAD-2, H-4, text=f"₹{max_sr:.0f}", fill=C["muted"],
                         font=FONT_SMALL, anchor="e")

    def _draw_grid(self, W, H, PAD):
        for i in range(5):
            y = PAD + i * (H - PAD*2) / 4
            self.create_line(PAD, y, W-PAD, y, fill=C["border"], width=1)

# ═══════════════════════════════════════════════════════════════
# SEPARATOR
# ═══════════════════════════════════════════════════════════════
class HSep(tk.Frame):
    def __init__(self, master, **kw):
        super().__init__(master, height=1, bg=C["border"], **kw)

# ═══════════════════════════════════════════════════════════════
# RESULT CARD
# ═══════════════════════════════════════════════════════════════
class ResultCard(ctk.CTkFrame):
    def __init__(self, master, label, **kw):
        super().__init__(master,
            fg_color=C["bg_card2"],
            border_color=C["border"],
            border_width=1,
            corner_radius=8,
            **kw
        )
        self.label_txt = label
        self._lbl = ctk.CTkLabel(self, text=label,
            font=FONT_SMALL, text_color=C["muted"])
        self._lbl.pack(anchor="w", padx=12, pady=(10, 0))

        self._val = ctk.CTkLabel(self, text="—",
            font=FONT_MONO_L, text_color=C["white"])
        self._val.pack(anchor="w", padx=12)

        self._sub = ctk.CTkLabel(self, text="",
            font=FONT_SMALL, text_color=C["muted"])
        self._sub.pack(anchor="w", padx=12, pady=(0, 10))

    def set(self, value, sub="", color=C["white"]):
        self._val.configure(text=value, text_color=color)
        self._sub.configure(text=sub)

# ═══════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("P2P Calc  —  USDT ⇄ INR Trading Calculator")
        self.geometry("1080x760")
        self.minsize(900, 680)
        self.configure(fg_color=C["bg_base"])

        # Try to set a custom icon (graceful fallback)
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._live_rate   = None
        self._live_source = ""
        self._result      = None
        self._settings    = load_settings()
        self._pulse_on    = True
        self._last_saved  = time.time()

        self._build_ui()
        self._restore_settings()
        self._start_pulse()

        # Fetch rate in background on launch
        threading.Thread(target=self._bg_fetch, daemon=True).start()

    # ──────────────────────────────────────────────────────────
    # BUILD UI
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── App header ────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=C["bg_card"],
                           corner_radius=0, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        brand = ctk.CTkFrame(hdr, fg_color="#00e676",
                             corner_radius=10, width=44, height=44)
        brand.place(x=16, rely=0.5, anchor="w")
        brand.pack_propagate(False)
        ctk.CTkLabel(brand, text="₮", font=("Consolas", 22, "bold"),
                     text_color="#000").place(relx=0.5, rely=0.5, anchor="center")

        title_fr = ctk.CTkFrame(hdr, fg_color="transparent")
        title_fr.place(x=72, rely=0.5, anchor="w")
        ctk.CTkLabel(title_fr, text="P2P Calc",
                     font=("Segoe UI", 18, "bold"),
                     text_color=C["white"]).pack(anchor="w")
        ctk.CTkLabel(title_fr,
                     text="USDT  ·  INR  ·  TRADING DESK",
                     font=FONT_SMALL, text_color=C["sec"]).pack(anchor="w")

        # Live rate section in header
        rate_fr = ctk.CTkFrame(hdr, fg_color=C["bg_input"],
                               corner_radius=20,
                               border_color=C["border_hi"], border_width=1)
        rate_fr.place(relx=1, x=-16, rely=0.5, anchor="e")

        self._pulse_dot = tk.Canvas(rate_fr, width=10, height=10,
                                    bg=C["bg_input"], bd=0, highlightthickness=0)
        self._pulse_dot.pack(side="left", padx=(12,4), pady=12)
        self._pulse_dot.create_oval(1,1,9,9, fill=C["accent"], outline="", tags="dot")

        ctk.CTkLabel(rate_fr, text="LIVE", font=FONT_SMALL,
                     text_color=C["muted"]).pack(side="left")

        self._rate_lbl = ctk.CTkLabel(rate_fr, text="Fetching…",
            font=("Consolas", 12, "bold"), text_color=C["accent"], width=160)
        self._rate_lbl.pack(side="left", padx=(6, 4))

        self._src_lbl = ctk.CTkLabel(rate_fr, text="",
            font=FONT_SMALL, text_color=C["muted"])
        self._src_lbl.pack(side="left", padx=(0, 4))

        self._refresh_btn = ctk.CTkButton(rate_fr, text="↻", width=30, height=30,
            font=("Segoe UI", 14), fg_color="transparent",
            border_color=C["border_hi"], border_width=1,
            hover_color=C["bg_card"],
            text_color=C["sec"], corner_radius=15,
            command=lambda: threading.Thread(target=self._bg_fetch, daemon=True).start())
        self._refresh_btn.pack(side="left", padx=(0, 8), pady=8)

        # ── Tab bar ───────────────────────────────────────────
        tab_bar = ctk.CTkFrame(self, fg_color=C["bg_card"],
                               corner_radius=0, height=42)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)

        self._tab_btns = {}
        for tab_id, label in [("calc", "⚙   Calculator"),
                               ("proj", "📈  Projections"),
                               ("info", "ℹ   About")]:
            btn = ctk.CTkButton(tab_bar, text=label,
                font=FONT_BODY_B, width=150, height=42,
                fg_color="transparent", hover_color=C["bg_input"],
                text_color=C["muted"], corner_radius=0,
                command=lambda t=tab_id: self._switch_tab(t))
            btn.pack(side="left")
            self._tab_btns[tab_id] = btn

        # Active tab indicator (bottom border via canvas)
        self._tab_indicator = tk.Canvas(self, height=2,
                                        bg=C["bg_card"], bd=0, highlightthickness=0)
        self._tab_indicator.pack(fill="x")

        # ── Content area ──────────────────────────────────────
        self._frames = {}
        container = ctk.CTkFrame(self, fg_color=C["bg_base"], corner_radius=0)
        container.pack(fill="both", expand=True)

        for tab_id in ("calc", "proj", "info"):
            fr = ctk.CTkFrame(container, fg_color=C["bg_base"], corner_radius=0)
            fr.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._frames[tab_id] = fr

        self._build_calc_tab(self._frames["calc"])
        self._build_proj_tab(self._frames["proj"])
        self._build_info_tab(self._frames["info"])

        self._switch_tab("calc")

    # ──────────────────────────────────────────────────────────
    # CALCULATOR TAB
    # ──────────────────────────────────────────────────────────
    def _build_calc_tab(self, parent):
        # Two-column layout
        left  = ctk.CTkScrollableFrame(parent, fg_color=C["bg_base"],
                                       corner_radius=0, scrollbar_button_color=C["border"])
        right = ctk.CTkScrollableFrame(parent, fg_color=C["bg_base"],
                                       corner_radius=0, scrollbar_button_color=C["border"])
        left.pack(side="left", fill="both", expand=True, padx=(12,6), pady=12)
        right.pack(side="left", fill="both", expand=True, padx=(6,12), pady=12)

        # ── LEFT: Inputs ───────────────────────────────────────
        inp_card = ctk.CTkFrame(left, fg_color=C["bg_card"],
                                border_color=C["border"], border_width=1,
                                corner_radius=12)
        inp_card.pack(fill="x", pady=(0,10))

        self._card_hdr(inp_card, "⚙  TRADE SETUP")

        # Mode toggle
        mode_fr = ctk.CTkFrame(inp_card, fg_color="transparent")
        mode_fr.pack(fill="x", padx=16, pady=(0,10))
        ctk.CTkLabel(mode_fr, text="TRADE MODE", font=FONT_SMALL,
                     text_color=C["muted"]).pack(anchor="w", pady=(0,4))
        self._mode = tk.StringVar(value="buy")
        self._seg_mode = ctk.CTkSegmentedButton(mode_fr,
            values=["Buy → Sell", "Sell → Buy"],
            variable=self._mode,
            font=FONT_BODY_B,
            fg_color=C["bg_input"],
            selected_color=C["accent"],
            selected_hover_color=C["accent_d"],
            unselected_color=C["bg_input"],
            text_color_disabled="#000",
            command=self._on_change)
        self._seg_mode.set("Buy → Sell")
        self._seg_mode.pack(fill="x")

        HSep(inp_card).pack(fill="x", padx=16, pady=10)

        # Amount input
        amt_fr = ctk.CTkFrame(inp_card, fg_color="transparent")
        amt_fr.pack(fill="x", padx=16, pady=(0,6))

        amt_top = ctk.CTkFrame(amt_fr, fg_color="transparent")
        amt_top.pack(fill="x")
        self._amt_label_var = tk.StringVar(value="AMOUNT TO INVEST")
        ctk.CTkLabel(amt_top, textvariable=self._amt_label_var,
                     font=FONT_SMALL, text_color=C["muted"]).pack(side="left")

        self._amt_mode = tk.StringVar(value="INR  ₹")
        self._seg_amt = ctk.CTkSegmentedButton(amt_top,
            values=["INR  ₹", "USDT  ₮"],
            variable=self._amt_mode,
            font=FONT_SMALL, width=120, height=24,
            fg_color=C["bg_input"],
            selected_color=C["border_hi"],
            unselected_color=C["bg_input"],
            command=self._on_amt_mode)
        self._seg_amt.pack(side="right")

        self._var_amount = tk.StringVar()
        self._var_amount.trace_add("write", lambda *_: self._on_change())
        self._e_amount   = self._make_entry(amt_fr, self._var_amount, "₹", "0.00")

        HSep(inp_card).pack(fill="x", padx=16, pady=10)

        # Buy rate
        self._var_buy = tk.StringVar()
        self._var_buy.trace_add("write", lambda *_: self._on_change())
        self._make_labeled_entry(inp_card, "BUYING RATE  (₹ per USDT)",
                                 self._var_buy, "₹", "/ USDT")

        # Sell rate
        self._var_sell = tk.StringVar()
        self._var_sell.trace_add("write", lambda *_: self._on_change())
        self._make_labeled_entry(inp_card, "SELLING RATE  (₹ per USDT)",
                                 self._var_sell, "₹", "/ USDT")

        # Spread indicator
        self._spread_lbl = ctk.CTkLabel(inp_card, text="",
            font=FONT_MONO_S, text_color=C["gold"])
        self._spread_lbl.pack(pady=2)

        HSep(inp_card).pack(fill="x", padx=16, pady=10)

        # Fee
        fee_fr = ctk.CTkFrame(inp_card, fg_color="transparent")
        fee_fr.pack(fill="x", padx=16, pady=(0,8))
        ctk.CTkLabel(fee_fr, text="TRANSACTION FEE", font=FONT_SMALL,
                     text_color=C["muted"]).pack(anchor="w", pady=(0,4))

        fee_row = ctk.CTkFrame(fee_fr, fg_color="transparent")
        fee_row.pack(fill="x")
        ctk.CTkButton(fee_row, text="−", width=36, height=36,
            font=("Segoe UI", 16), fg_color=C["bg_input"],
            hover_color=C["border"], text_color=C["accent"],
            corner_radius=6,
            command=lambda: self._step_fee(-0.1)
        ).pack(side="left")

        self._var_fee = tk.StringVar(value="0.00")
        self._var_fee.trace_add("write", lambda *_: self._on_change())
        e = ctk.CTkEntry(fee_row, textvariable=self._var_fee,
            font=FONT_MONO, fg_color=C["bg_input"],
            border_color=C["border"], border_width=1,
            text_color=C["white"], height=36, corner_radius=6,
            justify="center")
        e.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(fee_row, text="%", font=FONT_BODY,
                     text_color=C["sec"]).pack(side="left", padx=(0,4))

        ctk.CTkButton(fee_row, text="+", width=36, height=36,
            font=("Segoe UI", 16), fg_color=C["bg_input"],
            hover_color=C["border"], text_color=C["accent"],
            corner_radius=6,
            command=lambda: self._step_fee(+0.1)
        ).pack(side="left")

        # Fee slider
        self._fee_slider = ctk.CTkSlider(inp_card, from_=0, to=5, number_of_steps=100,
            fg_color=C["border"], progress_color=C["accent"],
            button_color=C["accent"], button_hover_color=C["accent_d"],
            command=self._on_fee_slider)
        self._fee_slider.set(0)
        self._fee_slider.pack(fill="x", padx=16, pady=(4,12))

        # Buttons
        btn_fr = ctk.CTkFrame(inp_card, fg_color="transparent")
        btn_fr.pack(fill="x", padx=16, pady=(0,16))

        ctk.CTkButton(btn_fr, text="⚡  Use Live Rate",
            font=FONT_BODY_B,
            fg_color=C["accent"], hover_color=C["accent_d"],
            text_color="#000", height=40, corner_radius=8,
            command=self._apply_live
        ).pack(side="left", fill="x", expand=True, padx=(0,6))

        ctk.CTkButton(btn_fr, text="↺  Reset",
            font=FONT_BODY_B,
            fg_color="transparent", hover_color=C["bg_input"],
            border_color=C["border_hi"], border_width=1,
            text_color=C["sec"], height=40, corner_radius=8,
            command=self._reset
        ).pack(side="left", padx=(0,0))

        # ── RIGHT: Results ─────────────────────────────────────
        res_card = ctk.CTkFrame(right, fg_color=C["bg_card"],
                                border_color=C["border"], border_width=1,
                                corner_radius=12)
        res_card.pack(fill="x", pady=(0,10))

        hdr_fr = ctk.CTkFrame(res_card, fg_color="transparent")
        hdr_fr.pack(fill="x", padx=16, pady=(12,0))
        ctk.CTkLabel(hdr_fr, text="📊  TRADE RESULT",
                     font=FONT_TITLE, text_color=C["sec"]).pack(side="left")
        self._pl_badge = ctk.CTkLabel(hdr_fr, text="— NEUTRAL",
            font=("Consolas", 9, "bold"), text_color=C["muted"],
            fg_color=C["border"], corner_radius=10,
            width=100, padx=8, pady=4)
        self._pl_badge.pack(side="right")

        # 2×2 result cards
        grid_fr = ctk.CTkFrame(res_card, fg_color="transparent")
        grid_fr.pack(fill="x", padx=12, pady=10)
        grid_fr.columnconfigure((0,1), weight=1)

        self._rc_usdt  = ResultCard(grid_fr, "USDT YOU GET")
        self._rc_sell  = ResultCard(grid_fr, "SELLING VALUE")
        self._rc_pl    = ResultCard(grid_fr, "PROFIT / LOSS")
        self._rc_pct   = ResultCard(grid_fr, "RETURN %")

        self._rc_usdt.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        self._rc_sell.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")
        self._rc_pl.grid  (row=1, column=0, padx=4, pady=4, sticky="nsew")
        self._rc_pct.grid (row=1, column=1, padx=4, pady=4, sticky="nsew")

        # Breakeven bar
        be_fr = ctk.CTkFrame(res_card, fg_color=C["bg_input"],
                             border_color=C["border"], border_width=1,
                             corner_radius=8)
        be_fr.pack(fill="x", padx=12, pady=(0,8))

        for attr, label in [("_be_rate","BREAKEVEN SELL"),
                             ("_be_fee", "FEE DEDUCTED"),
                             ("_be_net", "NET RECEIVED")]:
            col = ctk.CTkFrame(be_fr, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, pady=10)
            ctk.CTkLabel(col, text=label, font=FONT_SMALL,
                         text_color=C["muted"]).pack()
            lbl = ctk.CTkLabel(col, text="₹—",
                               font=("Consolas", 11, "bold"), text_color=C["gold"])
            lbl.pack()
            setattr(self, attr, lbl)

        # Chart
        self._card_hdr(res_card, "PROFIT  vs  SELL RATE  (±5–10% range)")
        self._chart = ProfitChart(res_card, height=130)
        self._chart.pack(fill="x", padx=12, pady=(0,14))

    # ──────────────────────────────────────────────────────────
    # PROJECTIONS TAB
    # ──────────────────────────────────────────────────────────
    def _build_proj_tab(self, parent):
        outer = ctk.CTkScrollableFrame(parent, fg_color=C["bg_base"],
                                       corner_radius=0,
                                       scrollbar_button_color=C["border"])
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        # Inputs card
        inp_card = ctk.CTkFrame(outer, fg_color=C["bg_card"],
                                border_color=C["border"], border_width=1,
                                corner_radius=12)
        inp_card.pack(fill="x", pady=(0,10))
        self._card_hdr(inp_card, "📈  TRADING PROJECTION")

        self._var_trades  = tk.StringVar(value="5")
        self._var_capital = tk.StringVar(value="")
        self._var_trades.trace_add("write",  lambda *_: self._update_proj())
        self._var_capital.trace_add("write", lambda *_: self._update_proj())

        self._make_labeled_entry(inp_card, "TRADES PER DAY",
                                 self._var_trades, "#", "trades",
                                 hint="How many P2P trades you execute daily")
        self._make_labeled_entry(inp_card, "CAPITAL PER TRADE  (optional)",
                                 self._var_capital, "₹", "INR",
                                 hint="Leave blank to use Calculator amount")

        # Output grid
        out_card = ctk.CTkFrame(outer, fg_color=C["bg_card"],
                                border_color=C["border"], border_width=1,
                                corner_radius=12)
        out_card.pack(fill="x", pady=(0,10))
        self._card_hdr(out_card, "PROJECTED RETURNS")

        grid = ctk.CTkFrame(out_card, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0,12))
        grid.columnconfigure((0,1,2), weight=1)

        self._proj_labels = {}
        items = [
            ("trade",   "PER TRADE",  0, 0),
            ("daily",   "DAILY",      0, 1),
            ("weekly",  "WEEKLY",     0, 2),
            ("monthly", "MONTHLY",    1, 0),
            ("yearly",  "YEARLY",     1, 1),
            ("vol",     "VOL / DAY",  1, 2),
        ]
        for key, label, r, c in items:
            cell = ctk.CTkFrame(grid, fg_color=C["bg_input"],
                                border_color=C["border"], border_width=1,
                                corner_radius=8)
            cell.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            ctk.CTkLabel(cell, text=label, font=FONT_SMALL,
                         text_color=C["muted"]).pack(pady=(10,4))
            lbl = ctk.CTkLabel(cell, text="₹0",
                               font=("Consolas", 14, "bold"), text_color=C["white"])
            lbl.pack(pady=(0,10))
            self._proj_labels[key] = lbl

        # Summary note
        self._proj_note = ctk.CTkLabel(out_card, text="",
            font=FONT_SMALL, text_color=C["sec"])
        self._proj_note.pack(pady=(0,12))

    # ──────────────────────────────────────────────────────────
    # ABOUT TAB
    # ──────────────────────────────────────────────────────────
    def _build_info_tab(self, parent):
        outer = ctk.CTkScrollableFrame(parent, fg_color=C["bg_base"],
                                       corner_radius=0,
                                       scrollbar_button_color=C["border"])
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        card = ctk.CTkFrame(outer, fg_color=C["bg_card"],
                            border_color=C["border"], border_width=1,
                            corner_radius=12)
        card.pack(fill="x", pady=(0,10))

        info_lines = [
            ("USDT ⇄ INR P2P Trading Calculator", "title"),
            ("Version 1.0  ·  Windows Desktop App", "sub"),
            ("", "gap"),
            ("📡  LIVE RATE (4-TIER FALLBACK)", "head"),
            ("1. FreeCryptoAPI  — USDT/INR direct", "item"),
            ("2. FreeCryptoAPI  — USDT×USD/INR", "item"),
            ("3. CoinGecko  — Free tier", "item"),
            ("4. ExchangeRate-API  — USD/INR proxy", "item"),
            ("", "gap"),
            ("⚙  FEATURES", "head"),
            ("Buy→Sell and Sell→Buy modes", "item"),
            ("INR or USDT amount input toggle", "item"),
            ("Transaction fee with slider + stepper", "item"),
            ("Real-time profit / loss calculation", "item"),
            ("Breakeven sell rate calculation", "item"),
            ("SVG-style profit curve chart", "item"),
            ("Daily / Monthly / Yearly projections", "item"),
            ("Settings persist in AppData\\Roaming\\P2PCalc", "item"),
            ("", "gap"),
            ("⚠  DISCLAIMER", "head"),
            ("For informational purposes only.", "item"),
            ("Not financial advice. Verify rates before trading.", "item"),
            ("Regenerate API key at freecryptoapi.com/panel", "item"),
        ]

        for text, kind in info_lines:
            if kind == "title":
                ctk.CTkLabel(card, text=text,
                    font=("Segoe UI", 15, "bold"), text_color=C["accent"]
                ).pack(anchor="w", padx=20, pady=(20,2))
            elif kind == "sub":
                ctk.CTkLabel(card, text=text,
                    font=FONT_SMALL, text_color=C["sec"]
                ).pack(anchor="w", padx=20)
            elif kind == "head":
                ctk.CTkLabel(card, text=text,
                    font=FONT_BODY_B, text_color=C["gold"]
                ).pack(anchor="w", padx=20, pady=(14,4))
            elif kind == "item":
                ctk.CTkLabel(card, text="  •  " + text,
                    font=FONT_BODY, text_color=C["sec"]
                ).pack(anchor="w", padx=20)
            elif kind == "gap":
                tk.Frame(card, height=4, bg=C["bg_card"]).pack()

        tk.Frame(card, height=20, bg=C["bg_card"]).pack()

    # ──────────────────────────────────────────────────────────
    # HELPERS — UI building
    # ──────────────────────────────────────────────────────────
    def _card_hdr(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(f, text=title, font=FONT_TITLE, text_color=C["sec"]).pack(side="left")

    def _make_labeled_entry(self, parent, label, var, prefix, suffix="", hint=""):
        fr = ctk.CTkFrame(parent, fg_color="transparent")
        fr.pack(fill="x", padx=16, pady=(0,10))
        lrow = ctk.CTkFrame(fr, fg_color="transparent")
        lrow.pack(fill="x")
        ctk.CTkLabel(lrow, text=label, font=FONT_SMALL,
                     text_color=C["muted"]).pack(side="left", pady=(0,4))
        if hint:
            ctk.CTkLabel(lrow, text=hint, font=FONT_SMALL,
                         text_color="#2a3f2c").pack(side="left", padx=6)
        self._make_entry(fr, var, prefix, "0.00", suffix)

    def _make_entry(self, parent, var, prefix, placeholder, suffix=""):
        row = ctk.CTkFrame(parent, fg_color=C["bg_input"],
                           border_color=C["border"], border_width=1,
                           corner_radius=8)
        row.pack(fill="x", pady=(0,0))
        ctk.CTkLabel(row, text=prefix, font=("Consolas", 12, "bold"),
                     text_color=C["sec"], width=28).pack(side="left", padx=(8,0))
        e = ctk.CTkEntry(row, textvariable=var,
            font=FONT_MONO, fg_color="transparent",
            border_width=0, text_color=C["white"],
            placeholder_text=placeholder,
            placeholder_text_color=C["muted"],
            height=42)
        e.pack(side="left", fill="x", expand=True)
        if suffix:
            ctk.CTkLabel(row, text=suffix, font=FONT_SMALL,
                         text_color=C["muted"], width=50).pack(side="left", padx=4)
        return e

    # ──────────────────────────────────────────────────────────
    # TAB SWITCHING
    # ──────────────────────────────────────────────────────────
    def _switch_tab(self, tab_id):
        for tid, btn in self._tab_btns.items():
            is_on = tid == tab_id
            btn.configure(
                text_color=C["accent"] if is_on else C["muted"],
                fg_color=C["bg_input"] if is_on else "transparent"
            )
        for tid, fr in self._frames.items():
            if tid == tab_id:
                fr.lift()

    # ──────────────────────────────────────────────────────────
    # RATE FETCH
    # ──────────────────────────────────────────────────────────
    def _bg_fetch(self):
        self._refresh_btn.configure(state="disabled", text="…")
        self._rate_lbl.configure(text="Fetching…", text_color=C["muted"])
        try:
            rate, source = fetch_live_rate()
            self._live_rate   = rate
            self._live_source = source
            self.after(0, lambda: self._rate_lbl.configure(
                text=f"₹{rate:.2f} / USDT",
                text_color=C["accent"]
            ))
            self.after(0, lambda: self._src_lbl.configure(text=source))
        except Exception as e:
            self.after(0, lambda: self._rate_lbl.configure(
                text="⚠ Unavailable", text_color=C["muted"]
            ))
        finally:
            self.after(0, lambda: self._refresh_btn.configure(
                state="normal", text="↻"
            ))

    def _apply_live(self):
        if not self._live_rate:
            messagebox.showinfo("Rate not loaded",
                                "Click ↻ to fetch the live rate first.")
            return
        r = self._live_rate
        self._var_buy.set(f"{r:.2f}")
        self._var_sell.set(f"{r * 1.005:.2f}")

    # ──────────────────────────────────────────────────────────
    # FEE CONTROLS
    # ──────────────────────────────────────────────────────────
    def _step_fee(self, delta):
        try:
            v = round(max(0.0, min(100.0, float(self._var_fee.get() or 0) + delta)), 2)
            self._var_fee.set(f"{v:.2f}")
            self._fee_slider.set(min(v, 5))
        except Exception:
            pass

    def _on_fee_slider(self, val):
        self._var_fee.set(f"{float(val):.2f}")

    # ──────────────────────────────────────────────────────────
    # AMT MODE
    # ──────────────────────────────────────────────────────────
    def _on_amt_mode(self, _=None):
        mode = self._amt_mode.get()
        if "INR" in mode:
            self._amt_label_var.set("AMOUNT TO INVEST")
        else:
            self._amt_label_var.set("USDT AMOUNT")
        self._on_change()

    # ──────────────────────────────────────────────────────────
    # CALCULATION + UI UPDATE
    # ──────────────────────────────────────────────────────────
    def _on_change(self, *_):
        try:
            amount = float(self._var_amount.get() or 0)
            buy    = float(self._var_buy.get()    or 0)
            sell   = float(self._var_sell.get()   or 0)
            fee    = float(self._var_fee.get()    or 0)
        except ValueError:
            self._clear_results()
            return

        # Sync fee slider
        try:
            self._fee_slider.set(min(fee, 5))
        except Exception:
            pass

        # Spread
        sp = sell - buy
        if sp != 0 and buy > 0:
            self._spread_lbl.configure(
                text=f"━  Spread: ₹{fmt(sp)}  ━",
                text_color=C["gold"] if sp > 0 else C["muted"]
            )
        else:
            self._spread_lbl.configure(text="")

        # Mode
        mode_str = self._mode.get()
        mode = "sell" if "Sell" in mode_str else "buy"
        amt_m = "usdt" if "USDT" in self._amt_mode.get() else "inr"

        r = do_calc(amount, amt_m, mode, buy, sell, fee)
        self._result = r
        self._chart.update_data(r)
        self._update_results(r)
        self._update_proj()
        self._auto_save()

    def _update_results(self, r):
        if not r:
            self._clear_results()
            return

        is_profit = r["profit"] >  0.001
        is_loss   = r["profit"] < -0.001
        pl_type   = "profit" if is_profit else ("loss" if is_loss else "neutral")
        val_color = C["accent"] if is_profit else (C["red"] if is_loss else C["white"])

        self._rc_usdt.set(f"{fmt(r['usdt'], 4)} ₮",    "Tether", C["white"])
        self._rc_sell.set(f"₹{fmt(r['net_sell'])}",     "Net INR return", C["gold"])
        self._rc_pl.set(
            f"{'+'  if r['profit'] >= 0 else '−'}₹{fmt(abs(r['profit']))}",
            "After fees", val_color
        )
        self._rc_pct.set(
            f"{'+'  if r['pct'] >= 0 else ''}{r['pct']:.3f}%",
            "Per trade ROI", val_color
        )

        self._be_rate.configure(text=f"₹{fmt(r['be_rate'])}")
        self._be_fee.configure (text=f"₹{fmt(r['fee_amt'])}")
        self._be_net.configure (text=f"₹{fmt(r['net_sell'])}")

        badge_txt   = f"▲ PROFIT {r['pct']:.2f}%" if is_profit else \
                      f"▼ LOSS {abs(r['pct']):.2f}%" if is_loss else "— NEUTRAL"
        badge_color = C["accent"] if is_profit else (C["red"] if is_loss else C["muted"])
        badge_bg    = "rgba(0,230,118,0.1)" if is_profit else \
                      "rgba(255,77,109,0.1)" if is_loss else C["border"]
        self._pl_badge.configure(text=badge_txt, text_color=badge_color)

    def _clear_results(self):
        self._rc_usdt.set("0.0000 ₮",  "Tether")
        self._rc_sell.set("₹0.00",     "Net INR return", C["white"])
        self._rc_pl.set  ("₹0.00",     "After fees",     C["white"])
        self._rc_pct.set ("0.000%",    "Per trade ROI",  C["white"])
        self._be_rate.configure(text="₹—")
        self._be_fee.configure (text="₹—")
        self._be_net.configure (text="₹—")
        self._pl_badge.configure(text="— NEUTRAL", text_color=C["muted"])

    def _update_proj(self):
        try:
            trades  = max(1, float(self._var_trades.get()  or 1))
            cap_str = self._var_capital.get().strip()
            capital = float(cap_str) if cap_str else (self._result["inr"] if self._result else 0)
        except Exception:
            return

        if capital <= 0 or not self._result:
            for lbl in self._proj_labels.values():
                lbl.configure(text="₹0", text_color=C["white"])
            return

        r = self._result
        # Recalc profit for this capital
        try:
            u   = capital / r["buy_rate"]
            g   = u * r["sell_rate"]
            ppt = g * (1 - r["fee"] / 100) - capital
        except ZeroDivisionError:
            ppt = 0

        daily   = ppt * trades
        weekly  = daily * 7
        monthly = daily * 30
        yearly  = daily * 365
        vol_day = capital * trades

        color = C["accent"] if ppt >= 0 else C["red"]

        self._proj_labels["trade"  ].configure(text=f"₹{fmt(abs(ppt))}",     text_color=color)
        self._proj_labels["daily"  ].configure(text=fmt_k(abs(daily)),        text_color=color)
        self._proj_labels["weekly" ].configure(text=fmt_k(abs(weekly)),       text_color=color)
        self._proj_labels["monthly"].configure(text=fmt_k(abs(monthly)),      text_color=color)
        self._proj_labels["yearly" ].configure(text=fmt_k(abs(yearly)),       text_color=color)
        self._proj_labels["vol"    ].configure(text=fmt_k(vol_day),           text_color=C["gold"])

        self._proj_note.configure(
            text=f"{int(trades)} trade{'s' if trades!=1 else ''}/day  ×  ₹{fmt(capital,0)} capital  "
                 f"@  {r['pct']:.3f}% ROI per trade"
        )

    # ──────────────────────────────────────────────────────────
    # RESET
    # ──────────────────────────────────────────────────────────
    def _reset(self):
        for v in (self._var_amount, self._var_buy, self._var_sell):
            v.set("")
        self._var_fee.set("0.00")
        self._fee_slider.set(0)
        self._result = None
        self._chart.update_data(None)
        self._clear_results()

    # ──────────────────────────────────────────────────────────
    # PULSE ANIMATION (live dot)
    # ──────────────────────────────────────────────────────────
    def _start_pulse(self):
        def pulse():
            if not self.winfo_exists():
                return
            try:
                clr = C["accent"] if self._pulse_on else "#0a4020"
                self._pulse_dot.itemconfig("dot", fill=clr)
                self._pulse_on = not self._pulse_on
            except Exception:
                pass
            self.after(900, pulse)
        pulse()

    # ──────────────────────────────────────────────────────────
    # SETTINGS PERSIST
    # ──────────────────────────────────────────────────────────
    def _auto_save(self):
        now = time.time()
        if now - self._last_saved < 1.5:
            return
        self._last_saved = now
        data = {
            "amount":   self._var_amount.get(),
            "buy":      self._var_buy.get(),
            "sell":     self._var_sell.get(),
            "fee":      self._var_fee.get(),
            "mode":     self._mode.get(),
            "amt_mode": self._amt_mode.get(),
            "trades":   self._var_trades.get(),
            "capital":  self._var_capital.get(),
        }
        threading.Thread(target=save_settings, args=(data,), daemon=True).start()

    def _restore_settings(self):
        d = self._settings
        if d.get("amount"):  self._var_amount.set(d["amount"])
        if d.get("buy"):     self._var_buy.set(d["buy"])
        if d.get("sell"):    self._var_sell.set(d["sell"])
        if d.get("fee"):
            self._var_fee.set(d["fee"])
            try:
                self._fee_slider.set(min(float(d["fee"]), 5))
            except Exception:
                pass
        if d.get("mode"):
            self._mode.set(d["mode"])
            self._seg_mode.set(d["mode"])
        if d.get("amt_mode"):
            self._amt_mode.set(d["amt_mode"])
            self._seg_amt.set(d["amt_mode"])
        if d.get("trades"):  self._var_trades.set(d["trades"])
        if d.get("capital"): self._var_capital.set(d["capital"])

# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
