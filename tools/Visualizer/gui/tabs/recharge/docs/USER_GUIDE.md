# Recharge Analysis User Guide

## Overview

The Recharge Analysis module provides comprehensive tools for estimating groundwater recharge using water table fluctuation methods. This guide covers the updated interface with unified settings management, modern launcher system, and integrated help features.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Interface Overview](#interface-overview)
3. [Method Selection Guide](#method-selection-guide)
4. [Unified Settings](#unified-settings)
5. [Method Launcher](#method-launcher)
6. [Method Comparison](#method-comparison)
7. [User Preferences](#user-preferences)
8. [Help System](#help-system)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites
- Water level monitoring data loaded in the main application
- Wells selected from the "Available Wells" table
- Recommended: Unconfined aquifer wells for optimal results

### Quick Start Workflow
1. **Select Wells**: Choose monitoring wells from the main interface
2. **Choose Interface Mode**: Use traditional tabs or modern launcher
3. **Configure Settings**: Set unified parameters via "Global Settings"
4. **Select Method**: Choose RISE, MRC, or ERC based on your needs
5. **Run Analysis**: Execute calculations and review results
6. **Export Data**: Save results for reporting or further analysis

---

## Interface Overview

### Main Interface Components

#### Header Controls
- **Global Settings**: Access unified parameter management
- **🚀 Method Launcher**: Open modern method selection interface
- **⚙️ Preferences**: Configure user preferences and interface options
- **❓ Help**: Access comprehensive help system and method guidance

#### Method Tabs
- **RISE Method**: Simple, reliable recharge estimation
- **MRC Method**: Master Recession Curve analysis with precipitation integration
- **ERC Method**: Extended Recession Curve for research-grade analysis

### Interface Modes

#### Traditional Tab Mode
- Classic tabbed interface for sequential method access
- Ideal for users familiar with the original interface
- All methods accessible in a single window

#### Launcher Mode
- Modern card-based method selection
- Individual method windows for focused analysis
- Method comparison capabilities
- Recommended for new users and complex analyses

#### Mixed Mode
- Combines both tab and launcher interfaces
- Maximum flexibility for different workflows
- Switch between modes as needed

---

## Method Selection Guide

### RISE Method
**Best for**: Simple, fast recharge estimation with clear water level signals

**Characteristics**:
- ✅ Simple and intuitive
- ✅ Fast calculation
- ✅ Well documented
- ❌ No precipitation integration
- ❌ May miss subtle events

**Recommended when**:
- High-frequency data available (hourly or better)
- Clear recharge signals in water level data
- Quick assessment needed
- Beginning users

### MRC Method
**Best for**: Robust analysis with statistical validation and precipitation integration

**Characteristics**:
- ✅ Statistical validation
- ✅ Precipitation integration
- ✅ Robust to noise
- ❌ Complex setup
- ❌ Requires recession periods

**Recommended when**:
- Precipitation data available
- Need statistical validation
- Moderate complexity acceptable
- Water resource management applications

### ERC Method
**Best for**: Research-quality analysis with uncertainty quantification

**Characteristics**:
- ✅ Research-grade analysis
- ✅ Uncertainty quantification
- ✅ Advanced validation
- ❌ Complex interpretation
- ❌ Longer computation time

**Recommended when**:
- Research or publication goals
- Uncertainty quantification needed
- Complex hydrogeological conditions
- Advanced user expertise available

---

## Unified Settings

### Overview
The unified settings system consolidates common parameters across all methods, reducing interface complexity by ~75% while maintaining method-specific customization.

### Settings Categories

#### Common Parameters
- **Specific Yield**: Aquifer specific yield (0.1-0.3 typical)
- **Water Year**: Start month/day for analysis periods
- **Confidence Level**: Statistical confidence (90%, 95%, 99%)
- **Units**: Measurement units (feet/meters)

#### Preprocessing
- **Downsampling**: Data frequency reduction
- **Smoothing**: Data smoothing options
  - Enable/disable smoothing
  - Window size (2-14 days)
  - Smoothing type (Moving Average, Gaussian, Savitzky-Golay)
- **Quality Control**: Outlier removal settings

#### Method-Specific Settings
- **RISE**: Rise threshold, event detection parameters
- **MRC**: Deviation threshold, recession fitting options
- **ERC**: Seasonal analysis, validation framework settings

### Using Unified Settings

1. **Access**: Click "Global Settings" button
2. **Configure**: Set parameters in organized tabs
3. **Apply**: Changes automatically propagate to all method tabs
4. **Save**: Settings persist across sessions
5. **Reset**: Restore default values if needed

---

## Method Launcher

### Accessing the Launcher
- Click "🚀 Method Launcher" button in the main interface
- Modern card-based interface for method selection

### Features

#### Method Cards
- **Visual Method Selection**: Color-coded cards for each method
- **Method Information**: Key characteristics and use cases
- **Quick Access**: Direct launch to method analysis

#### Launch Options
- **New Window**: Open method in dedicated window
- **Use Unified Settings**: Apply global parameters automatically
- **Well Selection**: Choose specific wells for analysis

#### Method Comparison
- **Select Multiple Methods**: Choose 2-3 methods for comparison
- **Side-by-Side Analysis**: Compare results simultaneously
- **Validation**: Cross-validate results across methods

### Workflow
1. **Open Launcher**: Click launcher button
2. **Review Methods**: Read method descriptions and recommendations
3. **Select Options**: Choose launch preferences
4. **Launch**: Start analysis in new window or comparison mode

---

## Method Comparison

### Purpose
Compare multiple recharge estimation methods to:
- Validate results across different approaches
- Understand method-specific differences
- Build confidence in recharge estimates

### Features
- **Simultaneous Analysis**: Run multiple methods with same data
- **Result Comparison**: Side-by-side plots and statistics
- **Export Options**: Save comparison results
- **Validation Metrics**: Cross-method agreement statistics

### Best Practices
- Start with RISE and MRC for initial comparison
- Add ERC for research-quality validation
- Review method-specific assumptions
- Document differences in results

---

## User Preferences

### Accessing Preferences
Click "⚙️ Preferences" button to open comprehensive preferences dialog

### Preference Categories

#### Interface Preferences
- **Default Interface Mode**: Tabs, Launcher, or Mixed
- **Default Method**: Initial method selection
- **Launcher Button Visibility**: Show/hide launcher access
- **Window Behavior**: New window settings

#### Analysis Preferences
- **Auto-Apply Settings**: Automatically propagate unified settings
- **Save on Change**: Auto-save settings modifications
- **Auto-Save Sessions**: Preserve session state
- **Calculation Progress**: Show progress indicators

#### Visualization Preferences
- **Plot Style**: Professional, Scientific, or Publication quality
- **Color Schemes**: Standard or accessibility-friendly options
- **Grid Display**: Default grid visibility
- **Date Formatting**: Preferred date formats

#### Data Preferences
- **Default Water Year**: Standard water year start
- **Default Specific Yield**: Default values for different aquifer types
- **Units**: Preferred measurement units
- **Data Quality**: Automatic quality control settings

#### Advanced Preferences
- **Debug Logging**: Enable detailed logging
- **Auto-Backup**: Automatic settings backup
- **Update Checking**: Check for system updates
- **Usage Statistics**: Optional usage tracking

---

## Help System

### Comprehensive Help Features

#### Quick Start Guide
- Step-by-step getting started instructions
- Method selection flowchart
- Basic workflow overview
- Success tips and best practices

#### Method-Specific Guides
- Detailed documentation for each method
- Parameter explanations and recommendations
- Strengths and limitations analysis
- Example applications

#### Interactive Tutorials
- Video tutorial integration (coming soon)
- Step-by-step walkthroughs
- Common workflow examples
- Troubleshooting scenarios

#### Method Recommendation Wizard
- **Data Assessment**: Analyze your data characteristics
- **Objectives Evaluation**: Consider analysis goals
- **Experience Level**: Account for user expertise
- **Personalized Recommendations**: Get method suggestions with confidence scores

#### Troubleshooting Guide
- Common issues and solutions
- Data quality checklist
- Performance optimization tips
- Error message explanations

### Accessing Help
- Click "❓ Help" button for main help system
- Context-sensitive help available in method interfaces
- Method recommendation wizard in launcher

---

## Troubleshooting

### Common Issues

#### "No recharge events detected"
**Causes & Solutions**:
- Lower rise/deviation thresholds
- Check data quality and continuity
- Verify specific yield values
- Review water year settings
- Ensure sufficient data frequency

#### "Calculation errors or crashes"
**Causes & Solutions**:
- Fill data gaps or interpolate missing points
- Reduce data range or increase downsampling
- Reset to default settings
- Check file permissions for temporary files

#### "Unrealistic recharge estimates"
**Causes & Solutions**:
- Verify specific yield with field testing
- Consider different method selection
- Review validation metrics for uncertainty
- Compare with precipitation data

#### "Interface or display problems"
**Causes & Solutions**:
- Check display DPI settings in preferences
- Reset window positions
- Verify interface mode settings
- Reduce plot resolution if needed

### Data Quality Checklist
- ✅ Continuous time series with minimal gaps
- ✅ Appropriate measurement frequency (hourly or better)
- ✅ Adequate data span (minimum 1 year recommended)
- ✅ Barometric compensation applied
- ✅ Well screen in unconfined aquifer
- ✅ No significant pumping interference

### Getting Additional Help
- Use Method Recommendation Wizard for guidance
- Try Method Comparison to validate results
- Check video tutorials (when available)
- Contact technical support for software issues

---

## Best Practices

### Data Preparation
1. **Quality Control**: Ensure continuous, high-quality data
2. **Barometric Compensation**: Apply pressure corrections
3. **Gap Analysis**: Identify and address data gaps
4. **Frequency Check**: Verify adequate measurement frequency

### Method Selection
1. **Start Simple**: Begin with RISE method for initial assessment
2. **Consider Data**: Match method to data characteristics
3. **Validate Results**: Use multiple methods when possible
4. **Document Assumptions**: Record all parameter choices

### Parameter Configuration
1. **Use Unified Settings**: Leverage global parameter management
2. **Field Validation**: Use field-tested specific yield values
3. **Seasonal Considerations**: Account for seasonal variations
4. **Iterative Refinement**: Adjust parameters based on results

### Result Validation
1. **Precipitation Comparison**: Compare with rainfall patterns
2. **Hydrologic Reasonableness**: Assess realistic magnitude
3. **Temporal Patterns**: Review seasonal and annual trends
4. **Multiple Methods**: Cross-validate with different approaches

### Documentation
1. **Parameter Recording**: Document all settings used
2. **Method Justification**: Explain method selection rationale
3. **Quality Assessment**: Note data quality limitations
4. **Result Interpretation**: Provide context for estimates

---

## Support and Resources

### Built-in Resources
- Comprehensive help system with method guides
- Interactive method recommendation wizard
- Troubleshooting guide with common solutions
- Scientific references and documentation links

### External Resources
- USGS Groundwater Recharge Methods
- Water Table Fluctuation Method Guidelines
- Aquifer Testing and Specific Yield Determination
- Scientific literature on recharge estimation

### Technical Support
For software issues, calculation problems, or feature requests, use the built-in help system or contact the development team through the application.

---

*User Guide Version 2.0 - Updated for the new unified interface*  
*Last Updated: June 2025*