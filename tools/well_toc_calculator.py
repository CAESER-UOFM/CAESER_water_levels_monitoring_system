import pandas as pd
import requests
import json

def get_well_data(well_number, service_url):
    """Query the MONET Feature Service for a specific well"""
    # Build query parameters
    params = {
        'where': f"WN='{well_number}'",
        'outFields': 'Elevation,Surface_to_MP_ft',
        'f': 'json'
    }
    
    response = requests.get(service_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'features' in data and len(data['features']) > 0:
            return data['features'][0]['attributes']
    return None

def calculate_toc(elevation, surface_to_mp):
    """Calculate TOC from elevation and surface_to_mp"""
    if elevation is not None and surface_to_mp is not None:
        return elevation + surface_to_mp
    return None

def main():
    # ArcGIS Feature Service URL
    service_url = "https://services1.arcgis.com/EX9Lx0EdFAxE7zvX/arcgis/rest/services/MONET/FeatureServer/0/query"
    
    # Read the input CSV
    input_file = input("Enter the path to your CSV file: ")
    df = pd.read_csv(input_file)
    
    # Create new column for TOC if it doesn't exist
    if 'TOC' not in df.columns:
        df['TOC'] = None
    
    # Process each well
    for index, row in df.iterrows():
        well_number = row['WN']
        print(f"Processing well {well_number}...")
        
        well_data = get_well_data(well_number, service_url)
        if well_data:
            elevation = well_data.get('Elevation')
            surface_to_mp = well_data.get('Surface_to_MP_ft')
            toc = calculate_toc(elevation, surface_to_mp)
            
            if toc is not None:
                df.at[index, 'TOC'] = toc
                print(f"TOC calculated for well {well_number}: {toc}")
            else:
                print(f"Could not calculate TOC for well {well_number} - missing data")
        else:
            print(f"No data found for well {well_number}")
    
    # Save the updated CSV
    output_file = input_file.rsplit('.', 1)[0] + '_with_TOC.csv'
    df.to_csv(output_file, index=False)
    print(f"Updated data saved to {output_file}")

if __name__ == "__main__":
    main() 