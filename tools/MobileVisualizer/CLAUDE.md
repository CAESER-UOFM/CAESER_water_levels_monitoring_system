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

### Plot Customization Enhancements (Latest)
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