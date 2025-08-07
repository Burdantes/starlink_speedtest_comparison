import pandas as pd
from google.cloud import bigquery
import logging
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
import json
import requests
import json
import time

def fetch_all_asns_simple(output_path: str, page_size: int = 10000):
    url = "https://api.asrank.caida.org/v2/graphql"
    headers = {"Content-Type": "application/json"}

    query_template = """
    {
      asns(first: %d, offset: %d) {
        pageInfo {
          hasNextPage
          first
        }
        edges {
          node {
            asn
            asnName
            rank
          }
        }
      }
    }
    """

    all_asns = []
    offset = 0
    page = 0

    while True:
        query = query_template % (page_size, offset)
        response = requests.post(url, headers=headers, json={"query": query})
        response.raise_for_status()
        data = response.json()["data"]["asns"]

        nodes = [edge["node"] for edge in data["edges"]]
        all_asns.extend(nodes)

        page += 1
        print(f"Fetched page {page}, total ASNs: {len(all_asns)}")

        if not data["pageInfo"]["hasNextPage"]:
            break

        offset += data["pageInfo"]["first"]
        time.sleep(0.1)

    with open(output_path, "w") as f:
        json.dump({"asns": all_asns}, f, indent=2)

    print(f"Saved {len(all_asns)} ASNs to {output_path}")


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_as_rank_mapping(as_rank_path: str) -> pd.DataFrame:
    """
    Load AS Rank JSON (flat list of ASNs) and return a DataFrame mapping clientASN to clientASName.
    """
    with open(as_rank_path, 'r') as f:
        data = json.load(f)

    if "asns" not in data:
        raise ValueError("Invalid AS Rank JSON: missing 'asns' key")

    df = pd.DataFrame(data["asns"])
    if "asn" not in df.columns or "asnName" not in df.columns:
        raise ValueError("Missing required fields 'asn' and/or 'asnName' in AS Rank data")

    df["asn"] = df["asn"].astype(int)
    df = df.rename(columns={"asn": "clientASN", "asnName": "clientASName"})
    return df

# fetch_all_asns_simple("../data/asns.json")

as_rank_df = load_as_rank_mapping(os.path.join("../data/asns.json"))


