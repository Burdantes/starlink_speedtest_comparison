from flask import Flask, render_template, jsonify
import os
import glob
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_latest_visualizations():
    """Get the latest visualization files for each type."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    viz_dir = os.path.join(base_dir, 'output/visualizations')
    
    # Define visualization types and their patterns
    viz_types = {
        'speed_comparison': 'speed_comparison_*.html',
        'latency_comparison': 'latency_comparison_*.html',
        'geographic_speed_map': 'geographic_speed_map_*.html',
        'time_series_analysis': 'time_series_analysis_*.html'
    }
    
    latest_viz = {}
    for viz_type, pattern in viz_types.items():
        files = glob.glob(os.path.join(viz_dir, pattern))
        if files:
            # Get the most recent file
            latest_file = max(files, key=os.path.getctime)
            latest_viz[viz_type] = os.path.basename(latest_file)
    
    return latest_viz

@app.route('/')
def index():
    """Render the main page with visualization controls."""
    latest_viz = get_latest_visualizations()
    return render_template('index.html', visualizations=latest_viz)

@app.route('/visualization/<viz_type>')
def get_visualization(viz_type):
    """Serve the requested visualization."""
    base_dir = os.path.dirname(os.path.dirname(__file__))
    viz_dir = os.path.join(base_dir, 'output/visualizations')
    
    # Get the latest file for the requested type
    pattern = f'{viz_type}_*.html'
    files = glob.glob(os.path.join(viz_dir, pattern))
    
    if not files:
        return jsonify({'error': 'Visualization not found'}), 404
    
    latest_file = max(files, key=os.path.getctime)
    
    with open(latest_file, 'r') as f:
        content = f.read()
    
    return content

@app.route('/narrative')
def narrative():
    """Render the narrative-driven analysis page with embedded visualizations and descriptions."""
    latest_viz = get_latest_visualizations()
    base_dir = os.path.dirname(os.path.dirname(__file__))
    viz_dir = os.path.join(base_dir, 'output/visualizations')
    visuals_content = {}
    for key, fname in latest_viz.items():
        fpath = os.path.join(viz_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r') as f:
                visuals_content[key] = f.read()
        else:
            visuals_content[key] = '<div class="alert alert-warning">Visualization not found</div>'
    return render_template('narrative.html', visualizations=visuals_content)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 