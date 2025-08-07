#!/usr/bin/env python3
"""
Web Hosting Script for Starlink Speedtest Comparison Dashboard

This script serves the lightweight visualization dashboard and can be deployed to:
- Heroku
- Railway
- Render
- Any cloud platform that supports Python web applications

Usage:
    python web_hosting.py [--port PORT] [--host HOST] [--debug]
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the dashboard components
from visualizations.generate_visualizations_lightweight import dashboard
import panel as pn

def create_server_app():
    """Create the Panel server application."""
    # Configure Panel for production with proper session handling
    pn.config.sizing_mode = 'stretch_width'
    pn.config.theme = 'default'
    
    # Enable session state for proper multi-user support
    pn.config.session_state = True
    
    # Create the dashboard
    app = dashboard
    
    # Add a title and description
    title = pn.pane.Markdown(
        """
        <div style='text-align:center; padding: 20px; background-color: #f8f9fa; border-radius: 10px; margin-bottom: 20px;'>
        <h1>🚀 Starlink Speedtest Comparison Dashboard</h1>
        <p><strong>Interactive analysis of Starlink performance vs other ISPs using M-Lab and Cloudflare data</strong></p>
        <p>Select tabs below to explore different data sources and geographic comparisons</p>
        </div>
        """,
        sizing_mode='stretch_width'
    )
    
    # Combine title with dashboard
    full_app = pn.Column(
        title,
        app,
        sizing_mode='stretch_width'
    )
    
    return full_app

def main():
    """Main function to run the server."""
    parser = argparse.ArgumentParser(description='Starlink Speedtest Comparison Dashboard Server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Create the application
    app = create_server_app()
    
    # Configure server settings
    server_kwargs = {
        'port': args.port,
        'host': args.host,
        'allow_websocket_origin': ['*'],  # Allow connections from any origin
        'websocket_origin': ['*'],
        'session_state': True,  # Enable session state for multi-user support
    }
    
    if args.debug:
        server_kwargs['debug'] = True
    
    # Check if running on a cloud platform
    port = os.environ.get('PORT', args.port)
    if port:
        server_kwargs['port'] = int(port)
    
    print(f"🚀 Starting Starlink Speedtest Comparison Dashboard")
    print(f"📊 Dashboard will be available at: http://localhost:{server_kwargs['port']}")
    print(f"🌐 Host: {server_kwargs['host']}")
    print(f"🔧 Debug mode: {args.debug}")
    print(f"📈 Panel version: {pn.__version__}")
    
    # Start the server
    try:
        # Use pn.serve() for proper multi-user support
        pn.serve(app, **server_kwargs)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