class CloudflareSpeedTestCollector:
    def __init__(self, project_id="measurement-lab"):
        """Initialize the Cloudflare speed test data collector."""
        self.client = bigquery.Client(project=project_id)
        self.output_dir = os.path.join(os.path.dirname(__file__), '../data')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # PoP to location mapping
        self.pop_to_location = {
            'CDG': 'Paris_FR',
            'JNB': 'Johannesburg_ZA',
            'SYD': 'Sydney_AU',
            'SOF': 'Sofia_BG',
            'YYC': 'Calgary_CA',
            'MIA': 'Miami_US',
            'SEA': 'Seattle_US',
            'LAX': 'Los Angeles_US',
            'SIN': 'Singapore_SG',
            'FRA': 'Frankfurt_DE',
            'GRU': 'São Paulo_BR',
            'LHR': 'London_GB',
            'MEL': 'Melbourne_AU',
            'ORD': 'Chicago_US',
            'ATL': 'Atlanta_US',
            'EWR': 'Newark_US',
            'CHC': 'Christchurch_NZ',
            'AMS': 'Amsterdam_NL',
            'NRT': 'Tokyo_JP',
            'EZE': 'Buenos Aires_AR',
            'IAD': 'Washington, D.C._US',
            'MAD': 'Madrid_ES',
            'LIS': 'Lisbon_PT',
            'FOR': 'Fortaleza_BR',
            'SCL': 'Santiago_CL',
            'WAW': 'Warsaw_PL',
            'NBO': 'Nairobi_KE',
            'SJC': 'San Jose_US',
            'LOS': 'Lagos_NG',
            'MRS': 'Marseille_FR',
            'MSP': 'Minneapolis_US',
            'JAX': 'Jacksonville_US',
            'TLH': 'Tallahassee_US',
            'AKL': 'Auckland_NZ',
            'BOG': 'Bogotá_CO',
            'DFW': 'Dallas/Fort Worth_US',
            'BNA': 'Nashville_US',
            'DEN': 'Denver_US',
            'SLC': 'Salt Lake City_US',
            'CGK': 'Jakarta_ID',
            'CPT': 'Cape Town_ZA',
            'LAS': 'Las Vegas_US',
            'MNL': 'Manila_PH',
            'QRO': 'Querétaro_MX',
            'MXP': 'Milan_IT',
            'PER': 'Perth_AU',
            'PHX': 'Phoenix_US',
            'SAN': 'San Diego_US'
        }

    def collect_speed_data(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Collect speed test data from Cloudflare for a given date range.
        
        Args:
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str, optional): End date in 'YYYY-MM-DD' format. Defaults to today.
        
        Returns:
            pd.DataFrame: DataFrame containing the speed test data
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        query = f"""
        WITH base AS (
          SELECT
            serverPoP,
            clientCity,
            clientCountry,
            clientASN,
            latency_val AS latencyMs,
            download.bps[OFFSET(idx)] AS download,
            upload.bps[OFFSET(idx)] AS upload,
            packetLoss.lossRatio AS loss,
            jitterMs AS jitter,
            IF(clientASN IN (14593, 27277, 45700), 'Starlink', 'Other') AS group_type
          FROM `measurement-lab.cloudflare.speedtest_speed1`,
            UNNEST(latencyMs) AS latency_val WITH OFFSET AS idx
          WHERE
            date >= '{start_date}'
            AND clientCity IS NOT NULL
            AND clientCountry IS NOT NULL
            AND serverPoP IS NOT NULL
            AND ARRAY_LENGTH(download.bps) > idx
            AND ARRAY_LENGTH(upload.bps) > idx
            AND clientIPVersion = 4
        ),

        -- Only keep combinations where both groups (Starlink & Other) are present
        filtered_groups AS (
          SELECT
            serverPoP,
            clientCity,
            clientCountry
          FROM base
          GROUP BY serverPoP, clientCity, clientCountry
          HAVING COUNT(DISTINCT group_type) = 2
        )

        -- Final aligned, filtered dataset (one row per sample)
        SELECT
          b.serverPoP,
          b.clientCity,
          b.clientCountry,
          b.clientASN,
          b.group_type,
          b.jitter,
          b.latencyMs,
          b.download,
          b.upload,
          b.loss
        FROM base b
        JOIN filtered_groups fg
          ON b.serverPoP = fg.serverPoP
          AND b.clientCity = fg.clientCity
          AND b.clientCountry = fg.clientCountry
        """

        try:
            logger.info(f"Querying Cloudflare speed test data from {start_date} to {end_date}")
            df = self.client.query(query).to_dataframe()
            
            # Add server city information
            df['serverCity'] = df['serverPoP'].map(self.pop_to_location)
            df['clientASN'] = df['clientASN'].astype(int)
            # Add clientASName using AS Rank mapping
            df = df.merge(as_rank_df, on='clientASN', how='left')

            print(df.head())

            # Save to CSV
            output_file = os.path.join(
                self.output_dir, 
                f'cloudflare_speedtest_{start_date}_to_{end_date}.csv'
            )
            df.to_csv(output_file, index=False)
            logger.info(f"Saved Cloudflare speed test data to {output_file}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error collecting Cloudflare speed test data: {str(e)}")
            raise

    def collect_state_level_data(self, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Collect state-level speed test data for US locations.
        
        Args:
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str, optional): End date in 'YYYY-MM-DD' format. Defaults to today.
        
        Returns:
            pd.DataFrame: DataFrame containing state-level speed test data
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        query = f"""
        WITH base AS (
          SELECT
            serverPoP,
            clientCity,
            clientCountry,
            clientRegion,
            clientASN,
            measurementTime AS testHour,
            latency_val AS latencyMs,
            download.bps[OFFSET(idx)] AS download,
            upload.bps[OFFSET(idx)] AS upload,
            packetLoss.lossRatio AS loss,
            jitterMs AS jitter,
            IF(clientASN IN (14593, 27277, 45700), 'Starlink', 'Other') AS group_type
          FROM measurement-lab.cloudflare.speedtest_speed1,
            UNNEST(latencyMs) AS latency_val WITH OFFSET AS idx
          WHERE
            date >= '{start_date}'
            AND clientCity IS NOT NULL
            AND clientCountry = 'US'
            AND serverPoP IS NOT NULL
            AND ARRAY_LENGTH(download.bps) > idx
            AND ARRAY_LENGTH(upload.bps) > idx
            AND clientIPVersion = 4
        )

        SELECT
          b.serverPoP,
          b.clientCity,
          b.clientCountry,
          b.clientRegion,
          b.clientASN,
          b.group_type,
          b.jitter,
          b.latencyMs,
          b.download,
          b.upload,
          b.loss,
          b.testHour
        FROM base b
        """

        try:
            logger.info(f"Querying state-level Cloudflare speed test data from {start_date} to {end_date}")
            df = self.client.query(query).to_dataframe()
            # Add server city information
            df['serverCity'] = df['serverPoP'].map(self.pop_to_location)
            df['clientASN'] = df['clientASN'].astype(int)
            # Add clientASName using AS Rank mapping
            df = df.merge(as_rank_df, on='clientASN', how='left')


            # Save to CSV
            output_file = os.path.join(
                self.output_dir, 
                f'cloudflare_speedtest_states_{start_date}_to_{end_date}.csv'
            )
            df.to_csv(output_file, index=False)
            logger.info(f"Saved state-level Cloudflare speed test data to {output_file}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error collecting state-level Cloudflare speed test data: {str(e)}")
            raise

if __name__ == "__main__":
    # Example usage
    collector = CloudflareSpeedTestCollector()
    
    # Collect last 30 days of data
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    
    # Collect general speed test data
    df = collector.collect_speed_data(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    # Collect state-level data
    df_states = collector.collect_state_level_data(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    ) 