# -*- coding: utf-8 -*-

import os
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import grangercausalitytests
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")

SUMO_OUTPUT_XML = os.path.join(PROJECT_ROOT, "emulation", "e1output.xml")
INTERMEDIATE_DATA_CSV = os.path.join(PROJECT_ROOT, "data", "gc_input_data.csv")  # 保存中间数据的路径

MAX_LAG = 5


def create_dummy_files_for_granger():
    if not os.path.exists(SUMO_OUTPUT_XML):
        print(f"INFO: SUMO 输出 XML 文件不存在，正在创建虚拟文件：{SUMO_OUTPUT_XML}")
        os.makedirs(os.path.dirname(SUMO_OUTPUT_XML), exist_ok=True)
        dummy_xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<detector>
    <interval begin="0.00" end="1.00" id="det_A" nVehContrib="1" flow="10.00" occupancy="0.05" speed="15.50" harmonicMeanSpeed="15.00" length="5.00" nVehEntered="1"/>
    <interval begin="1.00" end="2.00" id="det_A" nVehContrib="1" flow="11.00" occupancy="0.05" speed="15.80" harmonicMeanSpeed="15.50" length="5.00" nVehEntered="1"/>
    <interval begin="2.00" end="3.00" id="det_A" nVehContrib="1" flow="10.50" occupancy="0.05" speed="15.00" harmonicMeanSpeed="14.80" length="5.00" nVehEntered="1"/>
    <interval begin="3.00" end="4.00" id="det_A" nVehContrib="1" flow="12.00" occupancy="0.06" speed="16.00" harmonicMeanSpeed="15.90" length="5.00" nVehEntered="1"/>
    <interval begin="4.00" end="5.00" id="det_A" nVehContrib="1" flow="13.00" occupancy="0.07" speed="16.50" harmonicMeanSpeed="16.30" length="5.00" nVehEntered="1"/>
    <interval begin="5.00" end="6.00" id="det_A" nVehContrib="1" flow="14.00" occupancy="0.07" speed="17.00" harmonicMeanSpeed="16.80" length="5.00" nVehEntered="1"/>
    <interval begin="0.00" end="1.00" id="det_B" nVehContrib="1" flow="8.00" occupancy="0.04" speed="14.00" harmonicMeanSpeed="13.80" length="5.00" nVehEntered="1"/>
    <interval begin="1.00" end="2.00" id="det_B" nVehContrib="1" flow="9.00" occupancy="0.04" speed="14.50" harmonicMeanSpeed="14.20" length="5.00" nVehEntered="1"/>
    <interval begin="2.00" end="3.00" id="det_B" nVehContrib="1" flow="9.50" occupancy="0.04" speed="14.80" harmonicMeanSpeed="14.60" length="5.00" nVehEntered="1"/>
    <interval begin="3.00" end="4.00" id="det_B" nVehContrib="1" flow="10.00" occupancy="0.05" speed="15.00" harmonicMeanSpeed="14.80" length="5.00" nVehEntered="1"/>
    <interval begin="4.00" end="5.00" id="det_B" nVehContrib="1" flow="10.50" occupancy="0.05" speed="15.20" harmonicMeanSpeed="15.00" length="5.00" nVehEntered="1"/>
    <interval begin="5.00" end="6.00" id="det_B" nVehContrib="1" flow="11.00" occupancy="0.06" speed="15.50" harmonicMeanSpeed="15.30" length="5.00" nVehEntered="1"/>
    <interval begin="0.00" end="1.00" id="det_C" nVehContrib="0" flow="0.00" occupancy="0.00" speed="-1.00" harmonicMeanSpeed="-1.00" length="-1.00" nVehEntered="0"/>
    <interval begin="1.00" end="2.00" id="det_C" nVehContrib="0" flow="0.00" occupancy="0.00" speed="-1.00" harmonicMeanSpeed="-1.00" length="-1.00" nVehEntered="0"/>
    <interval begin="2.00" end="3.00" id="det_C" nVehContrib="0" flow="0.00" occupancy="0.00" speed="-1.00" harmonicMeanSpeed="-1.00" length="-1.00" nVehEntered="0"/>
    <interval begin="3.00" end="4.00" id="det_C" nVehContrib="0" flow="0.00" occupancy="0.00" speed="-1.00" harmonicMeanSpeed="-1.00" length="-1.00" nVehEntered="0"/>
    <interval begin="4.00" end="5.00" id="det_C" nVehContrib="0" flow="0.00" occupancy="0.00" speed="-1.00" harmonicMeanSpeed="-1.00" length="-1.00" nVehEntered="0"/>
    <interval begin="5.00" end="6.00" id="det_C" nVehContrib="0" flow="0.00" occupancy="0.00" speed="-1.00" harmonicMeanSpeed="-1.00" length="-1.00" nVehEntered="0"/>
