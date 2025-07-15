import os
import xml.etree.ElementTree as ET
import pandas as pd
import json
import numpy as np
from collections import defaultdict
from scipy.signal import savgol_filter
from scipy.stats import median_abs_deviation
from tqdm import tqdm
from pathlib import Path
from files_path.file_path import data_path, screen_path

# ====================== 配置参数 ======================
data_paths = os.path.join(data_path, "final_output\\")
smoothed_path = os.path.join(data_path, "smoothed_output\\")
anomaly_path = os.path.join(data_path, "anomaly_results\\")
dycause_path = os.path.join(data_path, "dycause_outputs\\")
model_path = os.path.join(screen_path, "enhanced_model.json")

INPUT_DIR = data_paths  # 原始XML文件目录
SMOOTHED_DIR = smoothed_path  # 平滑后XML保存目录
ANOMALY_DIR = anomaly_path  # 异常检测结果保存目录
EXCEL_DIR = dycause_path  # Excel输出目录
MODEL_PATH = model_path  # 预训练模型路径

# 处理参数
WINDOW_SIZE = 19     # 平滑窗口大小（必须为奇数）
POLY_ORDER = 3       # 多项式阶数
PHASE_LENGTH = 90    # 信号周期长度
TIME_WINDOW = 30     # 时间窗口大小
TOP_K = 160          # 显示前K个异常检测器


# ====================== 工具类 ======================
class TrafficProcessor:
    def __init__(self):
        self.detector = EnhancedTrafficAnomalyDetector(
            phase_length=PHASE_LENGTH,
            time_window=TIME_WINDOW,
            top_k=TOP_K,
            verbose=False
        )
        if os.path.exists(MODEL_PATH):
            self.detector.load_model(MODEL_PATH)
        else:
            raise FileNotFoundError("未找到预训练模型")

    def process_single_file(self, input_path):
        """处理单个XML文件的完整流程"""
        try:
            # 创建输出目录
            os.makedirs(SMOOTHED_DIR, exist_ok=True)
            os.makedirs(ANOMALY_DIR, exist_ok=True)
            os.makedirs(EXCEL_DIR, exist_ok=True)

            # 生成基础文件名
            base_name = os.path.basename(input_path)
            file_stem = Path(base_name).stem

            # 步骤1: 异常检测生成JSON
            json_path = os.path.join(ANOMALY_DIR, f"{file_stem}_anomaly.json")
            if not os.path.exists(json_path):
                self.detector.detect_anomalies(input_path, json_path)

            # 步骤2: 数据平滑处理
            smoothed_path = os.path.join(SMOOTHED_DIR, f"{file_stem}_smoothed.xml")
            if not os.path.exists(smoothed_path):
                self._smooth_xml(input_path, smoothed_path)

            # 步骤3: 生成两种Excel文件
            for use_filter in [True, False]:
                suffix = "filtered" if use_filter else "unfiltered"
                excel_path = os.path.join(EXCEL_DIR, f"{file_stem}_{suffix}.xlsx")
                self._generate_excel(smoothed_path, json_path, excel_path, use_filter)

            return True
        except Exception as e:
            print(f"处理文件 {input_path} 时出错: {str(e)}")
            return False

    def _smooth_xml(self, input_path, output_path):
        """执行第一部分的数据平滑处理"""
        tree = ET.parse(input_path)
        root = tree.getroot()

        # 提取数据
        data = []
        for interval in root.findall('interval'):
            data.append([
                float(interval.get('begin')),
                float(interval.get('end')),
                interval.get('id'),
                float(interval.get('flow')),
                float(interval.get('occupancy')),
                float(interval.get('speed'))
            ])

        # 数据平滑
        df = pd.DataFrame(data, columns=['begin', 'end', 'id', 'flow', 'occupancy', 'speed'])
        smoothed_data = []
        for column in ['flow', 'occupancy', 'speed']:
            aspect = df[column].to_numpy()
            smooth = savgol_filter(aspect, WINDOW_SIZE, POLY_ORDER, mode='mirror')
            smoothed_data.append(np.maximum(smooth, 0))

        # 更新XML数据
        for index, interval in enumerate(root.findall('interval')):
            interval.set('flow', str(smoothed_data[0][index]))
            interval.set('occupancy', str(smoothed_data[1][index]))
            interval.set('speed', str(smoothed_data[2][index]))

        tree.write(output_path)

    def _generate_excel(self, xml_path, json_path, output_path, use_filter):
        """生成Excel文件，支持过滤模式"""
        # 加载过滤列表
        filtered_detectors = None
        if use_filter:
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                filtered_detectors = {item['detector_id'] for item in data['top_k_detectors']}
            except:
                filtered_detectors = set()

        # 解析XML
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # 提取数据
        detector_data = defaultdict(dict)
        time_points = set()
        for interval in root.findall('interval'):
            det_id = interval.get('id')
            if filtered_detectors and det_id not in filtered_detectors:
                continue

            begin = int(float(interval.get('begin')))
            speed = max(0.0, float(interval.get('speed')))
            time_points.add(begin)
            detector_data[det_id][begin] = speed

        # 生成时间序列
        sorted_times = sorted(time_points)
        output_rows = []
        for det_id, time_dict in detector_data.items():
            row = [det_id] + [round(time_dict.get(t, 0.0), 2) for t in sorted_times]
            output_rows.append(row)

        # 保存Excel
        if output_rows:
            pd.DataFrame(output_rows).to_excel(
                output_path, index=False, header=False, engine='openpyxl')


