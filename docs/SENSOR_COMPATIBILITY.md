# Sensor Compatibility and Integration Guide

## Overview

The CAESER Water Levels Monitoring System is designed with a modular architecture that supports multiple sensor manufacturers and data logger types. This guide explains current compatibility, integration procedures, and expansion capabilities.

## Current Sensor Support

### ✅ **Fully Supported: Solinst Data Loggers**

#### **Solinst Levelogger Series**
- **Models**: Levelogger 5, Levelogger Edge, Levelogger Gold
- **File Formats**: 
  - `.xle` (XML Logger Export) - Primary format
  - `.lev` (Legacy format) - Auto-converted to XLE
- **Features**:
  - Complete metadata preservation
  - Automatic barometric compensation
  - Temperature and pressure readings
  - GPS coordinates and installation data
  - Calibration parameters and corrections

#### **Solinst Barologger Series**
- **Models**: Barologger 5, Barologger Edge, Barologger Gold
- **Integration**: 
  - Atmospheric pressure compensation
  - Master barometric data creation
  - Multi-logger synthesis
  - Temperature correlation analysis

#### **Data Processing Capabilities**
```
Solinst XLE File → Metadata Extraction → Quality Control → Database Storage
                 ↓
          Barometric Compensation → Water Level Calculation → Analysis
```

---

## 🔄 **Expanding Compatibility**

### **Campbell Scientific** (Implementation Ready)
- **Target Models**: CR1000X, CR6, CR300 series
- **File Formats**: CSV, TOA5, binary formats
- **Integration Points**:
  - LoggerNet data retrieval
  - Custom CSV parsing templates
  - Real-time telemetry integration
  - Modular data conversion utilities

### **In-Situ** (Planned Integration)
- **Target Models**: Level TROLL, Aqua TROLL series
- **File Formats**: Win-Situ CSV exports, binary data
- **Features**:
  - Multi-parameter logging (level, temperature, conductivity)
  - Vented and non-vented pressure transducers
  - Wireless telemetry capabilities

### **OTT HydroMet** (Future Expansion)
- **Target Models**: OTT PLS, OTT CTD series
- **File Formats**: HydroOffice exports, CSV
- **Capabilities**:
  - High-precision water level measurement
  - Multi-parameter environmental monitoring
  - European standard compliance

---

## Modular Architecture Design

### **Data Import Framework**
```python
class DataImporter:
    """Base class for sensor data importers"""
    
    def __init__(self, manufacturer, model):
        self.manufacturer = manufacturer
        self.model = model
        self.supported_formats = []
    
    def import_data(self, file_path):
        """Override in manufacturer-specific implementations"""
        pass
    
    def validate_data(self, raw_data):
        """Common validation logic"""
        pass
    
    def extract_metadata(self, raw_data):
        """Extract sensor and deployment metadata"""
        pass

# Manufacturer-specific implementations
class SolinstImporter(DataImporter):
    """Solinst XLE and LEV file importer"""
    
    def import_data(self, file_path):
        if file_path.endswith('.xle'):
            return self.parse_xle(file_path)
        elif file_path.endswith('.lev'):
            return self.parse_lev(file_path)

class CampbellImporter(DataImporter):
    """Campbell Scientific data importer"""
    
    def import_data(self, file_path):
        if file_path.endswith('.csv'):
            return self.parse_csv(file_path)
        elif file_path.endswith('.dat'):
            return self.parse_dat(file_path)
```

### **Sensor Configuration System**
```json
{
  "sensors": {
    "solinst_levelogger": {
      "manufacturer": "Solinst",
      "type": "pressure_transducer",
      "file_formats": [".xle", ".lev"],
      "metadata_fields": [
        "serial_number", "location", "installation_date",
        "calibration_date", "pressure_range", "accuracy"
      ],
      "processing_pipeline": [
        "parse_xml", "extract_metadata", "validate_readings",
        "apply_calibration", "quality_control"
      ]
    },
    "campbell_cr1000": {
      "manufacturer": "Campbell Scientific",
      "type": "datalogger",
      "file_formats": [".csv", ".dat", ".toa5"],
      "metadata_fields": [
        "station_name", "logger_id", "program_name",
        "sampling_interval", "measurement_units"
      ],
      "processing_pipeline": [
        "parse_csv", "map_columns", "convert_units",
        "validate_timestamps", "quality_control"
      ]
    }
  }
}
```

---

## Integration Procedures

### **Adding New Sensor Support**

