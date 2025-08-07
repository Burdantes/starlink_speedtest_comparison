from data_collection.mlab_ndt_collector import MLabNDTCollector
from data_collection.cloudflare_collector import CloudflareSpeedTestCollector
from data_collection.starlink_collector import StarlinkDataCollector
from datetime import datetime, timedelta

# Collect data
mlab_collector = MLabNDTCollector()
cloudflare_collector = CloudflareSpeedTestCollector()
starlink_collector = StarlinkDataCollector()

# Collect data for last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

mlab_data = mlab_collector.collect_ndt_data(start_date, end_date)
cloudflare_data = cloudflare_collector.collect_speed_data(start_date, end_date)
starlink_data = starlink_collector.collect_country_level_data([start_date.strftime('%Y%m'), end_date.strftime('%Y%m')])