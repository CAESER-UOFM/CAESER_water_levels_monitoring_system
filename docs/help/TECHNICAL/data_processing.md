# Data Processing Workflows

## Overview

The CAESER Water Levels Monitoring System implements sophisticated data processing workflows that transform raw sensor readings into scientifically accurate water level measurements and analytical results.

## Data Processing Pipeline

### 1. Data Import Stage

#### XLE File Processing
```
Raw XLE File → XML Parser → Metadata Extraction → Data Validation → Database Storage
```

**Steps:**
1. **File Format Detection**: Identify Solinst XLE format and version
2. **XML Parsing**: Extract structured data from XML format
3. **Metadata Extraction**: 
   - Logger serial number and type
   - Installation location and dates
   - Calibration parameters
   - Measurement units and precision
4. **Data Validation**:
   - Timestamp continuity checks
   - Value range validation
   - Quality flag assignment
5. **Database Storage**: Insert validated data with proper indexing

#### Manual Reading Processing
```
Field Measurements → Validation → Tape Correction → Water Level Calculation → Database Storage
```

**Processing Logic:**
```python
# Simplified water level calculation
def calculate_water_level(dtw_measurement, tape_correction, top_of_casing):
    """
    Calculate water surface elevation from depth-to-water measurement
    
    Args:
        dtw_measurement: Depth to water (feet or meters)
        tape_correction: Instrument-specific correction factor
        top_of_casing: Elevation of measuring point
    
    Returns:
        water_level: Water surface elevation
    """
    corrected_dtw = dtw_measurement + tape_correction
    water_level = top_of_casing - corrected_dtw
    return water_level
```

---

### 2. Quality Control Stage

#### Automated Quality Control Algorithms

##### Range Validation
```sql
-- Flag readings outside reasonable ranges
UPDATE water_level_readings 
SET level_flag = 'error'
WHERE pressure < 0 OR pressure > 100  -- Example: 0-100 psi range
   OR temperature < -20 OR temperature > 50;  -- -20°C to 50°C
```

##### Temporal Consistency Checks
```python
def detect_anomalies(readings, threshold_std=3.0):
    """
    Detect anomalous readings using statistical methods
    
    Args:
        readings: Time series of water level readings
        threshold_std: Standard deviation threshold for anomaly detection
    
    Returns:
        anomaly_flags: Boolean array indicating anomalous readings
    """
    # Calculate rolling statistics
    rolling_mean = readings.rolling(window=24).mean()  # 24-hour window
    rolling_std = readings.rolling(window=24).std()
    
    # Flag readings beyond threshold
    z_scores = (readings - rolling_mean) / rolling_std
    anomaly_flags = abs(z_scores) > threshold_std
    
    return anomaly_flags
```

##### Data Continuity Assessment
- **Gap Detection**: Identify missing data periods
- **Sampling Rate Validation**: Verify consistent measurement intervals
- **Duplicate Detection**: Remove or flag duplicate timestamps

---

### 3. Barometric Compensation

#### Master Barometric Data Creation

##### Multi-Logger Synthesis
```python
def create_master_baro_data(barologger_readings):
    """
    Create composite barometric pressure record from multiple loggers
    
    Args:
        barologger_readings: Dictionary of readings by serial number
    
    Returns:
        master_data: Unified barometric pressure time series
    """
    # Align timestamps across all loggers
    aligned_data = align_timestamps(barologger_readings)
    
    # Quality-weighted averaging
    weights = calculate_quality_weights(aligned_data)
    master_pressure = weighted_average(aligned_data, weights)
    
    # Gap filling using interpolation
    master_data = fill_gaps(master_pressure, method='linear')
    
    return master_data
```

##### Gap Filling Algorithms
1. **Linear Interpolation**: For short gaps (< 6 hours)
2. **Seasonal Decomposition**: For longer gaps using historical patterns
3. **Nearest Neighbor**: When multiple barologgers are available
4. **Regional Data**: Use nearby weather stations as backup

#### Water Pressure Calculation
```python
def apply_barometric_compensation(transducer_pressure, baro_pressure):
    """
    Remove atmospheric pressure effects from transducer readings
    
    Args:
        transducer_pressure: Raw pressure from transducer (absolute)
        baro_pressure: Atmospheric pressure at same time
    
    Returns:
        water_pressure: Pressure due to water column only (gauge)
    """
    # Convert to consistent units if necessary
    transducer_psi = convert_to_psi(transducer_pressure)
    baro_psi = convert_to_psi(baro_pressure)
    
    # Calculate gauge pressure (water column only)
    water_pressure = transducer_psi - baro_psi
    
    return water_pressure
```

