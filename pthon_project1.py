"""
Zomato Restaurant Analytics Dashboard
======================================
A full-featured Python desktop app:
  - Tkinter GUI (tabbed interface)
  - SQLite database (auto-seeded from CSV)
  - Pandas & NumPy analysis
  - Matplotlib charts embedded in the GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import sys

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as mpatches

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "zomato_data.csv")
DB_PATH  = os.path.join(BASE_DIR, "zomato.db")

# ─────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────
BG        = "#1a1a2e"
CARD      = "#16213e"
ACCENT    = "#e94560"
ACCENT2   = "#0f3460"
TEXT      = "#eaeaea"
SUBTEXT   = "#a0a0c0"
GREEN     = "#4ecca3"
YELLOW    = "#f5a623"
CHART_BG  = "#0d1b2a"

COLORS = [ACCENT, GREEN, YELLOW, "#9b59b6", "#3498db", "#e67e22"]

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    """Create / connect to SQLite DB and seed from CSV."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            online_order TEXT,
            book_table  TEXT,
            rate        REAL,
            votes       INTEGER,
            approx_cost INTEGER,
            category    TEXT
        )
    """)

    # Seed only when table is empty
    cur.execute("SELECT COUNT(*) FROM restaurants")
    if cur.fetchone()[0] == 0:
        df = pd.read_csv(CSV_PATH)
        df.columns = ["name","online_order","book_table","rate","votes","approx_cost","category"]
        df["rate"] = pd.to_numeric(
            df["rate"].astype(str).str.replace("/5","", regex=False),
            errors="coerce"
        )
        df["approx_cost"] = pd.to_numeric(
            df["approx_cost"].astype(str).str.replace(",","", regex=False),
            errors="coerce"
        )
        df.dropna(subset=["name"], inplace=True)
        df.to_sql("restaurants", conn, if_exists="append", index=False)
        conn.commit()

    return conn


def load_df(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM restaurants", conn)


# ─────────────────────────────────────────────
# HELPER: styled matplotlib figure
# ─────────────────────────────────────────────

def styled_fig(rows=1, cols=1, figsize=(10, 4.5)):
    fig, axes = plt.subplots(rows, cols, figsize=figsize)
    fig.patch.set_facecolor(CHART_BG)
    for ax in (axes if hasattr(axes, "__iter__") else [axes]):
        ax.set_facecolor(CARD)
        ax.tick_params(colors=SUBTEXT, labelsize=9)
        ax.spines[:].set_color(ACCENT2)
        ax.title.set_color(TEXT)
        ax.xaxis.label.set_color(SUBTEXT)
        ax.yaxis.label.set_color(SUBTEXT)
    return fig, axes


def embed_fig(fig, parent):
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    return canvas


# ─────────────────────────────────────────────
# STAT CARD WIDGET
# ─────────────────────────────────────────────

def stat_card(parent, title: str, value: str, color: str = ACCENT):
    frame = tk.Frame(parent, bg=CARD, bd=0, relief=tk.FLAT, padx=18, pady=12)
    frame.pack(side=tk.LEFT, padx=8, pady=8, fill=tk.BOTH, expand=True)
    tk.Label(frame, text=title, bg=CARD, fg=SUBTEXT,
             font=("Segoe UI", 9)).pack(anchor="w")
    tk.Label(frame, text=value, bg=CARD, fg=color,
             font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(2,0))
    return frame


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────

class OverviewTab(tk.Frame):
    def __init__(self, parent, df, conn, *a, **kw):
        super().__init__(parent, bg=BG, *a, **kw)
        self.df   = df
        self.conn = conn
        self._build()

    def _build(self):
        # ── Stat row ──────────────────────────────
        stats_row = tk.Frame(self, bg=BG)
        stats_row.pack(fill=tk.X, padx=10, pady=(14,0))

        total       = len(self.df)
        avg_rate    = round(self.df["rate"].mean(), 2)
        avg_cost    = int(self.df["approx_cost"].mean())
        online_pct  = round(100 * (self.df["online_order"]=="Yes").sum() / total)

        stat_card(stats_row, "Total Restaurants", str(total),        GREEN)
        stat_card(stats_row, "Avg Rating",        f"⭐ {avg_rate}",  YELLOW)
        stat_card(stats_row, "Avg Cost (₹ 2)",    f"₹{avg_cost}",   ACCENT)
        stat_card(stats_row, "Online Delivery",   f"{online_pct}%",  "#3498db")

        # ── Two charts side by side ────────────────
        charts_frame = tk.Frame(self, bg=BG)
        charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Chart 1 – Category distribution
        left = tk.Frame(charts_frame, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cat_counts = self.df["category"].value_counts()
        fig1, ax1  = styled_fig(figsize=(5, 4))
        wedges, texts, autotexts = ax1.pie(
            cat_counts.values,
            labels=cat_counts.index,
            autopct="%1.1f%%",
            colors=COLORS[:len(cat_counts)],
            startangle=140,
            textprops={"color": TEXT, "fontsize": 9},
        )
        for at in autotexts:
            at.set_color(BG)
            at.set_fontweight("bold")
        ax1.set_title("Restaurant Categories", fontsize=12, pad=10)
        fig1.tight_layout()
        embed_fig(fig1, left)

        # Chart 2 – Rating histogram
        right = tk.Frame(charts_frame, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        fig2, ax2 = styled_fig(figsize=(5, 4))
        ax2.hist(self.df["rate"].dropna(), bins=15, color=ACCENT, edgecolor=CHART_BG, alpha=0.9)
        ax2.set_xlabel("Rating (out of 5)")
        ax2.set_ylabel("# Restaurants")
        ax2.set_title("Rating Distribution", fontsize=12)
        fig2.tight_layout()
        embed_fig(fig2, right)


class ChartsTab(tk.Frame):
    def __init__(self, parent, df, conn, *a, **kw):
        super().__init__(parent, bg=BG, *a, **kw)
        self.df   = df
        self.conn = conn
        self._build()

    def _build(self):
        title = tk.Label(self, text="Deep Dive Charts", bg=BG, fg=ACCENT,
                         font=("Segoe UI", 13, "bold"))
        title.pack(pady=(12, 4), anchor="w", padx=14)

        # ── Row 1 ──────────────────────────────────
        row1 = tk.Frame(self, bg=BG)
        row1.pack(fill=tk.BOTH, expand=True, padx=10)

        # Avg rating by category – horizontal bar
        left1 = tk.Frame(row1, bg=BG)
        left1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        avg_by_cat = self.df.groupby("category")["rate"].mean().sort_values()
        fig1, ax1  = styled_fig(figsize=(5, 3.5))
        bars = ax1.barh(avg_by_cat.index, avg_by_cat.values,
                        color=COLORS[:len(avg_by_cat)])
        ax1.set_xlim(0, 5)
        ax1.set_xlabel("Average Rating")
        ax1.set_title("Avg Rating by Category", fontsize=11)
        for bar, val in zip(bars, avg_by_cat.values):
            ax1.text(val + 0.05, bar.get_y() + bar.get_height()/2,
                     f"{val:.2f}", va="center", color=TEXT, fontsize=9)
        fig1.tight_layout()
        embed_fig(fig1, left1)

        # Cost distribution box plot
        right1 = tk.Frame(row1, bg=BG)
        right1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cats = self.df["category"].unique()
        data = [self.df[self.df["category"]==c]["approx_cost"].dropna().values for c in cats]
        fig2, ax2 = styled_fig(figsize=(5, 3.5))
        bp = ax2.boxplot(data, patch_artist=True, labels=cats, notch=False)
        for patch, color in zip(bp["boxes"], COLORS):
            patch.set_facecolor(color)
            patch.set_alpha(0.8)
        for element in ["whiskers","caps","medians","fliers"]:
            for item in bp[element]:
                item.set_color(TEXT)
        ax2.set_ylabel("Approx Cost (₹)")
        ax2.set_title("Cost Distribution by Category", fontsize=11)
        ax2.tick_params(axis="x", rotation=15)
        fig2.tight_layout()
        embed_fig(fig2, right1)

        # ── Row 2 ──────────────────────────────────
        row2 = tk.Frame(self, bg=BG)
        row2.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        # Online vs offline by category – stacked bar
        left2 = tk.Frame(row2, bg=BG)
        left2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        pivot = self.df.groupby(["category","online_order"]).size().unstack(fill_value=0)
        x     = np.arange(len(pivot))
        w     = 0.35
        fig3, ax3 = styled_fig(figsize=(5, 3.5))
        b1 = ax3.bar(x - w/2, pivot.get("Yes", [0]*len(x)), w, label="Online ✓", color=GREEN, alpha=0.9)
        b2 = ax3.bar(x + w/2, pivot.get("No",  [0]*len(x)), w, label="Offline ✗", color=ACCENT, alpha=0.9)
        ax3.set_xticks(x)
        ax3.set_xticklabels(pivot.index, rotation=12)
        ax3.set_ylabel("Count")
        ax3.set_title("Online vs Offline by Category", fontsize=11)
        ax3.legend(labelcolor=TEXT, facecolor=CARD, edgecolor=ACCENT2, fontsize=8)
        fig3.tight_layout()
        embed_fig(fig3, left2)

        # Scatter: cost vs rating
        right2 = tk.Frame(row2, bg=BG)
        right2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        clean = self.df.dropna(subset=["rate","approx_cost"])
        cat_list = clean["category"].unique()
        cmap     = {c: COLORS[i % len(COLORS)] for i, c in enumerate(cat_list)}
        fig4, ax4 = styled_fig(figsize=(5, 3.5))
        for cat in cat_list:
            sub = clean[clean["category"]==cat]
            ax4.scatter(sub["approx_cost"], sub["rate"],
                        color=cmap[cat], label=cat, alpha=0.75, s=40)
        # Trend line
        x_arr = clean["approx_cost"].values
        y_arr = clean["rate"].values
        z     = np.polyfit(x_arr, y_arr, 1)
        p     = np.poly1d(z)
        xs    = np.linspace(x_arr.min(), x_arr.max(), 200)
        ax4.plot(xs, p(xs), "--", color=YELLOW, linewidth=1.5, label="Trend")
        ax4.set_xlabel("Approx Cost (₹)")
        ax4.set_ylabel("Rating")
        ax4.set_title("Cost vs Rating (with trend)", fontsize=11)
        ax4.legend(labelcolor=TEXT, facecolor=CARD, edgecolor=ACCENT2, fontsize=7,
                   loc="lower right")
        fig4.tight_layout()
        embed_fig(fig4, right2)


class DataTab(tk.Frame):
    def __init__(self, parent, df, conn, *a, **kw):
        super().__init__(parent, bg=BG, *a, **kw)
        self.df     = df
        self.conn   = conn
        self._build()

    def _build(self):
        # ── Toolbar ───────────────────────────────
        toolbar = tk.Frame(self, bg=CARD, pady=8)
        toolbar.pack(fill=tk.X)

        tk.Label(toolbar, text="Filter:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(12,4))

        # Category filter
        self.cat_var = tk.StringVar(value="All")
        cats = ["All"] + sorted(self.df["category"].dropna().unique().tolist())
        cat_menu = ttk.Combobox(toolbar, textvariable=self.cat_var, values=cats,
                                width=14, state="readonly")
        cat_menu.pack(side=tk.LEFT, padx=4)
        cat_menu.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        # Online filter
        self.online_var = tk.StringVar(value="All")
        ttk.Combobox(toolbar, textvariable=self.online_var,
                     values=["All","Yes","No"], width=8,
                     state="readonly").pack(side=tk.LEFT, padx=4)

        tk.Button(toolbar, text="Apply", command=self._refresh,
                  bg=ACCENT, fg="white", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side=tk.LEFT, padx=6)

        # Search
        tk.Label(toolbar, text="Search:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(20,4))
        self.search_var = tk.StringVar()
        tk.Entry(toolbar, textvariable=self.search_var, bg=ACCENT2,
                 fg=TEXT, insertbackground=TEXT, relief=tk.FLAT,
                 font=("Segoe UI", 9), width=20).pack(side=tk.LEFT, padx=4)
        tk.Button(toolbar, text="🔍", command=self._refresh,
                  bg=ACCENT2, fg=TEXT, relief=tk.FLAT).pack(side=tk.LEFT)

        self.count_lbl = tk.Label(toolbar, text="", bg=CARD, fg=SUBTEXT,
                                  font=("Segoe UI", 9))
        self.count_lbl.pack(side=tk.RIGHT, padx=12)

        # ── Treeview ──────────────────────────────
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Zomato.Treeview",
            background=CARD, foreground=TEXT, rowheight=24,
            fieldbackground=CARD, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Zomato.Treeview.Heading",
            background=ACCENT2, foreground=TEXT, relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"))
        style.map("Zomato.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "white")])

        cols = ("Name","Category","Rating","Votes","Cost (₹)","Online","Table")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="Zomato.Treeview")
        widths = [200, 100, 70, 70, 90, 70, 70]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col,
                command=lambda c=col: self._sort_col(c))
            self.tree.column(col, width=w, anchor=tk.CENTER)
        self.tree.column("Name", anchor=tk.W)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._refresh()

    def _refresh(self):
        df = self.df.copy()
        if self.cat_var.get() != "All":
            df = df[df["category"] == self.cat_var.get()]
        if self.online_var.get() != "All":
            df = df[df["online_order"] == self.online_var.get()]
        q = self.search_var.get().strip().lower()
        if q:
            df = df[df["name"].str.lower().str.contains(q, na=False)]

        self.count_lbl.config(text=f"Showing {len(df)} restaurants")
        for item in self.tree.get_children():
            self.tree.delete(item)

        for _, row in df.iterrows():
            rate_str = f"{row['rate']:.1f} ⭐" if pd.notna(row["rate"]) else "N/A"
            cost_str = f"₹{int(row['approx_cost'])}" if pd.notna(row["approx_cost"]) else "N/A"
            self.tree.insert("", tk.END, values=(
                row["name"], row["category"], rate_str,
                int(row["votes"]) if pd.notna(row["votes"]) else "N/A",
                cost_str, row["online_order"], row["book_table"]
            ))

    def _sort_col(self, col):
        col_map = {"Name":"name","Category":"category","Rating":"rate",
                   "Votes":"votes","Cost (₹)":"approx_cost",
                   "Online":"online_order","Table":"book_table"}
        self.df.sort_values(col_map[col], inplace=True,
                            ascending=True, na_position="last")
        self._refresh()


class QueryTab(tk.Frame):
    def __init__(self, parent, df, conn, *a, **kw):
        super().__init__(parent, bg=BG, *a, **kw)
        self.df   = df
        self.conn = conn
        self._build()

    def _build(self):
        # SQL area
        sql_frame = tk.Frame(self, bg=CARD, pady=10, padx=12)
        sql_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(sql_frame, text="SQL Query", bg=CARD, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.sql_text = tk.Text(sql_frame, height=5, bg=ACCENT2, fg=TEXT,
                                insertbackground=TEXT, font=("Courier New", 10),
                                relief=tk.FLAT, padx=8, pady=6)
        self.sql_text.insert("1.0",
            "SELECT category, ROUND(AVG(rate),2) as avg_rating,\n"
            "       COUNT(*) as count\n"
            "FROM restaurants\n"
            "GROUP BY category\n"
            "ORDER BY avg_rating DESC;")
        self.sql_text.pack(fill=tk.X)

        btn_row = tk.Frame(sql_frame, bg=CARD)
        btn_row.pack(fill=tk.X, pady=(8,0))
        tk.Button(btn_row, text="▶  Run Query", command=self._run,
                  bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"),
                  relief=tk.FLAT, padx=14, pady=4).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Clear", command=lambda: self.sql_text.delete("1.0", tk.END),
                  bg=ACCENT2, fg=TEXT, font=("Segoe UI", 9),
                  relief=tk.FLAT, padx=10, pady=4).pack(side=tk.LEFT, padx=6)
        self.status = tk.Label(btn_row, text="", bg=CARD, fg=GREEN,
                               font=("Segoe UI", 9))
        self.status.pack(side=tk.LEFT, padx=10)

        # Result table
        res_frame = tk.Frame(self, bg=BG)
        res_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        self.result_tree = ttk.Treeview(res_frame, show="headings",
                                        style="Zomato.Treeview")
        vsb = ttk.Scrollbar(res_frame, orient="vertical",
                             command=self.result_tree.yview)
        hsb = ttk.Scrollbar(res_frame, orient="horizontal",
                             command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=vsb.set,
                                   xscrollcommand=hsb.set)
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        res_frame.rowconfigure(0, weight=1)
        res_frame.columnconfigure(0, weight=1)

    def _run(self):
        sql = self.sql_text.get("1.0", tk.END).strip()
        if not sql:
            return
        try:
            df = pd.read_sql_query(sql, self.conn)
            # reset columns
            self.result_tree["columns"] = list(df.columns)
            for col in df.columns:
                self.result_tree.heading(col, text=col)
                self.result_tree.column(col, width=130, anchor=tk.CENTER)
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            for _, row in df.iterrows():
                self.result_tree.insert("", tk.END, values=list(row))
            self.status.config(text=f"✓ {len(df)} rows returned", fg=GREEN)
        except Exception as exc:
            self.status.config(text=f"✗ {exc}", fg=ACCENT)
            messagebox.showerror("SQL Error", str(exc))


class StatsTab(tk.Frame):
    def __init__(self, parent, df, conn, *a, **kw):
        super().__init__(parent, bg=BG, *a, **kw)
        self.df   = df
        self.conn = conn
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win_id, width=e.width))

        # ── NumPy stats ──────────────────────────
        def section(title):
            tk.Label(inner, text=title, bg=BG, fg=ACCENT,
                     font=("Segoe UI", 11, "bold")).pack(
                     anchor="w", padx=16, pady=(14,2))

        def row(label, value, color=TEXT):
            f = tk.Frame(inner, bg=CARD)
            f.pack(fill=tk.X, padx=16, pady=2)
            tk.Label(f, text=label, bg=CARD, fg=SUBTEXT,
                     font=("Segoe UI", 9), width=36, anchor="w").pack(side=tk.LEFT, padx=8, pady=5)
            tk.Label(f, text=str(value), bg=CARD, fg=color,
                     font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)

        df = self.df
        rates  = df["rate"].dropna().values
        costs  = df["approx_cost"].dropna().values
        votes  = df["votes"].dropna().values

        section("📊 Ratings (NumPy analysis)")
        row("Mean",            f"{np.mean(rates):.3f}",        YELLOW)
        row("Median",          f"{np.median(rates):.3f}",      YELLOW)
        row("Std Dev",         f"{np.std(rates):.3f}",         YELLOW)
        row("Variance",        f"{np.var(rates):.3f}",         YELLOW)
        row("Min / Max",       f"{np.min(rates):.1f}  /  {np.max(rates):.1f}", GREEN)
        row("25th Percentile", f"{np.percentile(rates,25):.2f}", SUBTEXT)
        row("75th Percentile", f"{np.percentile(rates,75):.2f}", SUBTEXT)
        row("IQR",             f"{np.percentile(rates,75)-np.percentile(rates,25):.2f}", SUBTEXT)

        section("💰 Approx Cost for Two (₹)")
        row("Mean",   f"₹{np.mean(costs):.0f}",  YELLOW)
        row("Median", f"₹{np.median(costs):.0f}", YELLOW)
        row("Min",    f"₹{np.min(costs):.0f}",    GREEN)
        row("Max",    f"₹{np.max(costs):.0f}",    ACCENT)
        row("Std Dev",f"₹{np.std(costs):.0f}",    SUBTEXT)

        section("👍 Votes")
        row("Total Votes",  f"{int(np.sum(votes)):,}",     YELLOW)
        row("Average",      f"{np.mean(votes):.0f}",       YELLOW)
        row("Most votes",   f"{int(np.max(votes)):,}",     GREEN)
        row("Fewest votes", f"{int(np.min(votes)):,}",     ACCENT)

        # Correlation
        corr = np.corrcoef(
            df.dropna(subset=["rate","approx_cost"])[["rate","approx_cost"]].T
        )
        section("🔗 Correlation")
        row("Rating ↔ Cost (Pearson r)",
            f"{corr[0,1]:.4f}  {'(positive)' if corr[0,1]>0 else '(negative)'}",
            GREEN if corr[0,1]>0 else ACCENT)

        # Category breakdown
        section("🏷️ Category Breakdown")
        for cat, grp in df.groupby("category"):
            pct = 100*len(grp)/len(df)
            row(f"{cat}",
                f"{len(grp)} restaurants  ({pct:.1f}%)  avg ⭐{grp['rate'].mean():.2f}",
                COLORS[list(df["category"].unique()).index(cat) % len(COLORS)])


# ─────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────

class ZomatoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🍽️  Zomato Restaurant Analytics")
        self.geometry("1200x740")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self.conn = init_db()
        self.df   = load_df(self.conn)

        self._build_header()
        self._build_tabs()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self):
        hdr = tk.Frame(self, bg=ACCENT, height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        tk.Label(hdr, text="🍽️  Zomato Restaurant Analytics Dashboard",
                 bg=ACCENT, fg="white",
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=16, pady=10)
        tk.Label(hdr, text=f"DB: {DB_PATH}",
                 bg=ACCENT, fg="white",
                 font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=16)

    def _build_tabs(self):
        style = ttk.Style()
        style.configure("TNotebook",          background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",
            background=CARD, foreground=SUBTEXT,
            font=("Segoe UI", 9, "bold"),
            padding=[14,6])
        style.map("TNotebook.Tab",
            background=[("selected", ACCENT)],
            foreground=[("selected", "white")])

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        tabs = [
            ("📈 Overview",  OverviewTab),
            ("📊 Charts",    ChartsTab),
            ("🗃️ Data",      DataTab),
            ("🔍 SQL Query", QueryTab),
            ("🧮 Stats",     StatsTab),
        ]
        for label, TabClass in tabs:
            frame = TabClass(nb, self.df, self.conn)
            nb.add(frame, text=label)

    def _on_close(self):
        self.conn.close()
        plt.close("all")
        self.destroy()


if __name__ == "__main__":
    app = ZomatoApp()
    app.mainloop()
