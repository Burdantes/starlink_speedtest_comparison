import pandas as pd
import numpy as np
import os
from datetime import datetime
import pickle
import json

def calculate_boxplot_stats(group_data):
    """Calculate boxplot statistics for a group of data."""
    stats = {}
    for col in ['download', 'upload', 'latencyMs', 'loss']:
        if col in group_data.columns:
            data = group_data[col].dropna()
            if len(data) > 0:
                q1 = data.quantile(0.25)
                q3 = data.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                outliers = data[(data < lower_bound) | (data > upper_bound)]
                non_outliers = data[(data >= lower_bound) & (data <= upper_bound)]
                
                stats[col] = {
                    'min': non_outliers.min() if len(non_outliers) > 0 else data.min(),
                    'q1': q1,
                    'median': data.median(),
                    'q3': q3,
                    'max': non_outliers.max() if len(non_outliers) > 0 else data.max(),
                    'outliers': outliers.tolist(),
                    'count': len(data)
                }
    return stats

def preprocess_mlab_data():
    """Preprocess M-Lab data for visualization."""
    print("Processing M-Lab data...")
    
    # Load M-Lab data
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, 'data')
    start_week = "2025-07-18"
    end_date = "2025-07-23"
    mlab_file = os.path.join(data_dir, f"mlab_ndt_{start_week}_to_{end_date}.csv")
    
    df_mlab = pd.read_csv(mlab_file)
    
    # Preprocess
    df_mlab['latencyMs'] = df_mlab['latency']
    df_mlab['serverPoP'] = df_mlab['serverCity']
    df_mlab['clientASN'] = df_mlab['clientASN'].fillna(0).astype(int)
    
    # Create location key
    df_mlab['key'] = df_mlab.apply(
        lambda row: f"{row['clientCity']}, {row['clientCountry']} (to {row['serverPoP']})", axis=1
    )
    
    # Filter for locations with sufficient data
    df_mlab = df_mlab.groupby('key').filter(lambda x: len(x) >= 1000)
    
    # Calculate boxplot statistics for each location-ISP combination
    print("Calculating boxplot statistics for M-Lab data...")
    boxplot_stats = []
    
    for (key, asn, asname), group in df_mlab.groupby(['key', 'clientASN', 'clientASName']):
        if len(group) >= 10:  # Only include groups with sufficient data
            stats = calculate_boxplot_stats(group)
            if stats:  # Only include if we have valid stats
                row_data = {
                    'key': key,
                    'clientASN': asn,
                    'clientASName': asname,
                    'clientCity': group['clientCity'].iloc[0],
                    'clientCountry': group['clientCountry'].iloc[0],
                    'serverPoP': group['serverPoP'].iloc[0],
                    'boxplot_stats': json.dumps(stats)  # Convert to JSON string
                }
                boxplot_stats.append(row_data)
    
    return pd.DataFrame(boxplot_stats)

def preprocess_cloudflare_data():
    """Preprocess Cloudflare data for visualization."""
    print("Processing Cloudflare data...")
    
    # Load Cloudflare data
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, 'data')
    start_month = "2025-06-23"
    end_date = "2025-07-23"
    cloudflare_file = os.path.join(data_dir, f"cloudflare_speedtest_{start_month}_to_{end_date}.csv")
    
    df_cloudflare = pd.read_csv(cloudflare_file)
    
    # Create location key
    df_cloudflare['key'] = df_cloudflare.apply(
        lambda row: f"{row['clientCity']}, {row['clientCountry']} (to {row['serverPoP']})", axis=1
    )
    
    # Filter for locations with sufficient data
    df_cloudflare = df_cloudflare.groupby('key').filter(lambda x: len(x) >= 1000)
    
    # Calculate boxplot statistics for each location-ISP combination
    print("Calculating boxplot statistics for Cloudflare data...")
    boxplot_stats = []
    
    for (key, asn, asname), group in df_cloudflare.groupby(['key', 'clientASN', 'clientASName']):
        if len(group) >= 10:  # Only include groups with sufficient data
            stats = calculate_boxplot_stats(group)
            if stats:  # Only include if we have valid stats
                row_data = {
                    'key': key,
                    'clientASN': asn,
                    'clientASName': asname,
                    'clientCity': group['clientCity'].iloc[0],
                    'clientCountry': group['clientCountry'].iloc[0],
                    'serverPoP': group['serverPoP'].iloc[0],
                    'boxplot_stats': json.dumps(stats)  # Convert to JSON string
                }
                boxplot_stats.append(row_data)
    
    return pd.DataFrame(boxplot_stats)