---

### 4. Water Level Calculation

#### Pressure to Water Level Conversion
```python
def pressure_to_water_level(water_pressure, pressure_offset, elevation_offset):
    """
    Convert water pressure to water surface elevation
    
    Args:
        water_pressure: Gauge pressure from water column (psi)
        pressure_offset: Transducer calibration offset
        elevation_offset: Elevation of transducer above datum
    
    Returns:
        water_level: Water surface elevation above datum
    """
    # Convert pressure to feet of water (1 psi = 2.31 feet H2O)
    pressure_head = (water_pressure - pressure_offset) * 2.31
    
    # Calculate water surface elevation
    water_level = elevation_offset + pressure_head
    
    return water_level
```

#### Calibration Management
- **Factory Calibration**: Apply manufacturer calibration coefficients
- **Field Calibration**: Use manual measurements for field corrections
- **Drift Correction**: Account for sensor drift over time
- **Multi-point Calibration**: Use multiple reference points for accuracy

---

### 5. Data Integration and Merging

#### Multi-Source Data Consolidation
```python
def merge_data_sources(transducer_data, manual_readings, telemetry_data):
    """
    Combine data from multiple sources with proper precedence
    
    Args:
        transducer_data: Automated pressure transducer readings
        manual_readings: Field measurements with water level meter
        telemetry_data: Real-time telemetry system data
    
    Returns:
        consolidated_data: Merged dataset with quality indicators
    """
    # Establish data source precedence
    precedence = {
        'manual': 1,      # Highest - direct field measurements
        'transducer': 2,  # Medium - automated with corrections
        'telemetry': 3    # Lowest - real-time but less accurate
    }
    
    # Merge with conflict resolution
    merged_data = resolve_conflicts(
        [transducer_data, manual_readings, telemetry_data],
        precedence
    )
    
    return merged_data
```

#### Temporal Alignment
- **Timestamp Standardization**: Convert all data to UTC
- **Interpolation**: Align data to common time intervals
- **Synchronization**: Account for logger clock drift

---

### 6. Statistical Processing

#### Well Statistics Calculation
```sql
-- Generate comprehensive well statistics
INSERT INTO well_statistics (well_number, calculation_date, stats_json)
SELECT 
    well_number,
    CURRENT_TIMESTAMP,
    json_object(
        'count', COUNT(*),
        'mean_level', AVG(water_level),
        'std_dev', 
        'min_level', MIN(water_level),
        'max_level', MAX(water_level),
        'range', MAX(water_level) - MIN(water_level),
        'data_start', MIN(timestamp_utc),
        'data_end', MAX(timestamp_utc)
    ) as stats_json
FROM water_level_readings
WHERE level_flag != 'error'
GROUP BY well_number;
```

#### Trend Analysis
```python
def calculate_trends(water_levels, timestamps):
    """
    Calculate water level trends using statistical methods
    
    Args:
        water_levels: Time series of water level measurements
        timestamps: Corresponding timestamps
    
    Returns:
        trend_results: Dictionary with trend statistics
    """
    # Convert timestamps to numeric for regression
    time_numeric = convert_to_julian(timestamps)
    
    # Linear regression for overall trend
    slope, intercept, r_value, p_value = stats.linregress(time_numeric, water_levels)
    
    # Seasonal decomposition
    seasonal_component = seasonal_decompose(water_levels, period=365)
    
    # Mann-Kendall trend test for non-parametric analysis
    mk_trend, mk_p_value = mann_kendall_test(water_levels)
    
    return {
        'linear_trend': slope,
        'r_squared': r_value**2,
        'trend_significance': p_value,
        'seasonal_amplitude': seasonal_component.seasonal.std(),
        'mk_trend': mk_trend,
        'mk_significance': mk_p_value
    }
```

---

### 7. Recharge Calculations

#### RISE Method Processing
```python
def calculate_rise_recharge(water_levels, timestamps, specific_yield=0.15):
    """
    Calculate groundwater recharge using RISE method
    
    Args:
        water_levels: Time series of water level measurements
        timestamps: Corresponding timestamps
        specific_yield: Aquifer-specific yield parameter
    
    Returns:
        recharge_events: List of recharge events with quantities
    """
    # Identify recharge events (water level rises)
    events = detect_recharge_events(water_levels, timestamps)
    
    # Calculate recharge for each event
    recharge_events = []
    for event in events:
        # Water level rise in feet
        rise_magnitude = event['peak_level'] - event['pre_event_level']
        
        # Convert to recharge volume (rise × specific yield)
        recharge_inches = rise_magnitude * 12 * specific_yield
        
        recharge_events.append({
            'start_date': event['start_date'],
            'peak_date': event['peak_date'],
            'rise_feet': rise_magnitude,
            'recharge_inches': recharge_inches
        })
    
    return recharge_events
```

