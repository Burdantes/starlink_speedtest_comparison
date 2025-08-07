import pandas as pd
from google.cloud import bigquery
import logging
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLabNDTCollector:
    def __init__(self, project_id="measurement-lab"):
        """Initialize the M-Lab NDT data collector."""
        self.client = bigquery.Client(project=project_id)
        self.output_dir = os.path.join(os.path.dirname(__file__), '../data')
        os.makedirs(self.output_dir, exist_ok=True)

    def collect_ndt_data(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Collect NDT data from M-Lab for a given date range.
        
        Args:
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str, optional): End date in 'YYYY-MM-DD' format. Defaults to today.
        
        Returns:
            pd.DataFrame: DataFrame containing the NDT data
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        query = f"""
        WITH downloads AS (
          SELECT
            md.Value AS access_token,    server.Geo.City AS serverCity,
            server.Geo.CountryCode AS serverCountry,
            server.Network.ASName AS serverASName,
            server.Network.ASNumber AS serverASN,
            client.Geo.City AS clientCity,
            raw.clientIP As client_ip,
            raw.serverIP AS server_ip,
            client.Geo.CountryCode AS clientCountry,
            client.Geo.Subdivision1Name AS clientRegion,
            client.Geo.Latitude AS clientLat,
            client.Geo.Longitude AS clientLon,
            client.Network.ASNumber AS clientASN,
            client.Network.ASName AS clientASName,
            a.MeanThroughputMbps AS download,
            a.MinRTT AS latency,
            a.TestTime AS test_start,
            a.LossRate AS loss
          FROM measurement-lab.ndt.ndt7,
          UNNEST(raw.Download.ClientMetadata) AS md
          WHERE
            date BETWEEN '{start_date}' AND '{end_date}'
            AND raw.Download IS NOT NULL
            AND md.Name = "access_token"
        ),
        
        uploads AS (
          SELECT
            md.Value AS access_token,
            a.MeanThroughputMbps AS upload,
            a.MinRTT AS upload_latency,
            a.LossRate AS upload_loss
          FROM measurement-lab.ndt_raw.ndt7,
               UNNEST(raw.Upload.ClientMetadata) AS md
          WHERE
            date BETWEEN '{start_date}' AND '{end_date}'
            AND raw.Upload IS NOT NULL
            AND md.Name = "access_token"
        )
        
        SELECT
          d.client_ip,
          d.server_ip,
          d.serverCity,
          d.serverCountry,
          d.serverASN,
          d.serverASName,
          d.clientCity,
          d.clientCountry,
          d.clientRegion,
          d.clientLat,
          d.clientLon,
          d.clientASN,
          d.clientASName,
          d.download,
          d.latency,
          d.loss,
          d.test_start,
          u.upload,
          u.upload_latency,
          u.upload_loss,
          IF(d.clientASN IN (14593, 27277, 45700), 'Starlink', 'Other') AS group_type
        FROM downloads d
        LEFT JOIN uploads u
          ON d.access_token = u.access_token
        WHERE
          NOT REGEXP_CONTAINS(d.client_ip, ':') -- exclude IPv6
        """

        try:
            logger.info(f"Querying M-Lab NDT data from {start_date} to {end_date}")
            df = self.client.query(query).to_dataframe()
            
            # Save to CSV
            output_file = os.path.join(
                self.output_dir, 
                f'mlab_ndt_{start_date}_to_{end_date}.csv'
            )
            df.to_csv(output_file, index=False)
            logger.info(f"Saved M-Lab NDT data to {output_file}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error collecting M-Lab NDT data: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    collector = MLabNDTCollector()
    
    # Collect last 30 days of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)
    
    # Collect general NDT data
    df = collector.collect_ndt_data(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