#### **Step 1: Create Sensor Profile**
```python
# config/sensors/new_sensor.json
{
  "manufacturer": "Manufacturer Name",
  "model": "Sensor Model",
  "type": "pressure_transducer",
  "file_formats": [".csv", ".txt"],
  "column_mapping": {
    "timestamp": "Date/Time",
    "pressure": "Pressure (psi)",
    "temperature": "Temperature (°C)"
  },
  "unit_conversions": {
    "pressure": {"from": "psi", "to": "feet_h2o", "factor": 2.31},
    "temperature": {"from": "celsius", "to": "fahrenheit", "formula": "C*9/5+32"}
  }
}
```

#### **Step 2: Implement Data Parser**
```python
class NewSensorImporter(DataImporter):
    def __init__(self):
        super().__init__("Manufacturer", "Model")
        self.config = load_sensor_config("new_sensor.json")
    
    def parse_data_file(self, file_path):
        """Parse manufacturer-specific data format"""
        # Implementation specific to data format
        pass
    
    def map_columns(self, raw_data):
        """Map manufacturer columns to standard format"""
        mapping = self.config["column_mapping"]
        standardized_data = {}
        
        for standard_col, manufacturer_col in mapping.items():
            standardized_data[standard_col] = raw_data[manufacturer_col]
        
        return standardized_data
    
    def apply_unit_conversions(self, data):
        """Convert units to standard format"""
        conversions = self.config["unit_conversions"]
        
        for field, conversion in conversions.items():
            if field in data:
                data[field] = self.convert_units(data[field], conversion)
        
        return data
```

#### **Step 3: Register in System**
```python
# Register new sensor in the import system
SENSOR_IMPORTERS = {
    'solinst': SolinstImporter,
    'campbell': CampbellImporter,
    'new_sensor': NewSensorImporter,  # Add new sensor
}

def get_importer(file_path):
    """Auto-detect sensor type and return appropriate importer"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension in ['.xle', '.lev']:
        return SENSOR_IMPORTERS['solinst']()
    elif file_extension == '.csv':
        # Additional logic to distinguish CSV formats
        return detect_csv_format(file_path)
    
    return None
```

---

## Data Format Standards

### **Internal Data Format**
All sensor data is converted to a standardized internal format:

```python
{
    "metadata": {
        "sensor_id": "SN123456",
        "manufacturer": "Solinst",
        "model": "Levelogger 5",
        "installation_date": "2024-01-15T10:30:00Z",
        "location": {
            "latitude": 35.1174,
            "longitude": -89.9711,
            "elevation": 331.2
        }
    },
    "readings": [
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "pressure": 14.73,  # psi
            "temperature": 15.2,  # Celsius
            "water_level": null,  # Calculated after processing
            "quality_flag": "good"
        }
    ],
    "calibration": {
        "pressure_offset": 0.0,
        "temperature_offset": 0.0,
        "calibration_date": "2024-01-01T00:00:00Z"
    }
}
```

### **Quality Control Standards**
```python
QUALITY_CONTROL_RULES = {
    "pressure": {
        "range": {"min": 0, "max": 100},  # psi
        "rate_of_change": {"max": 5.0},   # psi/hour
        "statistical": {"z_score_threshold": 3.0}
    },
    "temperature": {
        "range": {"min": -20, "max": 50},  # Celsius
        "rate_of_change": {"max": 10.0},   # °C/hour
        "seasonal": {"expected_range": {"winter": [-5, 25], "summer": [10, 35]}}
    },
    "temporal": {
        "timestamp_continuity": True,
        "duplicate_detection": True,
        "future_date_check": True
    }
}
```

---

## Calibration and Accuracy

### **Multi-Point Calibration**
```python
def apply_calibration(raw_readings, calibration_points):
    """
    Apply multi-point calibration to sensor readings
    
    Args:
        raw_readings: List of raw sensor values
        calibration_points: List of (raw_value, true_value) pairs
    
    Returns:
        calibrated_readings: Corrected sensor values
    """
    # Create calibration curve using polynomial fitting
    raw_vals = [point[0] for point in calibration_points]
    true_vals = [point[1] for point in calibration_points]
    
    # Fit polynomial (typically 2nd or 3rd order)
    coefficients = np.polyfit(raw_vals, true_vals, deg=2)
    
    # Apply calibration to all readings
    calibrated_readings = []
    for reading in raw_readings:
        calibrated_value = np.polyval(coefficients, reading)
        calibrated_readings.append(calibrated_value)
    
    return calibrated_readings
```

