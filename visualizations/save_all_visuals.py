import pandas as pd
from starlink_speedtest.visualizations.speedtest_visualizer import SpeedTestVisualizer

# Load your data
mlab_data = pd.read_csv('../../starlink_speedtest/data/mlab_ndt_2025-05-08_to_2025-05-13.csv')
cloudflare_data = pd.read_csv('../../starlink_speedtest/data/cloudflare_speedtest_2025-04-13_to_2025-05-13.csv')

visualizer = SpeedTestVisualizer()

# 1. Speed Comparison
speed_fig = visualizer.create_speed_comparison(mlab_data, cloudflare_data)
visualizer.save_figure(speed_fig, 'speed_comparison')

# 2. Latency Comparison
latency_fig = visualizer.create_latency_comparison(mlab_data, cloudflare_data)
visualizer.save_figure(latency_fig, 'latency_comparison')

# 3. Geographic Speed Map
geo_fig = visualizer.create_geographic_speed_map(mlab_data)  # or combine data as needed
visualizer.save_figure(geo_fig, 'geographic_speed_map')

# 4. Time Series Analysis
# If you have a date column, use it; otherwise, adjust accordingly
time_fig = visualizer.create_time_series_analysis(mlab_data, date_col='date')
visualizer.save_figure(time_fig, 'time_series_analysis')