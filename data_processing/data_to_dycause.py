import os
import xml.etree.ElementTree as ET
import pandas as pd
import json
from collections import defaultdict
from files_path.file_path import screen_path, data_path


def load_filtered_detectors(json_path):
    """从JSON文件加载需要过滤的检测器ID列表"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return {item['detector_id'] for item in data['top_k_detectors']}


# 路径声明
xml_path = os.path.join(screen_path, "data_abnormal\\abnormal_0.xml")
output_path = os.path.join(data_path, "detector_speeds.xlsx")
json_path = os.path.join(data_path, "anomaly_results.json")

# 用户输入
use_filter = input("是否使用JSON文件过滤检测器？(y/n): ").lower() == 'y'
filtered_detectors = None

if use_filter:
    try:
        filtered_detectors = load_filtered_detectors(json_path)
        print(f"已加载 {len(filtered_detectors)} 个需要过滤的检测器")
    except Exception as e:
        print(f"加载JSON文件失败: {str(e)}")
        exit()

# 解析XML文件
tree = ET.parse(xml_path)
root = tree.getroot()

detector_data = defaultdict(dict)
time_points = set()

# 提取并处理数据
for interval in root.findall('interval'):
    det_id = interval.get('id')

    # 如果启用了过滤且检测器不在过滤列表中，则跳过
    if filtered_detectors and det_id not in filtered_detectors:
        continue

    begin = int(float(interval.get('begin')))  # 转换为整数秒
    speed = max(0.0, float(interval.get('speed')))  # 将-1转换为0

    time_points.add(begin)
    detector_data[det_id][begin] = speed

# 生成时间序列
sorted_times = sorted(time_points)

# 构建输出数据
output_rows = []
for det_id, time_dict in detector_data.items():
    row = [det_id]
    row.extend([round(time_dict.get(t, 0.0), 2) for t in sorted_times])
    output_rows.append(row)

# 创建DataFrame并保存为Excel
if output_rows:
    df = pd.DataFrame(output_rows)
    df.to_excel(output_path,
                index=False,
                header=False,
                engine='openpyxl')
    print(f"转换完成！结果已保存到 detector_speeds.xlsx，共转换 {len(output_rows)} 个检测器")
else:
    print("没有找到符合条件的数据，请检查过滤条件或输入文件")
