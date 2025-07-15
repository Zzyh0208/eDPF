import xml.etree.ElementTree as ET

# 检测器文件的路径
from files_path.file_path import emulation_path

detector_file = emulation_path + "e4.add.xml"

# 新的记录频率（单位：秒）
new_frequency = "1"

tree = ET.parse(detector_file)
root = tree.getroot()

# 找到所有 e1Detector 元素，这些元素包含了检测器的记录频率
detectors = root.findall(".//e1Detector")

# 遍历每个 e1Detector 元素，并将记录频率设置为新值
for detector in detectors:
    detector.set("freq", new_frequency)

# 保存修改后的检测器文件
tree.write(detector_file)

print("所有检测器的记录频率已经成功修改为", new_frequency, "秒。")
