from abnormal_injection.standard import all_same_54, intersection_normal_54, intersection_wered_test4
from files_path.file_path import emulation_path
import traci

sumoBinary = "sumo-gui"
sumoCmd = [sumoBinary, "-c", emulation_path + "osm4.sumocfg"]

try:
    traci.close()  # 确保上一个 traci 连接已经正常关闭
except Exception:
    pass

traci.start(sumoCmd)  # 通过命令行执行 sumo-gui 来启动仿真

step = 0

while traci.simulation.getMinExpectedNumber() > 0:
    # if 600 <= step <= 1800:
    #     traci.trafficlight.setRedYellowGreenState('1935078122', all_same_test2['all_red'])
    # elif step > 1800:
    phase_index = step % 90
    phase_key = ''
    if 0 <= phase_index < 39:
        phase_key = 'station_1'
    elif 39 <= phase_index < 45:
        phase_key = 'station_2'
    elif 45 <= phase_index < 84:
        phase_key = 'station_3'
    elif 84 <= phase_index < 90:
        phase_key = 'station_4'

    if 800 <= step <= 2800:
        traci.trafficlight.setRedYellowGreenState('2402915337', intersection_wered_test4['station_1'])
    else:
        traci.trafficlight.setRedYellowGreenState('2402915337', intersection_wered_test4[phase_key])

    traci.simulationStep()
    step += 1

traci.close()

#5-4
#cluster_1928080330_5128988682