</detector>
"""
        try:
            with open(SUMO_OUTPUT_XML, "w", encoding="utf-8") as f:
                f.write(dummy_xml_content)
        except Exception as e:
            print(f"ERROR: 创建虚拟 SUMO XML 文件失败: {e}")


def parse_sumo_xml_to_dataframe():
    try:
        tree = ET.parse(SUMO_OUTPUT_XML)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"ERROR: SUMO XML 文件未找到：'{SUMO_OUTPUT_XML}'。请检查路径是否正确。")
        return None
    except ET.ParseError as e:
        print(f"ERROR: 解析 SUMO XML 文件 '{SUMO_OUTPUT_XML}' 失败。文件格式可能错误。详情: {e}")
        return None
    except Exception as e:
        print(f"ERROR: 打开或解析 XML 文件时发生意外错误: {e}")
        return None

    time_series_data = defaultdict(dict)
    all_metrics_per_detector = defaultdict(set)
    METRICS_TO_EXTRACT = ['speed', 'flow', 'occupancy']

    for interval_element in root.findall('interval'):
        detector_id = interval_element.get('id')
        begin_time_str = interval_element.get('begin')

        if not (detector_id and begin_time_str):
            continue

        try:
            begin_time = float(begin_time_str)
            time_key = round(begin_time, 2)

            for metric in METRICS_TO_EXTRACT:
                value_str = interval_element.get(metric)

                if value_str is not None:
                    try:
                        value = float(value_str)
                        if value == -1.00:
                            value = np.nan

                        metric_column_name = f"{detector_id}__{metric}"
                        time_series_data[time_key][metric_column_name] = value
                        all_metrics_per_detector[detector_id].add(metric)

                    except ValueError:
                        metric_column_name = f"{detector_id}__{metric}"
                        time_series_data[time_key][metric_column_name] = np.nan
                        all_metrics_per_detector[detector_id].add(metric)
                else:
                    metric_column_name = f"{detector_id}__{metric}"
                    time_series_data[time_key][metric_column_name] = np.nan
                    all_metrics_per_detector[detector_id].add(metric)

        except ValueError:
            continue

    df_processed = pd.DataFrame.from_dict(time_series_data, orient='index')

    all_potential_columns = [f"{det}__{metric}" for det in all_metrics_per_detector for metric in METRICS_TO_EXTRACT]
    for col in all_potential_columns:
        if col not in df_processed.columns:
            df_processed[col] = np.nan

    df_processed = df_processed.sort_index(axis=1)
    df_processed = df_processed.sort_index()
    df_processed.dropna(axis=1, how='all', inplace=True)

    if df_processed.empty:
        print("未提取到任何有效的时间序列数据。")
        return None

    # 确保输出目录存在
    os.makedirs(os.path.dirname(INTERMEDIATE_DATA_CSV), exist_ok=True)

    # 保存 DataFrame 到 CSV 文件
    try:
        df_processed.to_csv(INTERMEDIATE_DATA_CSV, index=True, float_format='%.4f')
        print(f"INFO: 已将解析后的时间序列数据保存到：'{INTERMEDIATE_DATA_CSV}'")
        return df_processed  # 返回 DataFrame 以供后续立即使用（如果需要）
    except Exception as e:
        print(f"ERROR: 保存中间数据到 CSV 文件 '{INTERMEDIATE_DATA_CSV}' 失败: {e}")
        return None


def perform_granger_causality_tests(df_data):
    if df_data is None or df_data.empty:
        print("没有可用于格兰杰因果检验的数据。")
        return

    print(f"\n--- 开始执行格兰杰因果检验 (最大滞后阶数: {MAX_LAG}) ---")

    all_series_columns = df_data.columns.tolist()
    num_tests_performed = 0

    for i in range(len(all_series_columns)):
        for j in range(len(all_series_columns)):
            if i == j:
                continue

            series_A_name = all_series_columns[i]
            series_B_name = all_series_columns[j]

            df_pair = df_data[[series_A_name, series_B_name]]
            df_pair_cleaned = df_pair.dropna()

            min_data_points_required = MAX_LAG * 2 + 10

            if len(df_pair_cleaned) < min_data_points_required:
                continue

            try:
                gc_result = grangercausalitytests(df_pair_cleaned, maxlag=MAX_LAG, verbose=False)
                num_tests_performed += 1

                for lag, (test_stats, _, _, _) in gc_result.items():
                    p_value_f_test = test_stats['params_ftest'][1]
                    significance_level = 0.05
                    decision = "不 Granger 引起" if p_value_f_test > significance_level else "Granger 引起"

                    print(
                        f"  - 滞后阶数 {lag}: '{series_B_name}' {decision} '{series_A_name}' (p-value: {p_value_f_test:.4f})")

            except Exception as e:
                print(f"  ERROR: 对 '{series_A_name}' 与 '{series_B_name}' 进行格兰杰检验时出错: {e}")

    if num_tests_performed == 0:
        print("\n没有足够的数据或条件来执行任何格兰杰因果检验。")
    else:
        print(f"\n--- 完成了 {num_tests_performed} 项格兰杰因果检验 ---")


def main():
    create_dummy_files_for_granger()

    # 步骤 1: 解析 SUMO XML 并将数据转化为 DataFrame，并保存到 CSV
    print("--- 开始解析 SUMO XML 并准备数据 ---")
    df_intermediate = parse_sumo_xml_to_dataframe()

    if df_intermediate is None:
        print("未能成功准备数据，退出程序。")
        return

    print(f"INFO: DataFrame 包含 {df_intermediate.shape[0]} 个时间步和 {df_intermediate.shape[1]} 个 detector__metric 时间序列。")

    # 步骤 2: 从 CSV 加载数据并执行格兰杰因果检验
    print("\n--- 开始加载数据并执行格兰杰因果检验 ---")
    try:
        df_for_granger = pd.read_csv(INTERMEDIATE_DATA_CSV, index_col=0)
        # 确保加载的 DataFrame 的数据类型正确，尤其 NaN 值
        df_for_granger = df_for_granger.apply(pd.to_numeric, errors='coerce')
        perform_granger_causality_tests(df_for_granger)
    except FileNotFoundError:
        print(f"ERROR: 中间数据 CSV 文件未找到：'{INTERMEDIATE_DATA_CSV}'。请检查文件是否已成功创建。")
    except pd.errors.EmptyDataError:
        print(f"ERROR: 中间数据 CSV 文件 '{INTERMEDIATE_DATA_CSV}' 为空。")
    except Exception as e:
        print(f"ERROR: 加载或处理中间数据 CSV 文件时发生错误: {e}")


if __name__ == "__main__":
    main()