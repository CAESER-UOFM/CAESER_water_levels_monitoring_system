exports.id=376,exports.ids=[376],exports.modules={6468:(e,t,a)=>{Promise.resolve().then(a.t.bind(a,2994,23)),Promise.resolve().then(a.t.bind(a,6114,23)),Promise.resolve().then(a.t.bind(a,9727,23)),Promise.resolve().then(a.t.bind(a,9671,23)),Promise.resolve().then(a.t.bind(a,1868,23)),Promise.resolve().then(a.t.bind(a,4759,23))},3074:()=>{},5047:(e,t,a)=>{"use strict";var l=a(7389);a.o(l,"useParams")&&a.d(t,{useParams:function(){return l.useParams}}),a.o(l,"useRouter")&&a.d(t,{useRouter:function(){return l.useRouter}})},9609:(e,t,a)=>{"use strict";a.d(t,{T:()=>r});var l=a(326);function r({size:e="medium",className:t=""}){return l.jsx("div",{className:`loading-spinner ${{small:"w-4 h-4",medium:"w-8 h-8",large:"w-12 h-12"}[e]} ${t}`})}},3830:(e,t,a)=>{"use strict";a.d(t,{TD:()=>s,f4:()=>d});var l=a(470),r=a.n(l);let i=null;async function n(){if(!i)try{i=await r()({locateFile:e=>`https://sql.js.org/dist/${e}`})}catch(e){throw console.error("Failed to initialize sql.js:",e),Error("Database initialization failed")}}class s{constructor(e){this.arrayBuffer=e,this.db=null,this.initialized=!1}async initialize(){if(!this.initialized){if(await n(),!i)throw Error("SQL.js not initialized");try{this.db=new i.Database(new Uint8Array(this.arrayBuffer)),this.initialized=!0,await this.validateSchema()}catch(e){throw console.error("Failed to open database:",e),Error("Invalid database file")}}}async validateSchema(){if(!this.db)throw Error("Database not initialized");let e=this.db.prepare('SELECT name FROM sqlite_master WHERE type="table"'),t=[];for(;e.step();){let a=e.getAsObject();t.push(a.name)}for(let a of(e.free(),["wells","water_level_readings"]))if(!t.includes(a))throw Error(`Required table '${a}' not found in database`)}async getWells(e={}){if(!this.db)throw Error("Database not initialized");let{search:t="",field:a="",hasData:l,page:r=1,limit:i=50,sortBy:n="well_number",sortOrder:s="asc"}=e,o=`
      SELECT 
        w.*,
        COUNT(wlr.id) as total_readings,
        MAX(wlr.timestamp_utc) as last_reading_date,
        CASE WHEN COUNT(mr.id) > 0 THEN 1 ELSE 0 END as has_manual_readings,
        CASE WHEN COUNT(wlr.id) > 0 THEN 1 ELSE 0 END as has_transducer_data
      FROM wells w
      LEFT JOIN water_level_readings wlr ON w.well_number = wlr.well_number
      LEFT JOIN manual_readings mr ON w.well_number = mr.well_number
      WHERE 1=1
    `,d=[];if(t){o+=" AND (w.well_number LIKE ? OR w.cae_number LIKE ? OR w.well_field LIKE ?)";let e=`%${t}%`;d.push(e,e,e)}a&&(o+=" AND w.well_field = ?",d.push(a)),void 0!==l&&(l?o+=" AND COUNT(wlr.id) > 0":o+=" AND COUNT(wlr.id) = 0"),o+=" GROUP BY w.well_number",["well_number","cae_number","last_reading_date"].includes(n)&&(o+=` ORDER BY ${n} ${s.toUpperCase()}`),o+=" LIMIT ? OFFSET ?",d.push(i,(r-1)*i);try{let e=this.db.prepare(o);e.bind(d);let l=[];for(;e.step();){let t=e.getAsObject();l.push(this.mapRowToWell(t))}e.free();let n=`
        SELECT COUNT(DISTINCT w.well_number) as total
        FROM wells w
        LEFT JOIN water_level_readings wlr ON w.well_number = wlr.well_number
        WHERE 1=1
      `,s=[];if(t){n+=" AND (w.well_number LIKE ? OR w.cae_number LIKE ? OR w.well_field LIKE ?)";let e=`%${t}%`;s.push(e,e,e)}a&&(n+=" AND w.well_field = ?",s.push(a));let c=this.db.prepare(n);c.bind(s),c.step();let u=c.getAsObject().total;return c.free(),{success:!0,data:l,pagination:{page:r,limit:i,total:u,totalPages:Math.ceil(u/i)}}}catch(e){throw console.error("Error fetching wells:",e),Error("Failed to fetch wells data")}}async getWell(e){if(!this.db)throw Error("Database not initialized");let t=this.db.prepare(`
      SELECT 
        w.*,
        COUNT(wlr.id) as total_readings,
        MAX(wlr.timestamp_utc) as last_reading_date,
        CASE WHEN COUNT(mr.id) > 0 THEN 1 ELSE 0 END as has_manual_readings,
        CASE WHEN COUNT(wlr.id) > 0 THEN 1 ELSE 0 END as has_transducer_data
      FROM wells w
      LEFT JOIN water_level_readings wlr ON w.well_number = wlr.well_number
      LEFT JOIN manual_readings mr ON w.well_number = mr.well_number
      WHERE w.well_number = ?
      GROUP BY w.well_number
    `);if(t.bind([e]),t.step()){let e=t.getAsObject();return t.free(),this.mapRowToWell(e)}return t.free(),null}async getWaterLevelData(e){if(!this.db)throw Error("Database not initialized");let{wellNumber:t,startDate:a,endDate:l,dataType:r="all",downsample:i=!1,maxPoints:n=1e3}=e,s=`
      SELECT 
        id,
        well_number,
        timestamp_utc,
        julian_timestamp,
        water_level,
        temperature,
        dtw,
        'transducer' as data_source,
        baro_flag,
        level_flag
      FROM water_level_readings
      WHERE well_number = ?
    `,o=[t];a&&(s+=" AND timestamp_utc >= ?",o.push(a)),l&&(s+=" AND timestamp_utc <= ?",o.push(l)),("all"===r||"manual"===r)&&(s+=` UNION ALL
        SELECT 
          id,
          well_number,
          timestamp_utc,
          julian_timestamp,
          water_level,
          NULL as temperature,
          dtw,
          'manual' as data_source,
          NULL as baro_flag,
          NULL as level_flag
        FROM manual_readings
        WHERE well_number = ?
      `,o.push(t),a&&(s+=" AND timestamp_utc >= ?",o.push(a)),l&&(s+=" AND timestamp_utc <= ?",o.push(l))),s+=" ORDER BY timestamp_utc";try{let e=this.db.prepare(s);e.bind(o);let t=[];for(;e.step();){let a=e.getAsObject();t.push(this.mapRowToReading(a))}if(e.free(),i&&t.length>n)return this.downsampleData(t,n);return t}catch(e){throw console.error("Error fetching water level data:",e),Error("Failed to fetch water level data")}}async getRechargeResults(e){if(!this.db)throw Error("Database not initialized");let t=this.db.prepare(`
      SELECT name FROM sqlite_master 
      WHERE type='table' AND name IN ('rise_results', 'mrc_results', 'emr_results')
    `),a=[];for(;t.step();){let e=t.getAsObject();a.push(e.name)}if(t.free(),0===a.length)return[];let l=[];for(let t of a){let a=t.replace("_results","").toUpperCase();try{let r=this.db.prepare(`
          SELECT * FROM ${t}
          WHERE well_number = ?
          ORDER BY calculation_date DESC
        `);for(r.bind([e]);r.step();){let e=r.getAsObject();l.push({...e,method:a,calculation_parameters:e.calculation_parameters?JSON.parse(e.calculation_parameters):void 0})}r.free()}catch(e){console.error(`Error querying ${t}:`,e)}}return l}mapRowToWell(e){return{well_number:e.well_number,cae_number:e.cae_number,well_field:e.well_field,cluster:e.cluster,latitude:e.latitude,longitude:e.longitude,top_of_casing:e.top_of_casing,ground_elevation:e.ground_elevation,well_depth:e.well_depth,screen_top:e.screen_top,screen_bottom:e.screen_bottom,aquifer_type:e.aquifer_type,static_water_level:e.static_water_level,notes:e.notes,last_reading_date:e.last_reading_date,total_readings:e.total_readings||0,has_manual_readings:!!e.has_manual_readings,has_transducer_data:!!e.has_transducer_data,has_telemetry_data:!!e.has_telemetry_data}}mapRowToReading(e){return{id:e.id,well_number:e.well_number,timestamp_utc:e.timestamp_utc,julian_timestamp:e.julian_timestamp,water_level:e.water_level,temperature:e.temperature,dtw:e.dtw,data_source:e.data_source,baro_flag:e.baro_flag,level_flag:e.level_flag,notes:e.notes}}downsampleData(e,t){if(e.length<=t)return e;let a=Math.floor(e.length/t),l=[];for(let t=0;t<e.length;t+=a)l.push(e[t]);return l[l.length-1]!==e[e.length-1]&&l.push(e[e.length-1]),l}close(){this.db&&(this.db.close(),this.db=null,this.initialized=!1)}}class o{async loadDatabase(e,t){let a=new s(t);return await a.initialize(),this.databases.set(e,a),a}getDatabase(e){return this.databases.get(e)||null}closeDatabase(e){let t=this.databases.get(e);t&&(t.close(),this.databases.delete(e))}closeAllDatabases(){for(let[e,t]of this.databases)t.close();this.databases.clear()}constructor(){this.databases=new Map}}let d=new o},4769:(e,t,a)=>{"use strict";function l(e,t,a){if(0===e.length)throw Error("No data to export");let l=e.map(e=>[e.timestamp_utc,e.water_level?.toString()||"",e.temperature?.toString()||"",e.data_source||"",e.level_flag||""]);o(["# Water Level Data Export",`# Well: ${t.well_number}`,t.cae_number?`# CAE Number: ${t.cae_number}`:"",t.well_field?`# Field: ${t.well_field}`:"",`# Export Date: ${new Date().toISOString()}`,`# Total Records: ${e.length}`,"","Date/Time,Water Level (ft),Temperature (\xb0C),Data Type,Quality",...l.map(e=>e.join(","))].filter(e=>""!==e).join("\n"),a||`water_level_data_${t.well_number}_${new Date().toISOString().split("T")[0]}.csv`,"text/csv")}function r(e,t,a){if(0===e.length)throw Error("No data to export");o(JSON.stringify({metadata:{well_number:t.well_number,cae_number:t.cae_number,well_field:t.well_field,latitude:t.latitude,longitude:t.longitude,ground_elevation:t.ground_elevation,export_date:new Date().toISOString(),total_records:e.length},data:e.map(e=>({datetime:e.timestamp_utc,water_level_ft:e.water_level,temperature_c:e.temperature,data_source:e.data_source,level_flag:e.level_flag}))},null,2),a||`water_level_data_${t.well_number}_${new Date().toISOString().split("T")[0]}.json`,"application/json")}function i(e,t,a){if(0===e.length)throw Error("No recharge results to export");let l=e.map(e=>[e.method,e.calculation_date,e.start_date,e.end_date,e.recharge_mm?.toString()||"",e.recharge_inches?.toString()||"",e.specific_yield?.toString()||"",e.notes||""]);o(["# Recharge Results Export",`# Well: ${t.well_number}`,t.cae_number?`# CAE Number: ${t.cae_number}`:"",t.well_field?`# Field: ${t.well_field}`:"",`# Export Date: ${new Date().toISOString()}`,`# Total Calculations: ${e.length}`,"","Method,Calculation Date,Start Date,End Date,Recharge (mm),Recharge (inches),Specific Yield,Notes",...l.map(e=>e.join(","))].filter(e=>""!==e).join("\n"),a||`recharge_results_${t.well_number}_${new Date().toISOString().split("T")[0]}.csv`,"text/csv")}function n(e,t,a){if(0===e.length)throw Error("No recharge results to export");o(JSON.stringify({metadata:{well_number:t.well_number,cae_number:t.cae_number,well_field:t.well_field,latitude:t.latitude,longitude:t.longitude,export_date:new Date().toISOString(),total_calculations:e.length},recharge_results:e.map(e=>({method:e.method,calculation_date:e.calculation_date,period:{start_date:e.start_date,end_date:e.end_date},recharge:{mm:e.recharge_mm,inches:e.recharge_inches},specific_yield:e.specific_yield,notes:e.notes}))},null,2),a||`recharge_results_${t.well_number}_${new Date().toISOString().split("T")[0]}.json`,"application/json")}function s(e,t,a){if(0===e.length)throw Error("No recharge results to export");let l=function(e,t){let a=e.reduce((e,t)=>(e[t.method]||(e[t.method]=[]),e[t.method].push(t),e),{}),l={RISE:"Recharge Investigation and Simulation Tool - automated water table fluctuation method",MRC:"Manual Recharge Calculation - user-defined parameters and periods",EMR:"Enhanced Manual Recharge - advanced manual calculation with additional parameters"};return`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recharge Results Report - Well ${t.well_number}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
        .header { border-bottom: 2px solid #ccc; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { margin: 0; color: #2563eb; }
        .metadata { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 20px 0; }
        .metadata dt { font-weight: bold; }
        .method-section { margin: 30px 0; page-break-inside: avoid; }
        .method-title { background: #f3f4f6; padding: 10px; border-left: 4px solid #2563eb; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f9fafb; font-weight: 600; }
        .summary { background: #f0f9ff; padding: 15px; border-radius: 6px; margin: 20px 0; }
        @media print { body { margin: 0; } .no-print { display: none; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>Recharge Results Report</h1>
        <h2>Well ${t.well_number}</h2>
        <div class="metadata">
            ${t.cae_number?`<div><dt>CAE Number:</dt><dd>${t.cae_number}</dd></div>`:""}
            ${t.well_field?`<div><dt>Field:</dt><dd>${t.well_field}</dd></div>`:""}
            <div><dt>Export Date:</dt><dd>${new Date().toLocaleDateString()}</dd></div>
            <div><dt>Total Calculations:</dt><dd>${e.length}</dd></div>
        </div>
    </div>

    <div class="summary">
        <h3>Summary</h3>
        <p>This report contains ${e.length} recharge calculations for well ${t.well_number} using ${Object.keys(a).length} different methods.</p>
    </div>

    ${Object.entries(a).map(([e,t])=>`
    <div class="method-section">
        <div class="method-title">
            <h3>${e} Method (${t.length} calculations)</h3>
            <p style="margin: 5px 0; font-size: 14px; color: #666;">${l[e]||"Unknown method"}</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Calculation Date</th>
                    <th>Period</th>
                    <th>Recharge (mm)</th>
                    <th>Recharge (in)</th>
                    <th>Specific Yield</th>
                </tr>
            </thead>
            <tbody>
                ${t.sort((e,t)=>new Date(t.calculation_date).getTime()-new Date(e.calculation_date).getTime()).map(e=>`
                <tr>
                    <td>${new Date(e.calculation_date).toLocaleDateString()}</td>
                    <td>${new Date(e.start_date).toLocaleDateString()} - ${new Date(e.end_date).toLocaleDateString()}</td>
                    <td>${e.recharge_mm?.toFixed(2)||"—"}</td>
                    <td>${e.recharge_inches?.toFixed(3)||"—"}</td>
                    <td>${e.specific_yield?.toFixed(3)||"—"}</td>
                </tr>
                `).join("")}
            </tbody>
        </table>
    </div>
    `).join("")}

    <div class="no-print" style="margin-top: 40px; text-align: center;">
        <button onclick="window.print()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer;">
            Print Report
        </button>
    </div>
</body>
</html>
  `}(e,t);o(l,a||`recharge_report_${t.well_number}_${new Date().toISOString().split("T")[0]}.html`,"text/html");let r=window.open("","_blank");r&&(r.document.write(l),r.document.close(),r.focus())}function o(e,t,a){let l=new Blob([e],{type:a}),r=URL.createObjectURL(l),i=document.createElement("a");i.href=r,i.download=t,document.body.appendChild(i),i.click(),document.body.removeChild(i),URL.revokeObjectURL(r)}function d(e,t,a){return t||a?e.filter(e=>{let l=new Date(e.timestamp_utc),r=new Date(t||0),i=a?new Date(a):new Date;return l>=r&&l<=i}):e}a.d(t,{Kj:()=>n,OV:()=>i,Sz:()=>r,_W:()=>s,cv:()=>d,h:()=>l})},2029:(e,t,a)=>{"use strict";a.r(t),a.d(t,{default:()=>i,metadata:()=>r});var l=a(9510);a(5023);let r={title:"Water Level Visualizer",description:"Mobile water level monitoring data visualization",keywords:["water level","monitoring","groundwater","visualization"],authors:[{name:"Water Level Monitoring Team"}],viewport:{width:"device-width",initialScale:1,maximumScale:1,userScalable:!1},themeColor:"#3b82f6",manifest:"/manifest.json",appleWebApp:{capable:!0,statusBarStyle:"default",title:"Water Level Visualizer"},icons:{icon:"/favicon.ico",apple:"/apple-touch-icon.png"}};function i({children:e}){return(0,l.jsxs)("html",{lang:"en",children:[(0,l.jsxs)("head",{children:[l.jsx("meta",{name:"format-detection",content:"telephone=no"}),l.jsx("meta",{name:"mobile-web-app-capable",content:"yes"}),l.jsx("meta",{name:"apple-mobile-web-app-capable",content:"yes"}),l.jsx("meta",{name:"apple-mobile-web-app-status-bar-style",content:"default"}),l.jsx("link",{rel:"preconnect",href:"https://sql.js.org"})]}),l.jsx("body",{className:"min-h-screen bg-gray-50",children:(0,l.jsxs)("div",{className:"flex flex-col min-h-screen",children:[l.jsx("main",{className:"flex-1",children:e}),(0,l.jsxs)("footer",{className:"bg-white border-t border-gray-200 py-4 px-4 text-center text-sm text-gray-500",children:[l.jsx("p",{children:"Water Level Monitoring System"}),l.jsx("p",{className:"text-xs mt-1",children:"Mobile Visualizer v1.0"})]})]})})]})}},5023:()=>{}};