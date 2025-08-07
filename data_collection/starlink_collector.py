import pandas as pd
import requests
import json
import logging
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import pickle

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StarlinkDataCollector:
    def __init__(self):
        """Initialize the Starlink data collector."""
        self.base_url = "https://raw.githubusercontent.com/clarkzjw/starlink-geoip-data/master/latency/metrics_residential"
        self.output_dir = os.path.join(os.path.dirname(__file__), '../data')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Google Drive API setup
        self.SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        self.creds = None
        self.drive_service = None
        self.region_mapping = None

    def authenticate_drive(self):
        """Authenticate with Google Drive API."""
        try:
            # The file token.pickle stores the user's access and refresh tokens
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(self.creds, token)

            self.drive_service = build('drive', 'v3', credentials=self.creds)
            logger.info("Successfully authenticated with Google Drive")
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Drive: {str(e)}")
            raise

    def load_region_mapping_from_folder(self, folder_id: str) -> Dict[str, Dict[str, str]]:
        """
        Load and merge all JSON files in a Google Drive folder into the id_to_region format.

        Args:
            folder_id (str): Google Drive folder ID

        Returns:
            Dict[str, Dict[str, str]]: Mapping of encoded ID to {"state": ..., "country": ...}
        """
        if not self.drive_service:
            self.authenticate_drive()

        try:
            # List JSON files in the folder
            results = self.drive_service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/json'",
                spaces='drive',
                fields="files(id, name)"
            ).execute()
            items = results.get('files', [])
            if not items:
                logger.warning("No JSON files found in folder.")
                return {}

            id_to_region = {}

            for item in items:
                file_id = item['id']
                file_name = item['name']

                # Extract ISO2 country code from file name like 'adm1-US.json'
                if not file_name.startswith("adm1-") or not file_name.endswith(".json"):
                    continue
                iso2_country = file_name.split("-")[1].split(".")[0].upper()

                logger.info(f"Downloading {file_name}...")
                request = self.drive_service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

                fh.seek(0)
                content = fh.read().decode('utf-8')
                data = json.loads(content)
                region_map = data.get("all", {})

                for encoded_id, props in region_map.items():
                    id_to_region[encoded_id] = {
                        "state": props["name"],
                        "country": iso2_country
                    }

            self.region_mapping = id_to_region
            logger.info("Successfully built region mapping from folder.")
            return id_to_region

        except Exception as e:
            logger.error(f"Error loading region mapping folder: {str(e)}")
            raise

    def load_starlink_metrics(self, date_str: str) -> Dict:
        """
        Load Starlink metrics for a specific date.
        
        Args:
            date_str (str): Date string in format 'YYYYMM'
        
        Returns:
            Dict: Starlink metrics data
        """
        try:
            url = f"{self.base_url}/metrics_residential-{date_str}.json"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error loading Starlink metrics for {date_str}: {str(e)}")
            raise

    def collect_country_level_data(self, dates: List[str]) -> pd.DataFrame:
        """
        Collect country-level Starlink metrics for multiple dates.
        
        Args:
            dates (List[str]): List of dates in format 'YYYYMM'
        
        Returns:
            pd.DataFrame: DataFrame containing country-level metrics
        """
        frames = []
        for date in dates:
            try:
                data = self.load_starlink_metrics(date)
                df = pd.DataFrame.from_dict(data["admin0Metrics"], orient="index").reset_index()
                df = df.rename(columns={"index": "ISO_A3"})
                df["date"] = date
                frames.append(df)
            except Exception as e:
                logger.error(f"Error processing date {date}: {str(e)}")
                continue

        if not frames:
            raise ValueError("No data collected for any dates")

        all_data = pd.concat(frames, ignore_index=True)
        
        # Save to CSV
        output_file = os.path.join(
            self.output_dir, 
            f'starlink_country_metrics_{dates[0]}_to_{dates[-1]}.csv'
        )
        all_data.to_csv(output_file, index=False)
        logger.info(f"Saved country-level metrics to {output_file}")
        
        return all_data

    def collect_state_level_data(self, dates: List[str], region_mapping: Dict = None) -> pd.DataFrame:
        """
        Collect state-level Starlink metrics for multiple dates.
        
        Args:
            dates (List[str]): List of dates in format 'YYYYMM'
            region_mapping (Dict, optional): Mapping of encoded IDs to region information.
                                           If not provided, will use the loaded mapping.
        
        Returns:
            pd.DataFrame: DataFrame containing state-level metrics
        """
        if region_mapping is None:
            if self.region_mapping is None:
                raise ValueError("No region mapping provided or loaded")
            region_mapping = self.region_mapping

        frames = []
        for date in dates:
            try:
                starlink_data = self.load_starlink_metrics(date)
                admin1_metrics = starlink_data["admin1Metrics"]
                decoded_metrics = []

                for encoded_id, metrics in admin1_metrics.items():
                    region_info = region_mapping.get(encoded_id)
                    if region_info:
                        row = {
                            "state_name": region_info["state"],
                            "country_iso2": region_info["country"],
                            "date": date,
                            **metrics
                        }
                        decoded_metrics.append(row)

                df_month = pd.DataFrame(decoded_metrics)
                frames.append(df_month)
            except Exception as e:
                logger.error(f"Error processing date {date}: {str(e)}")
                continue

        if not frames:
            raise ValueError("No data collected for any dates")

        df_admin1 = pd.concat(frames, ignore_index=True)
        
        # Save to CSV
        output_file = os.path.join(
            self.output_dir, 
            f'starlink_state_metrics_{dates[0]}_to_{dates[-1]}.csv'
        )
        df_admin1.to_csv(output_file, index=False)
        logger.info(f"Saved state-level metrics to {output_file}")
        
        return df_admin1

if __name__ == "__main__":
    # Example usage
    collector = StarlinkDataCollector()
    
    # Load region mapping from Google Drive
    region_mapping = collector.load_region_mapping_from_folder('14Kq3-YZxzmVC7ulwWOYkbSOoZ7sJiqN3')
    
    # Collect data for the last two months
    current_date = datetime.now() - timedelta(days=1)
    print(f"Current date: {current_date.strftime('%Y-%m-%d')}")
    dates = [
        (current_date.replace(month=current_date.month-1)).strftime('%Y%m'),
        current_date.strftime('%Y%m')
    ]
    
    # Collect both country and state level data
    country_data = collector.collect_country_level_data(dates)
    state_data = collector.collect_state_level_data(dates, region_mapping) 