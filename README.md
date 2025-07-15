# eDPF: A High-fidelity Simulation Platform and Efficient Root Cause Location Framework for Urban Traffic Anomaly Analysis

This repository contains the source code for the paper titled "eDPF: A High-fidelity Simulation Platform and Efficient Root Cause Location Framework for Urban Traffic Anomaly Analysis".

This project aims to provide a **high-fidelity urban traffic simulation platform** capable of generating controllable and reproducible traffic anomaly scenarios and datasets. Concurrently, it introduces an innovative **eDPF (Efficient Detector Pre-Filtering) framework** to improve the efficiency and accuracy of traffic anomaly root cause localization.

## Project Overview

*   **High-Fidelity Simulation**: Based on SUMO (Simulation of Urban Mobility), we've created an automated simulation framework to generate detailed datasets encompassing various traffic anomalies (e.g., signal failures).
*   **eDPF Pre-Filtering**: We propose a novel eDPF framework that leverages phase-aware robust statistics to efficiently identify a subset of sensors highly relevant to anomalies.
*   **Root Cause Localization Support**: Data processing scripts are provided to transform simulation data into formats suitable for various downstream root cause localization algorithms such as Granger Causality, PC Algorithm, DyCause, and TCDF. Git links for these algorithms are also included.

## Core Features

*   **Automated Simulation Data Generation**: Utilizes SUMO to automatically construct urban traffic network models, deploy sensors, simulate normal traffic flow, and precisely inject various types of traffic anomalies (e.g., traffic signal failures).
*   **eDPF Anomaly Detection**: Employs phase-aware robust statistical methods (like median and MAD) to compute an "anomalousness index" for each sensor, then filters to select the Top-K sensors with the highest scores for subsequent analysis.
*   **Multi-Algorithm Data Preparation**: Provides data conversion scripts to process SUMO's XML output into input formats suitable for Granger Causality (`statsmodels`), PC Algorithm (`pcalg-py`), DyCause, and TCDF.

## Installation

### Prerequisites

*   **Python**: Python 3.7 or higher is recommended.
*   **SUMO**: SUMO (Simulation of Urban Mobility) must be pre-installed, and its executables (`sumo`, `sumo-gui`) should be accessible in your system's PATH. Please refer to the SUMO documentation for installation instructions:
    [Downloads - SUMO Documentation](https://sumo.dlr.de/docs/Downloads.php)
*   **SUMO_HOME Environment Variable**: The project uses the `SUMO_HOME` system variable to invoke SUMO. Ensure `SUMO_HOME` is correctly set to your SUMO installation directory. Refer to:
    [Basics/Basic Computer Skills - SUMO Documentation](https://sumo.dlr.de/docs/Basics/Basic_Computer_Skills.html#sumo_home)

### Dependencies

This project relies on several Python libraries. First, ensure SUMO is installed and the `traci` library is configured. Then, install other dependencies using pip:

```bash
pip install -r requirements.txt
```

## Usage

The core functionalities of the project are executed via Python scripts. The main workflow is as follows:

### 1. Simulation Data Generation

*   **Prepare SUMO Configuration**: Place your SUMO configuration files (`.sumocfg`), network files (`.net.xml`), detector files (`.add.xml`), etc., in the `emulation/` directory. For example, the main configuration file is `emulation/osm4.sumocfg`.
*   **Run Anomaly Injection Simulation**:
    ```bash
    python abnormal_injection/get_sumodata.py
    ```
    This script runs SUMO to simulate scenarios with traffic signal failures and other anomalies, saving the output XML data in the `emulation/final_output/` directory.
*   **Prepare Normal Data**: Place normal traffic flow simulation XML files (named starting with `normal_`) into the `screen/data_normal/` directory for training the eDPF model.

### 2. eDPF Anomaly Detection

*   **Train eDPF Model**: If you do not have a trained model (`screen/enhanced_model.json`), train it first on your normal data:
    ```bash
    python screen/screen.py
    ```
    This command will generate the model file `screen/enhanced_model.json`.
*   **Perform Anomaly Detection**: Run the detection script to process the simulation data generated for anomaly scenarios and output the detection results:
    ```bash
    python screen/screen.py 
    ```
    The detection results, including a ranked list of anomalous detectors, will be saved as `data/anomaly_results.json`.

### 3. Data Preprocessing (for Downstream Algorithms)

After generating simulation data and performing eDPF detection, prepare the data for specific root-cause localization algorithms:

*   **For DyCause**:
    ```bash
    python data_processing/data_to_dycause.py
    ```
    Follow the prompts in the script.
*   **For TCDF**:
    ```bash
    python data_processing/data_to_tcdf.py
    ```
    Follow the prompts to select the input mode.
*   **For Granger Causality (GC)**:
    ```bash
    python data_processing/data_to_gc.py
    ```
    This command generates `data/gc_input_data.csv`, formatted for `statsmodels`.
*   **For PC Algorithm**:
    ```bash
    python data_processing/data_to_pc.py
    ```
    This command generates `data/pc_input_data.csv`, formatted for `pcalg-py`.

### 4. Root Cause Localization Analysis

Use the data prepared by the above scripts to run your chosen root-cause localization algorithms.

*   **Granger Causality (GC)**:
    *   **Library**: `statsmodels`
    *   **Docs**: [statsmodels TSA Granger Causality Tests](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.grangercausalitytests.html)
*   **PC Algorithm**:
    *   **Library**: `pcalg-py`
    *   **Git Repo**: [https://github.com/Renovamen/pcalg-py](https://github.com/Renovamen/pcalg-py)
*   **DyCause**:
    *   **Git Repo**: https://github.com/PanYicheng/dycause_rca.git
*   **TCDF**:
    *   **Git Repo**: https://github.com/M-Nauta/TCDF.git

## Datasets

The project provides the following data and model files:

*   **Simulation Data**:
    *   **Normal Traffic Data**: Located in the `screen/data_normal/` directory, used for training the eDPF model.
    *   **Anomaly Scenario XML Outputs**: Generated by running SUMO via `abnormal_injection/get_sumodata.py` and saved in `emulation/final_output/`. These contain raw simulation data for various anomaly scenarios.
    *   **Pre-processed Data**: Data files for downstream algorithms (e.g., `data/gc_input_data.csv`, `data/pc_input_data.csv`) will be generated in the `data/` directory after processing with scripts in `data_processing/`.
    *   **Example Data for DyCause**: The `data_examples` directory contains data already converted to a format suitable for DyCause, facilitating quick reproduction of paper results.
*   **eDPF Model**: Trained model parameters are saved as `screen/enhanced_model.json`.
*   **Intersection Configuration**: `data/junction_data.json` contains the original phase information and names for each intersection.

You can generate custom simulation datasets by running `abnormal_injection/get_sumodata.py`.

## Acknowledgments

This work is partially supported by the National Natural Science Foundation of China (62072006, 92167104), Qiyuan Lab Innovation Fund (S20210201079), and National Key Laboratory of Intelligent Parallel Technology (2024JK15).
