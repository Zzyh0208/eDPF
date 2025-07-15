# -*- coding: utf-8 -*-

import os
import xml.etree.ElementTree as ET
import csv
import json
import pandas as pd
from collections import defaultdict

BASE_DIR = ".."

SUMO_OUTPUT_XML = os.path.join(BASE_DIR, "emulation", "e1output.xml")
OUTPUT_CSV = os.path.join(BASE_DIR, "data", "pc_input_data.csv")
DETECTORS_CSV = os.path.join(BASE_DIR, "data", "detectors.csv")
ANOMALY_RESULTS_JSON = os.path.join(BASE_DIR, "data", "anomaly_results.json")

def load_detector_ids_from_json():
    try:
        with open(ANOMALY_RESULTS_JSON, 'r', encoding='utf-8') as f:
            anomaly_results = json.load(f)
        base_ids = []
        if "top_k_detectors" not in anomaly_results:
            print("Warning: Key 'top_k_detectors' not found in JSON file.")
            return []
        for detector_info in anomaly_results.get("top_k_detectors", []):
            if not isinstance(detector_info, dict):
                print(f"Warning: Skipping invalid item in 'top_k_detectors': {detector_info}")
                continue
            detector_id_str = detector_info.get("detector_id")
            if detector_id_str and isinstance(detector_id_str, str):
                parts = detector_id_str.split('_')
                if len(parts) > 1 and parts[-1].isdigit():
                    base_id = "_".join(parts[:-1])
                    base_ids.append(base_id)
                else:
                    base_ids.append(detector_id_str)
            else:
                 print(f"Warning: Skipping detector with missing or invalid 'detector_id': {detector_info}")
        unique_base_ids = list(set(base_ids))
        if not unique_base_ids:
            print("Warning: No valid detector IDs were extracted from the JSON file.")
        return unique_base_ids
    except FileNotFoundError:
        print(f"Error: JSON file not found at '{ANOMALY_RESULTS_JSON}'. Please ensure the path is correct.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{ANOMALY_RESULTS_JSON}'. Check file format.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while loading detector IDs from JSON: {e}")
        return []

def load_detector_ids_from_csv():
    try:
        df = pd.read_csv(DETECTORS_CSV)
        if 'det_id' in df.columns:
            full_ids = df['det_id'].astype(str).tolist()
            full_ids = [fid for fid in full_ids if fid]
            if not full_ids:
                 print("Warning: No detector IDs found in the 'det_id' column of the CSV file.")
            return full_ids
        else:
            print(f"Error: Column 'det_id' not found in '{DETECTORS_CSV}'.")
            return []
    except FileNotFoundError:
        print(f"Error: CSV file not found at '{DETECTORS_CSV}'. Please ensure the path is correct.")
        return []
    except pd.errors.EmptyDataError:
        print(f"Error: CSV file '{DETECTORS_CSV}' is empty or cannot be read.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while loading detector IDs from CSV: {e}")
        return []

def get_target_detector_ids(mode):
    if mode == "1":
        return load_detector_ids_from_json()
    elif mode == "2":
        return load_detector_ids_from_csv()
    else:
        print("Invalid mode selected. Please choose '1' or '2'.")
        return []

def main():
    mode = input("Choose input mode (1: Use base IDs from JSON, 2: Use full IDs from CSV): ").strip()
    if mode not in ['1', '2']:
        print("Invalid input. Exiting.")
        return

    target_ids_input = get_target_detector_ids(mode)
    if not target_ids_input:
        print("No target detector IDs were loaded. Exiting.")
        return
    print(f"Selected target IDs ({len(target_ids_input)}): {target_ids_input[:5]}..." if len(target_ids_input) > 5 else target_ids_input)

    try:
        tree = ET.parse(SUMO_OUTPUT_XML)
        root = tree.getroot()
    except FileNotFoundError:
        print(f"Error: SUMO XML file not found at '{SUMO_OUTPUT_XML}'. Please ensure the path is correct.")
        return
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file '{SUMO_OUTPUT_XML}'. Malformed XML? Details: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred while opening or parsing the XML file: {e}")
        return

    intervals_data = defaultdict(dict)
    all_found_detector_ids = set()
    all_time_steps = set()

    for interval_element in root.findall('interval'):
        detector_id = interval_element.get('id')
        speed_str = interval_element.get('speed')
        begin_time_str = interval_element.get('begin')

        if not (detector_id and speed_str and begin_time_str):
            continue

        try:
            speed = float(speed_str)
            begin_time = float(begin_time_str)
            time_key = round(begin_time, 2)

            intervals_data[time_key][detector_id] = speed
            all_found_detector_ids.add(detector_id)
            all_time_steps.add(time_key)

        except ValueError:
            continue
        except TypeError:
             continue

    if not intervals_data:
        print("No valid interval data could be extracted from the SUMO output file.")
        return

    sorted_time_steps = sorted(list(all_time_steps))

    final_columns_ordered = []
    structured_rows_data = []

    if mode == "1":
        detector_groups = defaultdict(list)
        for found_id in sorted(list(all_found_detector_ids)):
            parts = found_id.split('_')
            base_id = found_id
            suffix = ''
            if len(parts) > 1 and parts[-1].isdigit():
                suffix = parts[-1]
                base_id = "_".join(parts[:-1])

            if base_id in target_ids_input:
                detector_groups[base_id].append({'full_id': found_id, 'suffix': suffix})

        sorted_base_ids = sorted(detector_groups.keys())
        for base_id in sorted_base_ids:
            detector_groups[base_id].sort(key=lambda x: int(x['suffix']) if x['suffix'].isdigit() else float('inf'))
            for det_info in detector_groups[base_id]:
                final_columns_ordered.append(det_info['full_id'])

        for time_step in sorted_time_steps:
            row_data = {}
            for base_id in sorted_base_ids:
                if base_id in detector_groups:
                    for det_info in detector_groups[base_id]:
                        full_id = det_info['full_id']
                        speed = intervals_data[time_step].get(full_id, -1.00)
                        row_data[full_id] = speed
            structured_rows_data.append(row_data)

    elif mode == "2":
        valid_target_full_ids = {tid for tid in target_ids_input if tid in all_found_detector_ids}
        final_columns_ordered = sorted(list(valid_target_full_ids))

        for time_step in sorted_time_steps:
            row_data = {}
            current_time_data = intervals_data.get(time_step, {})
            for col_id in final_columns_ordered:
                speed = current_time_data.get(col_id, -1.00)
                row_data[col_id] = speed
            structured_rows_data.append(row_data)
    else:
        print("Internal Error: Invalid mode encountered during data processing.")
        return

    if not final_columns_ordered:
        print("No matching detector data found for the specified targets. Cannot create CSV output.")
        return

    df_output = pd.DataFrame(structured_rows_data, columns=final_columns_ordered)
    df_output.fillna(-1.00, inplace=True)

    column_rename_map = {original_col: f'X{i+1}' for i, original_col in enumerate(final_columns_ordered)}
    df_output.rename(columns=column_rename_map, inplace=True)

    try:
        df_output.to_csv(OUTPUT_CSV, index=False, float_format='%.2f', encoding='utf-8')
        print(f"Successfully processed SUMO data and saved to '{OUTPUT_CSV}'")
        print(f"Output CSV contains {len(df_output)} rows (time steps) and {len(df_output.columns)} columns (detectors).")
    except Exception as e:
        print(f"Error: Failed to save data to CSV file '{OUTPUT_CSV}'. Details: {e}")

if __name__ == "__main__":
    main()