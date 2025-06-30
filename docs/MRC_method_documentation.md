# MRC Method Documentation

## Overview

The MRC (Master Recession Curve) method, also known as EMR (Episodic Master Recession), estimates groundwater recharge by identifying deviations from a fitted recession curve. This USGS-developed method is particularly effective for analyzing continuous water level data to identify episodic recharge events.

## Theory

The MRC method is based on the principle that groundwater levels follow predictable recession patterns during periods without recharge. The method:

1. **Identifies recession segments** from continuous water level data
2. **Fits a master recession curve** to these segments
3. **Calculates predicted water levels** based on the curve
4. **Identifies positive deviations** as potential recharge events

### Mathematical Models

The method supports three curve types:

#### Exponential Model
```
Q(t) = Q₀ × e^(-a×t)
```
- Q₀: Initial discharge/level
- a: Recession coefficient
- t: Time since recession start

#### Power Law Model
```
Q(t) = Q₀ × t^(-b)
```
- Q₀: Initial discharge/level
- b: Power law exponent
- t: Time since recession start

#### Linear Model
```
ln(Q) = intercept + slope × t
```
- Linear regression on log-transformed data

### Recharge Calculation

```
Recharge (inches) = Deviation (feet) × Specific Yield × 12
```

Where deviation = Observed Level - Predicted Level

## Method Parameters

### Recession Identification

1. **Minimum Recession Length** (5-30 days)
   - USGS recommends 10+ days minimum
   - Ensures statistical significance of recession segments
   - Longer periods improve curve fit reliability

2. **Fluctuation Tolerance** (0.001-0.1 ft)
   - USGS EMR parameter allowing small upticks during recession
   - Default: 0.01 ft (accounts for measurement noise)
   - Set to 0 for strict declining-only recession

3. **Precipitation Tolerance** (0-1.0 inches)
   - Maximum precipitation allowed during recession
   - Set to 0 for no precipitation tolerance
   - Site-specific based on aquifer response time

4. **Post-Precipitation Lag** (0-7 days)
   - Days to wait after precipitation before recession can start
   - USGS recommends 2-3 days typical
   - Accounts for travel time through unsaturated zone

### Curve Fitting Parameters

1. **Curve Type Selection**
   - Exponential: Most common for natural recession
   - Power Law: Alternative for complex aquifer systems
   - Linear: Simplified approach on log-transformed data

2. **R² Threshold**
   - Goodness of fit indicator for curve quality
   - Minimum 0.7 recommended for reliable curves
   - Higher values indicate better recession characterization

### Recharge Detection

1. **Specific Yield** (0.01-0.35)
   - Fraction of aquifer volume draining by gravity
   - Typical range for unconfined aquifers
   - Critical parameter affecting recharge magnitude

2. **Deviation Threshold** (0.01-0.5 ft)
   - Minimum positive deviation to qualify as recharge
   - Filters measurement noise and small variations
   - Higher values = fewer, larger events detected

### Water Year Configuration

- **Start Month/Day**: Define hydrologic year boundaries
- **Default**: October 1 (standard in many regions)
- **Customizable**: Based on local climate patterns

## Workflow

### Step 1: Data Preparation
1. Select well with continuous monitoring data
2. Configure preprocessing (daily median recommended)
3. Perform data quality checks
4. Preview processed data for completeness

### Step 2: Recession Segment Identification
1. Set minimum recession length (start with 10 days)
2. Configure fluctuation tolerance (0.01 ft default)
3. Click "Identify Segments"
4. Review identified segments in table
5. Select/deselect segments for curve fitting

### Step 3: Master Recession Curve Fitting
1. Choose curve type (exponential recommended)
2. Click "Fit Curve"
3. Review R² value and equation
4. Save curve to database if satisfactory

### Step 4: Recharge Calculation
1. Set specific yield and deviation threshold
2. Click "Calculate Recharge"
3. Review results in Results tab
4. Analyze yearly summaries and statistics

### Step 5: Analysis and Export
1. Compare different curves if available
2. Export results to CSV or Excel
3. Save calculation to database
4. Generate comparison plots

## USGS EMR Compliance

This implementation follows USGS EMR guidelines:

### Data Requirements
- **Continuous monitoring**: Daily or sub-daily frequency
- **Minimum duration**: At least 1 year for curve development
- **Data quality**: Gaps < 5% of record preferred

