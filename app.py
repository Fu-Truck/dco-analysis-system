import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
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

# ==================== 强制设置matplotlib全局字体 ====================
def force_set_chinese_font():
    """
    强制设置matplotlib支持中文显示，使用多种方法确保生效
    """
    try:
        # 方法1: 直接设置rcParams（最常用）
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 
                                           'DejaVu Sans', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 方法2: 通过matplotlib的字体管理器设置
        import matplotlib.font_manager as fm
        
        # 方法3: 创建自定义字体字典
        matplotlib.rc('font', family='DejaVu Sans')
        
        # 测试中文字符
        test_fig, test_ax = plt.subplots(figsize=(1, 1))
        test_ax.set_title("测试中文")
        test_ax.set_xlabel("横坐标")
        test_ax.set_ylabel("纵坐标")
        plt.close(test_fig)
        
        return True
    except Exception as e:
        st.warning(f"字体设置警告: {e}")
        return False

# 执行字体设置
FONT_OK = force_set_chinese_font()

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
st.markdown('<h1 class="main-header">📊 DCO综合分析系统</h1>', unsafe_allow_html=True)
st.markdown("---")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⚙️ 控制面板")
    st.markdown("---")
    
    st.info("📌 当前版本：完整统计分析与SPC控制")
    
    batch_file = st.file_uploader(
        "**批次数据** (DCO-batch data.xlsx)",
        type=['xlsx', 'xls']
    )
    
    activity_file = st.file_uploader(
        "**活动数据** (DCO-activity data.xlsx)",
        type=['xlsx', 'xls']
    )
    
    st.markdown("---")
    
    analysis_points = st.number_input(
        "SPC分析数据点数",
        min_value=10,
        max_value=500,
        value=100,
        step=10
    )
    
    time_threshold = st.number_input(
        "Time Elapsed阈值 (秒)",
        min_value=3600,
        max_value=36000,
        value=10800,
        step=600
    )
    
    show_details = st.checkbox("显示详细统计信息", value=True)
    
    st.markdown("---")
    run_button = st.button("🚀 开始全面分析", type="primary", use_container_width=True)

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
    
    # ========== SPC分析准备 ==========
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
        st.error("无法找到必要的数据列")
        return None
    
    data_values = df_sorted[data_column].values
    target_values = df_sorted[target_column].values
    n_points = len(data_values)
    
    # ========== 统计计算 ==========
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
    
    # ========== 创建SPC图 ==========
    # 再次确保字体设置生效
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 
                                       'DejaVu Sans', 'WenQuanYi Zen Hei', 'Noto Sans CJK SC']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1]})
    
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
    ax1.axhline(y=ucl, color='red', linestyle='--', linewidth=2, label=f'UCL (目标+20%): {ucl:.2f}')
    ax1.axhline(y=lcl, color='red', linestyle='--', linewidth=2, label=f'LCL (目标-20%): {lcl:.2f}')
    ax1.axhline(y=uwl, color='orange', linestyle=':', linewidth=2, label=f'UWL (目标+50%): {uwl:.2f}')
    ax1.axhline(y=lwl, color='orange', linestyle=':', linewidth=2, label=f'LWL (目标-50%): {lwl:.2f}')
    ax1.axhline(y=usl, color='darkred', linestyle='-', linewidth=1.5, label=f'USL (上规格限): {usl:.2f}')
    ax1.axhline(y=lsl, color='darkred', linestyle='-', linewidth=1.5, label=f'LSL (下规格限): {lsl:.2f}')
    
    # 标记前后10%区域
    ax1.axvspan(0, n_front_10-1, alpha=0.1, color='lightblue', label=f'前10%数据 (第1-{n_front_10}点)')
    ax1.axvspan(n_points - n_back_10, n_points-1, alpha=0.1, color='lightcoral', label=f'后10%数据 (第{n_points - n_back_10 + 1}-{n_points}点)')
    
    # ========== 异常点检测和标记 ==========
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
            ax1.plot(i, value, 'ro', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='规则1异常点' if i == 0 else "")
    
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
        if idx not in [a['序号']-1 for a in anomaly_records]:
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
            ax1.plot(idx, data_values[idx], 'yo', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='规则2异常点' if idx == rule2_anomalies[0] else "")
    
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
        if idx not in [a['序号']-1 for a in anomaly_records]:
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
            ax1.plot(idx, data_values[idx], 'go', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='规则3异常点' if idx == rule3_anomalies[0] else "")
    
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
        if idx not in [a['序号']-1 for a in anomaly_records]:
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
            ax1.plot(idx, data_values[idx], 'mo', markersize=10, markeredgecolor='black', markeredgewidth=1.5, label='规则4异常点' if idx == rule4_anomalies[0] else "")
    
    # 设置图表属性
    ax1.set_ylim(bottom=0, top=min(300, max(data_values) * 1.2))
    ax1.set_xlabel('数据点序号 (按时间排序)', fontsize=12)
    ax1.set_ylabel('时间 (分钟)', fontsize=12)
    ax1.set_title('SPC控制图 - 基于目标值百分比的控制限', fontsize=14, fontweight='bold')
    
    # 处理图例重复问题
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax1.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=8, ncol=2)
    
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
    
    # 标记分位点
    ax2.axvline(x=front_10_percentile, color='blue', linestyle=':', linewidth=1.5, alpha=0.7, label=f'前10%分位: {front_10_percentile:.2f}')
    ax2.axvline(x=back_10_percentile, color='red', linestyle=':', linewidth=1.5, alpha=0.7, label=f'后10%分位: {back_10_percentile:.2f}')
    ax2.axvline(x=front_25_percentile, color='lightblue', linestyle=':', linewidth=1.5, alpha=0.7, label=f'前25%分位: {front_25_percentile:.2f}')
    ax2.axvline(x=back_25_percentile, color='lightcoral', linestyle=':', linewidth=1.5, alpha=0.7, label=f'后75%分位: {back_25_percentile:.2f}')
    
    ax2.set_xlim(left=0, right=min(300, max(data_values) * 1.2))
    ax2.set_xlabel('时间 (分钟)', fontsize=12)
    ax2.set_ylabel('概率密度', fontsize=12)
    ax2.set_title('过程能力与统计分布分析', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    results['figures']['spc_chart'] = fig
    
    # 创建异常点DataFrame
    if anomaly_records:
        anomaly_df = pd.DataFrame(anomaly_records)
        anomaly_df = anomaly_df.drop_duplicates(subset=['批次号', '时间'])
        anomaly_df = anomaly_df.sort_values('序号')
        results['anomalies'] = anomaly_df
    
    return results

# ==================== 活动数据分析函数 ====================
def analyze_activity_data(df):
    """
    活动数据分析：数据清洗、阶段分析
    """
    results = {
        'cleaning_steps': [],
        'phase_analysis': {},
        'figures': {}
    }
    
    original_rows = len(df)
    results['cleaning_steps'].append(f"原始数据行数: {original_rows}")
    
    area_list = ['CPLine 9', 'CP Line 10', 'CP Line 11', 'CP Line 12', 'CP Line 05', 'CP Line08']
    df = df[df['Area'].isin(area_list)]
    results['cleaning_steps'].append(f"筛选指定产线后行数: {len(df)}")
    
    df = df[df['Changeover Type'] == '干清']
    results['cleaning_steps'].append(f"筛选'干清'类型后行数: {len(df)}")
    
    original_count = len(df)
    df = df.dropna(subset=['Actual Duration (seconds)'])
    removed_count = original_count - len(df)
    results['cleaning_steps'].append(f"删除Actual Duration空值{removed_count}行，剩余行数：{len(df)}")
    
    if 'Actual Duration (seconds)' in df.columns:
        df['Actual Duration (minutes)'] = (df['Actual Duration (seconds)'] / 60).round(2)
    
    results['cleaning_steps'].append(f"\n清洗完成，最终数据行数: {len(df)}")
    
    if 'PO Number' in df.columns:
        total_batches = df['PO Number'].nunique()
        results['batch_info'] = {
            'total_batches': total_batches,
            'total_records': len(df)
        }
        
        if 'Created At' in df.columns:
            df['Created At'] = pd.to_datetime(df['Created At'])
            results['batch_info']['time_range'] = f"{df['Created At'].min()} 至 {df['Created At'].max()}"
    
    phases = ['清场前准备', '清场', '切换', '产线配置']
    
    for phase in phases:
        phase_data = df[df['Phase Name'] == phase]
        
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
                '时间': fastest_record.get('Actual Duration (minutes)', 'N/A'),
                '操作员': fastest_record.get('Operator', 'N/A'),
                '活动描述': fastest_record.get('Task Description', 'N/A'),
                '批次号': fastest_record.get('PO Number', 'N/A')
            }
        
        if slowest_record is not None:
            slowest_info = {
                '时间': slowest_record.get('Actual Duration (minutes)', 'N/A'),
                '操作员': slowest_record.get('Operator', 'N/A'),
                '活动描述': slowest_record.get('Task Description', 'N/A'),
                '批次号': slowest_record.get('PO Number', 'N/A')
            }
        
        results['phase_analysis'][phase] = {
            '平均耗时': avg_duration,
            '最小耗时': min_duration,
            '最大耗时': max_duration,
            '标准差': std_duration,
            '活动数量': len(activity_duration),
            '记录数量': len(phase_data),
            '最耗时活动': activity_duration.head(5) if len(activity_duration) > 0 else pd.DataFrame(),
            '效率最高人员': operator_duration.head(5) if len(operator_duration) > 0 else pd.DataFrame(),
            '最快记录': fastest_info,
            '最慢记录': slowest_info
        }
    
    return results

