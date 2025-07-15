import os
import xml.etree.ElementTree as ET
import csv
import json
import pandas as pd

from files_path.file_path import emulation_path, data_path, data_pro_path

# Paths
input_data_path = os.path.join(data_pro_path, "abnormal_0.xml")
output_data_path = os.path.join(data_pro_path, "output.csv")
detectors_path = os.path.join(data_pro_path, "detectors.csv")
anomaly_results_path = os.path.join(data_path, "anomaly_results.json")


def load_top_k_detectors():
    """
    Load the top-k detector IDs from the anomaly_results.json file.
    :return: List of detector IDs
    """
    with open(anomaly_results_path, 'r') as f:
        anomaly_results = json.load(f)
    return [detector["detector_id"] for detector in anomaly_results["top_k_detectors"]]


def load_detectors_from_csv():
    """
    Load detector IDs from the detectors.csv file.
    :return: List of detector IDs
    """
    df = pd.read_csv(detectors_path)
    return df["det_id"].tolist()


def get_target_ids(mode):
    """
    Get the target detector IDs based on the selected mode.
    :param mode: Input mode (1 for top-k detectors, 2 for detectors.csv)
    :return: List of target detector IDs
    """
    if mode == "1":
        try:
            return load_top_k_detectors()
        except FileNotFoundError:
            print("Error: anomaly_results.json not found. Please ensure the file exists in the data directory.")
            return []
    elif mode == "2":
        try:
            return load_detectors_from_csv()
        except FileNotFoundError:
            print("Error: detectors.csv not found. Please ensure the file exists in the data_input directory.")
            return []
    else:
        print("Invalid mode selected. Please choose 1 or 2.")
        return []


def main():
    # Choose the input mode
    mode = input("Choose input mode (1 for top-k detectors, 2 for detectors.csv): ").strip()
    # Get the target detector IDs
    target_ids = get_target_ids(mode)
    if not target_ids:
        return

    # Parse the XML file
    tree = ET.parse(input_data_path)
    root = tree.getroot()

    # Load the detectors CSV file
    df = pd.read_csv(detectors_path)
    lane_ids = df['lane_id'].tolist()
    det_ids = df['det_id'].tolist()

    # Build a hash table for lane_id to det_id mapping
    lane_id_dict = {lane_id: det_id for lane_id, det_id in zip(lane_ids, det_ids)}

    # Initialize a dictionary to store matches
    matches = {}

    # Map target_ids to det_ids
    print(target_ids)
    for target_id in target_ids:
        print(target_id)
        print("1")
        if target_id in lane_id_dict:
            matches[target_id] = lane_id_dict[target_id]
        else:
            suffix_count = 0
            while True:
                modified_target_id = f"{target_id}_{suffix_count}"
                if modified_target_id in lane_id_dict:
                    matches[target_id] = lane_id_dict[modified_target_id]
                    break
                suffix_count += 1

    # Initialize a list to store the new target IDs
    new_target_ids = []

    print("1")
    # Replace target_ids with their corresponding det_ids
    for target_id in target_ids:
        if target_id in matches:
            new_target_ids.append(matches[target_id])
        else:
            new_target_ids.append(target_id)  # Keep the original ID if no match is found

    # Use the new target IDs
    target_ids = new_target_ids

    # Store speed data in a dictionary
    speed_data = {id_value: {} for id_value in target_ids}

    # Traverse the XML tree
    for interval in root.findall('interval'):
        id_value = interval.get('id')
        speed_value = interval.get('speed')
        begin_value = float(interval.get('begin'))

        # Check if the ID is in the target_ids and within the time range
        if 0 <= begin_value <= 3600:
            for target_id in target_ids:
                if target_id == id_value:
                    suffix = id_value.split('_')[-1]
                    speed_data[target_id].setdefault(suffix, []).append(speed_value)

    # Write the data to a CSV file
    with open(output_data_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Write the header row
        header = []
        for target_id in target_ids:
            header.extend([f'e1det_{target_id}_{suffix}' for suffix in sorted(speed_data[target_id].keys())])
        writer.writerow(header)

        # Write the speed data
        num_intervals = max(
            len(speed_data[target_id][suffix]) for target_id in target_ids for suffix in speed_data[target_id])
        print(num_intervals)
        for i in range(num_intervals):
            print(i)
            row = []
            for target_id in target_ids:
                for suffix in sorted(speed_data[target_id].keys()):
                    if i < len(speed_data[target_id][suffix]):
                        row.append(speed_data[target_id][suffix][i])
                    else:
                        row.append('-1.00')  # Fill missing data with '-1.00'
            writer.writerow(row)

    # Modify the column names in the CSV file
    data = pd.read_csv(output_data_path, header=0)
    edit = 1
    new_columns = [f'edit_{edit}-{i}' for i in range(len(data.columns))]
    data.columns = new_columns

    # Save the modified CSV file
    data.to_csv(output_data_path, index=False)
    print(f"Data has been saved to {output_data_path}")


if __name__ == "__main__":
    main()
