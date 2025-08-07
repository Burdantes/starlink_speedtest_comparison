import pandas as pd
import panel as pn
import os
import pickle
import json
import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

pn.extension('plotly')

# Load pre-processed data
base_dir = os.path.dirname(os.path.dirname(__file__))
processed_dir = os.path.join(base_dir, 'data', 'processed')

# Load boxplot statistics (much smaller files)
df_mlab = pd.read_csv(os.path.join(processed_dir, 'mlab_boxplot_stats.csv'))
df_cloudflare = pd.read_csv(os.path.join(processed_dir, 'cloudflare_boxplot_stats.csv'))

# Load state-level data
df_cloudflare_state = pd.read_csv(os.path.join(processed_dir, 'cloudflare_state_aggregated.csv'))
df_starlink_internal = pd.read_csv(os.path.join(processed_dir, 'starlink_state_aggregated.csv'))

# Load location maps
with open(os.path.join(processed_dir, 'location_maps.pkl'), 'rb') as f:
    location_maps = pickle.load(f)
    location_map_mlab = location_maps['mlab']
    location_map_cloudflare = location_maps['cloudflare']

print("Loaded pre-processed data:")
print(f"M-Lab records: {len(df_mlab)}")
print(f"Cloudflare records: {len(df_cloudflare)}")
print(f"Cloudflare state records: {len(df_cloudflare_state)}")
print(f"Starlink internal records: {len(df_starlink_internal)}")

# Starlink ASNs
starlink_asns = [14593, 27277, 45700]

