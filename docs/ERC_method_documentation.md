# ERC Method Documentation

## Overview

The ERC (Extended Recession Curve) method is an advanced variant of the Master Recession Curve (MRC) approach that estimates groundwater recharge through enhanced temporal analysis of recession characteristics. This method extends traditional recession curve analysis by incorporating seasonal variability, multiple curve fitting approaches, and cross-validation techniques to provide more robust recharge estimates.

## Theory

The ERC method builds upon the MRC foundation with several key enhancements:

1. **Temporal Variability Analysis**: Examines how recession characteristics change seasonally and annually
2. **Multiple Curve Types**: Supports exponential, power law, polynomial, and multi-segment curve fitting
3. **Cross-Validation**: Implements statistical validation to assess curve reliability
4. **Quality Scoring**: Provides quantitative assessment of event and calculation quality
5. **Enhanced Recession Identification**: Uses improved algorithms with fluctuation tolerance

### Mathematical Models

The ERC method supports four primary curve types:

#### Exponential Model
```
Q(t) = Q₀ × e^(-a×t)
```
- Q₀: Initial discharge/level
- a: Recession coefficient
- t: Time since recession start

#### Power Law Model
```
Q(t) = Q₀ × (t + 0.001)^(-b)
```
- Q₀: Initial discharge/level
- b: Power law exponent
- t: Time since recession start (offset prevents division by zero)

#### Polynomial Model
```
Q(t) = c₀ + c₁×t + c₂×t² + ... + cₙ×tⁿ
```
- cᵢ: Polynomial coefficients
- n: Polynomial degree (typically 2-4)

#### Multi-Segment Model
```
Q(t) = Qᵢ(t) for segment i, where i = f(seasonal_period)
```
- Different curve parameters for different temporal periods
- Allows for seasonal variations in recession behavior

### Recharge Calculation

```
Recharge (inches) = Deviation (feet) × Specific Yield × 12
```

Where deviation = Observed Level - Predicted Level

### Quality Scoring System

The ERC method includes a comprehensive quality scoring framework:

#### Event Quality Score (0-1)
- Deviation magnitude relative to threshold
- Consistency with seasonal patterns
- Validation against cross-validation curve
- Confidence based on local curve fit quality

#### Calculation Quality Score (0-1)
- Overall R² of master curve
- Number and distribution of recession segments
- Cross-validation performance
- Temporal consistency of results

## Method Parameters

### Enhanced Recession Identification

1. **Minimum Recession Length** (5-30 days)
   - Default: 10 days
   - Ensures statistical significance
   - USGS EMR compliance

2. **Fluctuation Tolerance** (0.001-0.1 ft)
   - Default: 0.01 ft
   - USGS EMR parameter for small upticks
   - Accounts for measurement noise

3. **Precipitation Tolerance** (0-1.0 inches)
   - Maximum precipitation during recession
   - Default: 0 inches (no precipitation)
   - Site-specific calibration

4. **Post-Precipitation Lag** (0-7 days)
   - Waiting period after precipitation
   - Default: 2 days
   - Accounts for unsaturated zone travel time

### Curve Fitting Parameters

1. **Primary Curve Type**
   - Exponential (recommended default)
   - Power Law (for complex systems)
   - Polynomial (flexible fitting)
   - Multi-Segment (seasonal variations)

2. **Cross-Validation Method**
   - K-Fold (default: k=5)
   - Leave-One-Out
   - Temporal Split
   - Random Sampling

3. **Seasonal Analysis**
   - Enable/disable seasonal curve fitting
   - Season definitions (meteorological vs. hydrological)
   - Minimum segments per season

### Quality Control Parameters

1. **R² Thresholds**
   - Master Curve: 0.7 minimum
   - Cross-Validation: 0.6 minimum
   - Seasonal Curves: 0.5 minimum

2. **Statistical Validation**
   - Outlier detection and removal
   - Residual analysis
   - Confidence interval calculation

### Recharge Detection

1. **Specific Yield** (0.01-0.35)
   - Aquifer-specific parameter
   - Controls recharge magnitude calculation
   - Critical for accurate estimates

2. **Deviation Threshold** (0.01-0.5 ft)
   - Minimum positive deviation for recharge
   - Filters measurement noise
   - Higher values = fewer, larger events

3. **Event Validation**
   - Cross-validation against alternative curves
   - Seasonal consistency checks
   - Magnitude plausibility assessment

## Workflow

### Step 1: Data Preparation and Quality Assessment
1. Select well with continuous monitoring data (≥1 year recommended)
2. Configure preprocessing (daily median recommended)
3. Perform comprehensive data quality checks
4. Preview processed data for completeness and patterns
5. Identify potential data issues or gaps

