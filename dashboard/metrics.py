"""
MarketFlow Telemetry & Observability State Bridge
Simulates real-time system metrics from the C++ Zero-Copy Engine and Python Risk/MM engines.
"""

import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class SystemState:
    # Dataset & Replay
    total_trades: int = 81_239_595
    processed_messages: int = 14_520_000
    replay_status: str = "PROCESSING"
    replay_speed: str = "10x"
    start_time: float = field(default_factory=time.time)
    current_timestamp: str = "2025-06-05 14:22:01.482910"
    
    # Throughput & HW Observability
    current_mps: float = 485_230.0
    rolling_mps: List[float] = field(default_factory=lambda: [450000.0] * 60)
    cpu_usage: float = 42.4
    mem_usage: float = 38.1
    disk_read_mb: float = 142.8
    ring_buffer_util: float = 64.2
    queue_size: int = 1284
    fps: int = 60
    
    # Latency Telemetry (nanoseconds / microseconds)
    dec_lat_avg: float = 34.2      # ns
    dec_lat_p99: float = 88.5      # ns
    risk_lat_avg: float = 1.12     # us
    risk_lat_p99: float = 3.45     # us
    strat_lat_avg: float = 2.05    # us
    e2e_lat_avg: float = 3.20      # us
    latency_hist_bins: List[int] = field(default_factory=lambda: [120, 450, 1800, 3200, 1500, 400, 80, 12, 2, 0])
    
    # Market Data & Order Book
    current_price: float = 104_591.88
    vwap: float = 104_540.12
    trade_volume: float = 18_420.50
    largest_trade: float = 45.00
    price_change_pct: float = +2.45
    bid_price: float = 104_591.80
    ask_price: float = 104_591.88
    bid_vol: float = 14.25
    ask_vol: float = 9.80
    
    # Risk Engine Rejections
    orders_accepted: int = 342_100
    orders_rejected: int = 1_420
    rej_price_collar: int = 850
    rej_inventory: int = 420
    rej_size: int = 150
    kill_switch_active: bool = False
    
    # Market Maker & PnL
    position: float = +2.50
    avg_entry: float = 104_510.00
    realized_pnl: float = 14_250.80
    unrealized_pnl: float = +204.70
    quotes_sent: int = 684_200
    orders_filled: int = 4_120
    
    # Performance Benchmark (Naive vs Zero-Copy)
    naive_mps: float = 2_150_000.0
    zerocopy_mps: float = 68_400_000.0
    memcpy_count: int = 0
    alloc_count: int = 0

    def step(self):
        """Simulate a live telemetry tick from the background execution engine."""
        if self.replay_status != "PROCESSING":
            return

        # Advance processed messages
        delta_msgs = int(self.current_mps * 0.1) # 100ms tick
        self.processed_messages = min(self.total_trades, self.processed_messages + delta_msgs)
        
        # Add realistic micro-jitter to throughput & latency
        self.current_mps = np.clip(np.random.normal(485_000, 15_000), 300_000, 700_000)
        self.rolling_mps.append(self.current_mps)
        if len(self.rolling_mps) > 60:
            self.rolling_mps.pop(0)
            
        # Jitter HW metrics
        self.cpu_usage = np.clip(np.random.normal(45.0, 3.0), 10.0, 95.0)
        self.ring_buffer_util = np.clip(np.random.normal(65.0, 5.0), 10.0, 99.0)
        
        # Random walk market price
        price_step = np.random.normal(0, 1.5)
        self.current_price += price_step
        self.bid_price = self.current_price - 0.04
        self.ask_price = self.current_price + 0.04
        
        # Update MM position and PnL
        if np.random.random() < 0.3:
            fill_qty = np.random.choice([-0.5, 0.5])
            self.position = np.clip(self.position + fill_qty, -10.0, 10.0)
            self.orders_filled += 1
            self.realized_pnl += max(0, fill_qty * (self.current_price - self.avg_entry))
            
        self.unrealized_pnl = self.position * (self.current_price - self.avg_entry)

# Global singleton representing active engine state
engine_state = SystemState()

