import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
import os
from typing import Dict, List, Optional, Union
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseVisualizer:
    def __init__(self):
        """Initialize the base visualizer."""
        self.output_dir = os.path.join(os.path.dirname(__file__), '../output/visualizations')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Common color schemes
        self.color_scheme = {
            'starlink': '#FF4B4B',  # Red
            'other': '#4B4BFF',     # Blue
            'background': '#FFFFFF', # White
            'grid': '#E5E5E5'       # Light Gray
        }

        self.layout_settings = {
            'template': 'plotly_white',
            'font': dict(family='Arial', size=14),  # sets base font for text
            'title': dict(font=dict(size=24)),
            'xaxis': dict(title_font=dict(size=18), tickfont=dict(size=14)),
            'yaxis': dict(title_font=dict(size=18), tickfont=dict(size=14)),
            'legend': dict(font=dict(size=14)),
            'margin': dict(l=50, r=50, t=50, b=50)
        }

    def save_figure(self, fig: go.Figure, filename: str, format: str = 'html') -> str:
        """
        Save a figure to file.
        
        Args:
            fig (go.Figure): Plotly figure to save
            filename (str): Name of the file (without extension)
            format (str): Output format ('html' or 'png')
        
        Returns:
            str: Path to the saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(
            self.output_dir,
            f'{filename}_{timestamp}.{format}'
        )
        
        try:
            if format == 'html':
                fig.write_html(output_file)
            elif format == 'png':
                fig.write_image(output_file)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
            logger.info(f"Saved visualization to {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error saving visualization: {str(e)}")
            raise

    def create_subplot(self, rows: int, cols: int, **kwargs) -> go.Figure:
        """
        Create a subplot figure with common settings.
        
        Args:
            rows (int): Number of rows
            cols (int): Number of columns
            **kwargs: Additional arguments for make_subplots
        
        Returns:
            go.Figure: Plotly figure with subplots
        """
        fig = make_subplots(
            rows=rows,
            cols=cols,
            **kwargs
        )
        
        # Apply common layout settings
        fig.update_layout(**self.layout_settings)
        
        return fig

    def add_common_annotations(self, fig: go.Figure, title: str, xlabel: str, ylabel: str):
        """
        Add common annotations to a figure.
        
        Args:
            fig (go.Figure): Plotly figure to annotate
            title (str): Figure title
            xlabel (str): X-axis label
            ylabel (str): Y-axis label
        """
        fig.update_layout(
            title=title,
            xaxis_title=xlabel,
            yaxis_title=ylabel,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

    def create_metric_comparison(self, 
                               data: pd.DataFrame,
                               metric: str,
                               group_col: str = 'group_type',
                               title: str = None,
                               xlabel: str = None,
                               ylabel: str = None) -> go.Figure:
        """
        Create a comparison plot for a specific metric.
        
        Args:
            data (pd.DataFrame): Input data
            metric (str): Metric column name
            group_col (str): Column name for grouping
            title (str): Plot title
            xlabel (str): X-axis label
            ylabel (str): Y-axis label
        
        Returns:
            go.Figure: Plotly figure
        """
        fig = px.box(
            data,
            x=group_col,
            y=metric,
            color=group_col,
            color_discrete_map={
                'Starlink': self.color_scheme['starlink'],
                'Other': self.color_scheme['other']
            }
        )
        
        if title is None:
            title = f'{metric} Comparison'
        if ylabel is None:
            ylabel = metric
            
        self.add_common_annotations(fig, title, xlabel or group_col, ylabel)
        
        return fig

    def create_time_series(self,
                          data: pd.DataFrame,
                          date_col: str,
                          metric: str,
                          group_col: str = 'group_type',
                          title: str = None,
                          xlabel: str = None,
                          ylabel: str = None) -> go.Figure:
        """
        Create a time series plot for a specific metric.
        
        Args:
            data (pd.DataFrame): Input data
            date_col (str): Date column name
            metric (str): Metric column name
            group_col (str): Column name for grouping
            title (str): Plot title
            xlabel (str): X-axis label
            ylabel (str): Y-axis label
        
        Returns:
            go.Figure: Plotly figure
        """
        fig = px.line(
            data,
            x=date_col,
            y=metric,
            color=group_col,
            color_discrete_map={
                'Starlink': self.color_scheme['starlink'],
                'Other': self.color_scheme['other']
            }
        )
        
        if title is None:
            title = f'{metric} Over Time'
        if ylabel is None:
            ylabel = metric
            
        self.add_common_annotations(fig, title, xlabel or 'Date', ylabel)
        
        return fig

    def create_geographic_plot(self,
                             data: pd.DataFrame,
                             lat_col: str,
                             lon_col: str,
                             metric: str,
                             group_col: str = 'group_type',
                             title: str = None) -> go.Figure:
        """
        Create a geographic scatter plot.
        
        Args:
            data (pd.DataFrame): Input data
            lat_col (str): Latitude column name
            lon_col (str): Longitude column name
            metric (str): Metric column name
            group_col (str): Column name for grouping
            title (str): Plot title
        
        Returns:
            go.Figure: Plotly figure
        """
        fig = px.scatter_geo(
            data,
            lat=lat_col,
            lon=lon_col,
            color=group_col,
            size=metric,
            color_discrete_map={
                'Starlink': self.color_scheme['starlink'],
                'Other': self.color_scheme['other']
            }
        )
        
        if title is None:
            title = f'Geographic Distribution of {metric}'
            
        self.add_common_annotations(fig, title, '', '')
        
        return fig 