### Step 2: Enhanced Recession Segment Identification
1. Set minimum recession length (start with 10 days)
2. Configure fluctuation tolerance (0.01 ft default)
3. Set precipitation tolerance and lag parameters
4. Click "Identify Segments" with enhanced algorithm
5. Review identified segments in detailed table
6. Assess seasonal distribution of segments
7. Select/deselect segments based on quality criteria

### Step 3: Multiple Curve Fitting and Cross-Validation
1. Choose primary curve type (exponential recommended)
2. Enable cross-validation (k-fold recommended)
3. Configure seasonal analysis if desired
4. Click "Fit Curves" for comprehensive analysis
5. Review multiple curve fits and statistics
6. Examine cross-validation results and R² values
7. Assess seasonal curve variations if applicable
8. Save high-quality curves to database

### Step 4: Enhanced Recharge Calculation
1. Set specific yield and deviation threshold
2. Configure event validation parameters
3. Click "Calculate Recharge" with quality scoring
4. Review results with quality indicators
5. Examine event-level confidence scores
6. Analyze temporal distribution and patterns
7. Review cross-validation consistency

### Step 5: Temporal Analysis and Quality Assessment
1. Examine seasonal analysis results if performed
2. Review temporal consistency of recharge patterns
3. Assess calculation quality scores
4. Compare different curve approaches
5. Validate against expected patterns
6. Document parameter selection rationale

### Step 6: Export and Documentation
1. Export detailed results to CSV or Excel
2. Include quality scores and validation metrics
3. Save calculation with full metadata
4. Generate comprehensive analysis reports
5. Document methodology and parameter choices

## Advanced Features

### Seasonal Analysis

The ERC method can perform detailed seasonal analysis:

1. **Seasonal Curve Fitting**
   - Separate recession curves for each season
   - Comparison of seasonal recession characteristics
   - Assessment of temporal stability

2. **Temporal Periods**
   - Annual: Year-by-year analysis
   - Seasonal: Spring, Summer, Fall, Winter
   - Monthly: Month-by-month variations
   - Custom: User-defined periods

3. **Variability Assessment**
   - Coefficient of variation across periods
   - Trend analysis in recession parameters
   - Statistical significance testing

### Cross-Validation Approaches

1. **K-Fold Cross-Validation**
   - Randomly divide segments into k groups
   - Train on k-1 groups, validate on remaining
   - Average performance across all folds

2. **Temporal Cross-Validation**
   - Split segments by time periods
   - Train on early periods, validate on later
   - Assess temporal stability of curves

3. **Leave-One-Out Validation**
   - Remove one segment at a time
   - Fit curve on remaining segments
   - Validate against removed segment

### Multi-Segment Curve Fitting

1. **Automatic Breakpoint Detection**
   - Statistical methods to identify optimal segments
   - Minimum segment size requirements
   - Continuity constraints at breakpoints

2. **Seasonal Breakpoints**
   - Pre-defined seasonal boundaries
   - Climate-based period definitions
   - Site-specific temporal patterns

3. **Quality Assessment**
   - Comparison with single-curve approaches
   - Information criteria for model selection
   - Residual analysis across segments

## Results Interpretation

### Curve Quality Indicators

1. **Master Curve Statistics**
   - R² Values: >0.9 excellent, 0.7-0.9 good, <0.7 poor
   - Cross-validation R²: Should be within 0.1 of training R²
   - Residual patterns: Check for systematic bias

2. **Segment Distribution**
   - Temporal coverage: Even distribution preferred
   - Seasonal representation: All seasons represented
   - Length distribution: Mix of short and long segments

3. **Validation Metrics**
   - Cross-validation consistency
   - Prediction interval coverage
   - Outlier identification and handling

### Event Quality Assessment

1. **Individual Event Scores**
   - High scores (>0.8): High confidence events
   - Medium scores (0.5-0.8): Moderate confidence
   - Low scores (<0.5): Questionable events

2. **Temporal Patterns**
   - Seasonal clustering: Expected in most climates
   - Event frequency: Should correlate with precipitation
   - Magnitude distribution: Log-normal typical

3. **Validation Indicators**
   - Cross-validation consistency: Events detected by multiple curves
   - Seasonal appropriateness: Events match expected timing
   - Physical plausibility: Reasonable magnitudes and rates

### Calculation Quality Metrics

1. **Overall Assessment**
   - Quality score >0.8: High confidence calculation
   - Quality score 0.6-0.8: Moderate confidence
   - Quality score <0.6: Low confidence, consider revision

2. **Component Scores**
   - Curve fit quality: Master curve R² and validation
   - Event detection quality: Average event confidence
   - Temporal consistency: Stability across time periods

## Best Practices

### Curve Development

1. **Use multiple years** of data for robust curve fitting
2. **Start with exponential model** unless site-specific evidence suggests alternatives
3. **Enable cross-validation** to assess curve reliability
4. **Perform seasonal analysis** if sufficient data available
5. **Document all parameter choices** and rationale

### Temporal Analysis

