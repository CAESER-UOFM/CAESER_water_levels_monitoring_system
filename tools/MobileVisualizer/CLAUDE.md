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