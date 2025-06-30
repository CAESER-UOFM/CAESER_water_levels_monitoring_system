# Recharge Calculation Methods

## Overview

The CAESER Water Levels Monitoring System implements multiple scientifically validated methods for groundwater recharge estimation. This comprehensive guide explains the algorithms, parameters, and implementation details for each method.

---

## 🌊 RISE Method (Water Table Fluctuation)

### **Scientific Basis**
The RISE (Recharge from Instantaneous water level riSE) method is based on the principle that increases in groundwater levels are directly related to recharge events. This method assumes that rapid water level rises following precipitation are primarily due to groundwater recharge.

### **Theoretical Foundation**
```
Recharge = Δh × Sy
```
Where:
- **Δh** = Water level rise (L)
- **Sy** = Specific yield (dimensionless)

### **Algorithm Implementation**

#### **Event Detection**
```python
def detect_recharge_events(water_levels, timestamps, min_rise=0.1, min_duration=6):
    """
    Detect recharge events based on water level rises
    
    Args:
        water_levels: Time series of water level measurements (feet)
        timestamps: Corresponding timestamps
        min_rise: Minimum rise to consider as event (feet)
        min_duration: Minimum event duration (hours)
    
    Returns:
        events: List of detected recharge events
    """
    events = []
    rising_phase = False
    event_start = None
    baseline_level = None
    
    for i in range(1, len(water_levels)):
        current_level = water_levels[i]
        previous_level = water_levels[i-1]
        current_time = timestamps[i]
        
        # Detect start of rising phase
        if not rising_phase and current_level > previous_level:
            rising_phase = True
            event_start = current_time
            baseline_level = previous_level
        
        # Detect end of rising phase
        elif rising_phase and current_level <= previous_level:
            # Check if event meets criteria
            total_rise = current_level - baseline_level
            event_duration = (current_time - event_start).total_seconds() / 3600
            
            if total_rise >= min_rise and event_duration >= min_duration:
                events.append({
                    'start_time': event_start,
                    'peak_time': current_time,
                    'baseline_level': baseline_level,
                    'peak_level': current_level,
                    'total_rise': total_rise,
                    'duration_hours': event_duration
                })
            
            rising_phase = False
    
    return events
```

#### **Recharge Calculation**
```python
def calculate_rise_recharge(events, specific_yield=0.15, efficiency=1.0):
    """
    Calculate recharge for each detected event
    
    Args:
        events: List of recharge events from detect_recharge_events()
        specific_yield: Aquifer specific yield (dimensionless)
        efficiency: Recharge efficiency factor (0-1)
    
    Returns:
        recharge_results: Detailed recharge calculations
    """
    recharge_results = []
    total_annual_recharge = 0
    
    for event in events:
        # Calculate recharge in inches
        rise_feet = event['total_rise']
        recharge_inches = rise_feet * 12 * specific_yield * efficiency
        
        # Calculate recharge rate
        duration_hours = event['duration_hours']
        recharge_rate = recharge_inches / duration_hours  # inches/hour
        
        event_result = {
            'event_id': f"RISE_{event['start_time'].strftime('%Y%m%d_%H%M')}",
            'start_time': event['start_time'],
            'peak_time': event['peak_time'],
            'rise_feet': rise_feet,
            'recharge_inches': recharge_inches,
            'recharge_rate_in_per_hr': recharge_rate,
            'duration_hours': duration_hours,
            'specific_yield_used': specific_yield,
            'efficiency_used': efficiency
        }
        
        recharge_results.append(event_result)
        total_annual_recharge += recharge_inches
    
    return {
        'events': recharge_results,
        'total_annual_recharge_inches': total_annual_recharge,
        'average_event_recharge': total_annual_recharge / len(events) if events else 0,
        'number_of_events': len(events)
    }
```

### **Parameter Configuration**
```python
RISE_PARAMETERS = {
    'specific_yield': {
        'default': 0.15,
        'range': [0.05, 0.35],
        'description': 'Aquifer specific yield (fraction of water released per unit volume)',
        'aquifer_types': {
            'sand': 0.20,
            'sandy_clay': 0.12,
            'clay': 0.05,
            'gravel': 0.25,
            'limestone': 0.10
        }
    },
    'min_rise_threshold': {
        'default': 0.1,  # feet
        'range': [0.02, 0.5],
        'description': 'Minimum water level rise to consider as recharge event'
    },
    'min_duration': {
        'default': 6,  # hours
        'range': [1, 24],
        'description': 'Minimum duration for valid recharge event'
    },
    'recharge_efficiency': {
        'default': 1.0,
        'range': [0.1, 1.0],
        'description': 'Fraction of precipitation that becomes recharge'
    }
}
```

