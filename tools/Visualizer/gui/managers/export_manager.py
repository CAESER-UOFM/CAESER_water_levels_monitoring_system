import os
import pandas as pd
from datetime import datetime
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QButtonGroup, 
    QRadioButton, QFileDialog, QMessageBox
)

logger = logging.getLogger(__name__)

class ExportManager:
    """Manages data and plot export operations."""
    
    def __init__(self, data_manager, plot_handler):
        self.data_manager = data_manager
        self.plot_handler = plot_handler
        self.db_path = data_manager.db_path  # Store db_path for use in plot_handler calls
    
    def export_to_csv(self, selected_wells, date_range, show_manual, apply_downsample=False, downsample_method=None, agg_method=None):
        """Export selected wells data to CSV.
        
        Args:
            selected_wells (list): List of well numbers to export
            date_range (dict): Dictionary with 'start' and 'end' dates
            show_manual (bool): Whether to include manual readings
            apply_downsample (bool): Whether to apply downsampling
            downsample_method (str): Downsampling method (e.g., '1 Hour', '1 Day')
            agg_method (str): Aggregation method (mean, median, min, max)
        """
        if not selected_wells:
            QMessageBox.warning(None, "No Wells Selected", "Please select at least one well to export.")
            return
        
        # Ask for output directory
        output_dir = QFileDialog.getExistingDirectory(None, "Select Output Directory")
        if not output_dir:
            return
        
        try:
            # Progress counter
            total_exports = len(selected_wells)
            success_count = 0
            exported_files = []
            
            for well_number in selected_wells:
                # Get well info to get CAE number from plot_handler instead of data_manager
                well_info = self.plot_handler.get_well_info(well_number, self.db_path)
                cae_number = well_info.get('cae_number', '') if well_info else ''
                
                # Create filename with well number and CAE number
                filename = f"{well_number}"
                if cae_number:
                    filename += f" ({cae_number})"
                
                # Get data for the selected well
                df = self.data_manager.get_well_data(well_number)
                
                # Apply date filtering
                if not df.empty and date_range['start'] and date_range['end']:
                    df = self.data_manager.filter_data_by_date_range(df, date_range['start'], date_range['end'])
                
                if df.empty:
                    logger.warning(f"No data to export for well {well_number}")
                    continue
                
                # Apply downsampling if requested
                if apply_downsample and downsample_method and not df.empty:
                    # Use the plot handler to apply the same downsampling as displayed in the plot
                    try:
                        # Add suffix to filename to indicate downsampling
                        filename += f"_{downsample_method.replace(' ', '')}"
                        if agg_method:
                            filename += f"_{agg_method}"
                            
                        # Set the aggregation method in the plot handler temporarily
                        original_agg_method = getattr(self.plot_handler, '_forced_agg_method', None)
                        self.plot_handler._forced_agg_method = agg_method
                        
                        # Apply downsampling
                        df = self.plot_handler.downsample_data(df, method=downsample_method)
                        
                        # Restore original setting
                        if original_agg_method is not None:
                            self.plot_handler._forced_agg_method = original_agg_method
                        else:
                            delattr(self.plot_handler, '_forced_agg_method')
                            
                    except Exception as e:
                        logger.error(f"Error applying downsampling for export: {e}")
                        # Continue with original data
                
                # Export to CSV
                file_path = os.path.join(output_dir, f"{filename}.csv")
                
                # Export to CSV
                df.to_csv(file_path, index=False)
                exported_files.append(os.path.basename(file_path))
                success_count += 1
                
                # Get manual readings too if showing them
                if show_manual:
                    manual_readings = self.data_manager.get_manual_readings(well_number)
                    
                    # Apply date filtering to manual readings
                    if not manual_readings.empty and date_range['start'] and date_range['end']:
                        manual_readings = self.data_manager.filter_data_by_date_range(
                            manual_readings, date_range['start'], date_range['end']
                        )
                    
                    # Export manual readings if available
                    if not manual_readings.empty:
                        manual_file_path = os.path.join(output_dir, f"{filename}_manual.csv")
                        manual_readings.to_csv(manual_file_path, index=False)
                        exported_files.append(os.path.basename(manual_file_path))
            
            # Show success message with list of exported files
            if success_count > 0:
                files_text = "\n".join(exported_files[:5])
                if len(exported_files) > 5:
                    files_text += f"\n... and {len(exported_files) - 5} more files"
                
                QMessageBox.information(None, "Export Successful", 
                                      f"Successfully exported data for {success_count} out of {total_exports} wells to {output_dir}.\n\n"
                                      f"Exported files:\n{files_text}")
            else:
                QMessageBox.warning(None, "Export Warning", 
                                  f"No data found to export for the selected wells in the specified date range.")
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            QMessageBox.critical(None, "Export Error", f"Failed to export data: {str(e)}")
    
    def export_plot_image(self, figure, selected_wells):
        """Export the current plot as an image."""
        if not selected_wells:
            QMessageBox.warning(None, "No Wells Selected", "Please select at least one well to export the plot.")
            return
        
        # If only one well is selected, use its name and CAE number for the filename
        default_filename = ""
        if len(selected_wells) == 1:
            well_number = selected_wells[0]
            # Use plot_handler's get_well_info instead of data_manager's
            well_info = self.plot_handler.get_well_info(well_number, self.db_path)
            cae_number = well_info.get('cae_number', '') if well_info else ''
            
            default_filename = f"{well_number}"
            if cae_number:
                default_filename += f" ({cae_number})"
            default_filename += ".png"
        
        # Ask for output directory rather than specific file
        output_dir = QFileDialog.getExistingDirectory(None, "Select Output Directory")
        if not output_dir:
            return
        
        try:
            # Create file path in the selected directory
            file_path = os.path.join(output_dir, default_filename)
            
            # Create a dialog to select resolution
            resolution_dialog = QDialog()
            resolution_dialog.setWindowTitle("Select Image Resolution")
            resolution_layout = QVBoxLayout(resolution_dialog)
            
            resolution_layout.addWidget(QLabel("Select Image Resolution (DPI):"))
            
            resolution_options = [("Low (100 DPI)", 100), 
                               ("Medium (300 DPI)", 300), 
                               ("High (600 DPI)", 600), 
                               ("Very High (1200 DPI)", 1200)]
            
            resolution_group = QButtonGroup(resolution_dialog)
            selected_dpi = 300  # Default to medium
            
            for i, (label, dpi) in enumerate(resolution_options):
                radio = QRadioButton(label)
                if i == 1:  # Medium is default
                    radio.setChecked(True)
                resolution_group.addButton(radio, dpi)
                resolution_layout.addWidget(radio)
            
            # Connect button group
            resolution_group.buttonClicked.connect(lambda button: setattr(resolution_dialog, 'selected_dpi', resolution_group.id(button)))
            resolution_dialog.selected_dpi = selected_dpi
            
            # Add OK button
            ok_btn = QPushButton("OK")
            ok_btn.clicked.connect(resolution_dialog.accept)
            resolution_layout.addWidget(ok_btn)
            
            # Show dialog
            if resolution_dialog.exec_() == QDialog.Accepted:
                dpi = resolution_dialog.selected_dpi
                
                # Save current figure with selected resolution
                figure.savefig(file_path, dpi=dpi, bbox_inches='tight')
                
                QMessageBox.information(None, "Export Successful", 
                                      f"Plot saved successfully as {os.path.basename(file_path)} at {dpi} DPI.")
            
        except Exception as e:
            logger.error(f"Error exporting plot: {e}")
            QMessageBox.critical(None, "Export Error", f"Failed to export plot: {str(e)}") 