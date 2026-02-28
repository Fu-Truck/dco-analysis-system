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
    page_title="DCO综合分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    .section-header {
        font-size: 1.2rem;
        color: #374151;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .stat-box {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #2563EB;
    }
    .warning-box {
        background-color: #FEF3C7;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #F59E0B;
    }
    .info-box {
        background-color: #E0F2FE;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #0EA5E9;
    }
    .success-box {
        background-color: #D1FAE5;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #10B981;
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
        border: none;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .stButton > button:hover {
        background-color: #1D4ED8;
    }
    .dataframe {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 设置sklearn不可用标志 ====================
# 由于我们完全移除了sklearn依赖，直接设置为False
SKLEARN_AVAILABLE = False

# ==================== 标题区域 ====================
st.markdown('<h1 class="main-header">📊 DCO综合分析系统</h1>', unsafe_allow_html=True)
st.markdown("---")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⚙️ 控制面板")
    st.markdown("---")
    
    # 显示提示信息
    st.info("📌 当前版本：批次分析 + 活动分析（不含机器学习）")
    
    # 文件上传区域
    st.markdown("### 📂 数据上传")
    
    batch_file = st.file_uploader(
        "**批次数据** (DCO-batch data.xlsx)",
        type=['xlsx', 'xls'],
        help="上传包含批次信息的Excel文件"
    )
    
    activity_file = st.file_uploader(
        "**活动数据** (DCO-activity data.xlsx)",
        type=['xlsx', 'xls'],
        help="上传包含活动信息的Excel文件"
    )
    
    st.markdown("---")
    
    # 分析设置
    st.markdown("### ⚡ 分析设置")
    
    analysis_points = st.number_input(
        "SPC分析数据点数",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="选择用于SPC分析的最新数据点数量"
    )
    
    time_threshold = st.number_input(
        "Time Elapsed阈值 (秒)",
        min_value=3600,
        max_value=36000,
        value=10800,
        step=600,
        help="删除Time Elapsed大于此值的数据"
    )
    
    show_details = st.checkbox(
        "显示详细统计信息",
        value=True,
        help="勾选以显示详细的统计分析结果"
    )
    
    st.markdown("---")
    
    # 执行按钮
    run_button = st.button("🚀 开始全面分析", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📌 使用说明")
    st.info(
        "1. 上传批次数据和活动数据Excel文件\n"
        "2. 设置分析参数\n"
        "3. 点击'开始全面分析'按钮\n"
        "4. 系统将执行：\n"
        "   - 批次数据清洗\n"
        "   - SPC控制图分析\n"
        "   - 异常点检测\n"
        "   - 活动数据清洗\n"
        "   - 阶段详细分析"
    )

# ==================== 批次数据分析函数 ====================
def analyze_batch_data(df, analysis_points=100, time_threshold=10800):
    """
    批次数据分析：数据清洗、SPC分析、异常检测
    """
    results = {
        'cleaning_steps': [],
        'statistics': {},
        'anomalies': None,
        'figures': {}
    }
    
    # ========== 数据清洗 ==========
    original_rows = len(df)
    results['cleaning_steps'].append(f"原始数据行数: {original_rows}")
    
    # 1. 删除Process Order ID空值
    df = df.dropna(subset=['Process Order ID'])
    results['cleaning_steps'].append(f"删除G列空值后行数: {len(df)}")
    
    # 2. 删除重复值
    df = df.drop_duplicates(subset=['Process Order ID'], keep='first')
    results['cleaning_steps'].append(f"删除G列重复值后行数: {len(df)}")
    
    # 3. 删除End date/time空值
    df = df.dropna(subset=['End date/time'])
    results['cleaning_steps'].append(f"删除K列空值后行数: {len(df)}")
    
    # 4. 保留"干清"类型
    df = df[df['Type'] == '干清']
    results['cleaning_steps'].append(f"保留'干清'类型后行数: {len(df)}")
    
    # 5. 保留指定产线
    allowed_locations = ['CP Line 9', 'CP Line 10', 'CP Line 11', 'CP Line 12', 'CP Line 05', 'CP Line 08']
    df = df[df['Location'].isin(allowed_locations)]
    results['cleaning_steps'].append(f"保留指定产线后行数: {len(df)}")
    
    # 6. 删除Time Elapsed大于阈值的数据
    if 'Time Elapsed (seconds)' in df.columns:
        before_count = len(df)
        df = df[df['Time Elapsed (seconds)'] <= time_threshold]
        removed_count = before_count - len(df)
        results['cleaning_steps'].append(f"删除Time Elapsed > {time_threshold}的数据后行数: {len(df)} (删除了{removed_count}行)")
    
    # 7. 将秒转换为分钟
    columns_to_convert = ['Time Elapsed (seconds)', 'Planned Duration (seconds)', 
                          'Changeover Planned/Actual Difference (seconds)']
    
    for col in columns_to_convert:
        if col in df.columns:
            df[col] = (df[col] / 60).round(2)
            new_col_name = col.replace('(seconds)', '(minutes)')
            df.rename(columns={col: new_col_name}, inplace=True)
    
    results['cleaning_steps'].append(f"\n清洗完成，最终数据行数: {len(df)}")
    results['cleaning_steps'].append(f"共删除了 {original_rows - len(df)} 行数据")
    
    # ========== SPC分析 ==========
    # 确保日期列是datetime类型
    df['End date/time'] = pd.to_datetime(df['End date/time'])
    
    # 按日期降序排序，取前N个数据，再按时间升序排列
    df_sorted = df.sort_values('End date/time', ascending=False).head(analysis_points)
    df_sorted = df_sorted.sort_values('End date/time', ascending=True)
    
    # 获取数据列
    data_column = 'Time Elapsed (minutes)'
    target_column = 'Planned Duration (minutes)'
    
    # 如果列不存在，尝试查找替代列
    if data_column not in df_sorted.columns:
        time_columns = [col for col in df_sorted.columns if 'Time Elapsed' in col]
        if time_columns:
            data_column = time_columns[0]
    
    if target_column not in df_sorted.columns:
        planned_columns = [col for col in df_sorted.columns if 'Planned' in col]
        if planned_columns:
            target_column = planned_columns[0]
    
    if data_column not in df_sorted.columns or target_column not in df_sorted.columns:
        st.error("无法找到必要的数据列")
        return None
    
    data_values = df_sorted[data_column].values
    target_values = df_sorted[target_column].values
    n_points = len(data_values)
    
    # ========== 统计计算 ==========
    overall_mean = np.mean(data_values)
    overall_median = np.median(data_values)
    overall_std = np.std(data_values, ddof=1)
    
    # 计算众数
    overall_mode_result = stats.mode(data_values, keepdims=True)
    overall_mode = overall_mode_result.mode[0]
    overall_mode_count = overall_mode_result.count[0]
    
    # 计算分位数
    sorted_data = np.sort(data_values)
    front_10_percentile = np.percentile(sorted_data, 10)
    back_10_percentile = np.percentile(sorted_data, 90)
    front_25_percentile = np.percentile(sorted_data, 25)
    back_25_percentile = np.percentile(sorted_data, 75)
    
    # 目标值统计
    target_mean = np.mean(target_values)
    
    # 控制线和警戒线
    ucl = target_mean * 1.2
    lcl = max(0, target_mean * 0.8)
    uwl = target_mean * 1.5
    lwl = max(0, target_mean * 0.5)
    
    # 区域划分
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
    
    # 规格限
    usl = target_mean * 1.2
    lsl = target_mean * 0.8
    
    # 过程能力指数
    cpu = (usl - overall_mean) / (3 * overall_std) if overall_std > 0 else 0
    cpl = (overall_mean - lsl) / (3 * overall_std) if overall_std > 0 else 0
    cpk = min(cpu, cpl)
    
    std_total = np.std(data_values, ddof=0)
    ppu = (usl - overall_mean) / (3 * std_total) if std_total > 0 else 0
    ppl = (overall_mean - lsl) / (3 * std_total) if std_total > 0 else 0
    ppk = min(ppu, ppl)
    
    cp = (usl - lsl) / (6 * overall_std) if overall_std > 0 else 0
    
    # 保存统计结果
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
        'target_mean': target_mean,
        'ucl': ucl,
        'lcl': lcl,
        'uwl': uwl,
        'lwl': lwl,
        'green_lower': green_lower,
        'green_upper': green_upper,
        'yellow_upper_lower': yellow_upper_lower,
        'yellow_upper_upper': yellow_upper_upper,
        'yellow_lower_lower': yellow_lower_lower,
        'yellow_lower_upper': yellow_lower_upper,
        'red_upper_lower': red_upper_lower,
        'red_upper_upper': red_upper_upper,
        'red_lower_lower': red_lower_lower,
        'red_lower_upper': red_lower_upper,
        'usl': usl,
        'lsl': lsl,
        'cp': cp,
        'cpk': cpk,
        'ppk': ppk,
        'min_value': np.min(data_values),
        'max_value': np.max(data_values),
        'range_value': np.max(data_values) - np.min(data_values)
    }
    
    # ========== 创建SPC图 ==========
    set_chinese_font()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
    
    x_values = range(len(data_values))
    n_front_10 = max(1, int(n_points * 0.1))
    n_back_10 = max(1, int(n_points * 0.1))
    
    # 上部：SPC控制图
    ax1.axhspan(red_lower_lower, red_lower_upper, alpha=0.2, color='red', label='A区 (红色: <50%目标)')
    ax1.axhspan(yellow_lower_lower, yellow_lower_upper, alpha=0.2, color='yellow', label='B区 (黄色: 50%-80%目标)')
    ax1.axhspan(green_lower, green_upper, alpha=0.2, color='green', label='C区 (绿色: 80%-120%目标)')
    ax1.axhspan(yellow_upper_lower, yellow_upper_upper, alpha=0.2, color='yellow')
    ax1.axhspan(red_upper_lower, red_upper_upper, alpha=0.2, color='red')
    
    # 绘制数据点
    ax1.plot(x_values, data_values, 'o-', color='blue', markersize=4, label='实际值 (分钟)')
    
    # 绘制统计线
    ax1.axhline(y=overall_mean, color='darkblue', linestyle='--', linewidth=1.5, alpha=0.7, label=f'整体均值: {overall_mean:.2f}')
    ax1.axhline(y=overall_median, color='darkgreen', linestyle='--', linewidth=1.5, alpha=0.7, label=f'整体中位数: {overall_median:.2f}')
    ax1.axhline(y=overall_mode, color='darkorange', linestyle='--', linewidth=1.5, alpha=0.7, label=f'整体众数: {overall_mode:.2f}')
    ax1.axhline(y=target_mean, color='purple', linestyle='-.', linewidth=2, label=f'目标均值: {target_mean:.2f}')
    ax1.axhline(y=ucl, color='red', linestyle='--', linewidth=2, label=f'UCL: {ucl:.2f}')
    ax1.axhline(y=lcl, color='red', linestyle='--', linewidth=2, label=f'LCL: {lcl:.2f}')
    ax1.axhline(y=uwl, color='orange', linestyle=':', linewidth=2, label=f'UWL: {uwl:.2f}')
    ax1.axhline(y=lwl, color='orange', linestyle=':', linewidth=2, label=f'LWL: {lwl:.2f}')
    ax1.axhline(y=usl, color='darkred', linestyle='-', linewidth=1.5, label=f'USL: {usl:.2f}')
    ax1.axhline(y=lsl, color='darkred', linestyle='-', linewidth=1.5, label=f'LSL: {lsl:.2f}')
    
    # 标记前后10%区域
    ax1.axvspan(0, n_front_10-1, alpha=0.1, color='lightblue', label=f'前10%数据')
    ax1.axvspan(n_points - n_back_10, n_points-1, alpha=0.1, color='lightcoral', label=f'后10%数据')
    
    ax1.set_ylim(bottom=0, top=min(300, max(data_values) * 1.2))
    ax1.set_xlabel('数据点序号 (按时间排序)', fontsize=11)
    ax1.set_ylabel('Time Elapsed (minutes)', fontsize=11)
    ax1.set_title('SPC控制图 - 基于目标值百分比的控制限', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=7, ncol=2)
    ax1.grid(True, alpha=0.3)
    
    # 设置x轴标签
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
    
    # 下部：过程能力分析图表
    ax2.hist(data_values, bins=20, density=True, alpha=0.7, color='skyblue', edgecolor='black', label='实际值分布')
    x_norm = np.linspace(max(0, min(data_values)), max(data_values), 100)
    y_norm = norm.pdf(x_norm, overall_mean, std_total)
    ax2.plot(x_norm, y_norm, 'r-', linewidth=2, label='正态分布拟合')
    
    # 标记规格限和统计量
    ax2.axvline(x=usl, color='darkred', linestyle='--', linewidth=2, label=f'USL: {usl:.2f}')
    ax2.axvline(x=lsl, color='darkred', linestyle='--', linewidth=2, label=f'LSL: {lsl:.2f}')
    ax2.axvline(x=target_mean, color='purple', linestyle='-.', linewidth=2, label=f'目标: {target_mean:.2f}')
    ax2.axvline(x=overall_mean, color='black', linestyle='-', linewidth=2, label=f'均值: {overall_mean:.2f}')
    ax2.axvline(x=overall_median, color='darkgreen', linestyle='--', linewidth=1.5, alpha=0.7, label=f'中位数: {overall_median:.2f}')
    ax2.axvline(x=overall_mode, color='darkorange', linestyle='--', linewidth=1.5, alpha=0.7, label=f'众数: {overall_mode:.2f}')
    ax2.axvline(x=front_10_percentile, color='blue', linestyle=':', linewidth=1.5, alpha=0.7, label=f'前10%分位: {front_10_percentile:.2f}')
    ax2.axvline(x=back_10_percentile, color='red', linestyle=':', linewidth=1.5, alpha=0.7, label=f'后10%分位: {back_10_percentile:.2f}')
    ax2.axvline(x=front_25_percentile, color='lightblue', linestyle=':', linewidth=1.5, alpha=0.7, label=f'前25%分位: {front_25_percentile:.2f}')
    ax2.axvline(x=back_25_percentile, color='lightcoral', linestyle=':', linewidth=1.5, alpha=0.7, label=f'后25%分位: {back_25_percentile:.2f}')
    
    ax2.set_xlim(left=0, right=min(300, max(data_values) * 1.2))
    ax2.set_xlabel('Time Elapsed (minutes)', fontsize=11)
    ax2.set_ylabel('概率密度', fontsize=11)
    ax2.set_title('过程能力与统计分布分析', fontsize=12, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=7)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    results['figures']['spc_chart'] = fig
    
    # ========== 异常点检测 ==========
    anomaly_records = []
    
    # 规则1: 一个点落在A区以外
    for i, value in enumerate(data_values):
        if value > ucl or value < lcl:
            rule = "规则1: 点落在A区以外"
            location = df_sorted.iloc[i]['Location'] if 'Location' in df_sorted.columns else '未知'
            process_id = df_sorted.iloc[i]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else '未知'
            date_time = df_sorted.iloc[i]['End date/time'] if 'End date/time' in df_sorted.columns else '未知'
            anomaly_records.append({
                '序号': i+1,
                '产线': location,
                '批次号': process_id,
                '时间': date_time,
                '实际值': round(value, 2),
                '目标值': round(target_values[i], 2),
                '偏差': round(value - target_values[i], 2),
                '异常规则': rule
            })
    
    # 规则2: 连续9个点落在中心线的同一侧
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
        rule = "规则2: 连续9个点在目标线同一侧"
        location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else '未知'
        process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else '未知'
        date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else '未知'
        anomaly_records.append({
            '序号': idx+1,
            '产线': location,
            '批次号': process_id,
            '时间': date_time,
            '实际值': round(data_values[idx], 2),
            '目标值': round(target_values[idx], 2),
            '偏差': round(data_values[idx] - target_values[idx], 2),
            '异常规则': rule
        })
    
    # 规则3: 连续6个点递增或递减
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
        rule = "规则3: 连续6个点递增或递减"
        location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else '未知'
        process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else '未知'
        date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else '未知'
        anomaly_records.append({
            '序号': idx+1,
            '产线': location,
            '批次号': process_id,
            '时间': date_time,
            '实际值': round(data_values[idx], 2),
            '目标值': round(target_values[idx], 2),
            '偏差': round(data_values[idx] - target_values[idx], 2),
            '异常规则': rule
        })
    
    # 规则4: 连续14个点中相邻点交替上下
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
        rule = "规则4: 连续14个点相邻点交替上下"
        location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else '未知'
        process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else '未知'
        date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else '未知'
        anomaly_records.append({
            '序号': idx+1,
            '产线': location,
            '批次号': process_id,
            '时间': date_time,
            '实际值': round(data_values[idx], 2),
            '目标值': round(target_values[idx], 2),
            '偏差': round(data_values[idx] - target_values[idx], 2),
            '异常规则': rule
        })
    
    # 创建异常点DataFrame并去重
    if anomaly_records:
        anomaly_df = pd.DataFrame(anomaly_records)
        anomaly_df = anomaly_df.drop_duplicates(subset=['批次号', '时间'])
        anomaly_df = anomaly_df.sort_values('序号')
        results['anomalies'] = anomaly_df
    
    return results

# ==================== 活动数据分析函数（无机器学习版本）====================
def analyze_activity_data(df):
    """
    活动数据分析：数据清洗、阶段分析（无随机森林）
    """
    results = {
        'cleaning_steps': [],
        'phase_analysis': {},
        'figures': {}
    }
    
    # ========== 数据清洗 ==========
    original_rows = len(df)
    results['cleaning_steps'].append(f"原始数据行数: {original_rows}")
    
    # 筛选指定产线
    area_list = ['CPLine 9', 'CP Line 10', 'CP Line 11', 'CP Line 12', 'CP Line 05', 'CP Line08']
    df = df[df['Area'].isin(area_list)]
    results['cleaning_steps'].append(f"筛选指定产线后行数: {len(df)}")
    
    # 筛选"干清"类型
    df = df[df['Changeover Type'] == '干清']
    results['cleaning_steps'].append(f"筛选'干清'类型后行数: {len(df)}")
    
    # 删除Actual Duration空值
    original_count = len(df)
    df = df.dropna(subset=['Actual Duration (seconds)'])
    removed_count = original_count - len(df)
    results['cleaning_steps'].append(f"删除Actual Duration空值{removed_count}行，剩余行数：{len(df)}")
    
    # 将秒数据转换为分钟
    if 'Actual Duration (seconds)' in df.columns:
        df['Actual Duration (minutes)'] = (df['Actual Duration (seconds)'] / 60).round(2)
    
    results['cleaning_steps'].append(f"\n清洗完成，最终数据行数: {len(df)}")
    
    # 计算批次信息
    if 'PO Number' in df.columns:
        total_batches = df['PO Number'].nunique()
        results['batch_info'] = {
            'total_batches': total_batches,
            'total_records': len(df)
        }
        
        if 'Created At' in df.columns:
            df['Created At'] = pd.to_datetime(df['Created At'])
            results['batch_info']['time_range'] = f"{df['Created At'].min()} 至 {df['Created At'].max()}"
    
    # ========== 阶段详细分析 ==========
    phases = ['清场前准备', '清场', '切换', '产线配置']
    
    for phase in phases:
        phase_data = df[df['Phase Name'] == phase]
        
        if len(phase_data) == 0:
            continue
        
        total_duration = phase_data['Actual Duration (minutes)'].sum()
        avg_duration = phase_data['Actual Duration (minutes)'].mean()
        
        # 按活动描述分组
        activity_duration = phase_data.groupby('Task Description')['Actual Duration (minutes)'].agg(['mean', 'sum', 'count']).round(2)
        activity_duration = activity_duration.sort_values('mean', ascending=False)
        
        # 按执行人员分组
        if 'Operator' in phase_data.columns:
            operator_duration = phase_data.groupby('Operator')['Actual Duration (minutes)'].agg(['mean', 'count']).round(2)
            operator_duration = operator_duration.sort_values('mean')
        else:
            operator_duration = pd.DataFrame()
        
        results['phase_analysis'][phase] = {
            '总耗时': total_duration,
            '平均耗时': avg_duration,
            '活动数量': len(activity_duration),
            '记录数量': len(phase_data),
            '最耗时活动': activity_duration.head(5) if len(activity_duration) > 0 else pd.DataFrame(),
            '效率最高人员': operator_duration.head(5) if len(operator_duration) > 0 else pd.DataFrame()
        }
    
    return results

# ==================== 设置中文字体函数 ====================
def set_chinese_font():
    """
    设置matplotlib支持中文显示
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        elif system == "Darwin":  # macOS
            plt.rcParams['font.sans-serif'] = ['PingFang SC', 'STHeiti', 'Arial Unicode MS']
        else:  # Linux
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS']
        
        plt.rcParams['axes.unicode_minus'] = False
        return True
    except Exception as e:
        print(f"设置中文字体时出错：{e}")
        return False

# ==================== 主程序 ====================
if run_button:
    if batch_file is None or activity_file is None:
        st.warning("⚠️ 请先上传批次数据和活动数据文件！")
    else:
        # 创建进度条和状态显示
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # ========== 第一部分：批次数据分析 ==========
            status_text.text("📊 正在分析批次数据...")
            progress_bar.progress(20)
            
            # 读取批次数据
            batch_df = pd.read_excel(batch_file)
            
            # 执行批次数据分析
            with st.spinner("正在执行批次数据分析..."):
                batch_results = analyze_batch_data(batch_df, analysis_points, time_threshold)
            
            if batch_results:
                # 显示批次分析结果
                st.markdown('<h2 class="sub-header">📈 批次数据分析结果</h2>', unsafe_allow_html=True)
                
                # 创建选项卡
                batch_tab1, batch_tab2, batch_tab3 = st.tabs(["数据清洗", "SPC控制图", "异常点检测"])
                
                with batch_tab1:
                    st.markdown("### 🔄 数据清洗步骤")
                    for step in batch_results['cleaning_steps']:
                        st.write(f"- {step}")
                
                with batch_tab2:
                    if 'spc_chart' in batch_results['figures']:
                        st.pyplot(batch_results['figures']['spc_chart'])
                        
                        # 显示统计摘要
                        if show_details:
                            st.markdown("### 📊 统计摘要")
                            stats = batch_results['statistics']
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("均值", f"{stats['overall_mean']:.2f}分钟")
                                st.metric("中位数", f"{stats['overall_median']:.2f}分钟")
                            with col2:
                                st.metric("标准差", f"{stats['overall_std']:.2f}")
                                st.metric("众数", f"{stats['overall_mode']:.2f} (出现{stats['overall_mode_count']}次)")
                            with col3:
                                st.metric("目标均值", f"{stats['target_mean']:.2f}分钟")
                                st.metric("UCL", f"{stats['ucl']:.2f}分钟")
                            with col4:
                                st.metric("LCL", f"{stats['lcl']:.2f}分钟")
                                st.metric("CPK", f"{stats['cpk']:.3f}")
                            
                            # 分位数信息
                            st.markdown("#### 📌 分位数分析")
                            col_q1, col_q2, col_q3, col_q4 = st.columns(4)
                            with col_q1:
                                st.info(f"前10%分位: {stats['front_10_percentile']:.2f}")
                            with col_q2:
                                st.info(f"后10%分位: {stats['back_10_percentile']:.2f}")
                            with col_q3:
                                st.info(f"前25%分位: {stats['front_25_percentile']:.2f}")
                            with col_q4:
                                st.info(f"后75%分位: {stats['back_25_percentile']:.2f}")
                
                with batch_tab3:
                    if batch_results['anomalies'] is not None and len(batch_results['anomalies']) > 0:
                        st.markdown(f"### ⚠️ 发现 {len(batch_results['anomalies'])} 个异常点")
                        
                        # 按规则统计
                        rule_counts = batch_results['anomalies']['异常规则'].value_counts()
                        for rule, count in rule_counts.items():
                            st.warning(f"{rule}: {count}个异常点")
                        
                        # 显示异常点表格
                        st.dataframe(
                            batch_results['anomalies'],
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # 下载按钮
                        csv = batch_results['anomalies'].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 下载异常点数据",
                            data=csv,
                            file_name=f"异常点检测结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.success("✅ 未发现异常点")
            
            progress_bar.progress(50)
            
            # ========== 第二部分：活动数据分析 ==========
            status_text.text("📋 正在分析活动数据...")
            
            # 读取活动数据
            activity_df = pd.read_excel(activity_file)
            
            # 执行活动数据分析
            with st.spinner("正在执行活动数据分析..."):
                activity_results = analyze_activity_data(activity_df)
            
            if activity_results:
                st.markdown('<h2 class="sub-header">📋 活动数据分析结果</h2>', unsafe_allow_html=True)
                
                # 创建选项卡
                activity_tab1, activity_tab2 = st.tabs(["数据清洗", "阶段分析"])
                
                with activity_tab1:
                    st.markdown("### 🔄 数据清洗步骤")
                    for step in activity_results['cleaning_steps']:
                        st.write(f"- {step}")
                    
                    if 'batch_info' in activity_results:
                        st.markdown("### 📊 批次信息")
                        info = activity_results['batch_info']
                        st.info(
                            f"总批次数: {info['total_batches']} | "
                            f"总记录数: {info['total_records']}"
                        )
                        if 'time_range' in info:
                            st.write(f"时间范围: {info['time_range']}")
                
                with activity_tab2:
                    if activity_results['phase_analysis']:
                        # 创建阶段总览图表
                        phase_summary = []
                        for phase, analysis in activity_results['phase_analysis'].items():
                            phase_summary.append({
                                '阶段': phase,
                                '平均耗时': analysis['平均耗时'],
                                '总耗时': analysis['总耗时'],
                                '活动数': analysis['活动数量']
                            })
                        
                        if phase_summary:
                            phase_df = pd.DataFrame(phase_summary)
                            
                            # 显示阶段对比图表
                            fig_phase, ax_phase = plt.subplots(figsize=(10, 5))
                            bars = ax_phase.bar(phase_df['阶段'], phase_df['平均耗时'])
                            ax_phase.set_xlabel('阶段')
                            ax_phase.set_ylabel('平均耗时 (分钟)')
                            ax_phase.set_title('各阶段平均耗时对比')
                            
                            # 添加数值标签
                            for bar in bars:
                                height = bar.get_height()
                                ax_phase.text(bar.get_x() + bar.get_width()/2., height,
                                            f'{height:.1f}', ha='center', va='bottom')
                            
                            plt.xticks(rotation=45)
                            plt.tight_layout()
                            st.pyplot(fig_phase)
                        
                        # 显示各阶段详细分析
                        for phase, analysis in activity_results['phase_analysis'].items():
                            with st.expander(f"### 📌 {phase} 阶段分析"):
                                col_p1, col_p2, col_p3 = st.columns(3)
                                with col_p1:
                                    st.metric("总耗时", f"{analysis['总耗时']:.2f}分钟")
                                with col_p2:
                                    st.metric("平均耗时", f"{analysis['平均耗时']:.2f}分钟")
                                with col_p3:
                                    st.metric("活动数", analysis['活动数量'])
                                
                                if not analysis['最耗时活动'].empty:
                                    st.markdown("#### ⏱️ 耗时最长的活动")
                                    st.dataframe(analysis['最耗时活动'], use_container_width=True)
                                
                                if not analysis['效率最高人员'].empty:
                                    st.markdown("#### 👤 效率最高的人员")
                                    st.dataframe(analysis['效率最高人员'], use_container_width=True)
                    else:
                        st.warning("未找到阶段分析数据")
            
            progress_bar.progress(100)
            status_text.text("✅ 分析完成！")
            
            # ========== 综合分析结论 ==========
            st.markdown("---")
            st.markdown('<h2 class="sub-header">📋 综合分析结论</h2>', unsafe_allow_html=True)
            
            col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
            
            with col_sum1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">总批次</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-value">{len(batch_df)}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">异常点数</p>', unsafe_allow_html=True)
                anomaly_count = len(batch_results['anomalies']) if batch_results and batch_results['anomalies'] is not None else 0
                st.markdown(f'<p class="metric-value">{anomaly_count}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">总活动数</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-value">{len(activity_df)}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown('<p class="metric-label">CPK</p>', unsafe_allow_html=True)
                cpk_value = batch_results['statistics']['cpk'] if batch_results else 0
                st.markdown(f'<p class="metric-value">{cpk_value:.3f}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 过程能力评估
            if batch_results:
                cpk = batch_results['statistics']['cpk']
                if cpk >= 1.33:
                    st.success("✅ **过程能力充足** - 过程满足规格要求")
                elif cpk >= 1.0:
                    st.warning("⚠️ **过程能力尚可** - 需要持续监控")
                else:
                    st.error("❌ **过程能力不足** - 需要立即改进")
            
        except Exception as e:
            st.error(f"❌ 分析过程中出现错误: {str(e)}")
            st.exception(e)

else:
    # 欢迎界面
    st.markdown("""
    <div style="text-align: center; padding: 3rem;">
        <h2 style="color: #1E3A8A;">欢迎使用DCO综合分析系统</h2>
        <p style="color: #4B5563; font-size: 1.2rem;">请在左侧控制面板上传数据文件并开始分析</p>
        <div style="margin-top: 2rem;">
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📊 SPC控制图
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                🔍 异常检测
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                ⏱️ 阶段分析
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📈 过程能力
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 系统功能说明
    col_func1, col_func2 = st.columns(2)
    
    with col_func1:
        st.markdown("""
        #### 📈 批次分析功能
        - 数据自动清洗（7个清洗步骤）
        - SPC控制图绘制（红-黄-绿区域）
        - 4种判异规则检测
        - 过程能力指数(CP/CPK/PPK)
        - 分位数统计分析（前10%、后10%等）
        - 异常点自动标记和导出
        """)
    
    with col_func2:
        st.markdown("""
        #### 📋 活动分析功能
        - 活动数据自动清洗
        - 4个阶段分析（清场前准备、清场、切换、产线配置）
        - 各阶段耗时统计
        - 耗时最长的活动排名
        - 效率最高的人员排名
        - 阶段对比图表
        """)

# ==================== 页脚 ====================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        <p>DCO综合分析系统 v2.2 | 完全兼容Python 3.13 | 稳定可靠版本</p>
        <p style="font-size: 0.8rem;">© 2024 版权所有 | 包含SPC分析、异常检测、阶段分析</p>
    </div>
    """,
    unsafe_allow_html=True
)