def create_boxplot_from_stats(stats_data, metric, title):
    """Create a proper boxplot from pre-calculated statistics."""
    print(f"Creating boxplot for {metric} with {len(stats_data)} records")
    
    fig = go.Figure()
    
    # Group by ISP
    isp_groups = stats_data.groupby(['clientASN', 'clientASName'])
    print(f"Found {len(isp_groups)} ISP groups")
    
    # Identify Starlink ISPs
    starlink_names = []
    other_names = []
    
    for (asn, asname), group in isp_groups:
        isp_label = f"{asn} - {asname}"
        if asn in starlink_asns:
            starlink_names.append(isp_label)
        else:
            other_names.append(isp_label)
    
    # Sort: Starlink first, then others alphabetically
    ordered_names = starlink_names + sorted(other_names)
    print(f"Ordered ISPs: {ordered_names}")
    
    for isp_label in ordered_names:
        asn, asname = isp_label.split(' - ', 1)
        asn = int(asn)
        group = stats_data[(stats_data['clientASN'] == asn) & (stats_data['clientASName'] == asname)]
        
        print(f"Processing {isp_label}: {len(group)} records")
        
        if len(group) == 0:
            continue
            
        # Get stats for this metric
        all_stats = []
        for _, row in group.iterrows():
            if 'boxplot_stats' in row and isinstance(row['boxplot_stats'], str):
                try:
                    stats = json.loads(row['boxplot_stats'])
                    if metric in stats:
                        all_stats.append(stats[metric])
                except Exception as e:
                    print(f"Error parsing stats for {isp_label}: {e}")
                    continue
        
        print(f"Found {len(all_stats)} valid stats for {isp_label}")
        
        if not all_stats:
            continue
            
        # Generate representative data points from the statistics
        all_data_points = []
        for stats in all_stats:
            # Generate points that represent the distribution
            median = stats['median']
            q1 = stats['q1']
            q3 = stats['q3']
            min_val = stats['min']
            # Don't use max_val as it's often an outlier
            
            # Generate points to represent the distribution
            n_points = min(stats['count'], 50)  # Limit to reasonable number
            
            if n_points > 0:
                # Generate points that approximate the distribution
                # 50% of points around median, 25% around Q1, 25% around Q3
                median_points = int(n_points * 0.5)
                q1_points = int(n_points * 0.25)
                q3_points = n_points - median_points - q1_points
                
                # Generate points with some spread, but stay within reasonable bounds
                # Use Q3 as upper bound instead of max to avoid outliers
                median_spread = (q3 - q1) / 4
                q1_spread = max((median - q1) / 4, (q1 - min_val) / 4)
                q3_spread = (q3 - median) / 4
                
                # Add points around median
                if median_points > 0:
                    median_data = np.random.normal(median, median_spread, median_points)
                    # Clip to reasonable bounds
                    median_data = np.clip(median_data, min_val, q3)
                    all_data_points.extend(median_data)
                
                # Add points around Q1
                if q1_points > 0:
                    q1_data = np.random.normal(q1, q1_spread, q1_points)
                    # Clip to reasonable bounds
                    q1_data = np.clip(q1_data, min_val, median)
                    all_data_points.extend(q1_data)
                
                # Add points around Q3
                if q3_points > 0:
                    q3_data = np.random.normal(q3, q3_spread, q3_points)
                    # Clip to reasonable bounds
                    q3_data = np.clip(q3_data, median, q3)
                    all_data_points.extend(q3_data)
                
                # Only add outliers that are within a reasonable range (not extreme)
                # Filter outliers to only include those that aren't too extreme
                reasonable_outliers = []
                for outlier in stats['outliers']:
                    # Only include outliers that aren't more than 2x the Q3 value
                    if outlier <= q3 * 2:
                        reasonable_outliers.append(outlier)
                
                all_data_points.extend(reasonable_outliers)
        
        if all_data_points:
            # Color: red for Starlink, gray for others
            color = '#FF4B4B' if asn in starlink_asns else '#888888'
            
            # Create boxplot trace with the generated data points
            fig.add_trace(go.Box(
                x=[isp_label] * len(all_data_points),
                y=all_data_points,
                name=isp_label,
                marker_color=color,
                boxpoints='outliers',
                showlegend=(asn in starlink_asns),
                legendgroup='Starlink' if asn in starlink_asns else 'Other'
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title="ASN - ISP Name",
        yaxis_title=title,
        height=450,
        template='plotly_white',
        legend=dict(itemsizing='constant', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    print(f"Created boxplot with {len(fig.data)} traces")
    return fig

def make_isp_boxplots(stats_data, label, is_mlab):
    metrics = [
        ('latencyMs', 'Download Latency (ms)'),
        ('upload_latency', 'Upload Latency (ms)'),
        ('download', 'Download Speed (Mbps)'),
        ('upload', 'Upload Speed (Mbps)'),
        ('loss', 'Download Packet Loss Ratio'),
        ('upload_loss', 'Upload Packet Loss Ratio'),
    ]
    plots = []
    for metric, title in metrics:
        if metric in ['download', 'upload', 'latencyMs', 'loss']:
            fig = create_boxplot_from_stats(stats_data, metric, title)
            plots.append(pn.pane.Plotly(fig, sizing_mode='stretch_width'))
    return pn.Column(*plots, sizing_mode='stretch_width', align='center')

def create_measurement_details_panel(stats_data):
    """Create a panel showing detailed measurement information."""
    # Get unique ISPs
    isps = stats_data.groupby(['clientASN', 'clientASName']).first().reset_index()
    isp_options = [f"{row['clientASN']} - {row['clientASName']}" for _, row in isps.iterrows()]
    
    isp_select = pn.widgets.Select(name='Select ISP for Details', options=isp_options, sizing_mode='stretch_width')
    
    def show_isp_details(isp_label):
        if not isp_label:
            return pn.pane.Markdown("Select an ISP to see measurement details.", sizing_mode='stretch_width')
        
        asn, asname = isp_label.split(' - ', 1)
        asn = int(asn)
        
        # Get data for this ISP
        isp_data = stats_data[(stats_data['clientASN'] == asn) & (stats_data['clientASName'] == asname)]
        
        if len(isp_data) == 0:
            return pn.pane.Markdown("No data available for this ISP.", sizing_mode='stretch_width')
        
        # Collect all statistics
        all_stats = {}
        for _, row in isp_data.iterrows():
            if 'boxplot_stats' in row and isinstance(row['boxplot_stats'], str):
                try:
                    stats = json.loads(row['boxplot_stats'])
                    for metric in ['download', 'upload', 'latencyMs', 'loss']:
                        if metric in stats:
                            if metric not in all_stats:
                                all_stats[metric] = []
                            all_stats[metric].append(stats[metric])
                except:
                    continue
        
        if not all_stats:
            return pn.pane.Markdown("No valid statistics found for this ISP.", sizing_mode='stretch_width')
        
        # Create detailed view
        details_html = f"""
        <div style='text-align:left; padding: 20px;'>
            <h3>Measurement Details for {isp_label}</h3>
            <p><strong>Total Locations:</strong> {len(isp_data)}</p>
        """
        
        for metric, metric_stats in all_stats.items():
            if metric_stats:
                total_measurements = sum([s['count'] for s in metric_stats])
                details_html += f"""
                <h4>{metric.upper()} Statistics:</h4>
                <p><strong>Total Measurements:</strong> {total_measurements:,}</p>
                <table style='width:100%; border-collapse: collapse; margin-bottom: 20px;'>
                    <tr style='background-color: #f0f0f0;'>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Location</th>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Count</th>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Min</th>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Q1</th>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Median</th>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Q3</th>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Max</th>
                        <th style='border: 1px solid #ddd; padding: 8px;'>Outliers</th>
                    </tr>
                """
                
                for i, stats in enumerate(metric_stats):
                    details_html += f"""
                        <tr>
                            <td style='border: 1px solid #ddd; padding: 8px;'>Location {i+1}</td>
                            <td style='border: 1px solid #ddd; padding: 8px;'>{stats['count']:,}</td>
                            <td style='border: 1px solid #ddd; padding: 8px;'>{stats['min']:.2f}</td>
                            <td style='border: 1px solid #ddd; padding: 8px;'>{stats['q1']:.2f}</td>
                            <td style='border: 1px solid #ddd; padding: 8px;'>{stats['median']:.2f}</td>
                            <td style='border: 1px solid #ddd; padding: 8px;'>{stats['q3']:.2f}</td>
                            <td style='border: 1px solid #ddd; padding: 8px;'>{stats['max']:.2f}</td>
                            <td style='border: 1px solid #ddd; padding: 8px;'>{len(stats['outliers'])}</td>
                        </tr>
                    """
                
                details_html += "</table>"
        
        details_html += "</div>"
        
        return pn.pane.HTML(details_html, sizing_mode='stretch_width')
    
    return pn.Column(
        isp_select,
        pn.bind(show_isp_details, isp_label=isp_select),
        sizing_mode='stretch_width',
        align='center'
    )

# --- M-Lab Source/Destination Logic ---
starlink_sources_mlab = df_mlab[df_mlab['clientASN'].isin(starlink_asns)][['clientCity', 'clientCountry']].dropna()
starlink_sources_mlab['source'] = starlink_sources_mlab['clientCity'].astype(str) + ', ' + starlink_sources_mlab['clientCountry'].astype(str)
source_options_mlab = sorted([s for s in starlink_sources_mlab['source'].unique() if isinstance(s, str)])

source_select_mlab = pn.widgets.Select(name='Select Source (Starlink City)', options=source_options_mlab, sizing_mode='stretch_width')
dest_select_mlab = pn.widgets.Select(name='Select Destination PoP', options=[], sizing_mode='stretch_width')

def update_dest_options_mlab(event):
    if not event.new:
        dest_select_mlab.options = []
        return
    city, country = event.new.split(', ', 1)
    dests = df_mlab[
        (df_mlab['clientCity'] == city) &
        (df_mlab['clientCountry'] == country) &
        (df_mlab['clientASN'].isin(starlink_asns))
    ]['serverPoP'].dropna().unique()
    dest_select_mlab.options = sorted(dests)
    if dests.size > 0:
        dest_select_mlab.value = sorted(dests)[0]
    else:
        dest_select_mlab.value = None

source_select_mlab.param.watch(update_dest_options_mlab, 'value')

def update_mlab_plot(source, dest):
    if not source or not dest:
        return pn.pane.Markdown('Select both a source and a destination.')
    
    print(f"Updating M-Lab plot for source: {source}, dest: {dest}")
    
    city, country = source.split(', ', 1)
    df_focus = df_mlab[
        (df_mlab['clientCity'] == city) &
        (df_mlab['clientCountry'] == country) &
        (df_mlab['serverPoP'] == dest)
    ].copy()
    
    print(f"Found {len(df_focus)} records for {city}, {country} to {dest}")
    
    # Filter top ISPs
    isp_counts = df_focus.groupby(['clientASN', 'clientASName']).size().reset_index(name='count')
    starlink_rows = isp_counts[isp_counts['clientASN'].isin(starlink_asns)]
    top_others = isp_counts[~isp_counts['clientASN'].isin(starlink_asns)].nlargest(10 - len(starlink_rows), 'count')
    top_isps = pd.concat([starlink_rows, top_others])
    df_focus = df_focus[df_focus['clientASN'].isin(top_isps['clientASN'])]
    
    print(f"After filtering, have {len(df_focus)} records from {len(top_isps)} ISPs")
    print(f"ISPs: {list(top_isps['clientASN'].astype(str) + ' - ' + top_isps['clientASName'])}")
    
    # Create the boxplots and details panel
    boxplots = make_isp_boxplots(df_focus, "M-Lab", is_mlab=True)
    details_panel = create_measurement_details_panel(df_focus)
    
    return pn.Column(
        boxplots,
        pn.pane.Markdown("---", sizing_mode='stretch_width'),
        details_panel,
        sizing_mode='stretch_width',
        align='center'
    )

mlab_panel = pn.Column(
    pn.pane.Markdown(
        """
        <div style='text-align:center'>
        <h2>M-Lab Speed Test Results</h2>
        <p><b>M-Lab (Measurement Lab)</b> is a research platform that provides open, verifiable speed test data. M-Lab tests are typically run by users via web-based tools or integrations in search engines. The tests use the NDT protocol and are designed to measure the maximum achievable throughput, latency, and packet loss between the client and a geographically close server. M-Lab's infrastructure is distributed globally and is often used for academic and regulatory research.</p>
        <p>The visuals below show Starlink's performance compared to other ISPs for the selected source and destination, using M-Lab data.</p>
        </div>
        """,
        sizing_mode='stretch_width',
        align='center',
    ),
    source_select_mlab,
    dest_select_mlab,
    pn.bind(update_mlab_plot, source=source_select_mlab, dest=dest_select_mlab),
    align='center',
    sizing_mode='stretch_width'
)

# --- Cloudflare Source/Destination Logic ---
starlink_sources_cf = df_cloudflare[df_cloudflare['clientASN'].isin(starlink_asns)][['clientCity', 'clientCountry']].dropna()
starlink_sources_cf['source'] = starlink_sources_cf['clientCity'].astype(str) + ', ' + starlink_sources_cf['clientCountry'].astype(str)
source_options_cf = sorted([s for s in starlink_sources_cf['source'].unique() if isinstance(s, str)])

source_select_cf = pn.widgets.Select(name='Select Source (Starlink City)', options=source_options_cf, sizing_mode='stretch_width')
dest_select_cf = pn.widgets.Select(name='Select Destination PoP', options=[], sizing_mode='stretch_width')

def update_dest_options_cf(event):
    if not event.new:
        dest_select_cf.options = []
        return
    city, country = event.new.split(', ', 1)
    dests = df_cloudflare[
        (df_cloudflare['clientCity'] == city) &
        (df_cloudflare['clientCountry'] == country) &
        (df_cloudflare['clientASN'].isin(starlink_asns))
    ]['serverPoP'].dropna().unique()
    dest_select_cf.options = sorted(dests)
    if dests.size > 0:
        dest_select_cf.value = sorted(dests)[0]
    else:
        dest_select_cf.value = None

source_select_cf.param.watch(update_dest_options_cf, 'value')

def update_cf_plot(source, dest):
    if not source or not dest:
        return pn.pane.Markdown('Select both a source and a destination.')
    
    print(f"Updating Cloudflare plot for source: {source}, dest: {dest}")
    
    city, country = source.split(', ', 1)
    df_focus = df_cloudflare[
        (df_cloudflare['clientCity'] == city) &
        (df_cloudflare['clientCountry'] == country) &
        (df_cloudflare['serverPoP'] == dest)
    ].copy()
    
    print(f"Found {len(df_focus)} records for {city}, {country} to {dest}")
    
    # Filter top ISPs
    isp_counts = df_focus.groupby(['clientASN', 'clientASName']).size().reset_index(name='count')
    starlink_rows = isp_counts[isp_counts['clientASN'].isin(starlink_asns)]
    top_others = isp_counts[~isp_counts['clientASN'].isin(starlink_asns)].nlargest(10 - len(starlink_rows), 'count')
    top_isps = pd.concat([starlink_rows, top_others])
    df_focus = df_focus[df_focus['clientASN'].isin(top_isps['clientASN'])]
    
    print(f"After filtering, have {len(df_focus)} records from {len(top_isps)} ISPs")
    print(f"ISPs: {list(top_isps['clientASN'].astype(str) + ' - ' + top_isps['clientASName'])}")
    
    # Create the boxplots and details panel
    boxplots = make_isp_boxplots(df_focus, "Cloudflare", is_mlab=False)
    details_panel = create_measurement_details_panel(df_focus)
    
    return pn.Column(
        boxplots,
        pn.pane.Markdown("---", sizing_mode='stretch_width'),
        details_panel,
        sizing_mode='stretch_width',
        align='center'
    )

cf_panel = pn.Column(
    pn.pane.Markdown(
        """
        <div style='text-align:center'>
        <h2>Cloudflare Speed Test Results</h2>
        <p><b>Cloudflare</b> operates a global CDN and security platform, and its speed test is available at <a href='https://speed.cloudflare.com/'>speed.cloudflare.com</a>. Cloudflare's test is browser-based and leverages their own infrastructure, which is highly distributed and optimized for low latency. The test measures download/upload speeds, latency, and packet loss, but may be influenced by Cloudflare's network optimizations and peering relationships, which can differ from those of M-Lab.</p>
        <p>The visuals below show Starlink's performance compared to other ISPs for the selected source and destination, using Cloudflare data.</p>
        </div>
        """,
        sizing_mode='stretch_width',
        align='center',
    ),
    source_select_cf,
    dest_select_cf,
    pn.bind(update_cf_plot, source=source_select_cf, dest=dest_select_cf),
    align='center',
    sizing_mode='stretch_width'
)

intro = pn.pane.Markdown(
    """
    <div style='text-align:center'>
    <h1>Understanding Starlink Performance: M-Lab vs Cloudflare</h1>
    <p>
    Our goal was to get a good understanding of how well Starlink seems to be performing according to two large speed-test infrastructures: <b>M-Lab</b> and <b>Cloudflare</b>.<br><br>
    <b>How are these speed-tests different?</b><br>
    </p>
    </div>
    """,
    sizing_mode='stretch_width',
    align='center',
)

# --- State-level (Admin1) Mapping Tab ---
admin1_shp = '../data/ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp'
gdf_admin1 = gpd.read_file(admin1_shp)

# Filter shapefile for US only
gdf_admin1_us = gdf_admin1[gdf_admin1['iso_a2'] == 'US'].copy()

# Merge with shapefile
gdf_cf = gdf_admin1_us.merge(df_cloudflare_state, on=['name', 'iso_a2'], how='left')
gdf_starlink = gdf_admin1_us.merge(df_starlink_internal, on=['name', 'iso_a2'], how='left')

# For M-Lab state data, we need to aggregate from the main dataset
def aggregate_mlab_state_data():
    df_mlab_us = df_mlab[df_mlab['clientCountry'] == 'US'].copy()
    
    # We need to map cities to states for proper aggregation
    # For now, let's use the clientRegion if available, otherwise we'll need to create a mapping
    if 'clientRegion' in df_mlab_us.columns:
        state_col = 'clientRegion'
    else:
        # Create a simple city-to-state mapping for major cities
        city_to_state = {
            'New York': 'New York',
            'Los Angeles': 'California',
            'Chicago': 'Illinois',
            'Houston': 'Texas',
            'Phoenix': 'Arizona',
            'Philadelphia': 'Pennsylvania',
            'San Antonio': 'Texas',
            'San Diego': 'California',
            'Dallas': 'Texas',
            'San Jose': 'California',
            'Austin': 'Texas',
            'Jacksonville': 'Florida',
            'Fort Worth': 'Texas',
            'Columbus': 'Ohio',
            'Charlotte': 'North Carolina',
            'San Francisco': 'California',
            'Indianapolis': 'Indiana',
            'Seattle': 'Washington',
            'Denver': 'Colorado',
            'Washington': 'District of Columbia',
            'Boston': 'Massachusetts',
            'El Paso': 'Texas',
            'Nashville': 'Tennessee',
            'Detroit': 'Michigan',
            'Oklahoma City': 'Oklahoma',
            'Portland': 'Oregon',
            'Las Vegas': 'Nevada',
            'Memphis': 'Tennessee',
            'Louisville': 'Kentucky',
            'Baltimore': 'Maryland',
            'Milwaukee': 'Wisconsin',
            'Albuquerque': 'New Mexico',
            'Tucson': 'Arizona',
            'Fresno': 'California',
            'Sacramento': 'California',
            'Mesa': 'Arizona',
            'Kansas City': 'Missouri',
            'Atlanta': 'Georgia',
            'Long Beach': 'California',
            'Colorado Springs': 'Colorado',
            'Raleigh': 'North Carolina',
            'Miami': 'Florida',
            'Virginia Beach': 'Virginia',
            'Omaha': 'Nebraska',
            'Oakland': 'California',
            'Minneapolis': 'Minnesota',
            'Tulsa': 'Oklahoma',
            'Arlington': 'Texas',
            'Tampa': 'Florida',
            'New Orleans': 'Louisiana',
            'Wichita': 'Kansas',
            'Cleveland': 'Ohio',
            'Bakersfield': 'California',
            'Aurora': 'Colorado',
            'Anaheim': 'California',
            'Honolulu': 'Hawaii',
            'Santa Ana': 'California',
            'Corpus Christi': 'Texas',
            'Riverside': 'California',
            'Lexington': 'Kentucky',
            'Stockton': 'California',
            'Henderson': 'Nevada',
            'Saint Paul': 'Minnesota',
            'St. Louis': 'Missouri',
            'Fort Wayne': 'Indiana',
            'Jersey City': 'New Jersey',
            'Chandler': 'Arizona',
            'Madison': 'Wisconsin',
            'Lubbock': 'Texas',
            'Scottsdale': 'Arizona',
            'Reno': 'Nevada',
            'Buffalo': 'New York',
            'Gilbert': 'Arizona',
            'Glendale': 'Arizona',
            'North Las Vegas': 'Nevada',
            'Winston-Salem': 'North Carolina',
            'Chesapeake': 'Virginia',
            'Norfolk': 'Virginia',
            'Fremont': 'California',
            'Garland': 'Texas',
            'Irving': 'Texas',
            'Hialeah': 'Florida',
            'Richmond': 'Virginia',
            'Boise': 'Idaho',
            'Spokane': 'Washington',
            'Baton Rouge': 'Louisiana',
            'Tacoma': 'Washington',
            'San Bernardino': 'California',
            'Grand Rapids': 'Michigan',
            'Huntsville': 'Alabama',
            'Salt Lake City': 'Utah',
            'Fayetteville': 'North Carolina',
            'Yonkers': 'New York',
            'Amarillo': 'Texas',
            'Glendale': 'California',
            'Montgomery': 'Alabama',
            'Aurora': 'Illinois',
            'Shreveport': 'Louisiana',
            'Akron': 'Ohio',
            'Little Rock': 'Arkansas',
            'Des Moines': 'Iowa',
            'Rochester': 'New York',
            'Toledo': 'Ohio',
            'Laredo': 'Texas',
            'Fort Collins': 'Colorado',
            'Springfield': 'Missouri',
            'Newark': 'New Jersey',
            'Plano': 'Texas',
            'Lincoln': 'Nebraska',
            'Anchorage': 'Alaska',
            'Orlando': 'Florida',
            'Greensboro': 'North Carolina',
            'Durham': 'North Carolina',
            'Chula Vista': 'California',
            'Irvine': 'California'
        }
        df_mlab_us['state'] = df_mlab_us['clientCity'].map(city_to_state)
        state_col = 'state'
    
    # Extract metrics from boxplot_stats for aggregation
    state_metrics = []
    
    for _, row in df_mlab_us.iterrows():
        if 'boxplot_stats' in row and isinstance(row['boxplot_stats'], str):
            try:
                stats = json.loads(row['boxplot_stats'])
                state_name = row[state_col] if state_col in row else None
                
                if state_name and state_name in city_to_state.values():
                    # Extract median values for each metric
                    metrics = {}
                    for metric in ['download', 'upload', 'latencyMs', 'loss']:
                        if metric in stats:
                            metrics[metric] = stats[metric]['median']
                    
                    if metrics:  # Only include if we have valid metrics
                        metrics['name'] = state_name
                        metrics['iso_a2'] = 'US'
                        state_metrics.append(metrics)
            except:
                continue
    
    if state_metrics:
        mlab_state_agg = pd.DataFrame(state_metrics)
        # Group by state and take the mean of medians
        mlab_state_agg = mlab_state_agg.groupby(['name', 'iso_a2']).agg({
            'download': 'mean',
            'upload': 'mean', 
            'latencyMs': 'mean',
            'loss': 'mean'
        }).reset_index()
    else:
        # Fallback: create empty DataFrame with correct structure
        mlab_state_agg = pd.DataFrame(columns=['name', 'iso_a2', 'download', 'upload', 'latencyMs', 'loss'])
    
    return mlab_state_agg

mlab_state_agg = aggregate_mlab_state_data()
gdf_mlab = gdf_admin1_us.merge(mlab_state_agg, on=['name', 'iso_a2'], how='left')

# Metric dropdown only (no country needed for US-only)
available_metrics = ['download', 'upload', 'latencyMs']
metric_labels = {
    'download': 'Download Speed (Mbps)',
    'upload': 'Upload Speed (Mbps)',
    'latencyMs': 'Upload Latency (ms)',
}
metric_labels_available = {k: v for k, v in metric_labels.items() if k in available_metrics}
metric_select = pn.widgets.Select(name='Metric', options=list(metric_labels_available.values()), value='Download Speed (Mbps)', sizing_mode='stretch_width')

# Plotting helper for US-only maps
def plot_admin1_map_us(gdf, metric, title, vmin, vmax):
    fig = px.choropleth(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color=metric,
        hover_name='name',
        hover_data={metric: ':.2f', 'iso_a2': True},
        title=title,
        color_continuous_scale='Viridis',
        labels={metric: metric},
        height=500,
        range_color=[vmin, vmax]
    )
    # Simple US-focused configuration
    fig.update_geos(
        scope='usa',
        showland=True,
        landcolor='rgb(243, 243, 243)',
        showcoastlines=True,
        coastlinecolor='rgb(204, 204, 204)',
        showocean=True,
        oceancolor='rgb(230, 230, 230)'
    )
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0}
    )
    return fig

# Callback for interactive maps (US-only with three datasets)
def update_state_maps(metric_label):
    if not metric_label:
        return pn.pane.Markdown("Please select a metric.")
    
    # Find the metric key from the label
    metric = None
    for k, v in metric_labels_available.items():
        if v == metric_label:
            metric = k
            break
    
    if not metric:
        return pn.pane.Markdown("Invalid metric selected.")
    
    # Compute global min/max for the metric (US data only)
    all_vals = pd.concat([gdf_mlab[metric], gdf_cf[metric], gdf_starlink[metric]], ignore_index=True)
    vmin, vmax = np.nanmin(all_vals), np.nanmax(all_vals)
    
    # Handle case where all values are NaN
    if np.isnan(vmin) or np.isnan(vmax):
        return pn.pane.Markdown(f"No data available for {metric_label}")
    
    mlab_fig = plot_admin1_map_us(gdf_mlab, metric, f"M-Lab: {metric_label}", vmin, vmax)
    cf_fig = plot_admin1_map_us(gdf_cf, metric, f"Cloudflare: {metric_label}", vmin, vmax)
    starlink_fig = plot_admin1_map_us(gdf_starlink, metric, f"Starlink Internal: {metric_label}", vmin, vmax)
    
    return pn.Column(
        pn.pane.Plotly(mlab_fig, config={'displayModeBar': False}, sizing_mode='stretch_width'),
        pn.pane.Markdown("""
        <div style='text-align:center'>
        ---
        <br>
        <b>Comparison:</b> The above map shows M-Lab data, the middle map shows Cloudflare data, and the bottom map shows Starlink's internal M-Lab data for the same metric across US states. All use the same color scale for direct comparison.
        </div>
        """, sizing_mode='stretch_width', align='center'),
        pn.pane.Plotly(cf_fig, config={'displayModeBar': False}, sizing_mode='stretch_width'),
        pn.pane.Markdown("""
        <div style='text-align:center'>
        ---
        <br>
        </div>
        """, sizing_mode='stretch_width', align='center'),
        pn.pane.Plotly(starlink_fig, config={'displayModeBar': False}, sizing_mode='stretch_width'),
        align='center',
        sizing_mode='stretch_width',
    )

state_map_panel = pn.Column(
    pn.pane.Markdown(
        """
        <div style='text-align:center'>
        <h2>US State-level Maps: M-Lab vs Cloudflare vs Starlink Internal</h2>
        <p>Select a metric to compare the average value at the state level across the United States for three datasets: M-Lab, Cloudflare, and Starlink's internal M-Lab data. All maps use the same color scale for direct comparison.</p>
        </div>
        """,
        sizing_mode='stretch_width',
        align='center',
    ),
    pn.Row(metric_select, align='center', sizing_mode='stretch_width'),
    pn.bind(update_state_maps, metric_label=metric_select),
    align='center',
    sizing_mode='stretch_width',
)

dashboard = pn.Column(
    intro,
    pn.Tabs(
        ("M-Lab", mlab_panel),
        ("Cloudflare", cf_panel),
        ("State-level Maps", state_map_panel),
        tabs_location='above',
        align='center',
        sizing_mode='stretch_width',
    ),
    align='center',
    sizing_mode='stretch_width',
)

if __name__ == "__main__":
    dashboard.show() 