### Methodological Standards
- **Fluctuation tolerance**: Small upticks allowed during recession
- **Minimum segment length**: 10+ days recommended
- **Statistical validation**: R² values for curve quality assessment

### Parameter Determination
- **Site-specific calibration**: Parameters determined through iterative analysis
- **Consistency**: Same parameters used for all analyses at a site
- **Documentation**: Parameter rationale and sensitivity analysis

## Results Interpretation

### Curve Quality Indicators

1. **R² Values**
   - > 0.9: Excellent fit
   - 0.7-0.9: Good fit
   - < 0.7: Poor fit, consider different approach

2. **Number of Segments**
   - More segments generally improve curve reliability
   - Minimum 3-5 segments recommended
   - Too few may indicate inadequate data or parameters

### Event Characteristics

1. **Recharge Event Distribution**
   - Events should correlate with precipitation patterns
   - Frequency depends on climate and aquifer properties
   - Magnitude should be realistic for local conditions

2. **Temporal Patterns**
   - Seasonal clustering expected in most climates
   - Multi-year averages more reliable than individual years
   - Compare with regional recharge studies

### Quality Control

1. **Physical Plausibility**
   - Compare total recharge with precipitation
   - Check against regional water balance studies
   - Validate large events with precipitation records

2. **Method Comparison**
   - Compare with RISE method results
   - Cross-validate with other recharge estimation techniques
   - Assess consistency across parameter variations

## Best Practices

### Curve Development

1. **Use multiple years** of data for curve fitting
2. **Start with exponential model** unless site-specific reasons exist
3. **Validate curve parameters** with independent data
4. **Document parameter selection** rationale

### Recharge Analysis

1. **Apply consistent parameters** across time periods
2. **Perform sensitivity analysis** on key parameters
3. **Validate results** against precipitation and other data
4. **Compare multiple methods** when possible

### Data Management

1. **Save high-quality curves** to database for reuse
2. **Document analysis decisions** and parameter choices
3. **Export detailed results** for external analysis
4. **Maintain analysis history** for reproducibility

## Limitations

### Method Assumptions
- Natural recession follows predictable patterns
- All positive deviations represent recharge
- Recession curve parameters remain constant
- Negligible effects from pumping, barometric pressure

### Data Requirements
- Continuous, high-frequency monitoring needed
- Sensitive to measurement precision and drift
- Requires sufficient recession periods for curve development
- May be affected by nearby anthropogenic influences

### Environmental Factors
- Less effective in highly variable aquifer systems
- May struggle with multiple porosity or fractured systems
- Assumes simple aquifer response to recharge
- Climate-dependent recession characteristics

## Troubleshooting

### Common Issues

1. **Poor Curve Fits (Low R²)**
   - Increase minimum recession length
   - Apply more aggressive data smoothing
   - Try different curve types
   - Check for data quality issues

2. **Too Few Recession Segments**
   - Decrease minimum recession length
   - Increase fluctuation tolerance
   - Check precipitation tolerance settings
   - Verify data completeness

3. **Unrealistic Recharge Values**
   - Verify specific yield estimate
   - Check deviation threshold setting
   - Compare with precipitation totals
   - Validate curve parameters

4. **Inconsistent Results**
   - Ensure consistent parameter application
   - Check for temporal changes in aquifer response
   - Validate data quality across entire period
   - Consider external influences

### Data Quality Issues

1. **Gaps and Missing Data**
   - Gap-fill using interpolation if < 1 day
   - Exclude periods with significant gaps
   - Document data completeness for each analysis

2. **Measurement Drift**
   - Apply drift correction if available
   - Use relative changes rather than absolute levels
   - Compare with nearby monitoring wells

3. **External Influences**
   - Identify and exclude pumping effects
   - Account for barometric pressure variations
   - Consider surface water interactions

## References

### Primary Sources
- Nimmo, J.R., Horowitz, C., and Mitchell, L., 2015, Discrete-storm water-table fluctuation method to estimate episodic recharge: Groundwater, v. 53, no. 2.
- Heppner, C.S., and Nimmo, J.R., 2005, A computer program for predicting recharge with a master recession curve: USGS Scientific Investigations Report 2005-5172.

### Supporting Literature
- USGS EMR Method Guidelines: https://wwwrcamnl.wr.usgs.gov/uzf/EMR_Method/
- Healy, R.W., and Cook, P.G., 2002, Using groundwater levels to estimate recharge: Hydrogeology Journal, v. 10, p. 91-109.