#### MRC Method Processing
```python
def calculate_mrc_recharge(water_levels, timestamps):
    """
    Calculate recharge using Master Recession Curve method
    
    Args:
        water_levels: Time series of water level measurements  
        timestamps: Corresponding timestamps
    
    Returns:
        mrc_results: Recession analysis and recharge estimates
    """
    # Identify recession periods
    recession_periods = identify_recessions(water_levels, timestamps)
    
    # Create master recession curve
    master_curve = create_master_recession_curve(recession_periods)
    
    # Calculate recharge based on deviations from master curve
    recharge_estimates = []
    for period in recession_periods:
        deviation = calculate_curve_deviation(period, master_curve)
        recharge = deviation_to_recharge(deviation)
        recharge_estimates.append(recharge)
    
    return {
        'master_curve': master_curve,
        'recession_periods': recession_periods,
        'recharge_estimates': recharge_estimates
    }
```

---

### 8. Export and Visualization Processing

#### Data Preparation for Visualization
```python
def prepare_visualization_data(raw_data, aggregation_level='daily'):
    """
    Prepare data for efficient visualization and export
    
    Args:
        raw_data: High-resolution time series data
        aggregation_level: Temporal aggregation ('hourly', 'daily', 'monthly')
    
    Returns:
        viz_data: Optimized data for plotting and export
    """
    # Temporal aggregation for performance
    if aggregation_level == 'daily':
        agg_data = raw_data.resample('D').agg({
            'water_level': ['mean', 'min', 'max'],
            'temperature': 'mean'
        })
    
    # Quality flag summarization
    quality_summary = summarize_quality_flags(raw_data)
    
    # Statistical summaries
    stats = calculate_summary_statistics(agg_data)
    
    return {
        'data': agg_data,
        'quality': quality_summary,
        'statistics': stats
    }
```

#### Export Format Processing
- **CSV Export**: Tabular data with metadata headers
- **JSON Export**: Structured data for API consumption
- **Database Export**: SQLite files for sharing and archival
- **GIS Export**: Shapefiles and KML for mapping applications

---

## Error Handling and Recovery

### Data Integrity Checks
```sql
-- Comprehensive data integrity validation
SELECT 
    'Orphaned readings' as issue_type,
    COUNT(*) as count
FROM water_level_readings wlr
LEFT JOIN wells w ON wlr.well_number = w.well_number
WHERE w.well_number IS NULL

UNION ALL

SELECT 
    'Invalid timestamps' as issue_type,
    COUNT(*) as count
FROM water_level_readings
WHERE timestamp_utc > datetime('now', '+1 day')
   OR timestamp_utc < datetime('1990-01-01');
```

### Recovery Procedures
1. **Automatic Correction**: Fix common data issues automatically
2. **Manual Review**: Flag issues requiring human intervention
3. **Rollback Capability**: Undo problematic processing steps
4. **Backup Integration**: Restore from backups when necessary

---

## Performance Optimization

### Batch Processing
```python
def batch_process_files(file_list, batch_size=100):
    """
    Process large numbers of files efficiently
    
    Args:
        file_list: List of files to process
        batch_size: Number of files to process simultaneously
    
    Returns:
        results: Processing results and statistics
    """
    results = []
    
    for i in range(0, len(file_list), batch_size):
        batch = file_list[i:i+batch_size]
        
        # Parallel processing within batch
        with ThreadPoolExecutor(max_workers=4) as executor:
            batch_results = list(executor.map(process_single_file, batch))
        
        results.extend(batch_results)
        
        # Progress reporting
        progress = (i + len(batch)) / len(file_list) * 100
        update_progress(progress)
    
    return results
```

### Memory Management
- **Streaming Processing**: Handle large datasets without loading entirely into memory
- **Chunked Database Operations**: Process data in manageable chunks
- **Connection Pooling**: Efficient database connection management
- **Cache Management**: Strategic caching of frequently accessed data

---

**Next Steps**: Continue to [Calculations](calculations.md) to understand the specific algorithms used for recharge calculations and other analytical methods.