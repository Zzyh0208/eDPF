import os
import xml.etree.ElementTree as ET
import json
from collections import defaultdict

from files_path.file_path import emulation_path, data_path


def parse_detectors(add_file):
    """解析.add.xml文件，返回精确的车道ID到检测器ID的映射"""
    tree = ET.parse(add_file)
    root = tree.getroot()

    lane_to_detectors = defaultdict(list)
    all_lanes = set()

    for e1 in root.findall('.//e1Detector'):
        det_id = e1.get('id')
        lane_id = e1.get('lane')
        lane_to_detectors[lane_id].append(det_id)
        all_lanes.add(lane_id)

    return lane_to_detectors, all_lanes


def parse_tl_logics(net_file):
    """解析交通信号灯配置"""
    tree = ET.parse(net_file)
    root = tree.getroot()

    tl_logics = {}
    for tl in root.findall('.//tlLogic'):
        tl_id = tl.get('id')
        phases = []
        for phase in tl.findall('phase'):
            phase_data = {
                'duration': float(phase.get('duration')),
                'state': phase.get('state'),
                'minDur': float(phase.get('minDur')) if phase.get('minDur') else None,
                'maxDur': float(phase.get('maxDur')) if phase.get('maxDur') else None
            }
            phases.append(phase_data)
        tl_logics[tl_id] = {
            'type': tl.get('type'),
            'programID': tl.get('programID'),
            'offset': float(tl.get('offset')),
            'phases': phases
        }
    return tl_logics


def find_valid_junctions(net_file, all_lanes):
    """查找有效交叉口"""
    tree = ET.parse(net_file)
    root = tree.getroot()

    valid_junctions = {}

    for junction in root.findall('.//junction'):
        jid = junction.get('id')
        # 只处理信号灯控制的交叉口
        if junction.get('type') != 'traffic_light':
            continue

        inc_lanes = junction.get('incLanes', '').split()
        if inc_lanes and all(lane in all_lanes for lane in inc_lanes):
            valid_junctions[jid] = inc_lanes

    return valid_junctions


def build_final_data(valid_junctions, lane_to_detectors, tl_logics):
    """构建最终数据结构"""
    result = {}

    for jid, lane_ids in valid_junctions.items():
        # 获取检测器ID
        detectors = []
        for lid in lane_ids:
            detectors.extend(lane_to_detectors[lid])
        unique_detectors = list(dict.fromkeys(detectors))

        # 获取信号灯配置
        tl_data = tl_logics.get(jid, None)

        # 构建条目
        result[jid] = {
            'detectors': unique_detectors,
            'traffic_light': tl_data
        }

    return result


if __name__ == "__main__":
    # 输入文件路径
    add_file = os.path.join(emulation_path, "e4.add.xml")
    net_file = os.path.join(emulation_path, "map.net.xml")
    output_path = os.path.join(data_path, "junction_data.json")

    # 1. 解析检测器数据
    lane_to_detectors, all_lanes = parse_detectors(add_file)

    # 2. 解析交通信号灯配置
    tl_logics = parse_tl_logics(net_file)

    # 3. 查找有效交叉口
    valid_junctions = find_valid_junctions(net_file, all_lanes)

    # 4. 构建最终数据
    final_data = build_final_data(valid_junctions, lane_to_detectors, tl_logics)

    # 5. 保存为JSON
    with open(output_path, 'w') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)

    print("处理完成，结果已保存到 : ", output_path)
