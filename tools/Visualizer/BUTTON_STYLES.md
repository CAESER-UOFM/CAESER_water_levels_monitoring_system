# Consistent Button Styling Guide

This document defines the standard button styling for the Water Level Visualizer application to maintain visual consistency throughout the interface.

## Standard Button Style

Use this styling for primary action buttons (export, settings, launcher, etc.):

```python
button.setStyleSheet("""
    QPushButton {
        padding: 5px 10px;
        border: 1px solid #ccc;
        border-radius: 4px;
        background-color: #f8f9fa;
    }
    QPushButton:hover {
        background-color: #e9ecef;
        border-color: #adb5bd;
    }
    QPushButton:disabled {
        background-color: #e9ecef;
        color: #6c757d;
        border-color: #dee2e6;
    }
""")
```

## Style Features

- **Padding**: 5px vertical, 10px horizontal for comfortable touch targets
- **Border**: 1px solid light gray (#ccc) for subtle definition
- **Border radius**: 4px for modern rounded corners
- **Background**: Light gray (#f8f9fa) for subtle contrast
- **Hover effect**: Darker gray (#e9ecef) with darker border (#adb5bd)
- **Disabled state**: Muted colors (#e9ecef background, #6c757d text, #dee2e6 border)

## Implementation Notes

1. Apply this style to all primary action buttons
2. Keep icon usage consistent with `self.style().standardIcon()`
3. Set appropriate tooltips for all buttons
4. Use consistent maximum widths where space is constrained

## Current Implementations

- Export Plot button (water_level_visualizer.py:354-370)
- Export Data button (water_level_visualizer.py:372-388)
- Recharge tab header buttons (recharge_tab.py:83-134)
- Main Calculate buttons in all method tabs (rise_tab.py:175-191, mrc_tab.py:204-220, erc_tab.py:196-212)

## TODO

- Apply to remaining recharge method buttons (export, save/load, refresh, etc.)
- Apply to other dialog buttons throughout the application
- Consider creating a helper function to apply standard styling