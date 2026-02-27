import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="DCO分析系统",
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
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2563EB;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #F3F4F6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .info-text {
        color: #4B5563;
        font-size: 0.9rem;
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
st.markdown('<h1 class="main-header">🔬 DCO数据分析与SPC监控系统</h1>', unsafe_allow_html=True)
st.markdown("---")

# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("## ⚙️ 控制面板")
    st.markdown("---")
    
    # 文件上传区域
    st.markdown("### 📂 数据上传")
    uploaded_batch = st.file_uploader(
        "**批次数据** (DCO-batch data.xlsx)",
        type=['xlsx', 'xls'],
        help="上传包含批次信息的Excel文件"
    )
    
    uploaded_activity = st.file_uploader(
        "**活动数据** (DCO-activity data.xlsx)",
        type=['xlsx', 'xls'],
        help="上传包含活动信息的Excel文件"
    )
    
    st.markdown("---")
    
    # 分析设置
    st.markdown("### ⚡ 分析设置")
    batch_size = st.number_input(
        "SPC分析数据点数",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
        help="选择用于SPC分析的最新数据点数量"
    )
    
    show_cleaning_steps = st.checkbox(
        "显示数据清洗步骤",
        value=True,
        help="勾选以显示详细的数据清洗过程"
    )
    
    st.markdown("---")
    
    # 执行按钮
    run_analysis = st.button("🚀 开始分析", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📌 使用说明")
    st.info(
        "1. 上传批次数据和活动数据文件\n"
        "2. 设置分析参数\n"
        "3. 点击'开始分析'按钮\n"
        "4. 查看分析结果和图表"
    )

# ==================== 主内容区域 ====================
if run_analysis:
    if uploaded_batch is None or uploaded_activity is None:
        st.warning("⚠️ 请先上传批次数据和活动数据文件！")
    else:
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # ==================== 第一部分：批次数据分析 ====================
            status_text.text("正在分析批次数据...")
            progress_bar.progress(20)
            
            with st.expander("查看批次数据清洗步骤", expanded=show_cleaning_steps):
                # 读取批次数据
                df_batch = pd.read_excel(uploaded_batch)
                st.write(f"📊 **原始数据行数**: {len(df_batch)}")
                
                # 清洗步骤
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**清洗前**:")
                    st.write(f"- 原始行数: {len(df_batch)}")
                
                df_batch = df_batch.dropna(subset=['Process Order ID'])
                df_batch = df_batch.drop_duplicates(subset=['Process Order ID'], keep='first')
                df_batch = df_batch.dropna(subset=['End date/time'])
                df_batch = df_batch[df_batch['Type'] == '干清']
                allowed_locations = ['CP Line 9', 'CP Line 10', 'CP Line 11', 'CP Line 12', 'CP Line 05', 'CP Line 08']
                df_batch = df_batch[df_batch['Location'].isin(allowed_locations)]
                
                if 'Time Elapsed (seconds)' in df_batch.columns:
                    df_batch = df_batch[df_batch['Time Elapsed (seconds)'] <= 10800]
                
                with col2:
                    st.write("**清洗后**:")
                    st.write(f"- 最终行数: {len(df_batch)}")
                    st.write(f"- 删除行数: {uploaded_batch.size - len(df_batch)}")
            
            progress_bar.progress(40)
            
            # 数据处理
            if 'End date/time' in df_batch.columns:
                df_batch['End date/time'] = pd.to_datetime(df_batch['End date/time'])
            
            # 单位转换
            for col in ['Time Elapsed (seconds)', 'Planned Duration (seconds)']:
                if col in df_batch.columns:
                    df_batch[col.replace('(seconds)', '(minutes)')] = (df_batch[col] / 60).round(2)
            
            # 取最新数据
            df_sorted = df_batch.sort_values('End date/time', ascending=False).head(batch_size)
            df_sorted = df_sorted.sort_values('End date/time', ascending=True)
            
            # 创建两列布局
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown('<h2 class="sub-header">📈 批次数据分析</h2>', unsafe_allow_html=True)
                
                # 获取数据列
                data_column = 'Time Elapsed (minutes)' if 'Time Elapsed (minutes)' in df_sorted.columns else None
                target_column = 'Planned Duration (minutes)' if 'Planned Duration (minutes)' in df_sorted.columns else None
                
                if data_column and target_column:
                    data_values = df_sorted[data_column].values
                    target_values = df_sorted[target_column].values
                    
                    # 统计计算
                    overall_mean = np.mean(data_values)
                    overall_median = np.median(data_values)
                    overall_std = np.std(data_values, ddof=1)
                    target_mean = np.mean(target_values)
                    
                    # 计算分位数
                    sorted_data = np.sort(data_values)
                    front_10 = np.percentile(sorted_data, 10)
                    back_10 = np.percentile(sorted_data, 90)
                    front_25 = np.percentile(sorted_data, 25)
                    back_25 = np.percentile(sorted_data, 75)
                    
                    # 控制限
                    ucl = target_mean * 1.2
                    lcl = max(0, target_mean * 0.8)
                    uwl = target_mean * 1.5
                    lwl = max(0, target_mean * 0.5)
                    
                    # 创建指标卡片
                    metric_row1 = st.columns(3)
                    with metric_row1[0]:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.metric("实际均值", f"{overall_mean:.2f}分钟")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with metric_row1[1]:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.metric("目标均值", f"{target_mean:.2f}分钟")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with metric_row1[2]:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.metric("标准差", f"{overall_std:.2f}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    metric_row2 = st.columns(3)
                    with metric_row2[0]:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.metric("UCL(目标+20%)", f"{ucl:.2f}分钟")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with metric_row2[1]:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.metric("中位数", f"{overall_median:.2f}分钟")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with metric_row2[2]:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.metric("LCL(目标-20%)", f"{lcl:.2f}分钟")
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # 创建SPC图
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    # 绘制区域
                    ax.axhspan(0, target_mean*0.5, alpha=0.2, color='red', label='A区(红: <50%目标)')
                    ax.axhspan(target_mean*0.5, target_mean*0.8, alpha=0.2, color='yellow', label='B区(黄: 50%-80%目标)')
                    ax.axhspan(target_mean*0.8, target_mean*1.2, alpha=0.2, color='green', label='C区(绿: 80%-120%目标)')
                    ax.axhspan(target_mean*1.2, target_mean*1.5, alpha=0.2, color='yellow')
                    ax.axhspan(target_mean*1.5, max(target_mean*3, 300), alpha=0.2, color='red')
                    
                    # 绘制数据点
                    x_values = range(len(data_values))
                    ax.plot(x_values, data_values, 'o-', color='blue', markersize=4, linewidth=1, label='实际值')
                    
                    # 绘制控制线
                    ax.axhline(y=target_mean, color='purple', linestyle='-.', linewidth=2, label=f'目标值: {target_mean:.2f}')
                    ax.axhline(y=ucl, color='red', linestyle='--', linewidth=1.5, label=f'UCL: {ucl:.2f}')
                    ax.axhline(y=lcl, color='red', linestyle='--', linewidth=1.5, label=f'LCL: {lcl:.2f}')
                    ax.axhline(y=overall_mean, color='darkblue', linestyle='-', linewidth=1.5, label=f'均值: {overall_mean:.2f}')
                    
                    # 标记异常点
                    anomalies = []
                    for i, value in enumerate(data_values):
                        if value > ucl or value < lcl:
                            ax.plot(i, value, 'ro', markersize=8, markeredgecolor='black', markeredgewidth=1)
                            anomalies.append(i+1)
                    
                    ax.set_ylim(bottom=0, top=min(300, max(data_values)*1.2))
                    ax.set_xlabel('数据点序号 (按时间排序)', fontsize=11)
                    ax.set_ylabel('时间 (分钟)', fontsize=11)
                    ax.set_title(f'SPC控制图 (最新{batch_size}个批次)', fontsize=12, fontweight='bold')
                    ax.legend(loc='upper right', fontsize=8, ncol=2)
                    ax.grid(True, alpha=0.3)
                    
                    st.pyplot(fig)
                    
                    if anomalies:
                        st.warning(f"⚠️ 发现 {len(anomalies)} 个异常点: 第 {', '.join(map(str, anomalies[:10]))} 点" + ("..." if len(anomalies)>10 else ""))
            
            progress_bar.progress(70)
            
            # ==================== 第二部分：活动数据分析 ====================
            with col_right:
                st.markdown('<h2 class="sub-header">📋 活动数据分析</h2>', unsafe_allow_html=True)
                
                # 读取活动数据
                df_activity = pd.read_excel(uploaded_activity)
                
                with st.expander("查看活动数据清洗步骤", expanded=show_cleaning_steps):
                    st.write(f"📊 **原始数据行数**: {len(df_activity)}")
                    
                    # 数据清洗
                    area_list = ['CPLine 9', 'CP Line 10', 'CP Line 11', 'CP Line 12', 'CP Line 05', 'CP Line08']
                    df_activity = df_activity[df_activity['Area'].isin(area_list)]
                    df_activity = df_activity[df_activity['Changeover Type'] == '干清']
                    df_activity = df_activity.dropna(subset=['Actual Duration (seconds)'])
                    
                    st.write(f"✅ **清洗后数据行数**: {len(df_activity)}")
                
                if 'Actual Duration (seconds)' in df_activity.columns:
                    df_activity['Actual Duration (minutes)'] = (df_activity['Actual Duration (seconds)'] / 60).round(2)
                
                # 按时间筛选最新100个批次
                if 'Created At' in df_activity.columns:
                    df_activity['Created At'] = pd.to_datetime(df_activity['Created At'])
                    batch_latest = df_activity.groupby('PO Number')['Created At'].max().reset_index()
                    batch_latest = batch_latest.sort_values('Created At', ascending=False).head(100)
                    latest_batches = batch_latest['PO Number'].tolist()
                    df_activity_filtered = df_activity[df_activity['PO Number'].isin(latest_batches)]
                    
                    st.info(f"📊 **分析范围**: 最新 {len(df_activity_filtered['PO Number'].unique())} 个批次, 共 {len(df_activity_filtered)} 条活动记录")
                else:
                    df_activity_filtered = df_activity
                
                # 阶段分析
                phases = ['清场前准备', '清场', '切换', '产线配置']
                
                # 创建阶段耗时图表
                phase_data = []
                for phase in phases:
                    phase_df = df_activity_filtered[df_activity_filtered['Phase Name'] == phase]
                    if len(phase_df) > 0:
                        phase_data.append({
                            '阶段': phase,
                            '平均耗时': phase_df['Actual Duration (minutes)'].mean(),
                            '总耗时': phase_df['Actual Duration (minutes)'].sum(),
                            '活动数': len(phase_df)
                        })
                
                if phase_data:
                    phase_df = pd.DataFrame(phase_data)
                    
                    # 创建两列显示
                    phase_col1, phase_col2 = st.columns(2)
                    
                    with phase_col1:
                        st.subheader("📊 各阶段平均耗时")
                        fig2, ax2 = plt.subplots(figsize=(6, 4))
                        bars = ax2.bar(phase_df['阶段'], phase_df['平均耗时'], color=['#3B82F6', '#10B981', '#F59E0B', '#EF4444'])
                        ax2.set_ylabel('平均耗时 (分钟)')
                        ax2.set_title('各阶段平均耗时对比')
                        ax2.tick_params(axis='x', rotation=45)
                        
                        # 添加数值标签
                        for bar in bars:
                            height = bar.get_height()
                            ax2.text(bar.get_x() + bar.get_width()/2., height,
                                    f'{height:.1f}', ha='center', va='bottom')
                        
                        plt.tight_layout()
                        st.pyplot(fig2)
                    
                    with phase_col2:
                        st.subheader("📈 各阶段总耗时")
                        fig3, ax3 = plt.subplots(figsize=(6, 4))
                        wedges, texts, autotexts = ax3.pie(phase_df['总耗时'], labels=phase_df['阶段'], autopct='%1.1f%%', startangle=90)
                        ax3.set_title('各阶段总耗时占比')
                        st.pyplot(fig3)
                    
                    # 详细数据表格
                    with st.expander("查看阶段详细数据"):
                        st.dataframe(phase_df, use_container_width=True)
                    
                    # 找出最耗时的阶段
                    max_phase = phase_df.loc[phase_df['平均耗时'].idxmax()]
                    st.info(f"⏱️ **最耗时阶段**: {max_phase['阶段']} (平均 {max_phase['平均耗时']:.2f} 分钟)")
                    
                    # 产线效率分析
                    st.subheader("🏭 产线效率分析")
                    line_efficiency = df_activity_filtered.groupby('Area')['Actual Duration (minutes)'].agg(['mean', 'count', 'sum']).round(2)
                    line_efficiency = line_efficiency.sort_values('mean')
                    
                    fig4, ax4 = plt.subplots(figsize=(8, 4))
                    colors = plt.cm.RdYlGn_r(line_efficiency['mean'] / line_efficiency['mean'].max())
                    ax4.barh(line_efficiency.index, line_efficiency['mean'], color=colors)
                    ax4.set_xlabel('平均耗时 (分钟)')
                    ax4.set_title('各产线平均耗时对比')
                    
                    # 添加数值标签
                    for i, (idx, row) in enumerate(line_efficiency.iterrows()):
                        ax4.text(row['mean'] + 0.5, i, f"{row['mean']:.1f}", va='center')
                    
                    st.pyplot(fig4)
            
            progress_bar.progress(100)
            status_text.text("✅ 分析完成！")
            
            # ==================== 底部总结 ====================
            st.markdown("---")
            st.markdown("## 📋 分析总结")
            
            summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
            
            with summary_col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("总批次", f"{len(df_batch)}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with summary_col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("总活动数", f"{len(df_activity_filtered)}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with summary_col3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("异常点数", f"{len(anomalies) if 'anomalies' in locals() else 0}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with summary_col4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("分析批次", f"{batch_size}")
                st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ 分析过程中出现错误: {str(e)}")
            st.exception(e)

else:
    # 欢迎界面
    st.markdown("""
    <div style="text-align: center; padding: 3rem;">
        <h2 style="color: #1E3A8A;">欢迎使用DCO分析系统</h2>
        <p style="color: #4B5563; font-size: 1.2rem;">请在左侧控制面板上传数据文件并开始分析</p>
        <div style="margin-top: 2rem;">
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📊 SPC控制图
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                🔍 异常检测
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                📈 特征分析
            </span>
            <span style="background-color: #EFF6FF; padding: 0.5rem 1rem; border-radius: 20px; margin: 0.5rem;">
                ⏱️ 阶段分析
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 显示示例图片
    st.markdown("---")
    st.markdown("### 🖥️ 系统功能预览")
    st.info("上传数据后，您将看到SPC控制图、阶段分析、产线效率对比等分析结果")
    
    # 系统功能说明
    func_col1, func_col2, func_col3 = st.columns(3)
    
    with func_col1:
        st.markdown("""
        #### 📈 批次分析功能
        - SPC控制图绘制
        - 异常点自动检测
        - 统计指标计算
        - 过程能力分析
        """)
    
    with func_col2:
        st.markdown("""
        #### 📋 活动分析功能
        - 阶段耗时对比
        - 产线效率分析
        - 活动类型统计
        - 批次时间筛选
        """)
    
    with func_col3:
        st.markdown("""
        #### ⚙️ 系统特点
        - 实时数据处理
        - 可视化图表展示
        - 自动异常预警
        - 交互式操作界面
        """)

# ==================== 页脚 ====================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #6B7280; padding: 1rem;">
        <p>DCO分析系统 v1.0 | 基于Streamlit构建 | 数据驱动决策支持</p>
        <p style="font-size: 0.8rem;">© 2024 版权所有</p>
    </div>
    """,
    unsafe_allow_html=True
)
