CrystalPilot
=======================

# User Guide

## Overview
CrystalPilot is a comprehensive tool designed to streamline hardware experiment management and facilitate data analysis. With its intuitive graphical user interface, users can easily configure experimental setups by selecting and customizing hardware modules according to their requirements. The application enables real-time monitoring of connected hardware, providing live status updates and detailed logs to ensure smooth operation throughout the experiment.

In addition to setup and monitoring, CrystalPilot simplifies the process of exporting experimental data. Users can export results in various formats, such as CSV and JSON, for further analysis or reporting. The tool is tightly integrated with the analysis.sns.gov platform, allowing seamless data transfer and collaboration with other analysis tools. CrystalPilot is ideal for researchers and engineers seeking an efficient, user-friendly solution for managing complex hardware experiments.

## Features


- **Experiment setup and configuration**  
    - *Select and customize hardware modules*: Choose from a list of supported hardware devices (e.g., sensors, controllers) and adjust their settings to fit your experiment’s needs.  
    - *Define experiment parameters*: Specify variables such as duration, sampling rates, and trigger conditions to tailor the experiment workflow.  
    - *Save and load experiment profiles*: Store your configuration as a profile for easy reuse or sharing, and quickly reload previous setups to save time.

- **Real-time hardware monitoring**  
    - *View live status of connected devices*: Instantly see which devices are online, their operational state, and any connection issues.  
    - *Access detailed logs and alerts*: Review a chronological log of system events, warnings, and errors to help diagnose problems or track experiment progress.  
    - *Monitor performance metrics*: Track key indicators like data throughput, device health, and resource usage in real time.

- **Seamless connection with external software**  
    - *Export results as CSV or npy files*: Save your experiment data in widely-used formats for compatibility with analysis tools like Excel, Python, or MATLAB.  
    - *Choose specific datasets for export*: Select only the relevant portions of your data to export, reducing file size and focusing on what matters.  
    - *Automate export after experiment completion*: Set up automatic data export so results are saved and ready for analysis as soon as the experiment finishes.

- **Integration with analysis.sns.gov**  
    - *Seamless data transfer to the platform*: Send your experiment results directly to analysis.sns.gov without manual uploads, ensuring data integrity and saving time.  
    - *Collaborate with team members*: Share data and experiment profiles with colleagues, enabling joint analysis and feedback.  
    - *Access advanced analysis tools*: Leverage the powerful analytics and visualization features available on analysis.sns.gov for deeper insights.

## Getting Started

1. **Launch the Application**  
    - Navigate to the installation directory: `/SNS/TOPAZ/shared/CrystalPilot`.
    - Run the application using the command: `run-crystalpilot.py`.
    - The graphical user interface (GUI) will open, ready for configuration.

2. **Configure Experiment**  
    - In the GUI, select the hardware modules you wish to use.
    - Adjust each module’s settings and define experiment parameters such as timing, triggers, and data collection preferences.
    - Optionally, save your configuration as a profile for future use.

3. **Monitor Hardware**  
    - Use the dashboard to observe the real-time status of all connected devices.
    - Check logs for system messages, errors, or alerts.
    - Monitor performance metrics to ensure the experiment is running smoothly.

4. **Execute external software and export data**  
    - After the experiment completes, use the "Export" button in the GUI.
    - Choose your preferred export format (CSV, JSON, or npy).
    - Select specific datasets if needed, and initiate the export for further analysis or reporting.

## Troubleshooting

- **Ensure all hardware is connected before launching**: Double-check physical connections and power supplies for all devices.
- **Check the logs panel for error messages**: Review logs in the GUI for any issues or warnings that may require attention.
- **For network issues, verify your connection to analysis.sns.gov**: Ensure your computer is connected to the correct network and that analysis.sns.gov is accessible.

For more details, refer to the code comments and the [DEVELOPMENT.md](DEVELOPMENT.md) file.