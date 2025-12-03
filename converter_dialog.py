"""
Converter Dialog for UMM-STAC Converter Plugin
"""
import os
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QProgressBar
)
from qgis.core import QgsMessageLog, Qgis

from .umm_to_stac import UMMToSTACConverter
from .stac_to_umm import STACToUMMConverter
from .umm_to_dq4eo import UMMToDQ4EOConverter
from .dq4eo_to_umm import DQ4EOToUMMConverter


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'converter_dialog_base.ui'))


class ConversionWorker(QThread):
    """Worker thread for file conversion."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, input_files, output_dir, conversion_mode, conversion_type):
        """Initialize worker.
        
        :param input_files: List of input file paths
        :param output_dir: Output directory path
        :param conversion_mode: 'umm_to_stac' or 'stac_to_umm'
        :param conversion_type: 'item' or 'collection'
        """
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.conversion_mode = conversion_mode
        self.conversion_type = conversion_type
        self._is_running = True
        
    def run(self):
        """Run the conversion process."""
        try:
            if self.conversion_mode == 'umm_to_stac':
                converter = UMMToSTACConverter()
            elif self.conversion_mode == 'stac_to_umm':
                converter = STACToUMMConverter()
            elif self.conversion_mode == 'umm_to_dq4eo':
                converter = UMMToDQ4EOConverter()
            elif self.conversion_mode == 'dq4eo_to_umm':
                converter = DQ4EOToUMMConverter()
            else:
                raise ValueError(f"Unknown conversion mode: {self.conversion_mode}")
            
            total = len(self.input_files)
            success_count = 0
            
            for i, input_file in enumerate(self.input_files):
                if not self._is_running:
                    break
                
                # Generate output filename
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                if self.conversion_mode == 'umm_to_stac':
                    output_file = os.path.join(self.output_dir, f"{base_name}_stac.json")
                elif self.conversion_mode == 'stac_to_umm':
                    output_file = os.path.join(self.output_dir, f"{base_name}_umm.json")
                elif self.conversion_mode == 'umm_to_dq4eo':
                    output_file = os.path.join(self.output_dir, f"{base_name}_dq4eo.json")
                elif self.conversion_mode == 'dq4eo_to_umm':
                    output_file = os.path.join(self.output_dir, f"{base_name}_umm.json")
                
                # Convert file
                success = converter.convert_file(input_file, output_file, self.conversion_type)
                
                if success:
                    success_count += 1
                
                self.progress.emit(i + 1, total)
            
            message = f"Converted {success_count} of {total} files successfully."
            self.finished.emit(success_count > 0, message)
            
        except Exception as e:
            self.finished.emit(False, f"Error during conversion: {str(e)}")
    
    def stop(self):
        """Stop the conversion process."""
        self._is_running = False


class ConverterDialog(QDialog, FORM_CLASS):
    """Dialog for UMM-STAC conversion."""
    
    def __init__(self, parent=None):
        """Constructor."""
        super(ConverterDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.input_files = []
        self.output_dir = ""
        self.worker = None
        
        # Connect signals
        self.btnBrowseInput.clicked.connect(self.browse_input)
        self.btnBrowseOutput.clicked.connect(self.browse_output)
        self.btnConvert.clicked.connect(self.start_conversion)
        self.btnClose.clicked.connect(self.reject)
        
        # Set up conversion mode
        self.radioUmmToStac.toggled.connect(self.update_ui_state)
        self.radioStacToUmm.toggled.connect(self.update_ui_state)
        self.radioUmmToDq4eo.toggled.connect(self.update_ui_state)
        self.radioDq4eoToUmm.toggled.connect(self.update_ui_state)
        
        # Set defaults
        self.radioUmmToStac.setChecked(True)
        self.radioItem.setChecked(True)
        self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI elements based on selected mode."""
        # Enable/disable conversion type based on mode
        # Both modes support item and collection conversion
        pass
    
    def browse_input(self):
        """Browse for input files."""
        file_filter = "JSON Files (*.json);;All Files (*.*)"
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Input Files",
            "",
            file_filter
        )
        
        if files:
            self.input_files = files
            self.txtInputFiles.setText(f"{len(files)} file(s) selected")
            self.log_message(f"Selected {len(files)} input file(s)")
    
    def browse_output(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            ""
        )
        
        if directory:
            self.output_dir = directory
            self.txtOutputDir.setText(directory)
            self.log_message(f"Output directory: {directory}")
    
    def start_conversion(self):
        """Start the conversion process."""
        # Validate inputs
        if not self.input_files:
            QMessageBox.warning(self, "Warning", "Please select input files.")
            return
        
        if not self.output_dir:
            QMessageBox.warning(self, "Warning", "Please select output directory.")
            return
        
        # Get conversion settings
        if self.radioUmmToStac.isChecked():
            conversion_mode = 'umm_to_stac'
        elif self.radioStacToUmm.isChecked():
            conversion_mode = 'stac_to_umm'
        elif self.radioUmmToDq4eo.isChecked():
            conversion_mode = 'umm_to_dq4eo'
        elif self.radioDq4eoToUmm.isChecked():
            conversion_mode = 'dq4eo_to_umm'
        else:
            QMessageBox.warning(self, "Warning", "Please select a conversion mode.")
            return
        
        if self.radioItem.isChecked():
            conversion_type = 'item'
        else:
            conversion_type = 'collection'
        
        # Disable controls during conversion
        self.set_controls_enabled(False)
        
        # Create and start worker thread
        self.worker = ConversionWorker(
            self.input_files,
            self.output_dir,
            conversion_mode,
            conversion_type
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.start()
        
        self.log_message(f"Starting conversion: {conversion_mode} ({conversion_type})")
    
    def update_progress(self, current, total):
        """Update progress bar.
        
        :param current: Current file number
        :param total: Total number of files
        """
        percentage = int((current / total) * 100)
        self.progressBar.setValue(percentage)
        self.lblStatus.setText(f"Converting file {current} of {total}...")
    
    def conversion_finished(self, success, message):
        """Handle conversion completion.
        
        :param success: Whether conversion was successful
        :param message: Status message
        """
        self.set_controls_enabled(True)
        self.progressBar.setValue(100 if success else 0)
        self.lblStatus.setText(message)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.log_message(message, Qgis.Success)
        else:
            QMessageBox.critical(self, "Error", message)
            self.log_message(message, Qgis.Critical)
        
        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
    
    def set_controls_enabled(self, enabled):
        """Enable or disable form controls.
        
        :param enabled: Whether to enable controls
        """
        self.btnBrowseInput.setEnabled(enabled)
        self.btnBrowseOutput.setEnabled(enabled)
        self.btnConvert.setEnabled(enabled)
        self.radioUmmToStac.setEnabled(enabled)
        self.radioStacToUmm.setEnabled(enabled)
        self.radioUmmToDq4eo.setEnabled(enabled)
        self.radioDq4eoToUmm.setEnabled(enabled)
        self.radioItem.setEnabled(enabled)
        self.radioCollection.setEnabled(enabled)
    
    def log_message(self, message, level=Qgis.Info):
        """Log a message to QGIS message log.
        
        :param message: Message to log
        :param level: Message level
        """
        QgsMessageLog.logMessage(message, 'UMM STAC Converter', level)
    
    def closeEvent(self, event):
        """Handle dialog close event.
        
        :param event: Close event
        """
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Conversion in Progress",
                "Conversion is still running. Do you want to stop it?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