# ====================== 异常检测类 ======================
class EnhancedTrafficAnomalyDetector:
    def __init__(self, phase_length=90, time_window=30, top_k=TOP_K, verbose=True):
        self.phase_length = phase_length
        self.time_window = time_window
        self.top_k = top_k
        self.verbose = verbose
        self.features = ['speed', 'occupancy', 'flow']
        self.normal_params = defaultdict(lambda: defaultdict(dict))
        self._model_trained = False

    def _print(self, message):
        if self.verbose:
            print(f"[SYSTEM] {message}")

    def _smooth_data(self, data, window_size=3):
        """使用移动平均进行数据平滑"""
        if len(data) < window_size:
            return data
        return np.convolve(data, np.ones(window_size) / window_size, mode='valid')

    def _parse_xml(self, file_path):
        """改进的XML解析，包含数据预处理"""
        tree = ET.parse(file_path)
        root = tree.getroot()

        time_series = defaultdict(lambda: defaultdict(list))
        for interval in root.findall('interval'):
            t = int(float(interval.get('begin')))
            detector_id = interval.get('id')

            record = {
                'speed': float(interval.get('speed')),
                'occupancy': float(interval.get('occupancy')),
                'flow': float(interval.get('flow'))
            }

            valid = record['speed'] > 0 and record['occupancy'] >= 0 and record['flow'] >= 0
            if valid:
                for feature in self.features:
                    time_series[detector_id][feature].append((t, record[feature]))

        for detector in time_series.values():
            for feature in self.features:
                if len(detector[feature]) > 0:
                    times, values = zip(*detector[feature])
                    smoothed = self._smooth_data(values)
                    if len(smoothed) > 0:
                        detector[feature] = list(zip(times[-len(smoothed):], smoothed))
        return time_series

    def train_normal_model(self, normal_dir, save_path=None):
        self._print(f"开始训练正常流量模型，数据目录: {normal_dir}")
        phase_buckets = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for file_name in tqdm(sorted(os.listdir(normal_dir)),
                              desc="处理正常数据文件",
                              disable=not self.verbose):
            if not file_name.startswith("normal_"):
                continue

            file_path = os.path.join(normal_dir, file_name)
            time_series = self._parse_xml(file_path)

            for detector, features in time_series.items():
                for feature in self.features:
                    for t, value in features[feature]:
                        phase = t % self.phase_length
                        phase_buckets[detector][phase][feature].append(value)

        self._print("计算鲁棒统计参数...")
        for detector in tqdm(phase_buckets.keys(),
                             desc="处理检测器",
                             disable=not self.verbose):
            for phase in range(self.phase_length):
                for feature in self.features:
                    data = phase_buckets[detector][phase][feature]
                    if len(data) >= 5:
                        median = np.median(data)
                        mad = median_abs_deviation(data, scale='normal')
                        self.normal_params[detector][phase][feature] = (median, mad)
                    else:
                        self.normal_params[detector][phase][feature] = (np.nan, np.nan)

        self._model_trained = True
        if save_path:
            self.save_model(save_path)

    def save_model(self, file_path):
        save_data = {}
        for detector, phases in self.normal_params.items():
            save_data[detector] = {}
            for phase, features in phases.items():
                save_data[detector][str(phase)] = {
                    feature: params for feature, params in features.items()
                }
        with open(file_path, 'w') as f:
            json.dump(save_data, f, indent=2)

    def load_model(self, file_path):
        self._print(f"加载预训练模型: {file_path}")
        with open(file_path, 'r') as f:
            loaded_data = json.load(f)

        self.normal_params = defaultdict(lambda: defaultdict(dict))
        for detector, phases in loaded_data.items():
            for phase_str, features in phases.items():
                phase = int(phase_str)
                for feature, params in features.items():
                    self.normal_params[detector][phase][feature] = tuple(params)
        self._model_trained = True

    def _calculate_feature_score(self, actual, median, mad):
        if mad == 0 or np.isnan(median) or np.isnan(mad):
            return 0
        return abs(actual - median) / mad

    def detect_anomalies(self, test_file, output_file=None):
        if not self._model_trained:
            raise RuntimeError("请先训练或加载模型")

        self._print(f"\n开始检测异常: {Path(test_file).name}")
        test_data = self._parse_xml(test_file)

        detector_scores = defaultdict(list)
        for detector_id, features in tqdm(test_data.items(),
                                          desc="处理检测器数据",
                                          disable=not self.verbose):
            feature_scores = {f: [] for f in self.features}
            time_points = set()

            for feature in self.features:
                for t, _ in features[feature]:
                    time_points.add(t)

            sorted_times = sorted(time_points)
            for t in sorted_times:
                phase = t % self.phase_length
                combined_score = 0
                valid_features = 0

                for feature in self.features:
                    current_value = next((v for (time, v) in features[feature] if time == t), None)
                    if current_value is None:
                        continue

                    params = self.normal_params[detector_id][phase].get(feature, (np.nan, np.nan))
                    if np.isnan(params[0]):
                        continue

                    score = self._calculate_feature_score(current_value, *params)
                    feature_scores[feature].append(score)
                    valid_features += 1

                if valid_features > 0:
                    window_scores = []
                    for feature in self.features:
                        if len(feature_scores[feature]) >= self.time_window:
                            window = feature_scores[feature][-self.time_window:]
                        else:
                            window = feature_scores[feature]

                        if len(window) > 0:
                            window_scores.append(np.median(window))

                    if len(window_scores) > 0:
                        combined_score = np.mean(window_scores)
                        detector_scores[detector_id].append(combined_score)

            if detector_scores[detector_id]:
                final_score = np.percentile(detector_scores[detector_id], 95)
                detector_scores[detector_id] = final_score
            else:
                detector_scores[detector_id] = 0

        valid_detectors = {
            k: v for k, v in detector_scores.items()
            if len(test_data[k]['speed']) >= 5
        }

        sorted_scores = sorted(valid_detectors.items(),
                               key=lambda x: x[1],
                               reverse=True)[:self.top_k]

        result_data = {
            "top_k_detectors": [
                {"detector_id": detector, "anomaly_score": score}
                for detector, score in sorted_scores
            ]
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result_data, f, indent=2)
        return sorted_scores


# ====================== 主执行流程 ======================
if __name__ == "__main__":
    processor = TrafficProcessor()

    xml_files = [os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR)
                 if f.endswith(".xml") and "normal" not in f]

    print(f"开始处理 {len(xml_files)} 个文件...")
    success_count = 0

    for xml_path in tqdm(xml_files, desc="处理进度"):
        if processor.process_single_file(xml_path):
            success_count += 1

    print(f"\n处理完成！成功处理 {success_count}/{len(xml_files)} 个文件")