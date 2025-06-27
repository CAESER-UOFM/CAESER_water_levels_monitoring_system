# Recharge Tab Plotting Standardization Guide

## Overview
This guide explains how to standardize the plotting across all recharge calculation method tabs (RISE, MRC, ERC) to ensure consistent, professional visualization of raw water level data.

## Key Components

### 1. Base Recharge Tab (`base_recharge_tab.py`)
The base class provides:
- Standardized matplotlib figure initialization
- Common display options (checkboxes for raw data, processed data, grid, legend)
- Professional plotting style with consistent colors and formatting
- Base plotting method that all tabs inherit

### 2. Standardized Features
All tabs now share:
- **Consistent colors**: 
  - Raw data: Professional blue (#1f77b4)
  - Processed data: Professional green (#2ca02c)
  - Background: Light gray (#f8f9fa)
- **Professional styling**:
  - Clean grid lines with subtle appearance
  - Proper axis labels with bold fonts
  - Consistent title formatting
  - Rotated date labels for readability
- **Common controls**:
  - Show/hide raw data
  - Show/hide processed data
  - Toggle grid
  - Toggle legend

### 3. Method-Specific Additions
Each tab adds its own analysis elements:
- **RISE**: Red markers and lines for rise events
- **MRC**: Red recession segments, black dashed master curve
- **ERC**: Seasonal colored recession segments, purple recharge events

## Implementation Steps

### For New Tabs:
1. Inherit from `BaseRechargeTab` instead of `QWidget`
2. Override `get_method_name()` to return your method name
3. Override `add_method_specific_plots(ax)` to add your analysis visualization
4. Use `self.update_plot()` which automatically calls the base plotting

### For Existing Tabs:
To update existing tabs to use standardized plotting:

1. **Modify the class inheritance**:
```python
# Old:
class RiseTab(QWidget):

# New:
from .base_recharge_tab import BaseRechargeTab
class RiseTab(BaseRechargeTab):
```

2. **Remove duplicate plotting code**:
- Remove figure/canvas initialization (handled by base class)
- Remove basic plot display options (inherited from base)
- Keep only method-specific options

3. **Update the update_plot method**:
```python
def update_plot(self):
    # Call base plotting
    ax = self.update_plot_base()
    if ax:
        # Add method-specific elements
        self.add_method_specific_plots(ax)
        
def add_method_specific_plots(self, ax):
    # Add your method-specific visualization here
    # e.g., rise events, recession curves, etc.
```

4. **Use standardized display options**:
```python
# In create_plot_panel():
display_options = self.create_plot_display_options()
# Add any method-specific options to the same group
```

## Benefits

1. **Consistency**: Users see the same professional plot style across all methods
2. **Maintainability**: Changes to base plotting automatically apply to all tabs
3. **Professionalism**: Clean, modern appearance with proper styling
4. **Code Reuse**: Less duplicate code, easier to maintain
5. **Extensibility**: Easy to add new recharge methods with consistent plotting

## Testing

Run the test script to see the standardized plotting in action:
```bash
python test_standardized_plotting.py
```

This will show all three tabs with identical base plotting before any calculations are performed.

## Notes

- The v2 files (rise_tab_v2.py, etc.) are simplified demonstrations
- The actual implementation should preserve all existing functionality
- Only the plotting visualization needs to be standardized
- All calculation logic remains unchanged