1. **Examine seasonal variations** in recession characteristics
2. **Assess long-term trends** in curve parameters
3. **Compare different temporal periods** for consistency
4. **Validate temporal patterns** against known climate drivers

### Quality Control

1. **Use quality scores** to filter reliable results
2. **Validate high-magnitude events** against precipitation records
3. **Compare multiple curve approaches** when possible
4. **Document uncertainty** and confidence levels

### Parameter Optimization

1. **Perform sensitivity analysis** on key parameters
2. **Use cross-validation** to guide parameter selection
3. **Compare with independent validation data** when available
4. **Iterate parameters** based on quality indicators

## Limitations

### Method Assumptions

- Recession characteristics remain relatively stable over analysis period
- All positive deviations represent recharge (no pumping/other influences)
- Master recession curve adequately represents natural recession
- Cross-validation provides reliable uncertainty estimates

### Data Requirements

- Continuous, high-frequency monitoring (preferably ≥15-minute intervals)
- Minimum 1 year of data (2+ years preferred for seasonal analysis)
- Sufficient recession periods for robust curve development
- Good data quality with minimal gaps or measurement errors

### Environmental Limitations

- Less effective in highly variable or complex aquifer systems
- May struggle with multiple porosity or heavily fractured systems
- Assumes relatively simple aquifer response to recharge
- Limited applicability in areas with strong anthropogenic influences

### Computational Considerations

- More computationally intensive than basic MRC method
- Requires sufficient data for meaningful cross-validation
- Seasonal analysis requires adequate data in each season
- Quality scoring adds complexity to interpretation

## Troubleshooting

### Common Issues

1. **Poor Cross-Validation Performance**
   - Check data quality and temporal distribution
   - Verify sufficient segments for validation
   - Consider simpler curve models
   - Examine residual patterns for systematic bias

2. **Low Overall Quality Scores**
   - Review parameter selection and curve fitting
   - Check data preprocessing and cleaning
   - Consider alternative curve types
   - Examine temporal stability of results

3. **Inconsistent Seasonal Results**
   - Verify adequate data in each season
   - Check for systematic temporal changes
   - Consider external influences (climate, land use)
   - Review seasonal boundary definitions

4. **Unrealistic Event Magnitudes**
   - Verify specific yield estimates
   - Check deviation threshold settings
   - Review curve fitting quality
   - Compare with precipitation records

### Data Quality Issues

1. **Insufficient Cross-Validation Data**
   - Extend analysis period if possible
   - Use simpler validation approaches
   - Increase minimum recession length carefully
   - Consider temporal split validation

2. **Poor Temporal Coverage**
   - Identify and fill critical data gaps
   - Adjust analysis period to maximize coverage
   - Use weighted validation approaches
   - Document limitations clearly

3. **Systematic Measurement Issues**
   - Apply drift correction if available
   - Use relative changes rather than absolute levels
   - Compare with nearby monitoring wells
   - Document data quality limitations

## Advanced Applications

### Comparative Analysis

1. **Multi-Method Comparison**
   - Compare ERC results with RISE and standard MRC
   - Assess consistency across different approaches
   - Identify method-specific biases or limitations

2. **Parameter Sensitivity**
   - Systematic variation of key parameters
   - Uncertainty propagation analysis
   - Robust parameter selection criteria

3. **Climate Correlation**
   - Compare recharge patterns with climate indices
   - Assess long-term trends and variability
   - Evaluate method performance under different conditions

### Integration with Other Data

1. **Precipitation Validation**
   - Correlate events with precipitation records
   - Assess lag times and response characteristics
   - Validate magnitude relationships

2. **Regional Studies**
   - Compare with nearby wells and regional estimates
   - Assess spatial variability and consistency
   - Contribute to regional water balance studies

## References

### Primary Sources
- Nimmo, J.R., Horowitz, C., and Mitchell, L., 2015, Discrete-storm water-table fluctuation method to estimate episodic recharge: Groundwater, v. 53, no. 2.
- Heppner, C.S., and Nimmo, J.R., 2005, A computer program for predicting recharge with a master recession curve: USGS Scientific Investigations Report 2005-5172.

### Supporting Literature
- USGS EMR Method Guidelines: https://wwwrcamnl.wr.usgs.gov/uzf/EMR_Method/
- Healy, R.W., and Cook, P.G., 2002, Using groundwater levels to estimate recharge: Hydrogeology Journal, v. 10, p. 91-109.
- Scanlon, B.R., Healy, R.W., and Cook, P.G., 2002, Choosing appropriate techniques for quantifying groundwater recharge: Hydrogeology Journal, v. 10, p. 18-39.

### Methodological References
- James, G., Witten, D., Hastie, T., and Tibshirani, R., 2013, An Introduction to Statistical Learning: Springer, 426 p.
- Hastie, T., Tibshirani, R., and Friedman, J., 2009, The Elements of Statistical Learning: Springer, 745 p.