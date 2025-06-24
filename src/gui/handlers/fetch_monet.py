# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 11:30:57 2025

@author: bledesma
"""

import requests
import pandas as pd

def fetch_monet_data(username, password, url, verbose=False):
    """
    Fetch Monet data from an ArcGIS FeatureService.
    Returns data with naive UTC timestamps.
    """
    # Generate the token
    token = generate_arcgis_token(username, password, verbose)

    # Define query parameters
    params = {
        'where': '1=1',
        'outFields': '*',
        'f': 'json',
        'token': token
    }

    try:
        # Fetch data from the service
        response = requests.get(url, params=params)
        response.raise_for_status()

        # Parse the response
        data = response.json()

        # Debugging: Print the raw response size and structure
        if verbose:
            print(f"Response size: {len(str(data))} bytes")
            print("Response keys:", data.keys())
            print(f"Number of features: {len(data.get('features', []))}")

        # Check for features
        features = data.get('features', [])
        if not features:
            print("No features returned by the service.")  # Always print this
            return {}

        # Extract attributes and convert to DataFrame
        attributes_list = [feature['attributes'] for feature in features]
        df = pd.DataFrame(attributes_list)
        
        print(f"Initial DataFrame shape: {df.shape}")  # Debug print
        print("Initial columns:", df.columns.tolist())  # Debug print

        # Filter columns (adjust as needed)
        required_columns = [
            'GWI_ID', 'Date_time', 'Num_etape',
            'DTW_1', 'DTW_2', 'Tape_error',
            'Comments'
        ]
        
        # Check if all required columns exist
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            print(f"Missing required columns: {missing_cols}")  # Debug print
            return {}

        df = df[required_columns]
        print(f"DataFrame shape after filtering: {df.shape}")  # Debug print
        
        # Convert milliseconds to naive UTC datetime (simpler conversion)
        df['Date_time'] = pd.to_datetime(df['Date_time'], unit='ms')  # This gives naive UTC
        
        # Handle NaT values before string conversion
        df = df.dropna(subset=['Date_time'])  # Remove rows with NaT timestamps

        # Format Date_time as string in UTC before grouping
        df['Date_time'] = df['Date_time'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(x) else None)

        # Handle dry wells and empty measurements
        df['is_dry'] = df['Comments'].str.lower().str.contains('dry', na=False)
        if df['is_dry'].any():
            print(f"Found {df['is_dry'].sum()} dry well measurements")
            df.loc[df['is_dry'], ['DTW_1', 'DTW_2']] = None
            df.loc[df['is_dry'], 'Comments'] = df.loc[df['is_dry'], 'Comments'].str.replace(r'(?i)dry|well was dry|well is dry', '').str.strip()
        
        # Debug: Check for duplicates and keep the most complete record
        duplicates = df[df.duplicated(['GWI_ID', 'Date_time'], keep=False)]
        if not duplicates.empty:
            print(f"Found {len(duplicates)} duplicate rows")
            if verbose:
                print("Duplicate measurements:")
                print(duplicates.sort_values(['GWI_ID', 'Date_time']))
            
            df = df.groupby(['GWI_ID', 'Date_time']).apply(
                lambda x: x.loc[x.notna().sum(axis=1).idxmax()]
            ).reset_index(drop=True)
            
            print(f"Kept the most complete record for each duplicate timestamp")
        
        # Group by GWI_ID and return (Date_time is now formatted UTC string)
        monet_data = {gwi_id: group_df.reset_index(drop=True)
                      for gwi_id, group_df in df.groupby('GWI_ID')}

        print(f"Number of wells in processed data: {len(monet_data)}")  # Debug print
        if verbose:
            print("Processed data:", monet_data)

        return monet_data

    except Exception as e:
        print(f"Error in fetch_monet_data: {str(e)}")  # Always print errors
        if verbose:
            import traceback
            print("Full traceback:")
            print(traceback.format_exc())
        return {}

def generate_arcgis_token(username, password, verbose=False):
    """
    Generate an ArcGIS token for accessing secured services.

    Parameters:
        username (str): Your ArcGIS account username.
        password (str): Your ArcGIS account password.
        verbose (bool): Print debug information if True.

    Returns:
        str: The generated token.
    """
    # Token generation URL
    token_url = "https://www.arcgis.com/sharing/rest/generateToken"

    # Parameters for the token request
    token_params = {
        'username': username,
        'password': password,
        'client': 'referer',
        'referer': 'https://www.arcgis.com',
        'expiration': 60,  # Token valid for 60 minutes
        'f': 'json'
    }

    try:
        # Make the POST request to get the token
        response = requests.post(token_url, data=token_params)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Parse the response JSON
        token_data = response.json()

        # Extract the token
        token = token_data.get("token")
        if not token:
            raise ValueError("Token not found in the response. Check credentials or service access.")

        if verbose:
            print("Token successfully retrieved:")
            print(token)

        return token

    except Exception as e:
        if verbose:
            print("An error occurred while generating the token:")
            print(e)
        raise

