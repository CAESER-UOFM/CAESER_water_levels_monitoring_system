# Claude Development Notes for MobileVisualizer

## Important: Netlify Deployment Process

⚠️ **CRITICAL REMINDER**: After making any changes to the codebase, **ALWAYS DEPLOY TO NETLIFY** to properly test the changes in production environment.

### Deployment Steps:
1. **Commit changes** to git
2. **Push to GitHub** 
3. **Deploy to Netlify** using: `netlify deploy --prod --build`

### Netlify Details:
- **Production URL**: https://water-level-visualizer-mobile.netlify.app
- **Account**: Already authenticated with Netlify CLI
- **Build Command**: `npm run build` (specified in netlify.toml)
- **Functions**: Located in `/netlify/functions/`

### Why This Matters:
- Local builds don't test the Netlify Functions properly
- Production environment may have different behavior than local
- Database connections and API endpoints need to be tested in production
- Users access the Netlify deployment, not local development

## Recent Major Changes:

### Zoom/Pan Improvements - Iteration 3 (Latest)
- **SUCCESSFULLY DEPLOYED**: https://water-level-visualizer-mobile.netlify.app  
- **✅ INDUSTRY-STANDARD SOLUTION**: Implemented proven zoom-to-point mathematical formula
- **✅ FIXED TRANSFORM ORDER**: Corrected CSS transform order to prevent coordinate system issues

**Research-Based Implementation:**
- **🔬 Mathematical Formula**: `xs = (mouseX - currentPan.x) / prevZoom; newPanX = mouseX - xs * newZoom`
- **⚙️ Transform Order Fix**: Changed from `translate scale` to `scale translate` order
- **📐 Origin Point**: Added `transform-origin: 0 0` for consistent coordinate calculations
- **🎯 Direct Approach**: Removed artificial delays and sensitivity reductions in favor of mathematical precision

**Technical Implementation:**
- Uses proven Stack Overflow solution for zoom-to-point functionality
- Calculates mouse position in current scaled coordinate system
- Applies industry-standard transform order for CSS transformations
- Works consistently for both wheel zoom and pinch zoom

### Zoom/Pan Improvements - Iteration 2
- **SUCCESSFULLY DEPLOYED**: https://water-level-visualizer-mobile.netlify.app
- **✅ REDUCED JUMP ISSUES**: Improved focal point zoom with stable calculations
- **✅ SMOOTHER EXPERIENCE**: Separated zoom and pan updates to prevent conflicts

**Stable Zoom Implementation:**
- **⚡ Async Updates**: Use `setTimeout(0)` to separate zoom and pan state updates
- **🎯 Better Focal Point**: Calculate mouse/touch positions relative to container center  
- **🔧 Reduced Sensitivity**: Lower sensitivity (0.5x wheel, 0.4x touch) for smoother transitions
- **📏 Optimized Steps**: Slightly larger zoom increments for smoother progression
- **🛡️ Smart Bounds**: Only update pan when zoom actually changes, with proper bounds checking

**Technical Changes:**
- Mouse wheel zoom uses relative positioning from container center
- Touch pinch zoom with reduced sensitivity and requestAnimationFrame
- Button zoom with minimal pan adjustments and bounds validation
- All methods now prevent unnecessary pan updates when zoom doesn't change

## Previous Major Changes:

### Mobile Layout Redesign - MAJOR IMPROVEMENT! (Latest)
- **SUCCESSFULLY DEPLOYED**: https://water-level-visualizer-mobile.netlify.app  
- **✅ ALWAYS-VISIBLE PLOT**: Plot now always shown with high quality (same as desktop)
- **✅ NO MORE MODAL**: Removed poor-quality preview modal system
- **✅ BETTER UX**: 60% plot preview + 40% controls layout

**Mobile Layout Transformation:**
- **📱 Split Layout**: Plot takes 60% of screen (top), controls 40% (bottom)  
- **🎯 High Quality**: Same plot quality as desktop version - no more cut-off or low resolution
- **🎛️ Smart Controls**: Collapsible bottom panel with scrollable controls sections
- **⚡ Real-time**: Users see changes immediately as they adjust settings
- **🚀 Quick Export**: Export button prominently placed in controls header