### **Drift Correction**
```python
def detect_and_correct_drift(readings, manual_measurements):
    """
    Detect sensor drift and apply corrections
    
    Args:
        readings: Continuous sensor readings
        manual_measurements: Periodic manual validation measurements
    
    Returns:
        corrected_readings: Drift-corrected sensor values
    """
    # Calculate drift over time
    drift_points = []
    for manual in manual_measurements:
        # Find nearest sensor reading
        nearest_reading = find_nearest_reading(readings, manual['timestamp'])
        drift = manual['value'] - nearest_reading['value']
        drift_points.append((manual['timestamp'], drift))
    
    # Interpolate drift correction over time
    drift_correction = interpolate_drift(drift_points, readings)
    
    # Apply corrections
    corrected_readings = []
    for i, reading in enumerate(readings):
        corrected_value = reading['value'] + drift_correction[i]
        corrected_readings.append({
            **reading,
            'value': corrected_value,
            'drift_correction': drift_correction[i]
        })
    
    return corrected_readings
```

---

## Testing and Validation

### **Sensor Integration Testing**
```python
def test_sensor_integration(sensor_importer, test_file):
    """
    Comprehensive testing of new sensor integration
    
    Args:
        sensor_importer: Sensor-specific importer class
        test_file: Path to test data file
    
    Returns:
        test_results: Dictionary with test outcomes
    """
    results = {
        'file_parsing': False,
        'metadata_extraction': False,
        'data_validation': False,
        'quality_control': False,
        'database_integration': False
    }
    
    try:
        # Test file parsing
        raw_data = sensor_importer.parse_data_file(test_file)
        results['file_parsing'] = True
        
        # Test metadata extraction
        metadata = sensor_importer.extract_metadata(raw_data)
        results['metadata_extraction'] = len(metadata) > 0
        
        # Test data validation
        validated_data = sensor_importer.validate_data(raw_data)
        results['data_validation'] = validated_data is not None
        
        # Test quality control
        qc_results = apply_quality_control(validated_data)
        results['quality_control'] = True
        
        # Test database integration
        db_success = store_in_database(validated_data, metadata)
        results['database_integration'] = db_success
        
    except Exception as e:
        results['errors'] = str(e)
    
    return results
```

---

## Best Practices for Integration

### **File Format Handling**
- **Robust Parsing**: Handle variations in manufacturer file formats
- **Error Recovery**: Gracefully handle corrupted or incomplete files
- **Format Validation**: Verify file integrity before processing
- **Encoding Support**: Handle different text encodings (UTF-8, ASCII, etc.)

### **Metadata Preservation**
- **Complete Records**: Preserve all available sensor and deployment metadata
- **Standardization**: Map to consistent internal metadata schema
- **Provenance**: Track data source and processing history
- **Validation**: Verify metadata completeness and accuracy

### **Performance Optimization**
- **Streaming Processing**: Handle large files without excessive memory usage
- **Batch Operations**: Process multiple files efficiently
- **Caching**: Cache frequently accessed calibration and configuration data
- **Parallel Processing**: Utilize multiple CPU cores for large datasets

### **Quality Assurance**
- **Automated Testing**: Comprehensive test suites for each sensor type
- **Validation Data**: Maintain test datasets for regression testing
- **Documentation**: Clear documentation for integration procedures
- **Version Control**: Track changes to sensor configurations and parsers

---

## Future Expansion Roadmap

### **Phase 1: Campbell Scientific Integration**
- **Timeline**: Q2 2024
- **Scope**: CR1000X, CR6, CR300 series support
- **Features**: Real-time telemetry, LoggerNet integration

### **Phase 2: In-Situ Support**
- **Timeline**: Q3 2024
- **Scope**: Level TROLL, Aqua TROLL series
- **Features**: Multi-parameter logging, wireless connectivity

### **Phase 3: Universal CSV Support**
- **Timeline**: Q4 2024
- **Scope**: Generic CSV parser with user-configurable mapping
- **Features**: Custom column mapping, unit conversion, quality control

### **Phase 4: Real-time Integration**
- **Timeline**: Q1 2025
- **Scope**: Live data feeds from telemetry systems
- **Features**: API integration, real-time alerts, continuous monitoring

---

**Next Steps**: Continue to [Integration Guide](../help/INTEGRATION/sensors.md) for detailed implementation procedures and examples.