---

## 📉 MRC Method (Master Recession Curve)

### **Scientific Basis**
The Master Recession Curve (MRC) method analyzes groundwater recession patterns to estimate recharge. This method assumes that deviations from the master recession curve indicate periods of additional recharge.

### **Theoretical Foundation**
The master recession curve represents the natural decline of groundwater levels in the absence of recharge:
```
dh/dt = -α × h^n
```
Where:
- **h** = Water level above some datum
- **α** = Recession coefficient
- **n** = Recession exponent (typically 1.0-2.0)

### **Algorithm Implementation**

#### **Recession Period Identification**
```python
def identify_recession_periods(water_levels, timestamps, min_duration=72):
    """
    Identify periods of continuous water level decline
    
    Args:
        water_levels: Time series of water level measurements
        timestamps: Corresponding timestamps
        min_duration: Minimum recession duration (hours)
    
    Returns:
        recession_periods: List of recession period data
    """
    recession_periods = []
    current_recession = None
    
    for i in range(1, len(water_levels)):
        current_level = water_levels[i]
        previous_level = water_levels[i-1]
        current_time = timestamps[i]
        
        # Check if water level is declining
        if current_level < previous_level:
            if current_recession is None:
                # Start new recession period
                current_recession = {
                    'start_time': timestamps[i-1],
                    'start_level': previous_level,
                    'levels': [previous_level, current_level],
                    'times': [timestamps[i-1], current_time]
                }
            else:
                # Continue current recession
                current_recession['levels'].append(current_level)
                current_recession['times'].append(current_time)
        else:
            # End current recession if it meets duration criteria
            if current_recession is not None:
                duration = (current_recession['times'][-1] - current_recession['start_time']).total_seconds() / 3600
                
                if duration >= min_duration:
                    current_recession['end_time'] = current_recession['times'][-1]
                    current_recession['end_level'] = current_recession['levels'][-1]
                    current_recession['duration_hours'] = duration
                    current_recession['total_decline'] = current_recession['start_level'] - current_recession['end_level']
                    
                    recession_periods.append(current_recession)
                
                current_recession = None
    
    return recession_periods
```

#### **Master Recession Curve Creation**
```python
def create_master_recession_curve(recession_periods):
    """
    Create master recession curve from multiple recession periods
    
    Args:
        recession_periods: List of recession periods
    
    Returns:
        master_curve: Master recession curve parameters and function
    """
    # Normalize all recession periods to start at h=1.0 and t=0
    normalized_data = []
    
    for period in recession_periods:
        levels = np.array(period['levels'])
        times = np.array([(t - period['start_time']).total_seconds() / 3600 
                         for t in period['times']])
        
        # Normalize levels (h/h0)
        normalized_levels = levels / levels[0]
        
        # Store normalized data
        for i, (t, h) in enumerate(zip(times, normalized_levels)):
            if h > 0:  # Avoid log(0)
                normalized_data.append({'time': t, 'level': h})
    
    # Fit exponential decay curve: h(t) = exp(-α*t^n)
    def recession_function(t, alpha, n):
        return np.exp(-alpha * (t ** n))
    
    # Extract data for curve fitting
    times = [d['time'] for d in normalized_data]
    levels = [d['level'] for d in normalized_data]
    
    # Fit parameters using least squares
    try:
        popt, pcov = curve_fit(recession_function, times, levels, 
                              bounds=([0, 0.5], [1, 3.0]),
                              p0=[0.01, 1.0])
        alpha, n = popt
        
        # Calculate goodness of fit
        predicted = recession_function(np.array(times), alpha, n)
        r_squared = 1 - np.sum((np.array(levels) - predicted)**2) / np.sum((np.array(levels) - np.mean(levels))**2)
        
        return {
            'alpha': alpha,
            'n': n,
            'r_squared': r_squared,
            'function': lambda t: recession_function(t, alpha, n),
            'normalized_data': normalized_data
        }
    
    except Exception as e:
        return {'error': f"Curve fitting failed: {str(e)}"}
```

