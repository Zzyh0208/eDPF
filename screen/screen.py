import os
import xml.etree.ElementTree as ET
import numpy as np
import json
from collections import defaultdict
from tqdm import tqdm
from pathlib import Path
from scipy.stats import median_abs_deviation


class EnhancedTrafficAnomalyDetector:
    def __init__(self, phase_length=90, time_window=30, top_k=10, verbose=True):
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

            # 读取所有特征并预处理
            record = {
                'speed': float(interval.get('speed')),
                'occupancy': float(interval.get('occupancy')),
                'flow': float(interval.get('flow'))
            }

            # 数据有效性判断
            valid = record['speed'] > 0 and record['occupancy'] >= 0 and record['flow'] >= 0
            if valid:
                for feature in self.features:
                    time_series[detector_id][feature].append((t, record[feature]))

        # 数据平滑处理
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
        file_count = 0

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
            file_count += 1

        if file_count == 0:
            raise ValueError("未找到正常数据文件")

        # 计算鲁棒统计量
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
            self._print(f"模型已保存至: {save_path}")

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
        """计算基于MAD的鲁棒异常分数"""
        if mad == 0 or np.isnan(median) or np.isnan(mad):
            return 0
        return abs(actual - median) / mad

    def detect_anomalies(self, test_file, output_file=None):
        if not self._model_trained:
            raise RuntimeError("请先训练或加载模型")

        self._print(f"\n开始检测异常: {Path(test_file).name}")
        test_data = self._parse_xml(test_file)

        detector_scores = defaultdict(list)
        min_valid_samples = 3  # 窗口内最小有效样本数

        for detector_id, features in tqdm(test_data.items(),
                                          desc="处理检测器数据",
                                          disable=not self.verbose):
            feature_scores = {f: [] for f in self.features}
            time_points = set()

            # 收集所有时间点
            for feature in self.features:
                for t, _ in features[feature]:
                    time_points.add(t)

            # 按时间顺序处理
            sorted_times = sorted(time_points)
            for t in sorted_times:
                phase = t % self.phase_length
                combined_score = 0
                valid_features = 0

                for feature in self.features:
                    # 查找当前时间的特征值
                    current_value = next((v for (time, v) in features[feature] if time == t), None)
                    if current_value is None:
                        continue

                    # 获取正常参数
                    params = self.normal_params[detector_id][phase].get(feature, (np.nan, np.nan))
                    if np.isnan(params[0]):
                        continue

                    # 计算特征分数
                    score = self._calculate_feature_score(current_value, *params)
                    feature_scores[feature].append(score)
                    valid_features += 1

                # 组合多特征分数
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

            # 处理最终得分（使用95百分位数避免极端值）
            if detector_scores[detector_id]:
                final_score = np.percentile(detector_scores[detector_id], 95)
                detector_scores[detector_id] = final_score
            else:
                detector_scores[detector_id] = 0

        # 筛选有效检测器（至少有5个有效时间点）
        valid_detectors = {
            k: v for k, v in detector_scores.items()
            if len(test_data[k]['speed']) >= 5
        }

        sorted_scores = sorted(valid_detectors.items(),
                               key=lambda x: x[1],
                               reverse=True)[:self.top_k]

        self._print("\n异常检测结果:")
        for rank, (detector, score) in enumerate(sorted_scores, 1):
            self._print(f"Top {rank}: {detector} - 综合异常指数: {score:.2f}")

        # 保存结果到上一级目录的data文件夹中
        result_data = {
            "top_k_detectors": [
                {"detector_id": detector, "anomaly_score": score}
                for detector, score in sorted_scores
            ]
        }
        data_dir = os.path.join(os.path.dirname(os.getcwd()), "data")
        os.makedirs(data_dir, exist_ok=True)
        result_file = os.path.join(data_dir, "anomaly_results.json")
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        self._print(f"检测结果已保存至: {result_file}")

        if output_file:
            with open(output_file, 'w') as f:
                f.write("排名,检测器ID,异常指数\n")
                for rank, (detector, score) in enumerate(sorted_scores, 1):
                    f.write(f"{rank},{detector},{score:.4f}\n")
            self._print(f"结果已保存至: {output_file}")

        return sorted_scores


# 使用示例
if __name__ == "__main__":
    detector = EnhancedTrafficAnomalyDetector(
        phase_length=90,
        time_window=30,
        top_k=20,
        verbose=True
    )

    model_path = "enhanced_model.json"
    if os.path.exists(model_path):
        detector.load_model(model_path)
    else:
        # 训练新模型
        detector.train_normal_model(
            normal_dir="data_normal",
            save_path=model_path
        )

    # 检测异常
    # test_result = detector.detect_anomalies(
    #     test_file="data_abnormal/cluster_1928080330_5128988682_all_red_e1.xml",
    #     output_file="enhanced_result.csv"
    # )
    #
    # print("\n最终异常排名:")
    # for i, (detector_id, score) in enumerate(test_result, 1):
    #     print(f"{i:>2}. {detector_id}: {score:.2f}")
