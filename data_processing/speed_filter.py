import os
import xml.etree.ElementTree as ET
import pandas as pd
from scipy.signal import savgol_filter
import numpy as np

from files_path.file_path import emulation_path, data_path

# 输入文件路径
input_data_path = os.path.join(emulation_path, "e1output.xml")

# 解析XML文件
tree = ET.parse(input_data_path)
root = tree.getroot()

# 提取数据并存储到列表中
data = []
for interval in root.findall('interval'):
    begin = float(interval.get('begin'))
    end = float(interval.get('end'))
    id = interval.get('id')
    flow = float(interval.get('flow'))
    occupancy = float(interval.get('occupancy'))
    speed = float(interval.get('speed'))
    data.append([begin, end, id, flow, occupancy, speed])

# 将数据转换为DataFrame
df = pd.DataFrame(data, columns=['begin', 'end', 'id', 'flow', 'occupancy', 'speed'])

# 对flow、occupancy和speed列进行平滑处理
# 假设数据以1秒为间隔，5分钟窗口对应 5*60=300 个点
window_size = 19  # 必须为奇数
poly_order = 3

smoothed_data = []
for column in ['flow', 'occupancy', 'speed']:
    aspect = df[column].to_numpy()
    # 应用 Savitzky-Golay 滤波器
    smooth = savgol_filter(aspect, window_size, poly_order, mode='mirror')
    smooth = np.maximum(smooth, 0)  # 保证滤波结果非负
    smoothed_data.append(smooth)

# 更新XML文件中的数据
for index, interval in enumerate(root.findall('interval')):
    interval.set('flow', str(smoothed_data[0][index]))
    interval.set('occupancy', str(smoothed_data[1][index]))
    interval.set('speed', str(smoothed_data[2][index]))

# 将更新后的XML写回原文件
tree.write(input_data_path)

print(f"数据处理完成，平滑后的XML文件已保存到原文件: {input_data_path}")
