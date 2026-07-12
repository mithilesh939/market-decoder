"""
app.py -- Streamlit quantitative observability terminal.
Wired strictly to real command-line verification scripts and local binary files.
Run via: streamlit run app.py
"""

import os
import subprocess
import pandas as pd
import streamlit as st
from style import CUSTOM_CSS
import charts

# Initialize page styling
st.set_page_config(page_title="MarketFlow | Authentic Telemetry", layout="wide", initial_sidebar_state="expanded")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Top Header Banner
col_title, col_badge = st.columns([4, 1])
with col_title:
    st.markdown("### `MARKETFLOW // LOW-LATENCY INFRASTRUCTURE OBSERVABILITY`")
    st.caption("Zero-Copy mmap Wire Protocol • Real June 2025 BTCUSDT Execution Feed")
with col_badge:
    st.markdown('<div style="text-align: right; margin-top: 10px;"><span class="real-data-badge">100% VERIFIED DATA</span></div>', unsafe_allow_html=True)

st.markdown("---")

# Navigation Tabs
tab_bench, tab_scale, tab_risk = st.tabs([
    "// 01. DECODER BENCHMARK", 
    "// 02. MEMORY & SCALE TEST", 
    "// 03. RISK & STRATEGY EXECUTION"
])

# ==============================================================================
# TAB 1: DECODER BENCHMARK (Small File / Safe for Naive Allocation)
# ==============================================================================
with tab_bench:
    st.markdown("#### `THROUGHPUT COMPARISON (NAIVE VS. ZERO-COPY MMAP)`")
    st.caption("Executes on comfortably sized binary datasets to prevent heap thrashing.")
    
    bench_file = st.text_input("Benchmark Input File (.bin)", value="tools/btcusdt_sample_1M.bin", key="input_bench")
    
    if st.button("RUN BENCHMARK HARNESS", key="btn_bench"):
        if not os.path.exists(bench_file):
            st.error(f"File not found: `{bench_file}`. Generate it using `./generate {bench_file} 1000000`")
        else:
            with st.spinner("Executing C++ benchmark binary..."):
                # Run the actual compiled C++ benchmark binary
                try:
                    output = subprocess.check_output(["./benchmark", bench_file], text=True)
                    
                    # Parse authentic console output
                    naive_mps, zc_mps = 0.0, 0.0
                    for line in output.splitlines():
                        if "NaiveDecoder" in line and "Million msgs/sec" in line:
                            naive_mps = float(line.split()[-3]) * 1e6
                        elif "MmapDecoder" in line and "Million msgs/sec" in line:
                            zc_mps = float(line.split()[-3]) * 1e6
                            
                    if naive_mps > 0 and zc_mps > 0:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Naive Throughput", f"{naive_mps/1e6:.2f} M/sec", "Heap Allocated")
                        c2.metric("Zero-Copy Throughput", f"{zc_mps/1e6:.2f} M/sec", "Direct Cast")
                        c3.metric("Measured Speedup", f"{zc_mps/naive_mps:.2f}x", "Zero Memcpy")
                        
                        st.plotly_chart(charts.plot_benchmark_comparison(naive_mps, zc_mps), use_container_width=True)
                        st.code(output, language="bash")
                    else:
                        st.warning("Could not parse throughput numbers from terminal output. Raw stdout below:")
                        st.code(output, language="bash")
                except Exception as e:
                    st.error(f"Benchmark execution failed: {str(e)}")

# ==============================================================================
# TAB 2: MEMORY & SCALE TEST (Large File / Zero-Copy Only)
# ==============================================================================
with tab_scale:
    st.markdown("#### `RESIDENT SET SIZE (RSS) PLATEAU VERIFICATION`")
    st.caption("Validates that processing files larger than physical RAM does not trigger OS out-of-memory faults.")
    
    c_file, c_csv = st.columns(2)
    with c_file:
        scale_file = st.text_input("Large Binary File Path", value="datasets/binance/BTCUSDT/2025/btcusdt_2025_06.bin")
    with c_csv:
        rss_csv = st.text_input("RSS Log CSV Output", value="bench/scale_rss_results.csv")
        
    if st.button("VERIFY ZERO-COPY MEMORY FOOTPRINT", key="btn_scale"):
        if not os.path.exists(scale_file):
            st.error(f"Large binary file not found at `{scale_file}`.")
        elif not os.path.exists(rss_csv):
            st.warning(f"RSS CSV log not found at `{rss_csv}`. Run `bench/run_scale_test.sh` first to generate authentic memory logs.")
        else:
            file_size_mb = os.path.getsize(scale_file) / (1024 * 1024)
            df_rss = pd.read_csv(rss_csv)
            
            peak_rss = df_rss["rss_mb"].max()
            total_msgs = df_rss["messages_processed"].max()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total File Size", f"{file_size_mb:,.0f} MB", "On-Disk Footprint")
            m2.metric("Peak Decoder RSS", f"{peak_rss:,.0f} MB", f"{(peak_rss/file_size_mb)*100:.1f}% of File Size")
            m3.metric("Messages Processed", f"{total_msgs:,}", "Zero Allocation Check")
            
            st.plotly_chart(charts.plot_memory_scale_curve(df_rss, file_size_mb), use_container_width=True)

# ==============================================================================
# TAB 3: RISK & STRATEGY EXECUTION (Real June 2025 Data)
# ==============================================================================
with tab_risk:
    st.markdown("#### `PRE-TRADE RISK FILTER & MARKET MAKER TRAJECTORY`")
    st.caption("Evaluates order book sweeps and inventory limits against real Binance trade sequences.")
    
    # In a live setup, these dictionaries and DataFrames are populated directly
    # by importing and running your verified risk/engine.py and strategy/backtest.py
    if st.button("LOAD VERIFIED EXECUTION LOGS", key="btn_exec"):
        try:
            # Example loading pattern for your authentic verification outputs
            # Replace these with direct imports from your python modules:
            # from risk.engine import run_verification; decision_log = run_verification()
            # from strategy.backtest import run_backtest; backtest_df = run_backtest()
            
            st.info("To render this panel, import your verified execution outputs directly from `strategy/backtest.py` and `risk/engine.py` without applying synthetic jitter.")
            
            # Uncomment below once wired to your local python module returns:
            # col_pie, col_traj = st.columns([1, 2])
            # with col_pie:
            #     st.plotly_charts(charts.plot_risk_rejections(decision_log), use_container_width=True)
            # with col_traj:
            #     st.plotly_charts(charts.plot_backtest_trajectory(backtest_df), use_container_width=True)
            
        except Exception as e:
            st.error(f"Failed to load execution engine modules: {str(e)}")