**User Experience Improvements:**
- **🔍 Visual Feedback**: Users can see exactly what they'll download
- **📐 Proper Scaling**: Plot scales correctly for mobile screens while maintaining quality
- **👆 Touch Optimized**: All controls remain touch-friendly and accessible
- **💨 No Loading**: Instant preview updates without modal delays

**Technical Implementation:**
- Removed `showMobilePreview` state and modal code entirely
- Split mobile layout into plot preview container and controls panel
- LivePlotPreview with `showFullSize={false}` for proper mobile scaling
- Maximum height constraints for controls to preserve plot visibility

### Plot Customization UI Improvements - COMPLETE!
- **SUCCESSFULLY DEPLOYED**: https://water-level-visualizer-mobile.netlify.app
- **✅ IMPROVED ALIGNMENT**: Fixed data series styling with consistent grid layouts
- **✅ SUB-TABS ADDED**: Organized appearance section with Title, Axes, and Legend tabs

**Data Series Styling Improvements:**
- **🎯 Grid Layouts**: Replaced flexbox with grid for consistent field alignment
- **📐 Consistent Sizing**: All input fields now have uniform width and spacing
- **🏷️ Better Labels**: Improved label consistency and clarity across all sections
- **📊 Organized Controls**: Transducer, manual, and temperature data controls now properly aligned

**Appearance Section Organization:**
- **📑 Sub-tabs Navigation**: Title, Axes, and Legend tabs for better organization
- **🎨 Title Tab**: Contains title settings and general plot colors
- **📏 Axes Tab**: X-axis, Y-axis, and right axis (temperature) configuration
- **🏷️ Legend Tab**: All legend positioning and styling options
- **✨ Visual Separation**: Clear boundaries between different styling categories

### Mobile Responsive Plot Customization - COMPLETE!
- **SUCCESSFULLY DEPLOYED**: https://water-level-visualizer-mobile.netlify.app
- **✅ FULLY FUNCTIONAL**: All mobile panels now have complete control content

**Mobile Panel Implementation:**
- **📐 Dimensions**: Preset templates dropdown, aspect ratio, width/height inputs, DPI selection
- **📊 Data Selection**: Checkboxes for transducer, manual readings, temperature data
- **🎨 Appearance**: Plot colors, title settings with font size and color controls  
- **📋 Well Info**: Legend toggle and position sliders for horizontal/vertical placement
- **💾 Export**: Working export button with full functionality

**Mobile Preview System:**
- **✅ Fixed Image Dimensions**: Modal now shows actual plot dimensions for zoom capability
- **✅ Full Resolution**: Users can zoom and pan the complete high-resolution plot
- **✅ Desktop Preserved**: Desktop preview maintains scaled-to-fit behavior
- **✅ Touch Optimized**: Responsive controls work perfectly on touch devices

**Technical Implementation:**
- Added `showFullSize` prop to LivePlotPreview component
- Conditional dimension calculation (mobile vs desktop)
- Complete mobile control panels with native input elements
- Smart device detection with resize/orientation listeners

### Plot Customization Enhancements (Previous)
- Removed font size constraints (tick fonts up to 48px, labels up to 72px)
- Added significant figures control for Y-axis and right axis tick labels
- Implemented comprehensive right axis support for temperature data
- Enhanced LivePlotPreview and customPlotExport with dual-axis rendering

### Previous Improvements:
- Comprehensive legend system with 9 positioning options
- Axis label distance controls
- Enhanced data series styling (line styles, marker shapes)
- Temperature data visualization support
- Preset template system for quick customization

## Development Workflow:
1. Make changes locally
2. Test with `npm run build` 
3. Commit to git with descriptive messages
4. Push to GitHub
5. **Deploy to Netlify** ← Don't forget this step!
6. Test the live deployment
7. Report status to user

## Key Files:
- `src/components/PlotCustomizationDialog.tsx` - Main customization interface
- `src/components/LivePlotPreview.tsx` - Real-time preview component  
- `src/utils/customPlotExport.ts` - High-resolution export functionality
- `netlify/functions/` - Backend API functions

## Testing Checklist:
- [ ] Local build succeeds
- [ ] Git commit and push complete
- [ ] Netlify deployment successful
- [ ] Live site functions properly
- [ ] Plot customization features work
- [ ] Export functionality works
- [ ] Database connections active