#### **Recharge Estimation from Deviations**
```python
def calculate_mrc_recharge(water_levels, timestamps, master_curve):
    """
    Calculate recharge based on deviations from master recession curve
    
    Args:
        water_levels: Complete water level time series
        timestamps: Corresponding timestamps
        master_curve: Master recession curve from create_master_recession_curve()
    
    Returns:
        recharge_results: MRC-based recharge estimates
    """
    recharge_events = []
    
    # Find periods where actual levels exceed predicted recession
    for i in range(1, len(water_levels)):
        current_level = water_levels[i]
        current_time = timestamps[i]
        
        # Look back to find last recession peak
        recession_start_idx = find_last_recession_peak(water_levels, i)
        
        if recession_start_idx is not None:
            # Calculate time since recession started
            time_since_peak = (current_time - timestamps[recession_start_idx]).total_seconds() / 3600
            
            # Predict level using master curve
            initial_level = water_levels[recession_start_idx]
            predicted_ratio = master_curve['function'](time_since_peak)
            predicted_level = initial_level * predicted_ratio
            
            # Calculate deviation
            deviation = current_level - predicted_level
            
            # If deviation is positive and significant, consider it recharge
            if deviation > 0.05:  # 0.05 feet threshold
                # Convert deviation to recharge
                specific_yield = 0.15  # Default value, should be configurable
                recharge_inches = deviation * 12 * specific_yield
                
                recharge_events.append({
                    'time': current_time,
                    'predicted_level': predicted_level,
                    'actual_level': current_level,
                    'deviation_feet': deviation,
                    'recharge_inches': recharge_inches,
                    'time_since_peak_hours': time_since_peak
                })
    
    # Aggregate annual recharge
    total_recharge = sum(event['recharge_inches'] for event in recharge_events)
    
    return {
        'events': recharge_events,
        'total_annual_recharge_inches': total_recharge,
        'master_curve_parameters': {
            'alpha': master_curve['alpha'],
            'n': master_curve['n'],
            'r_squared': master_curve['r_squared']
        },
        'number_of_events': len(recharge_events)
    }
```

---

## ⚡ ERC Method (Enhanced Recharge Calculation)

### **Scientific Basis**
The Enhanced Recharge Calculation (ERC) method combines elements of both RISE and MRC methods while incorporating additional factors such as precipitation timing, soil moisture, and seasonal variations.

### **Algorithm Implementation**

#### **Multi-Factor Recharge Analysis**
```python
def calculate_erc_recharge(water_levels, timestamps, precipitation_data=None, 
                          soil_data=None, parameters=None):
    """
    Enhanced recharge calculation using multiple factors
    
    Args:
        water_levels: Water level time series
        timestamps: Corresponding timestamps
        precipitation_data: Optional precipitation data
        soil_data: Optional soil moisture data
        parameters: ERC-specific parameters
    
    Returns:
        erc_results: Enhanced recharge calculations
    """
    if parameters is None:
        parameters = ERC_DEFAULT_PARAMETERS
    
    # Step 1: Basic RISE calculation
    rise_events = detect_recharge_events(water_levels, timestamps)
    
    # Step 2: Recession analysis for baseline
    recession_periods = identify_recession_periods(water_levels, timestamps)
    master_curve = create_master_recession_curve(recession_periods)
    
    # Step 3: Enhanced analysis with additional factors
    enhanced_events = []
    
    for event in rise_events:
        enhanced_event = dict(event)
        
        # Factor 1: Precipitation correlation
        if precipitation_data:
            precip_correlation = correlate_with_precipitation(
                event, precipitation_data, parameters['precip_window_hours']
            )
            enhanced_event['precipitation_correlation'] = precip_correlation
            enhanced_event['precipitation_efficiency'] = calculate_precip_efficiency(
                event['recharge_inches'], precip_correlation['total_precip']
            )
        
        # Factor 2: Seasonal adjustment
        seasonal_factor = calculate_seasonal_factor(
            event['start_time'], parameters['seasonal_factors']
        )
        enhanced_event['seasonal_factor'] = seasonal_factor
        
        # Factor 3: Antecedent conditions
        antecedent_conditions = analyze_antecedent_conditions(
            water_levels, timestamps, event['start_time'], 
            parameters['antecedent_period_days']
        )
        enhanced_event['antecedent_conditions'] = antecedent_conditions
        
        # Factor 4: Soil moisture influence (if available)
        if soil_data:
            soil_influence = analyze_soil_moisture_influence(
                event, soil_data, parameters['soil_influence_weight']
            )
            enhanced_event['soil_moisture_factor'] = soil_influence
        
        # Calculate enhanced recharge estimate
        base_recharge = event['recharge_inches']
        enhancement_factor = (
            seasonal_factor * 
            antecedent_conditions['adjustment_factor'] *
            (soil_influence if soil_data else 1.0)
        )
        
        enhanced_event['enhanced_recharge_inches'] = base_recharge * enhancement_factor
        enhanced_event['enhancement_factor'] = enhancement_factor
        
        enhanced_events.append(enhanced_event)
    
    # Calculate uncertainty estimates
    uncertainty_analysis = calculate_uncertainty(enhanced_events, parameters)
    
    return {
        'events': enhanced_events,
        'total_annual_recharge_inches': sum(e['enhanced_recharge_inches'] for e in enhanced_events),
        'uncertainty_analysis': uncertainty_analysis,
        'method_comparison': {
            'rise_total': sum(e['recharge_inches'] for e in enhanced_events),
            'erc_total': sum(e['enhanced_recharge_inches'] for e in enhanced_events),
            'enhancement_ratio': sum(e['enhancement_factor'] for e in enhanced_events) / len(enhanced_events)
        }
    }
```

