import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Any
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                           QProgressBar, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Import the SolinstReader from its location
sys.path.append(str(Path(__file__).parent.parent / "src" / "gui" / "handlers"))
from solinst_reader import SolinstReader

# Set up logging
logger = logging.getLogger(__name__)

class PlotGenerator:
    """Generates pressure plots from organized XLE files"""
    
    def __init__(self):
        """Initialize plot generator"""
        self.reader = SolinstReader()
        self.colors = plt.cm.tab10.colors  # Color cycle for plots
        
    def generate_plots(self, input_dir: str) -> Dict[str, Any]:
        """
        Generate plots for all serial number folders
        
        Args:
            input_dir: Path to organized files directory
            
        Returns:
            Statistics about plots generated
        """
        input_path = Path(input_dir)
        
        # Create plots directory structure
        plots_dir = input_path / "plots"
        plots_dir.mkdir(exist_ok=True)
        
        baro_plots_dir = plots_dir / "Barologgers"
        level_plots_dir = plots_dir / "Leveloggers"
        
        baro_plots_dir.mkdir(exist_ok=True)
        level_plots_dir.mkdir(exist_ok=True)
        
        # Track statistics
        stats = {
            'barologger_plots': 0,
            'levelogger_plots': 0,
            'files_processed': 0,
            'errors': 0,
            'report': {
                'barologgers': {},
                'leveloggers': {}
            }
        }
        
        # Process Barologgers
        baro_dir = input_path / "Barologgers"
        if baro_dir.exists():
            for serial_dir in baro_dir.iterdir():
                if serial_dir.is_dir():
                    serial_number = serial_dir.name
                    try:
                        result = self._generate_serial_plot(serial_dir, baro_plots_dir / f"{serial_dir.name}.png", "Barologger")
                        stats['barologger_plots'] += 1
                        stats['files_processed'] += result['files_processed']
                        stats['errors'] += len(result['failed_files'])
                        stats['report']['barologgers'][serial_number] = result
                        logger.info(f"Generated plot for Barologger {serial_dir.name}")
                    except Exception as e:
                        stats['errors'] += 1
                        stats['report']['barologgers'][serial_number] = {
                            'success': False,
                            'error': str(e),
                            'files_processed': 0,
                            'files_plotted': 0,
                            'failed_files': []
                        }
                        logger.error(f"Error generating plot for {serial_dir}: {e}")
        
        # Process Leveloggers
        level_dir = input_path / "Leveloggers"
        if level_dir.exists():
            for serial_dir in level_dir.iterdir():
                if serial_dir.is_dir():
                    serial_number = serial_dir.name
                    try:
                        result = self._generate_serial_plot(serial_dir, level_plots_dir / f"{serial_dir.name}.png", "Levelogger")
                        stats['levelogger_plots'] += 1
                        stats['files_processed'] += result['files_processed']
                        stats['errors'] += len(result['failed_files'])
                        stats['report']['leveloggers'][serial_number] = result
                        logger.info(f"Generated plot for Levelogger {serial_dir.name}")
                    except Exception as e:
                        stats['errors'] += 1
                        stats['report']['leveloggers'][serial_number] = {
                            'success': False,
                            'error': str(e),
                            'files_processed': 0,
                            'files_plotted': 0,
                            'failed_files': []
                        }
                        logger.error(f"Error generating plot for {serial_dir}: {e}")
        
        # Generate report file
        self._generate_report_file(stats, plots_dir / "plot_report.txt")
        
        return stats
    
    def _generate_report_file(self, stats: Dict[str, Any], output_path: Path):
        """Generate a detailed report file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("SOLINST XLE PLOTTING REPORT\n")
            f.write("==========================\n\n")
            
            f.write(f"Total plots generated: {stats['barologger_plots'] + stats['levelogger_plots']}\n")
            f.write(f"Barologger plots: {stats['barologger_plots']}\n")
            f.write(f"Levelogger plots: {stats['levelogger_plots']}\n")
            f.write(f"Total files processed: {stats['files_processed']}\n")
            f.write(f"Files with errors: {stats['errors']}\n\n")
            
            # Barologger details
            f.write("BAROLOGGER DETAILS\n")
            f.write("-----------------\n")
            for serial, result in stats['report']['barologgers'].items():
                f.write(f"\nSerial Number: {serial}\n")
                if result.get('success', False):
                    f.write(f"  Status: Success\n")
                    f.write(f"  Files processed: {result['files_processed']}\n")
                    f.write(f"  Files successfully plotted: {result['files_plotted']}\n")
                    f.write(f"  Files failed: {len(result['failed_files'])}\n")
                    if result['failed_files']:
                        f.write("  Failed files:\n")
                        for failed in result['failed_files']:
                            f.write(f"    - {failed['file']}: {failed['error']}\n")
                else:
                    f.write(f"  Status: Failed\n")
                    f.write(f"  Error: {result.get('error', 'Unknown error')}\n")
            
            # Levelogger details
            f.write("\nLEVELOGGER DETAILS\n")
            f.write("------------------\n")
            for serial, result in stats['report']['leveloggers'].items():
                f.write(f"\nSerial Number: {serial}\n")
                if result.get('success', False):
                    f.write(f"  Status: Success\n")
                    f.write(f"  Files processed: {result['files_processed']}\n")
                    f.write(f"  Files successfully plotted: {result['files_plotted']}\n")
                    f.write(f"  Files failed: {len(result['failed_files'])}\n")
                    if result['failed_files']:
                        f.write("  Failed files:\n")
                        for failed in result['failed_files']:
                            f.write(f"    - {failed['file']}: {failed['error']}\n")
                else:
                    f.write(f"  Status: Failed\n")
                    f.write(f"  Error: {result.get('error', 'Unknown error')}\n")
    
    def _generate_serial_plot(self, serial_dir: Path, output_path: Path, logger_type: str) -> Dict[str, Any]:
        """
        Generate plot for a single serial number directory
        
        Args:
            serial_dir: Directory containing XLE files for a serial number
            output_path: Where to save the plot
            logger_type: "Barologger" or "Levellogger"
            
        Returns:
            Dictionary with plot generation results
        """
        # Find all XLE files in the directory
        xle_files = list(serial_dir.glob("*.xle"))
        
        if not xle_files:
            logger.warning(f"No XLE files found in {serial_dir}")
            return {
                'success': False,
                'error': "No XLE files found",
                'files_processed': 0,
                'files_plotted': 0,
                'failed_files': []
            }
            
        # DEBUG: Print information about the logger type determination
        logger.info(f"Processing directory: {serial_dir}")
        logger.info(f"Initial logger_type passed to function: {logger_type}")
        
        # Try to verify the logger type by checking the first file
        try:
            first_file = xle_files[0]
            first_metadata, _ = self.reader.get_file_metadata(first_file)
            
            # DEBUG: Print metadata details
            logger.info(f"First file metadata:")
            logger.info(f"  - Instrument Type: '{first_metadata.instrument_type}'")
            logger.info(f"  - Model Number: '{first_metadata.model_number}'")
            
            # Strip whitespace from model for debugging display
            model_stripped = first_metadata.model_number.strip() if first_metadata.model_number else ""
            logger.info(f"  - Model Number (stripped): '{model_stripped}'")
            
            # Check if the reader thinks it's a barologger
            is_baro = self.reader.is_barologger(first_metadata)
            logger.info(f"  - Reader classification - is_barologger(): {is_baro}")
            
            # Check if model is in BAROLOGGER_TYPES for debugging
            model_in_baro_types = False
            if first_metadata.instrument_type in self.reader.BAROLOGGER_TYPES:
                valid_models = self.reader.BAROLOGGER_TYPES[first_metadata.instrument_type]
                model_in_baro_types = any(model_stripped.startswith(valid_model) for valid_model in valid_models)
                logger.info(f"  - Model starts with a known barologger model: {model_in_baro_types}")
                logger.info(f"  - Valid baro models for this instrument: {valid_models}")
            else:
                logger.info(f"  - Instrument type not in known BAROLOGGER_TYPES")
            
            # Confirm logger_type based on file analysis
            corrected_logger_type = "Barologger" if is_baro else "Levellogger"
            
            if corrected_logger_type != logger_type:
                logger.warning(f"Logger type mismatch! Directory suggests {logger_type} but file indicates {corrected_logger_type}")
                # Use the corrected type for the plot
                logger_type = corrected_logger_type
        except Exception as e:
            logger.error(f"Error checking logger type: {e}")
            # Continue with the original logger_type if there was an error
        
        # Figure and axes
        fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
        
        # Generate a title
        serial_number = serial_dir.name
        title = f"{logger_type} {serial_number} - Pressure Data"
        ax.set_title(title, fontsize=14)
        
        # Configure axes
        ax.set_xlabel("Date", fontsize=12)
        
        # Determine y-axis label based on logger type
        if logger_type == "Barologger":
            ax.set_ylabel("Barometric Pressure (kPa)", fontsize=12)
        else:
            ax.set_ylabel("Water Level (m)", fontsize=12)
            
        # Track min/max dates for x-axis limits
        all_dates = []
        
        # Track file processing results
        result = {
            'success': True,
            'files_processed': len(xle_files),
            'files_plotted': 0,
            'failed_files': []
        }
        
        # Process each file, add to plot with different colors
        for i, xle_file in enumerate(xle_files):
            try:
                # Load data
                df, metadata = self.reader.read_xle(xle_file)
                
                # Skip empty dataframes
                if df.empty:
                    result['failed_files'].append({
                        'file': xle_file.name,
                        'error': "No valid data points"
                    })
                    continue
                
                # Use a cycling color from the color map
                color = self.colors[i % len(self.colors)]
                
                # Format the label to include date range
                start_date = df['timestamp'].min().strftime('%Y-%m-%d')
                end_date = df['timestamp'].max().strftime('%Y-%m-%d')
                label = f"{xle_file.name} ({start_date} to {end_date})"
                
                # Plot the data
                ax.plot(df['timestamp'], df['pressure'], label=label, color=color, alpha=0.8, linewidth=1.5)
                
                # Collect dates for x-axis limits
                all_dates.extend(df['timestamp'].tolist())
                
                # Count successful plot
                result['files_plotted'] += 1
                
                logger.info(f"Added {xle_file.name} to plot")
                
            except Exception as e:
                result['failed_files'].append({
                    'file': xle_file.name,
                    'error': str(e)
                })
                logger.error(f"Error plotting file {xle_file}: {e}")
        
        # Format the x-axis
        if all_dates:
            ax.set_xlim(min(all_dates), max(all_dates))
            
        # Format the date axis nicely
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()  # Rotate date labels
        
        # Add legend
        ax.legend(loc='best', fontsize=10)
        
        # Add grid for readability
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Save the figure
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close(fig)  # Close to prevent memory leaks
        
        return result


class PlotGeneratorWorker(QThread):
    """Worker thread for generating plots without freezing UI"""
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal(dict)  # Stats dictionary
    error = pyqtSignal(str)
    
    def __init__(self, input_dir):
        super().__init__()
        self.input_dir = input_dir
        self.generator = PlotGenerator()
        
    def run(self):
        try:
            self.status_update.emit("Scanning directory structure...")
            
            # Count total number of serial dirs for progress tracking
            input_path = Path(self.input_dir)
            baro_dir = input_path / "Barologgers"
            level_dir = input_path / "Levelloggers"
            
            serial_dirs = []
            
            if baro_dir.exists():
                serial_dirs.extend([d for d in baro_dir.iterdir() if d.is_dir()])
                
            if level_dir.exists():
                serial_dirs.extend([d for d in level_dir.iterdir() if d.is_dir()])
            
            total_dirs = len(serial_dirs)
            
            if total_dirs == 0:
                self.error.emit("No Barologger or Levelogger folders found in the input directory")
                return
                
            self.status_update.emit(f"Found {total_dirs} serial number folders to process")
            
            # Create stats tracker with report
            stats = {
                'barologger_plots': 0,
                'levelogger_plots': 0,
                'files_processed': 0,
                'errors': 0,
                'report': {
                    'barologgers': {},
                    'leveloggers': {}
                }
            }
            
            # Create output directory structure
            plots_dir = input_path / "plots"
            plots_dir.mkdir(exist_ok=True)
            
            baro_plots_dir = plots_dir / "Barologgers"
            level_plots_dir = plots_dir / "Levelloggers"
            
            baro_plots_dir.mkdir(exist_ok=True)
            level_plots_dir.mkdir(exist_ok=True)
            
            # Process each serial number directory
            processed = 0
            
            # Process Barologgers
            if baro_dir.exists():
                for serial_dir in baro_dir.iterdir():
                    if serial_dir.is_dir():
                        serial_number = serial_dir.name
                        self.status_update.emit(f"Processing Barologger {serial_dir.name}...")
                        
                        try:
                            result = self.generator._generate_serial_plot(
                                serial_dir, 
                                baro_plots_dir / f"{serial_dir.name}.png", 
                                "Barologger"
                            )
                            stats['barologger_plots'] += 1
                            stats['files_processed'] += result['files_processed']
                            stats['errors'] += len(result['failed_files'])
                            stats['report']['barologgers'][serial_number] = result
                            logger.info(f"Generated plot for Barologger {serial_dir.name}")
                        except Exception as e:
                            stats['errors'] += 1
                            stats['report']['barologgers'][serial_number] = {
                                'success': False,
                                'error': str(e),
                                'files_processed': 0,
                                'files_plotted': 0,
                                'failed_files': []
                            }
                            logger.error(f"Error generating plot for {serial_dir}: {e}")
                            
                        # Update progress
                        processed += 1
                        progress_percent = int((processed / total_dirs) * 100)
                        self.progress.emit(progress_percent)
            
            # Process Levelloggers
            if level_dir.exists():
                for serial_dir in level_dir.iterdir():
                    if serial_dir.is_dir():
                        serial_number = serial_dir.name
                        self.status_update.emit(f"Processing Levellogger {serial_dir.name}...")
                        
                        try:
                            result = self.generator._generate_serial_plot(
                                serial_dir, 
                                level_plots_dir / f"{serial_dir.name}.png", 
                                "Levellogger"
                            )
                            stats['levelogger_plots'] += 1
                            stats['files_processed'] += result['files_processed']
                            stats['errors'] += len(result['failed_files'])
                            stats['report']['leveloggers'][serial_number] = result
                            logger.info(f"Generated plot for Levellogger {serial_dir.name}")
                        except Exception as e:
                            stats['errors'] += 1
                            stats['report']['leveloggers'][serial_number] = {
                                'success': False,
                                'error': str(e),
                                'files_processed': 0,
                                'files_plotted': 0,
                                'failed_files': []
                            }
                            logger.error(f"Error generating plot for {serial_dir}: {e}")
                            
                        # Update progress
                        processed += 1
                        progress_percent = int((processed / total_dirs) * 100)
                        self.progress.emit(progress_percent)
            
            # Generate report file
            self.generator._generate_report_file(stats, plots_dir / "plot_report.txt")
                
            # Return the final stats
            self.finished.emit(stats)
            
        except Exception as e:
            import traceback
            logger.error(f"Plot generation error: {e}\n{traceback.format_exc()}")
            self.error.emit(f"Error generating plots: {str(e)}")


class PlotGeneratorApp(QMainWindow):
    """GUI Application for generating plots from organized XLE files"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Solinst Plot Generator")
        self.setMinimumSize(550, 250)
        
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Input folder selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setWordWrap(True)
        select_folder_btn = QPushButton("Select Folder")
        select_folder_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(QLabel("Input:"))
        folder_layout.addWidget(self.folder_label, 1)  # 1 = stretch factor
        folder_layout.addWidget(select_folder_btn)
        main_layout.addLayout(folder_layout)
        
        # Progress information
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Generate button
        generate_btn = QPushButton("Generate Plots")
        generate_btn.clicked.connect(self.start_plot_generation)
        main_layout.addWidget(generate_btn)
        
        # Result area
        self.result_label = QLabel("Select a folder containing organized XLE files to begin")
        self.result_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.result_label)
        
        # Store the selected folder path
        self.folder_path = None
        
        # Worker thread for plot generation
        self.worker = None
        
    def select_folder(self):
        """Open dialog to select input folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with Organized XLE Files")
        if folder:
            # Check if it has the expected structure
            has_barologger = (Path(folder) / "Barologgers").exists()
            has_levellogger = (Path(folder) / "Levelloggers").exists()
            
            if not (has_barologger or has_levellogger):
                QMessageBox.warning(
                    self,
                    "Invalid Folder Structure",
                    "The selected folder does not have the expected structure.\n\n"
                    "It should contain 'Barologgers' and/or 'Levelloggers' subfolders."
                )
                return
                
            self.folder_path = folder
            self.folder_label.setText(folder)
            self.result_label.setText(f"Ready to generate plots for files in {os.path.basename(folder)}")
            self.progress_bar.setValue(0)
            
    def start_plot_generation(self):
        """Start the plot generation process"""
        if not self.folder_path:
            QMessageBox.warning(self, "No Folder Selected", 
                               "Please select a folder containing organized XLE files first.")
            return
            
        # Reset progress
        self.progress_bar.setValue(0)
        self.result_label.setText("Generating plots...")
        
        # Create and start worker thread
        self.worker = PlotGeneratorWorker(self.folder_path)
        
        # Connect signals
        self.worker.progress.connect(self.update_progress)
        self.worker.status_update.connect(self.update_status)
        self.worker.finished.connect(self.generation_finished)
        self.worker.error.connect(self.show_error)
        
        # Start generation
        self.worker.start()
        
    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)
        
    def update_status(self, status_text):
        """Update the status label"""
        self.status_label.setText(status_text)
        
    def generation_finished(self, stats):
        """Handle completion of plot generation"""
        baro_count = stats['barologger_plots']
        level_count = stats['levelogger_plots']
        error_count = stats['errors']
        
        self.result_label.setText(f"Plot generation complete. Generated {baro_count + level_count} plots.")
        self.progress_bar.setValue(100)
        
        # Show a message box with the results
        message = f"Successfully generated {baro_count + level_count} plots:\n\n" + \
                  f"- {baro_count} Barologger plots\n" + \
                  f"- {level_count} Levellogger plots\n\n"
                  
        if error_count > 0:
            message += f"There were {error_count} errors during processing.\n\n"
            
        message += f"Plots have been saved to:\n{os.path.join(self.folder_path, 'plots')}\n\n"
        message += f"Detailed report available at:\n{os.path.join(self.folder_path, 'plots', 'plot_report.txt')}"
        
        QMessageBox.information(self, "Plot Generation Complete", message)
        
    def show_error(self, error_message):
        """Display error message"""
        QMessageBox.critical(self, "Plot Generation Error", error_message)
        self.result_label.setText("Plot generation failed. See error message.")


def process_command_line():
    """Process command line arguments if script is run directly"""
    parser = argparse.ArgumentParser(description='Generate plots from organized XLE files.')
    parser.add_argument('input_dir', help='Directory containing organized XLE files')
    
    if len(sys.argv) > 1:
        args = parser.parse_args()
        
        generator = PlotGenerator()
        
        try:
            print(f"Generating plots from {args.input_dir}...")
            stats = generator.generate_plots(args.input_dir)
            
            print(f"Successfully generated {stats['barologger_plots'] + stats['levellogger_plots']} plots:")
            print(f"- {stats['barologger_plots']} Barologger plots")
            print(f"- {stats['levelogger_plots']} Levellogger plots")
            
            if stats['errors'] > 0:
                print(f"There were {stats['errors']} errors during processing.")
                
            print(f"Plots saved to: {os.path.join(args.input_dir, 'plots')}")
            
        except Exception as e:
            print(f"Error: {e}")
            return False
            
        return True
        
    return False


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Set up matplotlib backend for headless environments if needed
    if not os.environ.get('DISPLAY') and not sys.platform.startswith('win') and not sys.platform == 'darwin':
        import matplotlib
        matplotlib.use('Agg')
    
    # Check if we should run command line mode
    if not process_command_line():
        # No command line arguments, start GUI
        app = QApplication(sys.argv)
        window = PlotGeneratorApp()
        window.show()
        sys.exit(app.exec_())
