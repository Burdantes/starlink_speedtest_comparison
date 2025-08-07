# Starlink Speedtest Comparison

A comprehensive tool for collecting and analyzing Starlink speed-test data from M-Lab, Cloudflare, and Starlink to compare performance across geographic locations and different speed-test infrastructure. This project provides both detailed data collection capabilities and a lightweight web-based visualization system.

## What This Code Does

### 🎯 **Core Purpose**
This project analyzes and compares Starlink's internet performance against other ISPs using data from multiple speed test platforms. It provides insights into how Starlink performs relative to traditional terrestrial ISPs across different geographic locations and network conditions.

### 📊 **Data Collection & Analysis**

#### **1. Multi-Source Data Collection**
- **M-Lab NDT Data**: Collects Network Diagnostic Tool data via BigQuery, providing academic-grade speed test measurements
- **Cloudflare Speed Test**: Gathers data from Cloudflare's global speed test infrastructure
- **Starlink Internal Metrics**: Accesses Starlink's internal performance data via Google Drive API

#### **2. Geographic Analysis**
- **State-level Comparisons**: Aggregates performance data by US states for regional analysis
- **City-to-PoP Mapping**: Tracks performance between specific cities and Points of Presence
- **ISP Classification**: Identifies and categorizes Starlink ASNs (14593, 27277, 45700) vs other providers

#### **3. Statistical Processing**
- **Boxplot Statistics**: Pre-calculates quartiles, medians, and outlier detection for efficient visualization
- **Performance Metrics**: Analyzes download/upload speeds, latency, and packet loss
- **Data Filtering**: Ensures sufficient sample sizes (1000+ measurements per location) for statistical significance

### 🖥️ **Visualization System**

#### **Interactive Dashboard Features**
- **Source-Destination Selection**: Users can select specific Starlink cities and destination PoPs
- **ISP Comparison**: Side-by-side boxplots showing Starlink vs other major ISPs
- **Detailed Statistics**: Expandable panels with measurement counts, quartiles, and outlier information
- **Geographic Maps**: Choropleth maps showing state-level performance comparisons

#### **Three Main Visualization Tabs**

1. **M-Lab Analysis**
   - Uses NDT
   - Shows performance from user-initiated tests

2. **Cloudflare Analysis**
   - Leverages Cloudflare's global CDN infrastructure
   - Browser-based speed test measurements


3. **State-level Maps**
   - US-focused geographic comparisons
   - Side-by-side maps for M-Lab, Cloudflare, and Starlink internal data
   - Same color scale for direct metric comparison

### 🔧 **Technical Architecture**

#### **Data Pipeline**
```
Raw Data Collection → Preprocessing → Statistical Analysis → Interactive Visualization
```

#### **Key Components**
- **Data Collectors**: Automated scripts for each data source
- **Preprocessing Engine**: Converts raw data into visualization-ready statistics
- **Web Interface**: Panel-based dashboard for interactive exploration
- **Geographic Integration**: Shapefile-based mapping for spatial analysis

#### **Performance Optimizations**
- **Pre-calculated Statistics**: Boxplot data pre-computed for fast loading
- **Lightweight Processing**: Efficient data structures for web deployment
- **Caching System**: Location maps and statistics cached for quick access

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Google Cloud SDK (optional, for BigQuery features)

### Quick Installation

#### Option 1: Using the installation script (Recommended)

**On macOS/Linux:**
```bash
./install.sh
```

**On Windows:**
```cmd
install.bat
```

**Using Python:**
```bash
python install.py
```

#### Option 2: Manual installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/starlink_speedtest_comparison.git
cd starlink_speedtest_comparison
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package in development mode:
```bash
pip install -e .
```

4. Create necessary directories:
```bash
mkdir -p data/processed output/visualizations logs
```

### Google Cloud Setup (Optional)

If you plan to use BigQuery features for data collection:

1. Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install
2. Authenticate with Google Cloud:
```bash
gcloud auth application-default login
```

## Usage

### Data Collection

Run the data collection script to gather speed test data:

```bash
python generating_data.py
```

This will collect data from:
- M-Lab NDT
- Cloudflare Speed Test
- Starlink internal metrics

### Visualization

#### Full Visualization System
Generate comprehensive interactive visualizations:

```bash
python visualizations/generate_visualizations.py
```

#### Lightweight Web-Ready System
Generate optimized visualizations for web hosting:

```bash
python visualizations/generate_visualizations_lightweight.py
```

### Web Application

Start the web interface:

```bash
cd web
python app.py
```

Then open your browser to `http://localhost:5000`

## Web Hosting the Simplified Visualizations

The `generate_visualizations_lightweight.py` script creates a Panel-based dashboard that can be easily deployed to the web. Here are several hosting options:

### Option 1: Panel Server (Recommended)

The lightweight script uses Panel, which can be served directly:

```bash
# Run the dashboard as a server
python visualizations/generate_visualizations_lightweight.py --port 8080
```

### Option 2: Deploy to Heroku

Create a `Procfile`:
```
web: python visualizations/generate_visualizations_lightweight.py --port $PORT
```

### Option 3: Deploy to Streamlit Cloud

Convert the Panel dashboard to Streamlit for easy cloud deployment.

### Option 4: Static HTML Export

Export the dashboard as static HTML for any web hosting service.

## Project Structure

```
starlink_speedtest_comparison/
├── data_collection/          # Data collection modules
│   ├── cloudflare_collector.py
│   ├── mlab_ndt_collector.py
│   ├── starlink_collector.py
│   └── preprocess_visualization_data.py
├── visualizations/           # Visualization modules
│   ├── base_visualizer.py
│   ├── speedtest_visualizer.py
│   ├── generate_visualizations.py
│   └── generate_visualizations_lightweight.py  # Web-ready version
├── web/                     # Web application
│   ├── app.py
│   ├── requirements.txt
│   └── templates/
├── data/                    # Data storage
│   ├── processed/           # Processed data files
│   └── *.csv               # Raw data files
├── output/                  # Generated outputs
│   └── visualizations/      # Generated charts
├── requirements.txt         # Python dependencies
├── setup.py                # Package setup
├── install.py              # Installation script
├── install.sh              # Unix installation script
└── install.bat             # Windows installation script
```

## Dependencies

### Core Dependencies
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **flask**: Web framework
- **plotly**: Interactive visualizations
- **panel**: Dashboard framework
- **geopandas**: Geographic data processing

### Google Cloud Dependencies
- **google-cloud-bigquery**: BigQuery client
- **google-auth**: Authentication
- **google-api-python-client**: Google API client

### Other Dependencies
- **requests**: HTTP library
- **tqdm**: Progress bars
- **pickle-mixin**: Data serialization

## Configuration

### Google Cloud Project

Update the project ID in the collector files:
- `data_collection/mlab_ndt_collector.py`
- `data_collection/cloudflare_collector.py`
- `data_collection/ixp_collector.py`

### Data Sources

The project collects data from:
- **M-Lab**: Network diagnostic data via BigQuery
- **Cloudflare**: Speed test data via BigQuery
- **Starlink**: Internal metrics via Google Drive API

## Development

### Setting up development environment

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Install pre-commit hooks (optional):
```bash
pre-commit install
```

### Running tests

```bash
pytest
```

### Code formatting

```bash
black .
flake8 .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the existing issues
2. Create a new issue with detailed information
3. Include your Python version and operating system

## Acknowledgments

- M-Lab for providing network diagnostic data
- Cloudflare for speed test data
- Starlink for internal metrics
- The open-source community for the tools and libraries used

