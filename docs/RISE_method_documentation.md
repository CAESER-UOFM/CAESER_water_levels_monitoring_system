# RISE Method Documentation

## Overview

The RISE (Rainfall-Induced Surge Estimation) method estimates groundwater recharge by analyzing water table fluctuations in response to precipitation events. This method is particularly effective for unconfined aquifers where water levels respond directly to surface recharge.

## Theory

The RISE method identifies discrete water level rises above the antecedent recession curve and attributes these rises to recharge events. The calculation follows these key principles:

- **Antecedent Recession**: The expected water level if no recharge occurred
- **Water Level Rise**: The difference between observed and antecedent levels
- **Specific Yield**: The fraction of aquifer volume that drains by gravity

### Mathematical Formula

```
Recharge (inches) = Water Level Rise (feet) × Specific Yield × 12
```

## Method Parameters

### Core Parameters

1. **Specific Yield** (0.01-0.35)
   - Typical values for unconfined aquifers
   - Controls conversion from water level change to recharge volume
   - Site-specific parameter requiring field determination

2. **Rise Threshold** (0.01-0.5 ft)
   - Minimum water level rise to qualify as recharge event
   - Filters out measurement noise and minor fluctuations
   - Higher values = fewer, larger events detected

3. **Antecedent Period** (1-30 days)
   - Number of days to look back for recession baseline
   - Longer periods smooth out short-term variations
   - Shorter periods capture rapid changes

### Water Year Settings

- **Start Month/Day**: Define water year boundaries (default: October 1)
- **Analysis Period**: Select specific water years for calculation

### Data Processing

1. **Downsampling Options**:
   - None (raw 15-minute data)
   - Hourly (1h intervals)
   - Daily (recommended for RISE method)

2. **Downsampling Methods**:
   - Mean: Average values over period
   - Median: Middle value (reduces outlier effects)
   - Last: End-of-period value

3. **Smoothing Options**:
   - Moving Average: Reduces high-frequency noise
   - Window Size: 3-30 data points

## Workflow

### Step 1: Data Preparation
1. Select well from main data table
2. Choose water years for analysis
3. Configure preprocessing (daily median recommended)
4. Preview processed data

### Step 2: Parameter Configuration
1. Set specific yield (start with 0.2 for sandy soils)
2. Adjust rise threshold based on data noise
3. Set antecedent period (7-14 days typical)

### Step 3: Calculate Recharge
1. Click "Calculate RISE"
2. Review identified events in Results tab
3. Check yearly summaries and statistics

### Step 4: Analysis and Export
1. Review temporal distribution of events
2. Compare with precipitation records if available
3. Export results to CSV or Excel
4. Save calculation to database for future reference

## Results Interpretation

### Event-Level Results
- **Event Date**: When water level rise occurred
- **Rise Amount**: Magnitude of water level increase (ft)
- **Recharge Value**: Calculated recharge (inches)
- **Antecedent Level**: Baseline level before rise

### Annual Summaries
- **Total Recharge**: Sum of all events in water year
- **Number of Events**: Count of recharge episodes
- **Maximum Rise**: Largest single event
- **Annual Rate**: Total recharge per year

### Quality Indicators
- **R² Value**: Goodness of fit for antecedent curve
- **Event Distribution**: Temporal spacing of events
- **Rise Magnitude Range**: Variability in event sizes

## Best Practices

### Data Requirements
- Continuous water level monitoring (15-minute to hourly)
- Minimum 1 year of data for meaningful analysis
- Unconfined aquifer conditions preferred
- Co-located precipitation data helpful for validation

### Parameter Selection
1. **Start with literature values** for specific yield by soil type
2. **Calibrate rise threshold** to match expected event frequency
3. **Adjust antecedent period** based on aquifer response time
4. **Compare with other methods** when possible

### Quality Control
- Check for data gaps and measurement errors
- Validate events against precipitation records
- Compare results across different parameter sets
- Review outlier events for physical plausibility

## Limitations

### Method Limitations
- Assumes all water level rises are due to recharge
- May include non-recharge factors (barometric effects, pumping)
- Requires estimate of specific yield
- Less effective in confined aquifers

### Data Requirements
- Needs high-frequency, continuous monitoring
- Sensitive to measurement precision and drift
- May be affected by nearby pumping or surface water

### Environmental Factors
- Works best in areas with distinct wet/dry periods
- Less suitable for constant recharge conditions
- May underestimate during prolonged wet periods

## Troubleshooting

### Common Issues

1. **Too Many Small Events**
   - Increase rise threshold
   - Apply more aggressive smoothing
   - Check for measurement noise

2. **Too Few Events**
   - Decrease rise threshold
   - Reduce antecedent period
   - Check data quality and gaps

3. **Unrealistic Recharge Values**
   - Verify specific yield estimate
   - Check units and conversions
   - Compare with regional studies

4. **Poor Antecedent Curve Fit**
   - Adjust antecedent period length
   - Apply data smoothing
   - Check for data quality issues

### Data Quality Checks
- Verify timestamp continuity
- Check for negative or zero water levels
- Identify and handle data gaps
- Remove obvious measurement errors

## References

- Healy, R.W., and Cook, P.G., 2002, Using groundwater levels to estimate recharge: Hydrogeology Journal, v. 10, p. 91-109.
- Sophocleous, M.A., 1991, Combining the soilwater balance and water-level fluctuation methods to estimate natural groundwater recharge: Practical aspects: Journal of Hydrology, v. 124, p. 229-241.