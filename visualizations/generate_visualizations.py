import pandas as pd
import panel as pn
import os
from speedtest_visualizer import SpeedTestVisualizer
import geopandas as gpd
import numpy as np

pn.extension('plotly')

# Load Data
base_dir = os.path.dirname(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data')
start_week = "2025-07-18"
end_date = "2025-07-23"
start_month = "2025-06-23"
mlab_file = os.path.join(data_dir, f"mlab_ndt_{start_week}_to_{end_date}.csv")
cloudflare_file = os.path.join(data_dir, f"cloudflare_speedtest_{start_month}_to_{end_date}.csv")

df_mlab = pd.read_csv(mlab_file)
df_cloudflare = pd.read_csv(cloudflare_file)
# fillna with 0
df_mlab['clientASN'] = df_mlab['clientASN'].fillna(0)
df_mlab['clientASN'] = df_mlab['clientASN'].astype(int)
# Preprocess M-Lab
df_mlab['latencyMs'] = df_mlab['latency']
df_mlab['serverPoP'] = df_mlab['serverCity']
print(df_mlab['clientASN'].value_counts())

# Build M-Lab location map

df_mlab['key'] = df_mlab.apply(
    lambda row: f"{row['clientCity']}, {row['clientCountry']} (to {row['serverPoP']})", axis=1
)
df_mlab = df_mlab.groupby('key').filter(lambda x: len(x) >= 1000)
location_map_mlab = {
    row['key']: (row['clientCity'], row['clientCountry'], row['serverPoP'])
    for _, row in df_mlab[['clientCity', 'clientCountry', 'serverPoP', 'key']].dropna().drop_duplicates().iterrows()
}

# Build Cloudflare location map
df_cloudflare['key'] = df_cloudflare.apply(
    lambda row: f"{row['clientCity']}, {row['clientCountry']} (to {row['serverPoP']})", axis=1
)
df_cloudflare = df_cloudflare.groupby('key').filter(lambda x: len(x) >= 1000)
location_map_cloudflare = {
    row['key']: (row['clientCity'], row['clientCountry'], row['serverPoP'])
    for _, row in df_cloudflare[['clientCity', 'clientCountry', 'serverPoP', 'key']].dropna().drop_duplicates().iterrows()
}

starlink_asns = [14593, 27277, 45700]

visualizer = SpeedTestVisualizer()

def make_isp_boxplots(df, label, is_mlab):
    metrics = [
        ('latencyMs', 'Download Latency (ms)'),
        ('upload_latency', 'Upload Latency (ms)'),
        ('download', 'Download Speed (Mbps)'),
        ('upload', 'Upload Speed (Mbps)'),
        ('loss', 'Download Packet Loss Ratio (%)'),
        ('upload_loss', 'Upload Packet Loss Ratio (%)'),
    ]
    plots = []
    for metric, title in metrics:
        if metric in df.columns:
            d = df.copy()
            if not is_mlab and metric in ['download', 'upload']:
                d[metric] = d[metric] / 1e6
            fig = visualizer.plot_metric_boxplot(d, metric, title)
            plots.append(pn.pane.Plotly(fig, sizing_mode='stretch_width'))
    return pn.Column(*plots, sizing_mode='stretch_width', align='center')

# --- M-Lab Source/Destination Logic ---
starlink_sources_mlab = df_mlab[df_mlab['clientASN'].isin(starlink_asns)][['clientCity', 'clientCountry']].dropna()
starlink_sources_mlab['source'] = starlink_sources_mlab['clientCity'].astype(str) + ', ' + starlink_sources_mlab['clientCountry'].astype(str)
source_options_mlab = sorted([s for s in starlink_sources_mlab['source'].unique() if isinstance(s, str)])

source_select_mlab = pn.widgets.Select(name='Select Source (Starlink City)', options=source_options_mlab, width=400)
dest_select_mlab = pn.widgets.Select(name='Select Destination PoP', options=[], width=400)

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
    city, country = source.split(', ', 1)
    df_focus = df_mlab[
        (df_mlab['clientCity'] == city) &
        (df_mlab['clientCountry'] == country) &
        (df_mlab['serverPoP'] == dest)
    ].copy()
    # Filter top ISPs
    isp_counts = df_focus.groupby(['clientASN', 'clientASName']).size().reset_index(name='count')
    starlink_rows = isp_counts[isp_counts['clientASN'].isin(starlink_asns)]
    top_others = isp_counts[~isp_counts['clientASN'].isin(starlink_asns)].nlargest(10 - len(starlink_rows), 'count')
    top_isps = pd.concat([starlink_rows, top_others])
    df_focus = df_focus[df_focus['clientASN'].isin(top_isps['clientASN'])]
    print('I am in M-Lab')
    print(starlink_asns)
    print(df_focus['clientASN'].unique())
    print(df_focus['clientASName'].unique())
    return make_isp_boxplots(df_focus, "M-Lab", is_mlab=True)

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

source_select_cf = pn.widgets.Select(name='Select Source (Starlink City)', options=source_options_cf, width=400)
dest_select_cf = pn.widgets.Select(name='Select Destination PoP', options=[], width=400)

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
    city, country = source.split(', ', 1)
    df_focus = df_cloudflare[
        (df_cloudflare['clientCity'] == city) &
        (df_cloudflare['clientCountry'] == country) &
        (df_cloudflare['serverPoP'] == dest)
    ].copy()
    # Filter top ISPs
    isp_counts = df_focus.groupby(['clientASN', 'clientASName']).size().reset_index(name='count')
    starlink_rows = isp_counts[isp_counts['clientASN'].isin(starlink_asns)]
    top_others = isp_counts[~isp_counts['clientASN'].isin(starlink_asns)].nlargest(10 - len(starlink_rows), 'count')
    top_isps = pd.concat([starlink_rows, top_others])
    df_focus = df_focus[df_focus['clientASN'].isin(top_isps['clientASN'])]
    print(df_focus['clientASN'].unique())
    print(df_focus['clientASName'].unique())
    return make_isp_boxplots(df_focus, "Cloudflare", is_mlab=False)

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

# Load state-level Cloudflare data
cloudflare_state_file = '../data/cloudflare_speedtest_states_2025-06-23_to_2025-07-23.csv'
df_cloudflare_state = pd.read_csv(cloudflare_state_file)

# Load Starlink internal M-Lab data
starlink_internal_file = '../data/starlink_state_metrics_202506_to_202507.csv'
df_starlink_internal = pd.read_csv(starlink_internal_file)

# Ensure download/upload are in Mbps for all datasets
for df in [df_mlab, df_cloudflare_state]:
    if df['download'].max() > 1e4:  # Heuristic: if values are very large, they're in bps
        df['download'] = df['download'] / 1e6
    if df['upload'].max() > 1e4:
        df['upload'] = df['upload'] / 1e6

# Process Starlink internal data - it's already in Mbps, but we need to map columns
# The Starlink data has different column names: download_p50, upload_p50, latency_p50
df_starlink_internal['download'] = df_starlink_internal['download_p50']
df_starlink_internal['upload'] = df_starlink_internal['upload_p50']
df_starlink_internal['latencyMs'] = df_starlink_internal['latency_p50']
# Note: Starlink data doesn't have loss metric, so we'll skip it

mlab_metrics = ['download', 'upload', 'latencyMs', 'loss']
metric_labels = {
    'download': 'Download Speed (Mbps)',
    'upload': 'Upload Speed (Mbps)',
    'latencyMs': 'Upload Latency (ms)',
    'loss': 'Packet Loss Ratio',
}

# Aggregate by state/country - filter for US only
def aggregate_admin1(df, metrics, region_col='clientRegion', country_col='clientCountry'):
    # Filter for US data only
    df_us = df[df[country_col] == 'US'].copy()
    agg = df_us.groupby([region_col, country_col])[metrics].mean().reset_index()
    agg = agg.rename(columns={region_col: 'name', country_col: 'iso_a2'})
    return agg

# Special aggregation for Starlink internal data
def aggregate_starlink_internal(df, metrics):
    # Filter for US data only and map state names
    df_us = df[df['country_iso2'] == 'US'].copy()
    # Map state names to match shapefile (some may need adjustment)
    state_name_mapping = {
        'District of Columbia': 'District of Columbia',  # Keep as is
        # Add any other mappings if needed
    }
    df_us['name'] = df_us['state_name'].map(lambda x: state_name_mapping.get(x, x))
    agg = df_us.groupby('name')[metrics].mean().reset_index()
    agg['iso_a2'] = 'US'  # All are US
    return agg

mlab_admin1 = aggregate_admin1(df_mlab, mlab_metrics)
cf_admin1 = aggregate_admin1(df_cloudflare_state, mlab_metrics)
starlink_admin1 = aggregate_starlink_internal(df_starlink_internal, ['download', 'upload', 'latencyMs'])

# Filter shapefile for US only
gdf_admin1_us = gdf_admin1[gdf_admin1['iso_a2'] == 'US'].copy()

# Merge with shapefile
gdf_mlab = gdf_admin1_us.merge(mlab_admin1, on=['name', 'iso_a2'], how='left')
gdf_cf = gdf_admin1_us.merge(cf_admin1, on=['name', 'iso_a2'], how='left')
gdf_starlink = gdf_admin1_us.merge(starlink_admin1, on=['name', 'iso_a2'], how='left')

# Metric dropdown only (no country needed for US-only)
# Remove 'loss' from options since Starlink internal doesn't have it
available_metrics = ['download', 'upload', 'latencyMs']
metric_labels_available = {k: v for k, v in metric_labels.items() if k in available_metrics}
metric_select = pn.widgets.Select(name='Metric', options=list(metric_labels_available.values()), value='Download Speed (Mbps)', width=250, sizing_mode='stretch_width')

# Plotting helper for US-only maps
def plot_admin1_map_us(gdf, metric, title, vmin, vmax):
    import plotly.express as px
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

dashboard.show()