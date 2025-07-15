import traci
import pandas as pd

from files_path.file_path import emulation_path

sumoBinary = "sumo"
sumoCmd = [sumoBinary, "-c", emulation_path + "osm4.sumocfg"]

try:
    traci.close()  # Ensure that the last trace connection closes normally
except Exception:
    pass
traci.start(sumoCmd)  # Execute sumo-gui on the command line to start the simulation

# Get detectors list
detector_data = []
detector_ids = traci.inductionloop.getIDList()
for detector_id in detector_ids:
    if detector_id.startswith('e'):
        lane_id = traci.inductionloop.getLaneID(detector_id)
        detector_data.append({'lane_id': lane_id, 'det_id': detector_id})

# Convert detector data to DataFrame
out_df = pd.DataFrame(detector_data)

# Save DataFrame to CSV
out_df.to_csv('data_input/detectors.csv', index=False)

traci.close()