#### **Precipitation Correlation Analysis**
```python
def correlate_with_precipitation(recharge_event, precipitation_data, window_hours=48):
    """
    Correlate recharge events with precipitation data
    
    Args:
        recharge_event: Single recharge event
        precipitation_data: Precipitation time series
        window_hours: Time window to consider before event (hours)
    
    Returns:
        correlation_results: Precipitation correlation analysis
    """
    event_start = recharge_event['start_time']
    window_start = event_start - timedelta(hours=window_hours)
    
    # Find precipitation within time window
    relevant_precip = []
    for precip_record in precipitation_data:
        if window_start <= precip_record['timestamp'] <= event_start:
            relevant_precip.append(precip_record)
    
    if not relevant_precip:
        return {'total_precip': 0, 'max_intensity': 0, 'correlation_strength': 0}
    
    # Calculate precipitation statistics
    total_precip = sum(p['amount'] for p in relevant_precip)
    max_intensity = max(p['intensity'] for p in relevant_precip)
    
    # Calculate lag time (time between precipitation peak and water level response)
    precip_peak_time = max(relevant_precip, key=lambda x: x['intensity'])['timestamp']
    lag_hours = (event_start - precip_peak_time).total_seconds() / 3600
    
    # Estimate correlation strength based on lag time and amounts
    correlation_strength = calculate_correlation_strength(
        total_precip, max_intensity, lag_hours, recharge_event['total_rise']
    )
    
    return {
        'total_precip': total_precip,
        'max_intensity': max_intensity,
        'lag_hours': lag_hours,
        'correlation_strength': correlation_strength,
        'precipitation_events': len(relevant_precip)
    }
```

### **Parameter Configuration**
```python
ERC_DEFAULT_PARAMETERS = {
    'specific_yield': 0.15,
    'precip_window_hours': 48,
    'antecedent_period_days': 30,
    'seasonal_factors': {
        'spring': 1.2,  # Higher recharge efficiency
        'summer': 0.8,  # Lower due to ET
        'fall': 1.1,    # Moderate efficiency
        'winter': 1.0   # Baseline
    },
    'soil_influence_weight': 0.3,
    'uncertainty_factors': {
        'measurement_error': 0.05,
        'parameter_uncertainty': 0.15,
        'method_uncertainty': 0.10
    }
}
```

---

## 📊 Method Comparison and Validation

