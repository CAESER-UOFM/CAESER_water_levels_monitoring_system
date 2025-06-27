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

### Mobile Responsive Plot Customization - COMPLETE! (Latest)
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