def get_telemetry_snapshot() -> Dict[str, Any]:
    """Returns a serialized dictionary of the system state for UI rendering."""
    engine_state.step()
    s = engine_state
    
    elapsed_sec = time.time() - s.start_time
    rem_msgs = s.total_trades - s.processed_messages
    rem_sec = rem_msgs / max(1.0, s.current_mps)
    progress_pct = (s.processed_messages / s.total_trades) * 100.0
    
    return {
        "header": {
            "dataset": "BTCUSDT June 2025 (81.2M)",
            "status": s.replay_status,
            "speed_lbl": s.replay_speed,
            "mps": f"{s.current_mps:,.0f}",
            "elapsed": time.strftime("%H:%M:%S", time.gmtime(elapsed_sec)),
            "remaining": time.strftime("%H:%M:%S", time.gmtime(rem_sec)),
            "timestamp": s.current_timestamp,
            "cpu": f"{s.cpu_usage:.1f}%",
            "mem": f"{s.mem_usage:.1f}%",
            "disk": f"{s.disk_read_mb:.1f} MB/s"
        },
        "health": {
            "Decoder": "OK", "Replay Engine": "OK", "Risk Engine": "OK", 
            "Strategy Engine": "OK", "Dashboard": "OK", "Market Data Reader": "OK",
            "CSV Streaming": "IDLE", "Binary Decoder": "OK"
        },
        "latency": {
            "dec_avg": f"{s.dec_lat_avg:.1f} ns", "dec_p99": f"{s.dec_lat_p99:.1f} ns",
            "risk_avg": f"{s.risk_lat_avg:.2f} µs", "risk_p99": f"{s.risk_lat_p99:.2f} µs",
            "strat_avg": f"{s.strat_lat_avg:.2f} µs", "e2e_avg": f"{s.e2e_lat_avg:.2f} µs",
            "hist_bins": s.latency_hist_bins
        },
        "throughput": {
            "mps_num": s.current_mps, "tps": f"{s.current_mps * 0.12:,.0f}",
            "processed": f"{s.processed_messages:,}", "remaining": f"{rem_msgs:,}",
            "progress": f"{progress_pct:.2f}%", "rolling_mps": s.rolling_mps
        },
        "market": {
            "price": f"${s.current_price:,.2f}", "vwap": f"${s.vwap:,.2f}",
            "vol": f"{s.trade_volume:,.2f} BTC", "largest": f"{s.largest_trade:.2f} BTC",
            "change": f"{s.price_change_pct:+.2f}%"
        },
        "orderbook": {
            "bid": f"{s.bid_price:,.2f}", "ask": f"{s.ask_price:,.2f}",
            "spread": f"{(s.ask_price - s.bid_price):.2f} (0.04 bps)",
            "mid": f"{((s.bid_price + s.ask_price)/2):,.2f}",
            "bid_vol": f"{s.bid_vol:.2f}", "ask_vol": f"{s.ask_vol:.2f}",
            "imbalance": f"{((s.bid_vol - s.ask_vol)/(s.bid_vol + s.ask_vol)*100):+.1f}%"
        },
        "risk": {
            "accepted": f"{s.orders_accepted:,}", "rejected": f"{s.orders_rejected:,}",
            "collar_rej": s.rej_price_collar, "inv_rej": s.rej_inventory,
            "size_rej": s.rej_size, "kill_switch": "ENGAGED" if s.kill_switch_active else "ARMED / OK"
        },
        "mm": {
            "pos": f"{s.position:+.2f} BTC", "avg_entry": f"${s.avg_entry:,.2f}",
            "pnl_total": f"${(s.realized_pnl + s.unrealized_pnl):,.2f}",
            "pnl_realized": f"${s.realized_pnl:,.2f}", "pnl_unrealized": f"${s.unrealized_pnl:+.2f}",
            "quotes": f"{s.quotes_sent:,}", "filled": f"{s.orders_filled:,}",
            "fill_ratio": f"{(s.orders_filled / max(1, s.quotes_sent)*100):.3f}%"
        },
        "strategy_analytics": {
            "sharpe": "3.84", "win_rate": "68.4%", "avg_trade": "+$12.40",
            "max_dd": "-$1,240.00 (-0.8%)", "profit_factor": "2.41", "exposure": f"${abs(s.position)*s.current_price:,.0f}"
        },
        "performance": {
            "naive_mps": f"{s.naive_mps/1e6:.2f}M msgs/s",
            "zerocopy_mps": f"{s.zerocopy_mps/1e6:.2f}M msgs/s",
            "improvement": f"{(s.zerocopy_mps / s.naive_mps):.1f}x Speedup",
            "cache_miss": "< 0.02%", "mem_alloc": f"{s.alloc_count}", "memcpy": f"{s.memcpy_count}",
            "zerocopy_pct": "100.00%"
        },
        "observability": {
            "cpu": s.cpu_usage, "mem": s.mem_usage, "disk_val": s.disk_read_mb,
            "q_size": f"{s.queue_size:,}", "ring_util": s.ring_buffer_util,
            "events_wait": "14", "thread_util": "88.4%", "fps": f"{s.fps}"
        }
    }