### **Cross-Method Validation**
```python
def compare_recharge_methods(water_levels, timestamps, validation_data=None):
    """
    Compare results from all three recharge calculation methods
    
    Args:
        water_levels: Water level time series
        timestamps: Corresponding timestamps
        validation_data: Optional validation data for comparison
    
    Returns:
        comparison_results: Comprehensive method comparison
    """
    # Calculate recharge using all three methods
    rise_results = calculate_rise_recharge(
        detect_recharge_events(water_levels, timestamps)
    )
    
    recession_periods = identify_recession_periods(water_levels, timestamps)
    master_curve = create_master_recession_curve(recession_periods)
    mrc_results = calculate_mrc_recharge(water_levels, timestamps, master_curve)
    
    erc_results = calculate_erc_recharge(water_levels, timestamps)
    
    # Statistical comparison
    comparison = {
        'annual_recharge_inches': {
            'RISE': rise_results['total_annual_recharge_inches'],
            'MRC': mrc_results['total_annual_recharge_inches'],
            'ERC': erc_results['total_annual_recharge_inches']
        },
        'number_of_events': {
            'RISE': rise_results['number_of_events'],
            'MRC': mrc_results['number_of_events'],
            'ERC': erc_results['number_of_events']
        },
        'statistics': {
            'mean': np.mean([
                rise_results['total_annual_recharge_inches'],
                mrc_results['total_annual_recharge_inches'],
                erc_results['total_annual_recharge_inches']
            ]),
            'std_dev': np.std([
                rise_results['total_annual_recharge_inches'],
                mrc_results['total_annual_recharge_inches'],
                erc_results['total_annual_recharge_inches']
            ]),
            'coefficient_of_variation': None  # Calculated below
        }
    }
    
    # Calculate coefficient of variation
    mean_recharge = comparison['statistics']['mean']
    if mean_recharge > 0:
        comparison['statistics']['coefficient_of_variation'] = (
            comparison['statistics']['std_dev'] / mean_recharge
        )
    
    # Method reliability assessment
    comparison['reliability_assessment'] = assess_method_reliability(
        rise_results, mrc_results, erc_results, validation_data
    )
    
    return comparison
```

### **Uncertainty Analysis**
```python
def calculate_uncertainty(recharge_results, parameters):
    """
    Calculate uncertainty bounds for recharge estimates
    
    Args:
        recharge_results: Recharge calculation results
        parameters: Method parameters including uncertainty factors
    
    Returns:
        uncertainty_bounds: Upper and lower confidence intervals
    """
    base_recharge = sum(event['enhanced_recharge_inches'] for event in recharge_results['events'])
    
    # Sources of uncertainty
    measurement_error = parameters['uncertainty_factors']['measurement_error']
    parameter_uncertainty = parameters['uncertainty_factors']['parameter_uncertainty']
    method_uncertainty = parameters['uncertainty_factors']['method_uncertainty']
    
    # Combined uncertainty (assuming independence)
    total_uncertainty = np.sqrt(
        measurement_error**2 + 
        parameter_uncertainty**2 + 
        method_uncertainty**2
    )
    
    # Calculate confidence intervals (95%)
    confidence_interval = 1.96 * total_uncertainty * base_recharge
    
    return {
        'total_recharge': base_recharge,
        'uncertainty_percentage': total_uncertainty * 100,
        'confidence_interval_inches': confidence_interval,
        'lower_bound': base_recharge - confidence_interval,
        'upper_bound': base_recharge + confidence_interval,
        'uncertainty_sources': {
            'measurement': measurement_error * 100,
            'parameters': parameter_uncertainty * 100,
            'method': method_uncertainty * 100
        }
    }
```

---

## 🎯 Best Practices and Recommendations

### **Method Selection Guidelines**
1. **RISE Method**: 
   - Best for wells with clear, distinct recharge events
   - Requires good quality, high-frequency data
   - Most reliable in areas with episodic recharge

2. **MRC Method**:
   - Suitable for wells with consistent recession patterns
   - Good for areas with more continuous recharge
   - Requires long-term data for reliable master curve

3. **ERC Method**:
   - Most comprehensive but requires additional data
   - Best when precipitation and climate data available
   - Provides most robust uncertainty estimates

### **Quality Control Recommendations**
- **Data Quality**: Ensure high-quality, barometrically compensated data
- **Manual Validation**: Cross-check automated calculations with manual readings
- **Parameter Sensitivity**: Test sensitivity to key parameters
- **Regional Calibration**: Calibrate methods using local validation data
- **Multiple Methods**: Use multiple methods for cross-validation

### **Reporting Standards**
- **Method Documentation**: Clearly document which method(s) used
- **Parameter Values**: Report all parameter values and assumptions
- **Uncertainty Bounds**: Include uncertainty estimates in all reports
- **Data Quality**: Document data quality and limitations
- **Validation**: Include validation against independent measurements where available

---

**Next Steps**: Continue to [File Formats](file_formats.md) to understand the data formats used throughout the system.