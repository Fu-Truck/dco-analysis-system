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
import subprocess

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

# ==================== 设置中文字体（增强版）====================
def setup_chinese_font():
    """
    在Linux环境中安装和设置中文字体
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            return True
            
        elif system == "Darwin":  # macOS
            plt.rcParams['font.sans-serif'] = ['PingFang SC', 'STHeiti', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
            return True
            
        else:  # Linux (Streamlit Cloud)
            # 尝试安装中文字体
            try:
                # 检查是否已安装字体
                import matplotlib.font_manager as fm
                
                # 尝试多种中文字体
                chinese_fonts = ['WenQuanYi Zen Hei', 'Noto Sans CJK SC', 'Noto Sans SC', 
                                'Droid Sans Fallback', 'DejaVu Sans', 'Arial Unicode MS']
                
                for font in chinese_fonts:
                    try:
                        plt.rcParams['font.sans-serif'] = [font]
                        # 测试中文显示
                        test_fig, test_ax = plt.subplots()
                        test_ax.set_title("测试中文")
                        plt.close(test_fig)
                        plt.rcParams['axes.unicode_minus'] = False
                        return True
                    except:
                        continue
                
                # 如果都失败，使用英文标签
                plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
                return False
                
            except Exception as e:
                print(f"字体设置失败: {e}")
                return False
                
    except Exception as e:
        print(f"字体设置错误: {e}")
        return False

# 初始化字体
FONT_CHINESE_SUPPORT = setup_chinese_font()

# ==================== 辅助函数：安全的中文文本 ====================
def safe_text(text, default=None):
    """
    如果中文显示有问题，返回英文或默认文本
    """
    if FONT_CHINESE_SUPPORT:
        return text
    else:
        # 中文到英文的映射
        translations = {
            # 批次分析相关
            'A区 (红色: <50%目标)': 'Zone A (<50% Target)',
            'B区 (黄色: 50%-80%目标)': 'Zone B (50%-80% Target)',
            'C区 (绿色: 80%-120%目标)': 'Zone C (80%-120% Target)',
            '实际值 (分钟)': 'Actual Value (min)',
            '整体均值': 'Mean',
            '整体中位数': 'Median',
            '整体众数': 'Mode',
            '目标均值': 'Target Mean',
            'UCL (目标+20%)': 'UCL (+20%)',
            'LCL (目标-20%)': 'LCL (-20%)',
            'UWL (目标+50%)': 'UWL (+50%)',
            'LWL (目标-50%)': 'LWL (-50%)',
            'USL (上规格限)': 'USL',
            'LSL (下规格限)': 'LSL',
            '前10%数据': 'Top 10%',
            '后10%数据': 'Bottom 10%',
            '数据点序号': 'Data Point',
            '时间 (分钟)': 'Time (min)',
            '概率密度': 'Probability Density',
            'SPC控制图': 'SPC Control Chart',
            '过程能力与统计分布分析': 'Process Capability & Distribution',
            
            # 规则名称
            '规则1: 点落在A区以外': 'Rule 1: Point outside Zone A',
            '规则2: 连续9个点在目标线同一侧': 'Rule 2: 9 points on same side',
            '规则3: 连续6个点递增或递减': 'Rule 3: 6 points trend',
            '规则4: 连续14个点相邻点交替上下': 'Rule 4: 14 points alternating',
            
            # 活动分析相关
            '阶段': 'Phase',
            '平均耗时': 'Avg Time',
            '最小耗时': 'Min Time',
            '最大耗时': 'Max Time',
            '标准差': 'Std Dev',
            '活动数': 'Activities',
            '记录数': 'Records',
            '操作员': 'Operator',
            '活动描述': 'Activity',
            '批次号': 'Batch ID',
            '最快记录': 'Fastest Record',
            '最慢记录': 'Slowest Record',
            
            # 分位数
            '前10%分位': '10th Percentile',
            '后10%分位': '90th Percentile',
            '前25%分位': '25th Percentile',
            '后75%分位': '75th Percentile',
        }
        
        if text in translations:
            return translations[text]
        elif default:
            return default
        else:
            # 如果找不到翻译，尝试移除中文
            import re
            english_only = re.sub(r'[^\x00-\x7F]+', '', text)
            return english_only if english_only else "Label"

# ==================== 标题区域 ====================
st.markdown('<h1 class="main-header">📊 DCO综合分析系统</h1>', unsafe_allow_html=True)
st.markdown("---")

# 显示字体状态
if not FONT_CHINESE_SUPPORT:
    st.warning("⚠️ 当前环境中文显示可能不正常，将使用英文标签替代")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⚙️ 控制面板")
    st.markdown("---")
    
    # 显示提示信息
    st.info("📌 当前版本：完整统计分析与SPC控制")
    
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
        "   - SPC控制图分析（含异常点标记）\n"
        "   - 完整统计分析（均值、中位数、众数、分位数）\n"
        "   - 正态分布拟合\n"
        "   - 活动数据分析（最大值、最小值）"
    )

# ==================== 批次数据分析函数 ====================
def analyze_batch_data(df, analysis_points=100, time_threshold=10800):
    """
    批次数据分析：数据清洗、SPC分析、异常检测、完整统计分析
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
    
    # ========== 完整统计计算 ==========
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
    
    # 计算最大值和最小值
    min_value = np.min(data_values)
    max_value = np.max(data_values)
    range_value = max_value - min_value
    
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
        'min_value': min_value,
        'max_value': max_value,
        'range_value': range_value,
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
        'ppk': ppk
    }
    
    # ========== 创建SPC图（使用安全文本）==========
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1]})
    
    x_values = range(len(data_values))
    n_front_10 = max(1, int(n_points * 0.1))
    n_back_10 = max(1, int(n_points * 0.1))
    
    # 上部：SPC控制图 - 使用 safe_text 确保标签正确显示
    ax1.axhspan(red_lower_lower, red_lower_upper, alpha=0.2, color='red', 
                label=safe_text('A区 (红色: <50%目标)', 'Zone A (<50%)'))
    ax1.axhspan(yellow_lower_lower, yellow_lower_upper, alpha=0.2, color='yellow', 
                label=safe_text('B区 (黄色: 50%-80%目标)', 'Zone B (50%-80%)'))
    ax1.axhspan(green_lower, green_upper, alpha=0.2, color='green', 
                label=safe_text('C区 (绿色: 80%-120%目标)', 'Zone C (80%-120%)'))
    ax1.axhspan(yellow_upper_lower, yellow_upper_upper, alpha=0.2, color='yellow')
    ax1.axhspan(red_upper_lower, red_upper_upper, alpha=0.2, color='red')
    
    # 绘制数据点
    ax1.plot(x_values, data_values, 'o-', color='blue', markersize=4, 
             label=safe_text('实际值 (分钟)', 'Actual (min)'))
    
    # 绘制统计线 - 使用 f-string 但确保中文部分被转换
    mean_label = f"{safe_text('整体均值', 'Mean')}: {overall_mean:.2f}"
    median_label = f"{safe_text('整体中位数', 'Median')}: {overall_median:.2f}"
    mode_label = f"{safe_text('整体众数', 'Mode')}: {overall_mode:.2f}"
    target_label = f"{safe_text('目标均值', 'Target')}: {target_mean:.2f}"
    ucl_label = f"{safe_text('UCL', 'UCL')}: {ucl:.2f}"
    lcl_label = f"{safe_text('LCL', 'LCL')}: {lcl:.2f}"
    uwl_label = f"{safe_text('UWL', 'UWL')}: {uwl:.2f}"
    lwl_label = f"{safe_text('LWL', 'LWL')}: {lwl:.2f}"
    usl_label = f"{safe_text('USL', 'USL')}: {usl:.2f}"
    lsl_label = f"{safe_text('LSL', 'LSL')}: {lsl:.2f}"
    
    ax1.axhline(y=overall_mean, color='darkblue', linestyle='--', linewidth=1.5, alpha=0.7, label=mean_label)
    ax1.axhline(y=overall_median, color='darkgreen', linestyle='--', linewidth=1.5, alpha=0.7, label=median_label)
    ax1.axhline(y=overall_mode, color='darkorange', linestyle='--', linewidth=1.5, alpha=0.7, label=mode_label)
    ax1.axhline(y=target_mean, color='purple', linestyle='-.', linewidth=2, label=target_label)
    ax1.axhline(y=ucl, color='red', linestyle='--', linewidth=2, label=ucl_label)
    ax1.axhline(y=lcl, color='red', linestyle='--', linewidth=2, label=lcl_label)
    ax1.axhline(y=uwl, color='orange', linestyle=':', linewidth=2, label=uwl_label)
    ax1.axhline(y=lwl, color='orange', linestyle=':', linewidth=2, label=lwl_label)
    ax1.axhline(y=usl, color='darkred', linestyle='-', linewidth=1.5, label=usl_label)
    ax1.axhline(y=lsl, color='darkred', linestyle='-', linewidth=1.5, label=lsl_label)
    
    # 标记前后10%区域
    front_label = f"{safe_text('前10%数据', 'Top 10%')} (1-{n_front_10})"
    back_label = f"{safe_text('后10%数据', 'Bottom 10%')} ({n_points - n_back_10 + 1}-{n_points})"
    ax1.axvspan(0, n_front_10-1, alpha=0.1, color='lightblue', label=front_label)
    ax1.axvspan(n_points - n_back_10, n_points-1, alpha=0.1, color='lightcoral', label=back_label)
    
    # ========== 异常点检测和标记 ==========
    anomaly_records = []
    rule1_indices = []
    rule2_indices = []
    rule3_indices = []
    rule4_indices = []
    
    # 规则1: 一个点落在A区以外（超出UCL/LCL）
    for i, value in enumerate(data_values):
        if value > ucl or value < lcl:
            rule = safe_text('规则1: 点落在A区以外', 'Rule 1: Outside Zone A')
            location = df_sorted.iloc[i]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[i]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[i]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
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
            rule1_indices.append(i)
            # 在图上标记异常点（红色圆圈）
            ax1.plot(i, value, 'ro', markersize=10, markeredgecolor='black', markeredgewidth=1.5, 
                    label=safe_text('规则1异常点', 'Rule 1') if i == rule1_indices[0] else "")
    
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
            rule = safe_text('规则2: 连续9个点在目标线同一侧', 'Rule 2: 9 points same side')
            location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
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
            rule2_indices.append(idx)
            ax1.plot(idx, data_values[idx], 'yo', markersize=10, markeredgecolor='black', markeredgewidth=1.5,
                    label=safe_text('规则2异常点', 'Rule 2') if idx == rule2_anomalies[0] else "")
    
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
            rule = safe_text('规则3: 连续6个点递增或递减', 'Rule 3: 6 points trend')
            location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
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
            rule3_indices.append(idx)
            ax1.plot(idx, data_values[idx], 'go', markersize=10, markeredgecolor='black', markeredgewidth=1.5,
                    label=safe_text('规则3异常点', 'Rule 3') if idx == rule3_anomalies[0] else "")
    
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
            rule = safe_text('规则4: 连续14个点相邻点交替上下', 'Rule 4: 14 points alternating')
            location = df_sorted.iloc[idx]['Location'] if 'Location' in df_sorted.columns else 'Unknown'
            process_id = df_sorted.iloc[idx]['Process Order ID'] if 'Process Order ID' in df_sorted.columns else 'Unknown'
            date_time = df_sorted.iloc[idx]['End date/time'] if 'End date/time' in df_sorted.columns else 'Unknown'
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
            rule4_indices.append(idx)
            ax1.plot(idx, data_values[idx], 'mo', markersize=10, markeredgecolor='black', markeredgewidth=1.5,
                    label=safe_text('规则4异常点', 'Rule 4') if idx == rule4_anomalies[0] else "")
    
    # 设置图表属性
    ax1.set_ylim(bottom=0, top=min(300, max(data_values) * 1.2))
    ax1.set_xlabel(safe_text('数据点序号 (按时间排序)', 'Data Point (Chronological)'), fontsize=12)
    ax1.set_ylabel(safe_text('时间 (分钟)', 'Time (min)'), fontsize=12)
    ax1.set_title(safe_text('SPC控制图 - 基于目标值百分比的控制限', 'SPC Chart - Target Based Control Limits'), 
                 fontsize=14, fontweight='bold')
    
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
    ax2.hist(data_values, bins=20, density=True, alpha=0.7, color='skyblue', edgecolor='black', 
             label=safe_text('实际值分布', 'Actual Distribution'))
    x_norm = np.linspace(max(0, min(data_values)), max(data_values), 100)
    y_norm = norm.pdf(x_norm, overall_mean, std_total)
    ax2.plot(x_norm, y_norm, 'r-', linewidth=2, label=safe_text('正态分布拟合', 'Normal Fit'))
    
    # 标记规格限和统计量
    ax2.axvline(x=usl, color='darkred', linestyle='--', linewidth=2, label=f"USL: {usl:.2f}")
    ax2.axvline(x=lsl, color='darkred', linestyle='--', linewidth=2, label=f"LSL: {lsl:.2f}")
    ax2.axvline(x=target_mean, color='purple', linestyle='-.', linewidth=2, 
                label=f"{safe_text('目标', 'Target')}: {target_mean:.2f}")
    ax2.axvline(x=overall_mean, color='black', linestyle='-', linewidth=2, 
                label=f"{safe_text('均值', 'Mean')}: {overall_mean:.2f}")
    ax2.axvline(x=overall_median, color='darkgreen', linestyle='--', linewidth=1.5, alpha=0.7, 
                label=f"{safe_text('中位数', 'Median')}: {overall_median:.2f}")
    ax2.axvline(x=overall_mode, color='darkorange', linestyle='--', linewidth=1.5, alpha=0.7, 
                label=f"{safe_text('众数', 'Mode')}: {overall_mode:.2f}")
    
    # 标记分位点
    ax2.axvline(x=front_10_percentile, color='blue', linestyle=':', linewidth=1.5, alpha=0.7, 
                label=f"{safe_text('前10%分位', '10th Pctl')}: {front_10_percentile:.2f}")
    ax2.axvline(x=back_10_percentile, color='red', linestyle=':', linewidth=1.5, alpha=0.7, 
                label=f"{safe_text('后10%分位', '90th Pctl')}: {back_10_percentile:.2f}")
    ax2.axvline(x=front_25_percentile, color='lightblue', linestyle=':', linewidth=1.5, alpha=0.7, 
                label=f"{safe_text('前25%分位', '25th Pctl')}: {front_25_percentile:.2f}")
    ax2.axvline(x=back_25_percentile, color='lightcoral', linestyle=':', linewidth=1.5, alpha=0.7, 
                label=f"{safe_text('后75%分位', '75th Pctl')}: {back_25_percentile:.2f}")
    
    ax2.set_xlim(left=0, right=min(300, max(data_values) * 1.2))
    ax2.set_xlabel(safe_text('时间 (分钟)', 'Time (min)'), fontsize=12)
    ax2.set_ylabel(safe_text('概率密度', 'Probability Density'), fontsize=12)
    ax2.set_title(safe_text('过程能力与统计分布分析', 'Process Capability & Distribution'), 
                 fontsize=14, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    results['figures']['spc_chart'] = fig
    
    # 创建异常点DataFrame并去重
    if anomaly_records:
        anomaly_df = pd.DataFrame(anomaly_records)
        anomaly_df = anomaly_df.drop_duplicates(subset=['批次号', '时间'])
        anomaly_df = anomaly_df.sort_values('序号')
        results['anomalies'] = anomaly_df
    
    return results

# ==================== 活动数据分析函数 ====================
def analyze_activity_data(df):
    """
    活动数据分析：数据清洗、阶段分析（最大值、最小值分析）
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
        
        # 基础统计
        avg_duration = phase_data['Actual Duration (minutes)'].mean()
        min_duration = phase_data['Actual Duration (minutes)'].min()
        max_duration = phase_data['Actual Duration (minutes)'].max()
        std_duration = phase_data['Actual Duration (minutes)'].std()
        
        # 按活动描述分组
        activity_duration = phase_data.groupby('Task Description')['Actual Duration (minutes)'].agg(['mean', 'min', 'max', 'count']).round(2)
        activity_duration = activity_duration.sort_values('mean', ascending=False)
        
        # 按执行人员分组
        if 'Operator' in phase_data.columns:
            operator_duration = phase_data.groupby('Operator')['Actual Duration (minutes)'].agg(['mean', 'min', 'max', 'count']).round(2)
            operator_duration = operator_duration.sort_values('mean')
        else:
            operator_duration = pd.DataFrame()
        
        # 找出最快的和最慢的记录
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
                batch_tab1, batch_tab2, batch_tab3, batch_tab4 = st.tabs(
                    [safe_text("数据清洗", "Data Cleaning"), 
                     safe_text("SPC控制图", "SPC Chart"), 
                     safe_text("完整统计分析", "Statistics"), 
                     safe_text("异常点检测", "Anomalies")]
                )
                
                with batch_tab1:
                    st.markdown(f"### {safe_text('数据清洗步骤', 'Cleaning Steps')}")
                    for step in batch_results['cleaning_steps']:
                        st.write(f"- {step}")
                
                with batch_tab2:
                    if 'spc_chart' in batch_results['figures']:
                        st.pyplot(batch_results['figures']['spc_chart'])
                        
                        # 显示基本统计摘要
                        if show_details:
                            st.markdown(f"### {safe_text('基本统计摘要', 'Basic Statistics')}")
                            stats = batch_results['statistics']
                            
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric(safe_text("均值", "Mean"), f"{stats['overall_mean']:.2f}min")
                                st.metric(safe_text("中位数", "Median"), f"{stats['overall_median']:.2f}min")
                            with col2:
                                st.metric(safe_text("标准差", "Std Dev"), f"{stats['overall_std']:.2f}")
                                st.metric(safe_text("众数", "Mode"), f"{stats['overall_mode']:.2f}")
                            with col3:
                                st.metric(safe_text("最小值", "Min"), f"{stats['min_value']:.2f}min")
                                st.metric(safe_text("最大值", "Max"), f"{stats['max_value']:.2f}min")
                            with col4:
                                st.metric(safe_text("极差", "Range"), f"{stats['range_value']:.2f}min")
                                st.metric("CPK", f"{stats['cpk']:.3f}")
                
                with batch_tab3:
                    st.markdown(f"### {safe_text('完整统计分析', 'Complete Statistics')}")
                    stats = batch_results['statistics']
                    
                    # 整体统计
                    st.markdown(f"#### {safe_text('整体统计', 'Overall Statistics')}")
                    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                    with col_a1:
                        st.info(f"**{safe_text('均值', 'Mean')}**: {stats['overall_mean']:.2f}min")
                    with col_a2:
                        st.info(f"**{safe_text('中位数', 'Median')}**: {stats['overall_median']:.2f}min")
                    with col_a3:
                        st.info(f"**{safe_text('众数', 'Mode')}**: {stats['overall_mode']:.2f}min ({stats['overall_mode_count']}次)")
                    with col_a4:
                        st.info(f"**{safe_text('标准差', 'Std Dev')}**: {stats['overall_std']:.2f}")
                    
                    # 分位数分析
                    st.markdown(f"#### {safe_text('分位数分析', 'Percentile Analysis')}")
                    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
                    with col_b1:
                        st.success(f"**{safe_text('前10%分位', '10th Pctl')}**: {stats['front_10_percentile']:.2f}min")
                    with col_b2:
                        st.success(f"**{safe_text('后10%分位', '90th Pctl')}**: {stats['back_10_percentile']:.2f}min")
                    with col_b3:
                        st.success(f"**{safe_text('前25%分位', '25th Pctl')}**: {stats['front_25_percentile']:.2f}min")
                    with col_b4:
                        st.success(f"**{safe_text('后75%分位', '75th Pctl')}**: {stats['back_25_percentile']:.2f}min")
                    
                    # 极值分析
                    st.markdown(f"#### {safe_text('极值分析', 'Extreme Values')}")
                    col_c1, col_c2, col_c3 = st.columns(3)
                    with col_c1:
                        st.warning(f"**{safe_text('最小值', 'Min')}**: {stats['min_value']:.2f}min")
                    with col_c2:
                        st.warning(f"**{safe_text('最大值', 'Max')}**: {stats['max_value']:.2f}min")
                    with col_c3:
                        st.warning(f"**{safe_text('极差', 'Range')}**: {stats['range_value']:.2f}min")
                    
                    # 过程能力
                    st.markdown(f"#### {safe_text('过程能力分析', 'Process Capability')}")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        st.metric("CP", f"{stats['cp']:.3f}")
                    with col_d2:
                        st.metric("CPK", f"{stats['cpk']:.3f}")
                    with col_d3:
                        st.metric("PPK", f"{stats['ppk']:.3f}")
                    
                    # 过程能力评估
                    cpk = stats['cpk']
                    if cpk >= 1.33:
                        st.success(f"✅ **{safe_text('过程能力充足', 'Capable')}** - {safe_text('过程满足规格要求', 'Process meets specifications')}")
                    elif cpk >= 1.0:
                        st.warning(f"⚠️ **{safe_text('过程能力尚可', 'Marginally Capable')}** - {safe_text('需要持续监控', 'Needs monitoring')}")
                    else:
                        st.error(f"❌ **{safe_text('过程能力不足', 'Not Capable')}** - {safe_text('需要立即改进', 'Needs improvement')}")
                
                with batch_tab4:
                    if batch_results['anomalies'] is not None and len(batch_results['anomalies']) > 0:
                        st.markdown(f"### ⚠️ {safe_text('发现', 'Found')} {len(batch_results['anomalies'])} {safe_text('个异常点', 'anomalies')}")
                        
                        # 按规则统计
                        rule_counts = batch_results['anomalies']['异常规则'].value_counts()
                        for rule, count in rule_counts.items():
                            st.warning(f"{rule}: {count}{safe_text('个异常点', ' anomalies')}")
                        
                        # 显示异常点表格
                        st.dataframe(
                            batch_results['anomalies'],
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # 下载按钮
                        csv = batch_results['anomalies'].to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label=f"📥 {safe_text('下载异常点数据', 'Download Anomalies')}",
                            data=csv,
                            file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.success(f"✅ {safe_text('未发现异常点', 'No anomalies detected')}")
            
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
                activity_tab1, activity_tab2 = st.tabs(
                    [safe_text("数据清洗", "Data Cleaning"), 
                     safe_text("阶段分析", "Phase Analysis")]
                )
                
                with activity_tab1:
                    st.markdown(f"### {safe_text('数据清洗步骤', 'Cleaning Steps')}")
                    for step in activity_results['cleaning_steps']:
                        st.write(f"- {step}")
                    
                    if 'batch_info' in activity_results:
                        st.markdown(f"### {safe_text('批次信息', 'Batch Info')}")
                        info = activity_results['batch_info']
                        st.info(
                            f"{safe_text('总批次数', 'Total Batches')}: {info['total_batches']} | "
                            f"{safe_text('总记录数', 'Total Records')}: {info['total_records']}"
                        )
                        if 'time_range' in info:
                            st.write(f"{safe_text('时间范围', 'Time Range')}: {info['time_range']}")
                
                with activity_tab2:
                    if activity_results['phase_analysis']:
                        # 创建阶段统计表格
                        phase_summary = []
                        for phase, analysis in activity_results['phase_analysis'].items():
                            phase_summary.append({
                                safe_text('阶段', 'Phase'): phase,
                                safe_text('平均耗时', 'Avg'): round(analysis['平均耗时'], 2),
                                safe_text('最小耗时', 'Min'): round(analysis['最小耗时'], 2),
                                safe_text('最大耗时', 'Max'): round(analysis['最大耗时'], 2),
                                safe_text('标准差', 'Std'): round(analysis['标准差'], 2),
                                safe_text('活动数', 'Activities'): analysis['活动数量'],
                                safe_text('记录数', 'Records'): analysis['记录数量']
                            })
                        
                        if phase_summary:
                            phase_df = pd.DataFrame(phase_summary)
                            st.dataframe(phase_df, use_container_width=True, hide_index=True)
                            
                            # 创建对比图表
                            fig_phase, axes = plt.subplots(1, 2, figsize=(14, 5))
                            
                            # 左图：平均值、最小值、最大值对比
                            x = range(len(phase_df))
                            width = 0.25
                            
                            axes[0].bar([i - width for i in x], phase_df[safe_text('平均耗时', 'Avg')], 
                                       width, label=safe_text('平均耗时', 'Avg'), color='#3B82F6')
                            axes[0].bar(x, phase_df[safe_text('最小耗时', 'Min')], 
                                       width, label=safe_text('最小耗时', 'Min'), color='#10B981')
                            axes[0].bar([i + width for i in x], phase_df[safe_text('最大耗时', 'Max')], 
                                       width, label=safe_text('最大耗时', 'Max'), color='#EF4444')
                            
                            axes[0].set_xlabel(safe_text('阶段', 'Phase'))
                            axes[0].set_ylabel(safe_text('时间 (分钟)', 'Time (min)'))
                            axes[0].set_title(safe_text('各阶段耗时对比', 'Phase Time Comparison'))
                            axes[0].set_xticks(x)
                            axes[0].set_xticklabels(phase_df[safe_text('阶段', 'Phase')], rotation=45)
                            axes[0].legend()
                            axes[0].grid(True, alpha=0.3)
                            
                            # 右图：标准差对比
                            axes[1].bar(phase_df[safe_text('阶段', 'Phase')], phase_df[safe_text('标准差', 'Std')], 
                                       color='#F59E0B')
                            axes[1].set_xlabel(safe_text('阶段', 'Phase'))
                            axes[1].set_ylabel(safe_text('标准差', 'Std Dev'))
                            axes[1].set_title(safe_text('各阶段稳定性对比', 'Stability Comparison'))
                            axes[1].tick_params(axis='x', rotation=45)
                            axes[1].grid(True, alpha=0.3)
                            
                            plt.tight_layout()
                            st.pyplot(fig_phase)
                        
                        # 显示各阶段详细分析
                        for phase, analysis in activity_results['phase_analysis'].items():
                            with st.expander(f"### 📌 {phase} {safe_text('阶段详细分析', 'Phase Details')}"):
                                # 基本统计卡片
                                col_p1, col_p2, col_p3, col_p4 = st.columns(4)
                                with col_p1:
                                    st.metric(safe_text("平均耗时", "Avg Time"), f"{analysis['平均耗时']:.2f}min")
                                with col_p2:
                                    st.metric(safe_text("最小耗时", "Min Time"), f"{analysis['最小耗时']:.2f}min")
                                with col_p3:
                                    st.metric(safe_text("最大耗时", "Max Time"), f"{analysis['最大耗时']:.2f}min")
                                with col_p4:
                                    st.metric(safe_text("标准差", "Std Dev"), f"{analysis['标准差']:.2f}")
                                
                                # 最快和最慢记录
                                col_record1, col_record2 = st.columns(2)
                                with col_record1:
                                    st.markdown(f"#### ⚡ {safe_text('最快记录', 'Fastest Record')}")
                                    if analysis['最快记录']:
                                        st.success(
                                            f"**{safe_text('耗时', 'Time')}**: {analysis['最快记录']['时间']}min\n\n"
                                            f"**{safe_text('操作员', 'Operator')}**: {analysis['最快记录']['操作员']}\n\n"
                                            f"**{safe_text('活动', 'Activity')}**: {analysis['最快记录']['活动描述']}\n\n"
                                            f"**{safe_text('批次', 'Batch')}**: {analysis['最快记录']['批次号']}"
                                        )
                                    else:
                                        st.info(safe_text("无记录", "No data"))
                                
                                with col_record2:
                                    st.markdown(f"#### 🐢 {safe_text('最慢记录', 'Slowest Record')}")
                                    if analysis['最慢记录']:
                                        st.error(
                                            f"**{safe_text('耗时', 'Time')}**: {analysis['最慢记录']['时间']}min\n\n"
                                            f"**{safe_text('操作员', 'Operator')}**: {analysis['最慢记录']['操作员']}\n\n"
                                            f"**{safe_text('活动', 'Activity')}**: {analysis['最慢记录']['活动描述']}\n\n"
                                            f"**{safe_text('批次', 'Batch')}**: {analysis['最慢记录']['批次号']}"
                                        )
                                    else:
                                        st.info(safe_text("无记录", "No data"))
                                
                                if not analysis['最耗时活动'].empty:
                                    st.markdown(f"#### ⏱️ {safe_text('耗时最长的活动', 'Most Time-Consuming Activities')}")
                                    st.dataframe(analysis['最耗时活动'], use_container_width=True)
                                
                                if not analysis['效率最高人员'].empty:
                                    st.markdown(f"#### 👤 {safe_text('效率最高的人员', 'Most Efficient Operators')}")
                                    st.dataframe(analysis['效率最高人员'], use_container_width=True)
                    else:
                        st.warning(safe_text("未找到阶段分析数据", "No phase analysis data found"))
            
            progress_bar.progress(100)
            status_text.text("✅ 分析完成！")
            
            # ========== 综合分析结论 ==========
            st.markdown("---")
            st.markdown(f'<h2 class="sub-header">{safe_text("综合分析结论", "Summary")}</h2>', unsafe_allow_html=True)
            
            col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
            
            with col_sum1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-label">{safe_text("总批次", "Total Batches")}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-value">{len(batch_df)}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-label">{safe_text("异常点数", "Anomalies")}</p>', unsafe_allow_html=True)
                anomaly_count = len(batch_results['anomalies']) if batch_results and batch_results['anomalies'] is not None else 0
                st.markdown(f'<p class="metric-value">{anomaly_count}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-label">{safe_text("总活动数", "Total Activities")}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-value">{len(activity_df)}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_sum4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.markdown(f'<p class="metric-label">CPK</p>', unsafe_allow_html=True)
                cpk_value = batch_results['statistics']['cpk'] if batch_results else 0
                st.markdown(f'<p class="metric-value">{cpk_value:.3f}</p>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 过程能力评估
            if batch_results:
                cpk = batch_results['statistics']['cpk']
                if cpk >= 1.33:
                    st.success(f"✅ **{safe_text('过程能力充足', 'Capable')}** - {safe_text('过程满足规格要求', 'Process meets specifications')}")
                elif cpk >= 1.0:
                    st.warning(f"⚠️ **{safe_text('过程能力尚可', 'Marginally Capable')}** - {safe_text('需要持续监控', 'Needs monitoring')}")
                else:
                    st.error(f"❌ **{safe_text('过程能力不足', 'Not Capable')}** - {safe_text('需要立即改进', 'Needs improvement')}")
            
        except Exception as e:
            st.error(f"❌ {safe_text('分析过程中出现错误', 'Error during analysis')}: {str(e)}")
            st.exception(e)

else:
    # 欢迎界面
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem;">
        <h2 style="color: #1E3A8A;">{safe_text('欢迎使用DCO综合分析系统', 'Welcome to DCO Analysis System')}</h2>
        <p style="color: #4B5563; font-size: 1.2rem;">{safe_text('请在左侧控制面板上传数据文件并开始分析', 'Upload data files in the left panel to start analysis')}</p>
        <div style="margin-top: 2rem;">
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📊 {safe_text('SPC控制图', 'SPC Chart')}
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                🔍 {safe_text('异常检测', 'Anomaly Detection')}
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📈 {safe_text('完整统计', 'Statistics')}
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                ⚡ {safe_text('极值分析', 'Extreme Values')}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 系统功能说明
    col_func1, col_func2 = st.columns(2)
    
    with col_func1:
        st.markdown(f"""
        #### 📈 {safe_text('批次分析功能', 'Batch Analysis')}
        - {safe_text('数据自动清洗', 'Auto data cleaning')}（7 {safe_text('个清洗步骤', 'steps')}）
        - {safe_text('SPC控制图绘制', 'SPC chart')}（{safe_text('红-黄-绿区域', 'Red-Yellow-Green zones')}）
        - 4 {safe_text('种判异规则检测', 'control rules')}
        - {safe_text('完整统计分析', 'Complete statistics')}（{safe_text('均值、中位数、众数', 'mean, median, mode')}）
        - {safe_text('分位数分析', 'Percentile analysis')}（{safe_text('前/后十分位、前/后四分位', '10th/90th, 25th/75th')}）
        - {safe_text('正态分布拟合', 'Normal distribution fit')}
        """)
    
    with col_func2:
        st.markdown(f"""
        #### 📋 {safe_text('活动分析功能', 'Activity Analysis')}
        - {safe_text('活动数据自动清洗', 'Auto data cleaning')}
        - 4 {safe_text('个阶段分析', 'phase analysis')}
        - {safe_text('各阶段统计', 'Phase statistics')}（{safe_text('平均值、最小值、最大值、标准差', 'mean, min, max, std')}）
        - {safe_text('最快记录和最慢记录', 'Fastest/Slowest records')}
        - {safe_text('耗时最长的活动排名', 'Most time-consuming activities')}
        - {safe_text('效率最高的人员排名', 'Most efficient operators')}
        """)

# ==================== 页脚 ====================
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        <p>DCO综合分析系统 v3.1 | {safe_text('中英文双语支持', 'Bilingual Support')}</p>
        <p style="font-size: 0.8rem;">© 2024 {safe_text('版权所有', 'All Rights Reserved')}</p>
    </div>
    """,
    unsafe_allow_html=True
)
