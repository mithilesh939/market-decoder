"""
chart.py -- High-contrast terminal visualizations for real market telemetry.
Zero synthetic generation, zero random jitter. Ingests strictly verified outputs
from C++ benchmarks, memory scale logs, and Python risk/backtest engines.
"""

from typing import Dict, Any
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Terminal Palette matching style.py
THEME = {
    "bg": "#0B0E14",
    "paper": "#0B0E14",
    "grid": "#1E2430",
    "text": "#E8E6E0",
    "muted": "#7A8194",
    "accent": "#00D9C0",      # Bright Cyan (Zero-Copy / Approved)
    "warn": "#FFB000",        # Amber (Risk limits)
    "err": "#FF3366",         # Crimson (Rejections / Naive baseline)
    "blue": "#3399FF",        # Inventory / Latency
    "font": "'Courier New', monospace"
}

def _apply_terminal_style(fig: go.Figure, title: str, height: int = 280) -> go.Figure:
    """Applies strict dark-terminal typography and locks layouts against expansion."""
    fig.update_layout(
        title=dict(text=f"// {title}", font=dict(family=THEME["font"], size=13, color=THEME["text"])),
        height=height,
        autosize=False,
        margin=dict(l=15, r=15, t=40, b=20),
        paper_bgcolor=THEME["paper"],
        plot_bgcolor=THEME["bg"],
        font=dict(family=THEME["font"], size=11, color=THEME["muted"]),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    fig.update_xaxes(showgrid=True, gridcolor=THEME["grid"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=THEME["grid"], zeroline=False)
    return fig

def plot_benchmark_comparison(naive_mps: float, zerocopy_mps: float) -> go.Figure:
    """Renders exact throughput measurements from ./benchmark stdout."""
    speedup = zerocopy_mps / max(1.0, naive_mps)
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=["Naive (Read+Copy)", "mmap Zero-Copy"],
        x=[naive_mps / 1e6, zerocopy_mps / 1e6],
        orientation="h",
        marker=dict(color=[THEME["err"], THEME["accent"]]),
        text=[f"{naive_mps/1e6:.2f}M msgs/s", f"{zerocopy_mps/1e6:.2f}M msgs/s ({speedup:.2f}x)"],
        textposition="inside",
        insidetextfont=dict(family=THEME["font"], color="#000000", size=11)
    ))
    return _apply_terminal_style(fig, "THROUGHPUT BENCHMARK (MILLION MSGS/SEC)", height=180)

def plot_memory_scale_curve(rss_df: pd.DataFrame, file_size_mb: float) -> go.Figure:
    """
    Plots real Resident Set Size (RSS) over time from bench_scale CSV output.
    Proves memory plateaus at physical RAM ceiling instead of scaling linearly with file size.
    """
    fig = go.Figure()
    
    # Actual RSS consumption curve
    fig.add_trace(go.Scatter(
        x=rss_df["time_ms"] / 1000.0,
        y=rss_df["rss_mb"],
        mode="lines",
        name="Decoder RSS (MB)",
        line=dict(color=THEME["accent"], width=2)
    ))
    
    # Static reference line showing total file size on disk
    fig.add_hline(
        y=file_size_mb,
        line_dash="dot",
        line_color=THEME["err"],
        annotation_text=f"Total File Size ({file_size_mb:,.0f} MB)",
        annotation_position="top left",
        annotation_font=dict(family=THEME["font"], color=THEME["err"])
    )
    
    fig = _apply_terminal_style(fig, "ZERO-COPY MEMORY FOOTPRINT VS TIME (SEC)", height=260)
    fig.update_yaxes(title_text="Memory (MB)")
    fig.update_xaxes(title_text="Execution Time (s)")
    return fig

def plot_risk_rejections(decision_log: Dict[str, int]) -> go.Figure:
    """Displays authentic pre-trade risk filter rejections from verified execution logs."""
    labels = ["Accepted", "Price Collar Reject", "Inventory Limit Reject", "Order Size Reject"]
    values = [
        decision_log.get("accepted", 0),
        decision_log.get("collar_reject", 0),
        decision_log.get("inventory_reject", 0),
        decision_log.get("size_reject", 0)
    ]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=[THEME["accent"], THEME["err"], THEME["warn"], THEME["blue"]]),
        textinfo="label+value",
        textfont=dict(family=THEME["font"], size=11)
    )])
    return _apply_terminal_style(fig, "PRE-TRADE RISK ENGINE EXECUTION LOG", height=240)

def plot_backtest_trajectory(backtest_df: pd.DataFrame) -> go.Figure:
    """
    Renders dual-axis inventory and cumulative PnL from strategy/backtest.py.
    Requires continuous trade price data to show realistic execution sweeps.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Inventory Position (Step chart)
    fig.add_trace(go.Scatter(
        x=backtest_df.index,
        y=backtest_df["inventory"],
        mode="lines",
        name="Inventory (BTC)",
        line=dict(color=THEME["blue"], width=1.5, shape="hv")
    ), secondary_y=False)
    
    # Cumulative PnL
    fig.add_trace(go.Scatter(
        x=backtest_df.index,
        y=backtest_df["cumulative_pnl"],
        mode="lines",
        name="Realized PnL ($)",
        line=dict(color=THEME["accent"], width=2)
    ), secondary_y=True)

    if "realized_pnl" in backtest_df.columns:
        fig.add_trace(go.Scatter(
            x=backtest_df.index,
            y=backtest_df["realized_pnl"],
            mode="lines",
            name="Net PnL (After 5 bps Cost)",
            line=dict(color=THEME.get("red", "#FF5C5C"), width=1.5, dash="dot")
        ), secondary_y=True)
    
    fig = _apply_terminal_style(fig, "MARKET MAKER INVENTORY & PnL TRAJECTORY", height=300)
    fig.update_yaxes(title_text="Inventory (BTC)", secondary_y=False, gridcolor=THEME["grid"])
    fig.update_yaxes(title_text="PnL ($)", secondary_y=True, showgrid=False)
    return fig