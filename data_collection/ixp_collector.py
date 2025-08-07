import os
import logging
import datetime
import subprocess
from typing import List, Dict, Optional
from google.cloud import bigquery
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IXPCollector:
    def __init__(self, 
                 project_id: str = "mlab-collaboration",
                 wrapper_script_path: Optional[str] = None,
                 python_executable: Optional[str] = None,
                 output_dir: Optional[str] = None,
                 batch_size: int = 1000):
        """
        Initialize the IXP collector.
        
        Args:
            project_id (str): Google Cloud project ID
            wrapper_script_path (str): Path to the wrapper script
            python_executable (str): Path to Python executable
            output_dir (str): Directory for output files
            batch_size (int): Number of rows to insert in each batch
        """
        self.project_id = project_id
        self.batch_size = batch_size
        self.client = bigquery.Client(project=project_id)
        
        # Set default paths if not provided
        if wrapper_script_path is None:
            self.wrapper_script_path = os.path.join(
                os.path.dirname(__file__),
                '../../wrapper_automation/wrapper.py'
            )
        else:
            self.wrapper_script_path = wrapper_script_path
            
        if python_executable is None:
            self.python_executable = sys.executable
        else:
            self.python_executable = python_executable
            
        if output_dir is None:
            self.output_dir = os.path.join(
                os.path.dirname(__file__),
                '../data'
            )
        else:
            self.output_dir = output_dir
            
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Define BigQuery table
        self.table_id = f"{project_id}.ix_data.ixp_members"

    def run_wrapper_script(self) -> bool:
        """
        Run the wrapper script to generate IXP member data.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(self.wrapper_script_path):
            logger.error(f"Wrapper script not found: {self.wrapper_script_path}")
            return False

        try:
            logger.info(f"Running wrapper script: {self.wrapper_script_path}")
            result = subprocess.run(
                [self.python_executable, self.wrapper_script_path],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Wrapper script output: {result.stdout}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running wrapper script: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False

    def get_latest_data_file(self) -> Optional[str]:
        """
        Get the path to the latest data file.
        
        Returns:
            Optional[str]: Path to the latest data file, or None if not found
        """
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
        file_name = f"merged-members-gen-{yesterday}.txt"
        file_path = os.path.join(self.output_dir, file_name)
        
        if not os.path.exists(file_path):
            logger.warning(f"Data file not found: {file_path}")
            return None
            
        logger.info(f"Found data file: {file_path}")
        return file_path

    def process_data_file(self, file_path: str) -> List[Dict]:
        """
        Process the data file and prepare rows for BigQuery insertion.
        
        Args:
            file_path (str): Path to the data file
            
        Returns:
            List[Dict]: List of rows to insert
        """
        rows_to_insert = []
        
        # Extract partition date from filename
        partition_date_str = os.path.basename(file_path).split("-")[-1][:8]
        partition_date = datetime.datetime.strptime(partition_date_str, "%Y%m%d").strftime("%Y-%m-%d")
        
        logger.info(f"Processing data file with partition date: {partition_date}")
        
        with open(file_path, "r") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                    
                parts = line.strip().split("\t")
                if len(parts) != 3:
                    continue
                    
                ipv4, asn, name = parts
                row = {
                    "asn": int(asn),
                    "ipv4": ipv4,
                    "name": name,
                    "partition_date": partition_date
                }
                rows_to_insert.append(row)
                
        logger.info(f"Processed {len(rows_to_insert)} rows from data file")
        return rows_to_insert

    def insert_to_bigquery(self, rows: List[Dict]) -> bool:
        """
        Insert rows into BigQuery in batches.
        
        Args:
            rows (List[Dict]): List of rows to insert
            
        Returns:
            bool: True if successful, False otherwise
        """
        batches = [rows[i:i+self.batch_size] for i in range(0, len(rows), self.batch_size)]
        
        success = True
        for batch in tqdm(batches, desc="Inserting into BigQuery"):
            errors = self.client.insert_rows_json(self.table_id, batch)
            if errors:
                logger.error(f"Error inserting batch: {errors}")
                success = False
                
        return success

    def collect_ixp_data(self) -> bool:
        """
        Main method to collect and process IXP data.
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if data file exists, if not run wrapper script
        file_path = self.get_latest_data_file()
        if file_path is None:
            if not self.run_wrapper_script():
                return False
            file_path = self.get_latest_data_file()
            if file_path is None:
                return False
                
        # Process data file
        rows = self.process_data_file(file_path)
        if not rows:
            logger.error("No valid rows found in data file")
            return False
            
        # Insert into BigQuery
        if not self.insert_to_bigquery(rows):
            logger.error("Failed to insert data into BigQuery")
            return False
            
        logger.info(f"Successfully processed and inserted {len(rows)} rows")
        return True

if __name__ == "__main__":
    # Example usage
    collector = IXPCollector()
    collector.collect_ixp_data() 