# ==================== 主程序 ====================
if run_button:
    if batch_file is None or activity_file is None:
        st.warning("⚠️ 请先上传批次数据和活动数据文件！")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # ========== 批次数据分析 ==========
            status_text.text("📊 正在分析批次数据...")
            progress_bar.progress(20)
            
            batch_df = pd.read_excel(batch_file)
            
            with st.spinner("正在执行批次数据分析..."):
                batch_results = analyze_batch_data(batch_df, analysis_points, time_threshold)
            
            if batch_results:
                st.markdown('<h2 class="sub-header">📈 批次数据分析结果</h2>', unsafe_allow_html=True)
                
                batch_tab1, batch_tab2, batch_tab3, batch_tab4 = st.tabs(["数据清洗", "SPC控制图", "完整统计分析", "异常点检测"])
                
                with batch_tab1:
                    st.markdown("### 🔄 数据清洗步骤")
                    for step in batch_results['cleaning_steps']:
                        st.write(f"- {step}")
                
                with batch_tab2:
                    if 'spc_chart' in batch_results['figures']:
                        st.pyplot(batch_results['figures']['spc_chart'])
                        
                        if show_details:
                            st.markdown("### 📊 基本统计摘要")
                            stats = batch_results['statistics']
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("均值", f"{stats['overall_mean']:.2f}min")
                                st.metric("中位数", f"{stats['overall_median']:.2f}min")
                            with col2:
                                st.metric("标准差", f"{stats['overall_std']:.2f}")
                                st.metric("众数", f"{stats['overall_mode']:.2f}")
                            with col3:
                                st.metric("最小值", f"{stats['min_value']:.2f}min")
                                st.metric("最大值", f"{stats['max_value']:.2f}min")
                            with col4:
                                st.metric("极差", f"{stats['range_value']:.2f}min")
                                st.metric("CPK", f"{stats['cpk']:.3f}")
                
                with batch_tab3:
                    st.markdown("### 📊 完整统计分析")
                    stats = batch_results['statistics']
                    
                    st.markdown("#### 📈 整体统计")
                    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                    with col_a1:
                        st.info(f"**均值**: {stats['overall_mean']:.2f}min")
                    with col_a2:
                        st.info(f"**中位数**: {stats['overall_median']:.2f}min")
                    with col_a3:
                        st.info(f"**众数**: {stats['overall_mode']:.2f}min ({stats['overall_mode_count']}次)")
                    with col_a4:
                        st.info(f"**标准差**: {stats['overall_std']:.2f}")
                    
                    st.markdown("#### 📊 分位数分析")
                    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
                    with col_b1:
                        st.success(f"**前10%分位**: {stats['front_10_percentile']:.2f}min")
                    with col_b2:
                        st.success(f"**后10%分位**: {stats['back_10_percentile']:.2f}min")
                    with col_b3:
                        st.success(f"**前25%分位**: {stats['front_25_percentile']:.2f}min")
                    with col_b4:
                        st.success(f"**后75%分位**: {stats['back_25_percentile']:.2f}min")
                    
                    st.markdown("#### ⚡ 极值分析")
                    col_c1, col_c2, col_c3 = st.columns(3)
                    with col_c1:
                        st.warning(f"**最小值**: {stats['min_value']:.2f}min")
                    with col_c2:
                        st.warning(f"**最大值**: {stats['max_value']:.2f}min")
                    with col_c3:
                        st.warning(f"**极差**: {stats['range_value']:.2f}min")
                    
                    st.markdown("#### 🎯 过程能力分析")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        st.metric("CP", f"{stats['cp']:.3f}")
                    with col_d2:
                        st.metric("CPK", f"{stats['cpk']:.3f}")
                    with col_d3:
                        st.metric("PPK", f"{stats['ppk']:.3f}")
                    
                    cpk = stats['cpk']
                    if cpk >= 1.33:
                        st.success("✅ **过程能力充足** - 过程满足规格要求")
                    elif cpk >= 1.0:
                        st.warning("⚠️ **过程能力尚可** - 需要持续监控")
                    else:
                        st.error("❌ **过程能力不足** - 需要立即改进")
                
                with batch_tab4:
                    if batch_results['anomalies'] is not None and len(batch_results['anomalies']) > 0:
                        st.markdown(f"### ⚠️ 发现 {len(batch_results['anomalies'])} 个异常点")
                        
                        rule_counts = batch_results['anomalies']['异常规则'].value_counts()
                        for rule, count in rule_counts.items():
                            st.warning(f"{rule}: {count}个异常点")
                        
                        st.dataframe(batch_results['anomalies'], use_container_width=True, hide_index=True)
                        
                        csv = batch_results['anomalies'].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 下载异常点数据",
                            data=csv,
                            file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.success("✅ 未发现异常点")
            
            progress_bar.progress(50)
            
            # ========== 活动数据分析 ==========
            status_text.text("📋 正在分析活动数据...")
            activity_df = pd.read_excel(activity_file)
            
            with st.spinner("正在执行活动数据分析..."):
                activity_results = analyze_activity_data(activity_df)
            
            if activity_results:
                st.markdown('<h2 class="sub-header">📋 活动数据分析结果</h2>', unsafe_allow_html=True)
                
                activity_tab1, activity_tab2 = st.tabs(["数据清洗", "阶段分析"])
                
                with activity_tab1:
                    st.markdown("### 🔄 数据清洗步骤")
                    for step in activity_results['cleaning_steps']:
                        st.write(f"- {step}")
                    
                    if 'batch_info' in activity_results:
                        st.markdown("### 📊 批次信息")
                        info = activity_results['batch_info']
                        st.info(f"总批次数: {info['total_batches']} | 总记录数: {info['total_records']}")
                        if 'time_range' in info:
                            st.write(f"时间范围: {info['time_range']}")
                
                with activity_tab2:
                    if activity_results['phase_analysis']:
                        phase_summary = []
                        for phase, analysis in activity_results['phase_analysis'].items():
                            phase_summary.append({
                                '阶段': phase,
                                '平均耗时': round(analysis['平均耗时'], 2),
                                '最小耗时': round(analysis['最小耗时'], 2),
                                '最大耗时': round(analysis['最大耗时'], 2),
                                '标准差': round(analysis['标准差'], 2),
                                '活动数': analysis['活动数量'],
                                '记录数': analysis['记录数量']
                            })
                        
                        if phase_summary:
                            phase_df = pd.DataFrame(phase_summary)
                            st.dataframe(phase_df, use_container_width=True, hide_index=True)
                            
                            # 创建对比图表
                            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 
                                                               'DejaVu Sans', 'WenQuanYi Zen Hei']
                            plt.rcParams['axes.unicode_minus'] = False
                            
                            fig_phase, axes = plt.subplots(1, 2, figsize=(14, 5))
                            
                            x = range(len(phase_df))
                            width = 0.25
                            
                            axes[0].bar([i - width for i in x], phase_df['平均耗时'], width, label='平均耗时', color='#3B82F6')
                            axes[0].bar(x, phase_df['最小耗时'], width, label='最小耗时', color='#10B981')
                            axes[0].bar([i + width for i in x], phase_df['最大耗时'], width, label='最大耗时', color='#EF4444')
                            
                            axes[0].set_xlabel('阶段')
                            axes[0].set_ylabel('时间 (分钟)')
                            axes[0].set_title('各阶段耗时对比')
                            axes[0].set_xticks(x)
                            axes[0].set_xticklabels(phase_df['阶段'], rotation=45)
                            axes[0].legend()
                            axes[0].grid(True, alpha=0.3)
                            
                            axes[1].bar(phase_df['阶段'], phase_df['标准差'], color='#F59E0B')
                            axes[1].set_xlabel('阶段')
                            axes[1].set_ylabel('标准差')
                            axes[1].set_title('各阶段稳定性对比')
                            axes[1].tick_params(axis='x', rotation=45)
                            axes[1].grid(True, alpha=0.3)
                            
                            plt.tight_layout()
                            st.pyplot(fig_phase)
                        
                        for phase, analysis in activity_results['phase_analysis'].items():
                            with st.expander(f"### 📌 {phase} 阶段详细分析"):
                                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                                with col_p1:
                                    st.metric("平均耗时", f"{analysis['平均耗时']:.2f}min")
                                with col_p2:
                                    st.metric("最小耗时", f"{analysis['最小耗时']:.2f}min")
                                with col_p3:
                                    st.metric("最大耗时", f"{analysis['最大耗时']:.2f}min")
                                with col_p4:
                                    st.metric("标准差", f"{analysis['标准差']:.2f}")
                                
                                col_record1, col_record2 = st.columns(2)
                                with col_record1:
                                    st.markdown("#### ⚡ 最快记录")
                                    if analysis['最快记录']:
                                        st.success(
                                            f"**耗时**: {analysis['最快记录']['时间']}min\n\n"
                                            f"**操作员**: {analysis['最快记录']['操作员']}\n\n"
                                            f"**活动**: {analysis['最快记录']['活动描述']}\n\n"
                                            f"**批次**: {analysis['最快记录']['批次号']}"
                                        )
                                    else:
                                        st.info("无记录")
                                
                                with col_record2:
                                    st.markdown("#### 🐢 最慢记录")
                                    if analysis['最慢记录']:
                                        st.error(
                                            f"**耗时**: {analysis['最慢记录']['时间']}min\n\n"
                                            f"**操作员**: {analysis['最慢记录']['操作员']}\n\n"
                                            f"**活动**: {analysis['最慢记录']['活动描述']}\n\n"
                                            f"**批次**: {analysis['最慢记录']['批次号']}"
                                        )
                                    else:
                                        st.info("无记录")
                                
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
            
        except Exception as e:
            st.error(f"❌ 分析过程中出现错误: {str(e)}")
            st.exception(e)

else:
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
                📈 完整统计
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                ⚡ 极值分析
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_func1, col_func2 = st.columns(2)
    
    with col_func1:
        st.markdown("""
        #### 📈 批次分析功能
        - 数据自动清洗（7个清洗步骤）
        - SPC控制图绘制（红-黄-绿区域）
        - 4种判异规则检测
        - 完整统计分析（均值、中位数、众数）
        - 分位数分析（前/后十分位、前/后四分位）
        - 正态分布拟合
        """)
    
    with col_func2:
        st.markdown("""
        #### 📋 活动分析功能
        - 活动数据自动清洗
        - 4个阶段分析
        - 各阶段统计（平均值、最小值、最大值、标准差）
        - 最快记录和最慢记录
        - 耗时最长的活动排名
        - 效率最高的人员排名
        """)

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        <p>DCO综合分析系统 v3.2 | 完整统计分析版</p>
        <p style="font-size: 0.8rem;">© 2024 版权所有</p>
    </div>
    """,
    unsafe_allow_html=True
)
