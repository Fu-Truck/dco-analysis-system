import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy import stats
from scipy.stats import norm
import warnings
import io
from datetime import datetime
import platform
import tempfile
import os
import sys

warnings.filterwarnings('ignore')

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="DCO Analysis System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 强制设置英文字体 ====================
# 在Linux环境中使用英文字体，避免中文显示问题
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 自定义CSS样式 ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2563EB;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #E5E7EB;
    }
    .metric-card {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid #E5E7EB;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6B7280;
    }
    .stButton > button {
        width: 100%;
        background-color: #2563EB;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 标题区域 ====================
st.markdown('<h1 class="main-header">📊 DCO Analysis System</h1>', unsafe_allow_html=True)
st.markdown("---")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⚙️ Control Panel")
    st.markdown("---")
    
    st.info("📌 Version: Complete Statistical Analysis")
    
    batch_file = st.file_uploader(
        "**Batch Data** (DCO-batch data.xlsx)",
        type=['xlsx', 'xls']
    )
    
    activity_file = st.file_uploader(
        "**Activity Data** (DCO-activity data.xlsx)",
        type=['xlsx', 'xls']
    )
    
    st.markdown("---")
    
    analysis_points = st.number_input(
        "SPC Analysis Points",
        min_value=10,
        max_value=500,
        value=100,
        step=10
    )
    
    time_threshold = st.number_input(
        "Time Elapsed Threshold (seconds)",
        min_value=3600,
        max_value=36000,
        value=10800,
        step=600
    )
    
    show_details = st.checkbox("Show Detailed Statistics", value=True)
    
    st.markdown("---")
    run_button = st.button("🚀 Start Analysis", type="primary", use_container_width=True)

# ==================== 批次数据分析函数 ====================
def analyze_batch_data(df, analysis_points=100, time_threshold=10800):
    """
    Batch data analysis: Data cleaning, SPC analysis, anomaly detection
    """
    results = {
        'cleaning_steps': [],
        'statistics': {},
        'anomalies': None,
        'figures': {}
    }
    
    # ========== Data Cleaning ==========
    original_rows = len(df)
    results['cleaning_steps'].append(f"Original rows: {original_rows}")
    
    # 1. Remove null in Process Order ID
    df = df.dropna(subset=['Process Order ID'])
    results['cleaning_steps'].append(f"After removing null Process Order ID: {len(df)}")
    
    # 2. Remove duplicates
    df = df.drop_duplicates(subset=['Process Order ID'], keep='first')
    results['cleaning_steps'].append(f"After removing duplicates: {len(df)}")
    
    # 3. Remove null in End date/time
    df = df.dropna(subset=['End date/time'])
    results['cleaning_steps'].append(f"After removing null End date/time: {len(df)}")
    
    # 4. Keep only "干清" type
    df = df[df['Type'] == '干清']
    results['cleaning_steps'].append(f"After filtering '干清' type: {len(df)}")
    
    # 5. Keep specified lines
    allowed_locations = ['CP Line 9', 'CP Line 10', 'CP Line 11', 'CP Line 12', 'CP Line 05', 'CP Line 08']
    df = df[df['Location'].isin(allowed_locations)]
    results['cleaning_steps'].append(f"After filtering specified lines: {len(df)}")
    
    # 6. Remove Time Elapsed > threshold
    if 'Time Elapsed (seconds)' in df.columns:
        before_count = len(df)
        df = df[df['Time Elapsed (seconds)'] <= time_threshold]
        removed_count = before_count - len(df)
        results['cleaning_steps'].append(f"After removing Time Elapsed > {time_threshold}: {len(df)} (removed {removed_count})")
    
    # 7. Convert seconds to minutes
    columns_to_convert = ['Time Elapsed (seconds)', 'Planned Duration (seconds)', 
                          'Changeover Planned/Actual Difference (seconds)']
    
    for col in columns_to_convert:
        if col in df.columns:
            df[col] = (df[col] / 60).round(2)
            new_col_name = col.replace('(seconds)', '(minutes)')
            df.rename(columns={col: new_col_name}, inplace=True)
    
    results['cleaning_steps'].append(f"\nCleaning complete, final rows: {len(df)}")
    results['cleaning_steps'].append(f"Total removed: {original_rows - len(df)} rows")
    
    # ========== SPC Analysis Preparation ==========
    df['End date/time'] = pd.to_datetime(df['End date/time'])
    
    df_sorted = df.sort_values('End date/time', ascending=False).head(analysis_points)
    df_sorted = df_sorted.sort_values('End date/time', ascending=True)
    
    data_column = 'Time Elapsed (minutes)'
    target_column = 'Planned Duration (minutes)'
    
    if data_column not in df_sorted.columns:
        time_columns = [col for col in df_sorted.columns if 'Time Elapsed' in col]
        if time_columns:
            data_column = time_columns[0]
    
    if target_column not in df_sorted.columns:
        planned_columns = [col for col in df_sorted.columns if 'Planned' in col]
        if planned_columns:
            target_column = planned_columns[0]
    
    if data_column not in df_sorted.columns or target_column not in df_sorted.columns:
        st.error("Required columns not found")
        return None
    
    data_values = df_sorted[data_column].values
    target_values = df_sorted[target_column].values
    n_points = len(data_values)
    
    # ========== Statistical Calculations ==========
    overall_mean = np.mean(data_values)
    overall_median = np.median(data_values)
    overall_std = np.std(data_values, ddof=1)
    
    overall_mode_result = stats.mode(data_values, keepdims=True)
    overall_mode = overall_mode_result.mode[0]
    overall_mode_count = overall_mode_result.count[0]
    
    sorted_data = np.sort(data_values)
    front_10_percentile = np.percentile(sorted_data, 10)
    back_10_percentile = np.percentile(sorted_data, 90)
    front_25_percentile = np.percentile(sorted_data, 25)
    back_25_percentile = np.percentile(sorted_data, 75)
    
    min_value = np.min(data_values)
    max_value = np.max(data_values)
    range_value = max_value - min_value
    
    target_mean = np.mean(target_values)
    
    ucl = target_mean * 1.2
    lcl = max(0, target_mean * 0.8)
    uwl = target_mean * 1.5
    lwl = max(0, target_mean * 0.5)
    
    green_lower = target_mean * 0.8
    green_upper = target_mean * 1.2
    yellow_upper_lower = target_mean * 1.2
    yellow_upper_upper = target_mean * 1.5
    yellow_lower_lower = target_mean * 0.5
    yellow_lower_upper = target_mean * 0.8
    red_upper_lower = target_mean * 1.5
    red_upper_upper = max(target_mean * 3, 300)
    red_lower_lower = 0
    red_lower_upper = target_mean * 0.5
    
    usl = target_mean * 1.2
    lsl = target_mean * 0.8
    
    cpu = (usl - overall_mean) / (3 * overall_std) if overall_std > 0 else 0
    cpl = (overall_mean - lsl) / (3 * overall_std) if overall_std > 0 else 0
    cpk = min(cpu, cpl)
    
    std_total = np.std(data_values, ddof=0)
    ppu = (usl - overall_mean) / (3 * std_total) if std_total > 0 else 0
    ppl = (overall_mean - lsl) / (3 * std_total) if std_total > 0 else 0
    ppk = min(ppu, ppl)
    
    cp = (usl - lsl) / (6 * overall_std) if overall_std > 0 else 0
    
    results['statistics'] = {
        'n_points': n_points,
        'overall_mean': overall_mean,
        'overall_median': overall_median,
        'overall_std': overall_std,
        'overall_mode': overall_mode,
        'overall_mode_count': overall_mode_count,
        'front_10_percentile': front_10_percentile,
        'back_10_percentile': back_10_percentile,
        'front_25_percentile': front_25_percentile,
        'back_25_percentile': back_25_percentile,
        'min_value': min_value,
        'max_value': max_value,
        'range_value': range_value,
        'target_mean': target_mean,
        'ucl': ucl,
        'lcl': lcl,
        'uwl': uwl,
        'lwl': lwl,
        'usl': usl,
        'lsl': lsl,
        'cp': cp,
        'cpk': cpk,
        'ppk': ppk
    }
    
    # ========== Create SPC Chart (English labels) ==========
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1]})
    
    x_values = range(len(data_values))
    n_front_10 = max(1, int(n_points * 0.1))
    n_back_10 = max(1, int(n_points * 0.1))
    
    # Top: SPC Control Chart - ALL LABELS IN ENGLISH
    ax1.axhspan(red_lower_lower, red_lower_upper, alpha=0.2, color='red', label='Zone A (Red: <50% Target)')
    ax1.axhspan(yellow_lower_lower, yellow_lower_upper, alpha=0.2, color='yellow', label='Zone B (Yellow: 50%-80% Target)')
    ax1.axhspan(green_lower, green_upper, alpha=0.2, color='green', label='Zone C (Green: 80%-120% Target)')
    ax1.axhspan(yellow_upper_lower, yellow_upper_upper, alpha=0.2, color='yellow')
    ax1.axhspan(red_upper_lower, red_upper_upper, alpha=0.2, color='red')
    
    # Plot data points
    ax1.plot(x_values, data_values, 'o-', color='blue', markersize=4, label='Actual Value (min)')
    
    # Statistical lines
    ax1.axhline(y=overall_mean, color='darkblue', linestyle='--', linewidth=1.5, alpha=0.7, label=f'Mean: {overall_mean:.2f}')
    ax1.axhline(y=overall_median, color='darkgreen', linestyle='--', linewidth=1.5, alpha=0.7, label=f'Median: {overall_median:.2f}')
    ax1.axhline(y=overall_mode, color='darkorange', linestyle='--', linewidth=1.5, alpha=0.7, label=f'Mode: {overall_mode:.2f}')
    ax1.axhline(y=target_mean, color='purple', linestyle='-.', linewidth=2, label=f'Target: {target_mean:.2f}')
    ax1.axhline(y=ucl, color='red', linestyle='--', linewidth=2, label=f'UCL (+20%): {ucl:.2f}')
    ax1.axhline(y=lcl, color='red', linestyle='--', linewidth=2, label=f'LCL (-20%): {lcl:.2f}')
    ax1.axhline(y=uwl, color='orange', linestyle=':', linewidth=2, label=f'UWL (+50%): {uwl:.2f}')
    ax1.axhline(y=lwl, color='orange', linestyle=':', linewidth=2, label=f'LWL (-50%): {lwl:.2f}')
    ax1.axhline(y=usl, color='darkred', linestyle='-', linewidth=1.5, label=f'USL: {usl:.2f}')
    ax1.axhline(y=lsl, color='darkred', linestyle='-', linewidth=1.5, label=f'LSL: {lsl:.2f}')
    
    # Mark top/bottom 10% regions
    ax1.axvspan(0, n_front_10-1, alpha=0.1, color='lightblue', label=f'Top 10% (Points 1-{n_front_10})')
    ax1.axvspan(n_points - n_back_10, n_points-1, alpha=0.1, color='lightcoral', label=f'Bottom 10% (Points {n_points - n_back_10 + 1}-{n_points})')
    
    # ========== Anomaly Detection ==========
    anomaly_records = []
    
    # Rule 1: Point outside Zone A
    for i, value in enumerate(data_values):
        if value > ucl or value < lcl:
            rule = "Rule 1: Point outside Zone A"
            location = df_sorted.iloc[i]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[i]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[i]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
            anomaly_records.append({
                'Point': i+1,
                'Line': location,
                'Batch ID': process_id,
                'Time': date_time,
                'Value': round(value, 2),
                'Target': round(target_values[i], 2),
                'Deviation': round(value - target_values[i], 2),
                'Rule': rule
            })
            ax1.plot(i, value, 'ro', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='Rule 1' if i == 0 else "")
    
    # Rule 2: 9 consecutive points on same side
    def check_consecutive_on_one_side(data, target, n=9):
        anomalies = []
        for i in range(len(data) - n + 1):
            segment = data[i:i+n]
            if all(x > target for x in segment):
                for j in range(i, i+n):
                    anomalies.append(j)
            elif all(x < target for x in segment):
                for j in range(i, i+n):
                    anomalies.append(j)
        return list(set(anomalies))
    
    rule2_anomalies = check_consecutive_on_one_side(data_values, target_mean, 9)
    for idx in rule2_anomalies:
        if idx not in [a['Point']-1 for a in anomaly_records]:
            rule = "Rule 2: 9 points on same side"
            location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
            anomaly_records.append({
                'Point': idx+1,
                'Line': location,
                'Batch ID': process_id,
                'Time': date_time,
                'Value': round(data_values[idx], 2),
                'Target': round(target_values[idx], 2),
                'Deviation': round(data_values[idx] - target_values[idx], 2),
                'Rule': rule
            })
            ax1.plot(idx, data_values[idx], 'yo', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='Rule 2' if idx == rule2_anomalies[0] else "")
    
    # Rule 3: 6 points increasing or decreasing
    def check_trend(data, n=6):
        anomalies = []
        for i in range(len(data) - n + 1):
            segment = data[i:i+n]
            if all(segment[j] < segment[j+1] for j in range(n-1)):
                for j in range(i, i+n):
                    anomalies.append(j)
            elif all(segment[j] > segment[j+1] for j in range(n-1)):
                for j in range(i, i+n):
                    anomalies.append(j)
        return list(set(anomalies))
    
    rule3_anomalies = check_trend(data_values, 6)
    for idx in rule3_anomalies:
        if idx not in [a['Point']-1 for a in anomaly_records]:
            rule = "Rule 3: 6 points trend"
            location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
            anomaly_records.append({
                'Point': idx+1,
                'Line': location,
                'Batch ID': process_id,
                'Time': date_time,
                'Value': round(data_values[idx], 2),
                'Target': round(target_values[idx], 2),
                'Deviation': round(data_values[idx] - target_values[idx], 2),
                'Rule': rule
            })
            ax1.plot(idx, data_values[idx], 'go', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='Rule 3' if idx == rule3_anomalies[0] else "")
    
    # Rule 4: 14 points alternating
    def check_alternating(data, n=14):
        anomalies = []
        for i in range(len(data) - n + 1):
            segment = data[i:i+n]
            is_alternating = True
            for j in range(n-1):
                if j % 2 == 0:
                    if not (segment[j] < segment[j+1]):
                        is_alternating = False
                        break
                else:
                    if not (segment[j] > segment[j+1]):
                        is_alternating = False
                        break
            if is_alternating:
                for j in range(i, i+n):
                    anomalies.append(j)
        return list(set(anomalies))
    
    rule4_anomalies = check_alternating(data_values, 14)
    for idx in rule4_anomalies:
        if idx not in [a['Point']-1 for a in anomaly_records]:
            rule = "Rule 4: 14 points alternating"
            location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
            anomaly_records.append({
                'Point': idx+1,
                'Line': location,
                'Batch ID': process_id,
                'Time': date_time,
                'Value': round(data_values[idx], 2),
                'Target': round(target_values[idx], 2),
                'Deviation': round(data_values[idx] - target_values[idx], 2),
                'Rule': rule
            })
            ax1.plot(idx, data_values[idx], 'mo', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='Rule 4' if idx == rule4_anomalies[0] else "")
    
    # Chart properties
    ax1.set_ylim(bottom=0, top=min(300, max(data_values) * 1.2))
    ax1.set_xlabel('Data Point (Chronological)', fontsize=12)
    ax1.set_ylabel('Time (minutes)', fontsize=12)
    ax1.set_title('SPC Control Chart - Target Based Control Limits', fontsize=14, fontweight='bold')
    
    # Handle duplicate legends
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax1.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=8, ncol=2)
    
    ax1.grid(True, alpha=0.3)
    
    # X-axis labels
    if len(x_values) <= 20:
        xtick_labels = [d.strftime('%m-%d %H:%M') for d in df_sorted['End date/time']]
        ax1.set_xticks(x_values)
        ax1.set_xticklabels(xtick_labels, rotation=45, ha='right', fontsize=8)
    else:
        step = len(x_values) // 10
        xtick_positions = x_values[::step]
        xtick_labels = [df_sorted['End date/time'].iloc[i].strftime('%m-%d %H:%M') for i in xtick_positions]
        ax1.set_xticks(xtick_positions)
        ax1.set_xticklabels(xtick_labels, rotation=45, ha='right', fontsize=8)
    
    # Bottom: Process Capability Chart
    ax2.hist(data_values, bins=20, density=True, alpha=0.7, color='skyblue', edgecolor='black', label='Actual Distribution')
    x_norm = np.linspace(max(0, min(data_values)), max(data_values), 100)
    y_norm = norm.pdf(x_norm, overall_mean, std_total)
    ax2.plot(x_norm, y_norm, 'r-', linewidth=2, label='Normal Distribution Fit')
    
    # Mark specification limits and statistics
    ax2.axvline(x=usl, color='darkred', linestyle='--', linewidth=2, label=f'USL: {usl:.2f}')
    ax2.axvline(x=lsl, color='darkred', linestyle='--', linewidth=2, label=f'LSL: {lsl:.2f}')
    ax2.axvline(x=target_mean, color='purple', linestyle='-.', linewidth=2, label=f'Target: {target_mean:.2f}')
    ax2.axvline(x=overall_mean, color='black', linestyle='-', linewidth=2, label=f'Mean: {overall_mean:.2f}')
    ax2.axvline(x=overall_median, color='darkgreen', linestyle='--', linewidth=1.5, alpha=0.7, label=f'Median: {overall_median:.2f}')
    ax2.axvline(x=overall_mode, color='darkorange', linestyle='--', linewidth=1.5, alpha=0.7, label=f'Mode: {overall_mode:.2f}')
    
    # Mark percentiles
    ax2.axvline(x=front_10_percentile, color='blue', linestyle=':', linewidth=1.5, alpha=0.7, label=f'10th Pctl: {front_10_percentile:.2f}')
    ax2.axvline(x=back_10_percentile, color='red', linestyle=':', linewidth=1.5, alpha=0.7, label=f'90th Pctl: {back_10_percentile:.2f}')
    ax2.axvline(x=front_25_percentile, color='lightblue', linestyle=':', linewidth=1.5, alpha=0.7, label=f'25th Pctl: {front_25_percentile:.2f}')
    ax2.axvline(x=back_25_percentile, color='lightcoral', linestyle=':', linewidth=1.5, alpha=0.7, label=f'75th Pctl: {back_25_percentile:.2f}')
    
    ax2.set_xlim(left=0, right=min(300, max(data_values) * 1.2))
    ax2.set_xlabel('Time (minutes)', fontsize=12)
    ax2.set_ylabel('Probability Density', fontsize=12)
    ax2.set_title('Process Capability & Distribution Analysis', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    results['figures']['spc_chart'] = fig
    
    # Create anomaly DataFrame
    if anomaly_records:
        anomaly_df = pd.DataFrame(anomaly_records)
        anomaly_df = anomaly_df.drop_duplicates(subset=['Batch ID', 'Time'])
        anomaly_df = anomaly_df.sort_values('Point')
        results['anomalies'] = anomaly_df
    
    return results

# ==================== 活动数据分析函数 ====================
def analyze_activity_data(df):
    """
    Activity data analysis: Data cleaning, phase analysis
    """
    results = {
        'cleaning_steps': [],
        'phase_analysis': {},
        'figures': {}
    }
    
    original_rows = len(df)
    results['cleaning_steps'].append(f"Original rows: {original_rows}")
    
    area_list = ['CPLine 9', 'CP Line 10', 'CP Line 11', 'CP Line 12', 'CP Line 05', 'CP Line08']
    df = df[df['Area'].isin(area_list)]
    results['cleaning_steps'].append(f"After filtering lines: {len(df)}")
    
    df = df[df['Changeover Type'] == '干清']
    results['cleaning_steps'].append(f"After filtering '干清' type: {len(df)}")
    
    original_count = len(df)
    df = df.dropna(subset=['Actual Duration (seconds)'])
    removed_count = original_count - len(df)
    results['cleaning_steps'].append(f"After removing null Actual Duration: {len(df)} (removed {removed_count})")
    
    if 'Actual Duration (seconds)' in df.columns:
        df['Actual Duration (minutes)'] = (df['Actual Duration (seconds)'] / 60).round(2)
    
    results['cleaning_steps'].append(f"\nCleaning complete, final rows: {len(df)}")
    
    if 'PO Number' in df.columns:
        total_batches = df['PO Number'].nunique()
        results['batch_info'] = {
            'total_batches': total_batches,
            'total_records': len(df)
        }
        
        if 'Created At' in df.columns:
            df['Created At'] = pd.to_datetime(df['Created At'])
            results['batch_info']['time_range'] = f"{df['Created At'].min()} to {df['Created At'].max()}"
    
    phases = ['Pre-cleaning', 'Cleaning', 'Changeover', 'Line Configuration']
    phase_map = {
        'Pre-cleaning': '清场前准备',
        'Cleaning': '清场',
        'Changeover': '切换',
        'Line Configuration': '产线配置'
    }
    
    for eng_phase, chn_phase in phase_map.items():
        phase_data = df[df['Phase Name'] == chn_phase]
        
        if len(phase_data) == 0:
            continue
        
        avg_duration = phase_data['Actual Duration (minutes)'].mean()
        min_duration = phase_data['Actual Duration (minutes)'].min()
        max_duration = phase_data['Actual Duration (minutes)'].max()
        std_duration = phase_data['Actual Duration (minutes)'].std()
        
        activity_duration = phase_data.groupby('Task Description')['Actual Duration (minutes)'].agg(['mean', 'min', 'max', 'count']).round(2)
        activity_duration = activity_duration.sort_values('mean', ascending=False)
        
        if 'Operator' in phase_data.columns:
            operator_duration = phase_data.groupby('Operator')['Actual Duration (minutes)'].agg(['mean', 'min', 'max', 'count']).round(2)
            operator_duration = operator_duration.sort_values('mean')
        else:
            operator_duration = pd.DataFrame()
        
        fastest_record = phase_data.loc[phase_data['Actual Duration (minutes)'].idxmin()] if len(phase_data) > 0 else None
        slowest_record = phase_data.loc[phase_data['Actual Duration (minutes)'].idxmax()] if len(phase_data) > 0 else None
        
        fastest_info = {}
        slowest_info = {}
        
        if fastest_record is not None:
            fastest_info = {
                'Time': fastest_record.get('Actual Duration (minutes)', 'N/A'),
                'Operator': fastest_record.get('Operator', 'N/A'),
                'Activity': fastest_record.get('Task Description', 'N/A'),
                'Batch': fastest_record.get('PO Number', 'N/A')
            }
        
        if slowest_record is not None:
            slowest_info = {
                'Time': slowest_record.get('Actual Duration (minutes)', 'N/A'),
                'Operator': slowest_record.get('Operator', 'N/A'),
                'Activity': slowest_record.get('Task Description', 'N/A'),
                'Batch': slowest_record.get('PO Number', 'N/A')
            }
        
        results['phase_analysis'][eng_phase] = {
            'avg_time': avg_duration,
            'min_time': min_duration,
            'max_time': max_duration,
            'std_dev': std_duration,
            'activity_count': len(activity_duration),
            'record_count': len(phase_data),
            'top_activities': activity_duration.head(5) if len(activity_duration) > 0 else pd.DataFrame(),
            'top_operators': operator_duration.head(5) if len(operator_duration) > 0 else pd.DataFrame(),
            'fastest_record': fastest_info,
            'slowest_record': slowest_info
        }
    
    return results

# ==================== Main Program ====================
if run_button:
    if batch_file is None or activity_file is None:
        st.warning("⚠️ Please upload both batch data and activity data files!")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # ========== Batch Data Analysis ==========
            status_text.text("📊 Analyzing batch data...")
            progress_bar.progress(20)
            
            batch_df = pd.read_excel(batch_file)
            
            with st.spinner("Executing batch data analysis..."):
                batch_results = analyze_batch_data(batch_df, analysis_points, time_threshold)
            
            if batch_results:
                st.markdown('<h2 class="sub-header">📈 Batch Data Analysis Results</h2>', unsafe_allow_html=True)
                
                batch_tab1, batch_tab2, batch_tab3, batch_tab4 = st.tabs(["Data Cleaning", "SPC Chart", "Complete Statistics", "Anomaly Detection"])
                
                with batch_tab1:
                    st.markdown("### 🔄 Data Cleaning Steps")
                    for step in batch_results['cleaning_steps']:
                        st.write(f"- {step}")
                
                with batch_tab2:
                    if 'spc_chart' in batch_results['figures']:
                        st.pyplot(batch_results['figures']['spc_chart'])
                        
                        if show_details:
                            st.markdown("### 📊 Basic Statistics")
                            stats = batch_results['statistics']
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Mean", f"{stats['overall_mean']:.2f}min")
                                st.metric("Median", f"{stats['overall_median']:.2f}min")
                            with col2:
                                st.metric("Std Dev", f"{stats['overall_std']:.2f}")
                                st.metric("Mode", f"{stats['overall_mode']:.2f}")
                            with col3:
                                st.metric("Min", f"{stats['min_value']:.2f}min")
                                st.metric("Max", f"{stats['max_value']:.2f}min")
                            with col4:
                                st.metric("Range", f"{stats['range_value']:.2f}min")
                                st.metric("CPK", f"{stats['cpk']:.3f}")
                
                with batch_tab3:
                    st.markdown("### 📊 Complete Statistics")
                    stats = batch_results['statistics']
                    
                    st.markdown("#### 📈 Overall Statistics")
                    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                    with col_a1:
                        st.info(f"**Mean**: {stats['overall_mean']:.2f}min")
                    with col_a2:
                        st.info(f"**Median**: {stats['overall_median']:.2f}min")
                    with col_a3:
                        st.info(f"**Mode**: {stats['overall_mode']:.2f}min ({stats['overall_mode_count']} times)")
                    with col_a4:
                        st.info(f"**Std Dev**: {stats['overall_std']:.2f}")
                    
                    st.markdown("#### 📊 Percentile Analysis")
                    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
                    with col_b1:
                        st.success(f"**10th Pctl**: {stats['front_10_percentile']:.2f}min")
                    with col_b2:
                        st.success(f"**90th Pctl**: {stats['back_10_percentile']:.2f}min")
                    with col_b3:
                        st.success(f"**25th Pctl**: {stats['front_25_percentile']:.2f}min")
                    with col_b4:
                        st.success(f"**75th Pctl**: {stats['back_25_percentile']:.2f}min")
                    
                    st.markdown("#### ⚡ Extreme Values")
                    col_c1, col_c2, col_c3 = st.columns(3)
                    with col_c1:
                        st.warning(f"**Min**: {stats['min_value']:.2f}min")
                    with col_c2:
                        st.warning(f"**Max**: {stats['max_value']:.2f}min")
                    with col_c3:
                        st.warning(f"**Range**: {stats['range_value']:.2f}min")
                    
                    st.markdown("#### 🎯 Process Capability")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        st.metric("CP", f"{stats['cp']:.3f}")
                    with col_d2:
                        st.metric("CPK", f"{stats['cpk']:.3f}")
                    with col_d3:
                        st.metric("PPK", f"{stats['ppk']:.3f}")
                    
                    cpk = stats['cpk']
                    if cpk >= 1.33:
                        st.success("✅ **Capable** - Process meets specifications")
                    elif cpk >= 1.0:
                        st.warning("⚠️ **Marginally Capable** - Needs monitoring")
                    else:
                        st.error("❌ **Not Capable** - Needs improvement")
                
                with batch_tab4:
                    if batch_results['anomalies'] is not None and len(batch_results['anomalies']) > 0:
                        st.markdown(f"### ⚠️ Found {len(batch_results['anomalies'])} anomalies")
                        
                        rule_counts = batch_results['anomalies']['Rule'].value_counts()
                        for rule, count in rule_counts.items():
                            st.warning(f"{rule}: {count} anomalies")
                        
                        st.dataframe(batch_results['anomalies'], use_container_width=True, hide_index=True)
                        
                        csv = batch_results['anomalies'].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Anomaly Data",
                            data=csv,
                            file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.success("✅ No anomalies detected")
            
            progress_bar.progress(50)
            
            # ========== Activity Data Analysis ==========
            status_text.text("📋 Analyzing activity data...")
            activity_df = pd.read_excel(activity_file)
            
            with st.spinner("Executing activity data analysis..."):
                activity_results = analyze_activity_data(activity_df)
            
            if activity_results:
                st.markdown('<h2 class="sub-header">📋 Activity Data Analysis Results</h2>', unsafe_allow_html=True)
                
                activity_tab1, activity_tab2 = st.tabs(["Data Cleaning", "Phase Analysis"])
                
                with activity_tab1:
                    st.markdown("### 🔄 Data Cleaning Steps")
                    for step in activity_results['cleaning_steps']:
                        st.write(f"- {step}")
                    
                    if 'batch_info' in activity_results:
                        st.markdown("### 📊 Batch Information")
                        info = activity_results['batch_info']
                        st.info(f"Total Batches: {info['total_batches']} | Total Records: {info['total_records']}")
                        if 'time_range' in info:
                            st.write(f"Time Range: {info['time_range']}")
                
                with activity_tab2:
                    if activity_results['phase_analysis']:
                        phase_summary = []
                        for phase, analysis in activity_results['phase_analysis'].items():
                            phase_summary.append({
                                'Phase': phase,
                                'Avg Time': round(analysis['avg_time'], 2),
                                'Min Time': round(analysis['min_time'], 2),
                                'Max Time': round(analysis['max_time'], 2),
                                'Std Dev': round(analysis['std_dev'], 2),
                                'Activities': analysis['activity_count'],
                                'Records': analysis['record_count']
                            })
                        
                        if phase_summary:
                            phase_df = pd.DataFrame(phase_summary)
                            st.dataframe(phase_df, use_container_width=True, hide_index=True)
                            
                            # Create comparison chart
                            fig_phase, axes = plt.subplots(1, 2, figsize=(14, 5))
                            
                            x = range(len(phase_df))
                            width = 0.25
                            
                            axes[0].bar([i - width for i in x], phase_df['Avg Time'], width, label='Avg Time', color='#3B82F6')
                            axes[0].bar(x, phase_df['Min Time'], width, label='Min Time', color='#10B981')
                            axes[0].bar([i + width for i in x], phase_df['Max Time'], width, label='Max Time', color='#EF4444')
                            
                            axes[0].set_xlabel('Phase')
                            axes[0].set_ylabel('Time (minutes)')
                            axes[0].set_title('Phase Time Comparison')
                            axes[0].set_xticks(x)
                            axes[0].set_xticklabels(phase_df['Phase'], rotation=45)
                            axes[0].legend()
                            axes[0].grid(True, alpha=0.3)
                            
                            axes[1].bar(phase_df['Phase'], phase_df['Std Dev'], color='#F59E0B')
                            axes[1].set_xlabel('Phase')
                            axes[1].set_ylabel('Std Dev')
                            axes[1].set_title('Phase Stability Comparison')
                            axes[1].tick_params(axis='x', rotation=45)
                            axes[1].grid(True, alpha=0.3)
                            
                            plt.tight_layout()
                            st.pyplot(fig_phase)
                        
                        for phase, analysis in activity_results['phase_analysis'].items():
                            with st.expander(f"### 📌 {phase} Phase Details"):
                                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                                with col_p1:
                                    st.metric("Avg Time", f"{analysis['avg_time']:.2f}min")
                                with col_p2:
                                    st.metric("Min Time", f"{analysis['min_time']:.2f}min")
                                with col_p3:
                                    st.metric("Max Time", f"{analysis['max_time']:.2f}min")
                                with col_p4:
                                    st.metric("Std Dev", f"{analysis['std_dev']:.2f}")
                                
                                col_record1, col_record2 = st.columns(2)
                                with col_record1:
                                    st.markdown("#### ⚡ Fastest Record")
                                    if analysis['fastest_record']:
                                        st.success(
                                            f"**Time**: {analysis['fastest_record']['Time']}min\n\n"
                                            f"**Operator**: {analysis['fastest_record']['Operator']}\n\n"
                                            f"**Activity**: {analysis['fastest_record']['Activity']}\n\n"
                                            f"**Batch**: {analysis['fastest_record']['Batch']}"
                                        )
                                    else:
                                        st.info("No data")
                                
                                with col_record2:
                                    st.markdown("#### 🐢 Slowest Record")
                                    if analysis['slowest_record']:
                                        st.error(
                                            f"**Time**: {analysis['slowest_record']['Time']}min\n\n"
                                            f"**Operator**: {analysis['slowest_record']['Operator']}\n\n"
                                            f"**Activity**: {analysis['slowest_record']['Activity']}\n\n"
                                            f"**Batch**: {analysis['slowest_record']['Batch']}"
                                        )
                                    else:
                                        st.info("No data")
                                
                                if not analysis['top_activities'].empty:
                                    st.markdown("#### ⏱️ Most Time-Consuming Activities")
                                    st.dataframe(analysis['top_activities'], use_container_width=True)
                                
                                if not analysis['top_operators'].empty:
                                    st.markdown("#### 👤 Most Efficient Operators")
                                    st.dataframe(analysis['top_operators'], use_container_width=True)
                    else:
                        st.warning("No phase analysis data found")
            
            progress_bar.progress(100)
            status_text.text("✅ Analysis Complete!")
            
            st.markdown("---")
            st.markdown('<h2 class="sub-header">📋 Summary</h2>', unsafe_allow_html=True)
            
            col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
            
            with col_sum1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">Total Batches</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-value">{len(batch_df)}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">Anomalies</p>', unsafe_allow_html=True)
                anomaly_count = len(batch_results['anomalies']) if batch_results and batch_results['anomalies'] is not None else 0
                st.markdown(f'<p class="metric-value">{anomaly_count}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">Total Activities</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-value">{len(activity_df)}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">CPK</p>', unsafe_allow_html=True)
                cpk_value = batch_results['statistics']['cpk'] if batch_results else 0
                st.markdown(f'<p class="metric-value">{cpk_value:.3f}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ Error during analysis: {str(e)}")
            st.exception(e)

else:
    st.markdown("""
    <div style="text-align: center; padding: 3rem;">
        <h2 style="color: #1E3A8A;">Welcome to DCO Analysis System</h2>
        <p style="color: #4B5563; font-size: 1.2rem;">Please upload data files in the left panel to start analysis</p>
        <div style="margin-top: 2rem;">
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📊 SPC Chart
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                🔍 Anomaly Detection
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📈 Statistics
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                ⚡ Extreme Values
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_func1, col_func2 = st.columns(2)
    
    with col_func1:
        st.markdown("""
        #### 📈 Batch Analysis Features
        - Auto data cleaning (7 steps)
        - SPC control chart (Red-Yellow-Green zones)
        - 4 control rules detection
        - Complete statistics (mean, median, mode)
        - Percentile analysis (10th/90th, 25th/75th)
        - Normal distribution fit
        """)
    
    with col_func2:
        st.markdown("""
        #### 📋 Activity Analysis Features
        - Auto data cleaning
        - 4 phase analysis
        - Phase statistics (mean, min, max, std dev)
        - Fastest and slowest records
        - Most time-consuming activities
        - Most efficient operators
        """)

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        <p>DCO Analysis System v4.0 | English Version - Guaranteed Label Display</p>
        <p style="font-size: 0.8rem;">© 2024 All Rights Reserved</p>
    </div>
    """,
    unsafe_allow_html=True
)