def preprocess_state_data():
    """Preprocess state-level data for visualization."""
    print("Processing state-level data...")
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    # Load state-level Cloudflare data
    cloudflare_state_file = os.path.join(data_dir, "cloudflare_speedtest_states_2025-06-23_to_2025-07-23.csv")
    df_cloudflare_state = pd.read_csv(cloudflare_state_file)
    
    # Load Starlink internal data
    starlink_internal_file = os.path.join(data_dir, "starlink_state_metrics_202506_to_202507.csv")
    df_starlink_internal = pd.read_csv(starlink_internal_file)
    
    # Process Cloudflare state data - keep individual measurements
    df_cloudflare_state['download'] = df_cloudflare_state['download'] / 1e6  # Convert to Mbps
    df_cloudflare_state['upload'] = df_cloudflare_state['upload'] / 1e6
    
    # Process Starlink internal data - keep individual measurements
    df_starlink_internal['download'] = df_starlink_internal['download_p50']
    df_starlink_internal['upload'] = df_starlink_internal['upload_p50']
    df_starlink_internal['latencyMs'] = df_starlink_internal['latency_p50']
    
    # For state data, we'll keep the aggregated data since we don't have individual measurements
    # but we'll add the percentiles from the Starlink data
    cf_state_agg = df_cloudflare_state[df_cloudflare_state['clientCountry'] == 'US'].groupby('clientRegion').agg({
        'download': 'mean',
        'upload': 'mean',
        'latencyMs': 'mean',
        'loss': 'mean'
    }).reset_index()
    cf_state_agg['iso_a2'] = 'US'
    cf_state_agg = cf_state_agg.rename(columns={'clientRegion': 'name'})
    
    # For Starlink internal, we have percentiles, so let's use them
    starlink_state_agg = df_starlink_internal[df_starlink_internal['country_iso2'] == 'US'].copy()
    starlink_state_agg['iso_a2'] = 'US'
    starlink_state_agg = starlink_state_agg.rename(columns={'state_name': 'name'})
    
    return cf_state_agg, starlink_state_agg

def create_location_maps():
    """Create location mapping dictionaries."""
    print("Creating location maps...")
    
    # M-Lab location map
    df_mlab = preprocess_mlab_data()
    location_map_mlab = {
        row['key']: (row['clientCity'], row['clientCountry'], row['serverPoP'])
        for _, row in df_mlab[['clientCity', 'clientCountry', 'serverPoP', 'key']].dropna().drop_duplicates().iterrows()
    }
    
    # Cloudflare location map
    df_cloudflare = preprocess_cloudflare_data()
    location_map_cloudflare = {
        row['key']: (row['clientCity'], row['clientCountry'], row['serverPoP'])
        for _, row in df_cloudflare[['clientCity', 'clientCountry', 'serverPoP', 'key']].dropna().drop_duplicates().iterrows()
    }
    
    return location_map_mlab, location_map_cloudflare

def main():
    """Main preprocessing function."""
    print("Starting data preprocessing for visualization...")
    
    # Create output directory
    base_dir = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(base_dir, 'data', 'processed')
    os.makedirs(output_dir, exist_ok=True)
    
    # Process all data
    df_mlab = preprocess_mlab_data()
    df_cloudflare = preprocess_cloudflare_data()
    cf_state_agg, starlink_state_agg = preprocess_state_data()
    location_map_mlab, location_map_cloudflare = create_location_maps()
    
    # Save processed data
    print("Saving processed data...")
    
    # Save boxplot statistics (much smaller than full datasets)
    df_mlab.to_csv(os.path.join(output_dir, 'mlab_boxplot_stats.csv'), index=False)
    df_cloudflare.to_csv(os.path.join(output_dir, 'cloudflare_boxplot_stats.csv'), index=False)
    
    # Save state-level aggregated data
    cf_state_agg.to_csv(os.path.join(output_dir, 'cloudflare_state_aggregated.csv'), index=False)
    starlink_state_agg.to_csv(os.path.join(output_dir, 'starlink_state_aggregated.csv'), index=False)
    
    # Save location maps
    with open(os.path.join(output_dir, 'location_maps.pkl'), 'wb') as f:
        pickle.dump({
            'mlab': location_map_mlab,
            'cloudflare': location_map_cloudflare
        }, f)
    
    # Save metadata
    metadata = {
        'processed_date': datetime.now().isoformat(),
        'mlab_records': len(df_mlab),
        'cloudflare_records': len(df_cloudflare),
        'cf_state_records': len(cf_state_agg),
        'starlink_state_records': len(starlink_state_agg),
        'mlab_locations': len(location_map_mlab),
        'cloudflare_locations': len(location_map_cloudflare)
    }
    
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        import json
        json.dump(metadata, f, indent=2)
    
    print(f"Data preprocessing completed!")
    print(f"Output saved to: {output_dir}")
    print(f"Metadata: {metadata}")

if __name__ == "__main__":
    main() 