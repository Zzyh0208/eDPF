import os
import shutil
import json
import time
import traci

from files_path.file_path import emulation_path, data_path
import psutil  # 新增进程管理库

data_paths = os.path.join(data_path, "junction_data.json")
E1_SOURCE_PATH = os.path.join(emulation_path, "e1output.xml")


def kill_sumo_processes():
    """强制终止所有SUMO相关进程"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] in ['sumo-gui.exe', 'sumo.exe']:
            try:
                proc.kill()
                print(f"终止残留进程: {proc.pid}")
            except Exception as e:
                print(f"进程终止失败: {str(e)}")


def safe_copy(src, dst, retries=5, delay=2):
    """安全文件复制（带重试机制）"""
    for i in range(retries):
        try:
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            print(f"⚠️ 文件操作失败（尝试 {i+1}/{retries}）: {str(e)}")
            time.sleep(delay)
    return False


def generate_anomaly_states(original_state):
    """生成异常信号状态"""
    length = len(original_state)
    return {
        'all_red': 'r' * length,
        'all_green': 'G' * length
    }


def run_simulation(junction_id, anomaly_type, config_path, output_dir, steps=3600, traffic_scale=4):
    """运行单次仿真并保存结果"""
    # 预处理：清理残留进程
    kill_sumo_processes()
    time.sleep(3)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 启动SUMO
    sumoBinary = "sumo-gui"
    sumoCmd = [
        sumoBinary,
        "-c", config_path,
        "--start",  # 关键参数：自动开始运行
        "--quit-on-end",  # 完成后自动退出
        "--scale", str(traffic_scale),  # 新增流量缩放参数
        "--time-to-teleport", "-1",  # 禁用车辆传送
        "--waiting-time-memory", "1000",
        "--duration-log.statistics"
    ]

    # 启动前清理旧文件
    traci.start(sumoCmd)

    # 加载路口数据
    with open(data_paths) as f:
        junction_data = json.load(f)

    # 获取信号灯配置
    tl_config = junction_data[junction_id]['traffic_light']
    original_phases = tl_config['phases']

    # 生成异常状态
    sample_state = original_phases[0]['state']
    anomaly_states = generate_anomaly_states(sample_state)

    # 启动前清理旧文件
    if os.path.exists(E1_SOURCE_PATH):
        try:
            os.remove(E1_SOURCE_PATH)
        except:
            print("初始文件清理失败，继续运行...")

    step = 0
    try:
        while step < steps:
            # 异常注入时间段
            if 800 <= step <= 2800:
                traci.trafficlight.setRedYellowGreenState(
                    junction_id,
                    anomaly_states[anomaly_type]
                )
            else:
                # 正常相位控制
                current_phase = step % sum(p['duration'] for p in original_phases)
                phase_index = 0
                accumulated = 0
                for i, phase in enumerate(original_phases):
                    accumulated += phase['duration']
                    if current_phase < accumulated:
                        phase_index = i
                        break
                traci.trafficlight.setRedYellowGreenState(
                    junction_id,
                    original_phases[phase_index]['state']
                )

            traci.simulationStep()
            step += 1
    finally:
        traci.close()
        time.sleep(5)  # 基础等待时间
        kill_sumo_processes()  # 再次确认进程终止
        time.sleep(3)

    # 处理E1文件（新增核心逻辑）
    e1_target_name = f"{junction_id}_{anomaly_type}_e1.xml"
    e1_target_path = os.path.join(data_path, 'final_output', e1_target_name)

    # 创建目标目录
    os.makedirs(os.path.dirname(e1_target_path), exist_ok=True)

    if safe_copy(E1_SOURCE_PATH, e1_target_path):
        print(f"✅ 成功保存E1数据到: {e1_target_path}")
    else:
        print(f"❌ 严重错误: 无法保存E1文件 {e1_target_path}")


def batch_run_simulation(config_path):
    """批量运行所有异常场景"""
    with open(data_paths) as f:
        junction_data = json.load(f)

    # 创建最终输出目录
    final_output = os.path.join(emulation_path, 'final_output')
    os.makedirs(final_output, exist_ok=True)

    for junction_id in junction_data.keys():
        for anomaly_type in ['all_red', 'all_green']:
            print(f"\n=== 开始 {junction_id} 的 {anomaly_type} 场景 ===")
            temp_dir = os.path.join(emulation_path, f"temp_{junction_id}_{anomaly_type}")

            run_simulation(
                junction_id=junction_id,
                anomaly_type=anomaly_type,
                config_path=config_path,
                output_dir=temp_dir,
                steps=3600,
                traffic_scale=4
            )

            # 增强的目录清理逻辑
            if os.path.exists(temp_dir):
                for retry in range(3):
                    try:
                        shutil.rmtree(temp_dir)
                        break
                    except Exception as e:
                        print(f"清理失败（尝试{retry + 1}/3）：{str(e)}")
                        time.sleep(2)
                else:
                    print(f"警告：无法清理临时目录 {temp_dir}")

            time.sleep(5)  # 场景间间隔


if __name__ == "__main__":
    cfg_path = os.path.join(emulation_path, "osm4.sumocfg")
    batch_run_simulation(cfg_path)