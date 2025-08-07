import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Tuple

from starlink_speedtest.visualizations.base_visualizer import BaseVisualizer

class SpeedTestVisualizer(BaseVisualizer):
    def __init__(self):
        """Initialize the speed test visualizer."""
        super().__init__()

    def _format_axes(self, fig, x_title=None, y_title=None):
        fig.update_layout(
            xaxis=dict(
                title=x_title or fig.layout.xaxis.title.text,
                title_font=dict(size=18, family='Arial', color='black'),
                tickfont=dict(size=15, family='Arial'),
                showgrid=True,
                gridcolor='#E5E5E5',
                zeroline=False,
                linecolor='black',
                mirror=True,
            ),
            yaxis=dict(
                title=y_title or fig.layout.yaxis.title.text,
                title_font=dict(size=18, family='Arial', color='black'),
                tickfont=dict(size=15, family='Arial'),
                showgrid=True,
                gridcolor='#E5E5E5',
                zeroline=False,
                linecolor='black',
                mirror=True,
            ),
            font=dict(family='Arial', size=15, color='black'),
        )
        return fig

    def plot_metric_boxplot(self, df: pd.DataFrame, column: str, title: str) -> go.Figure:
        """
        Generate a Plotly box plot for a specific metric column grouped by ISP (clientASName),
        with outlier filtering and adaptive coloring. Starlink is always highlighted in red and appears first.
        """
        # Remove extreme outliers using IQR method
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        df_filtered = df[(df[column] >= Q1 - 1.5 * IQR) & (df[column] <= Q3 + 1.5 * IQR)].copy()

        # Relabel Starlink ASNs to 'Starlink' for highlighting
        starlink_asns = [14593, 27277, 45700]
        if 'clientASN' in df_filtered.columns:
            df_filtered.loc[df_filtered['clientASN'].isin(starlink_asns), 'clientASName'] = 'Starlink'
        # Build new label: ASN - ASName
        if 'clientASN' in df_filtered.columns and 'clientASName' in df_filtered.columns:
            df_filtered['isp_label'] = df_filtered['clientASN'].astype(str) + ' - ' + df_filtered['clientASName'].astype(str)
        else:
            df_filtered['isp_label'] = df_filtered['clientASName'].astype(str)
        # Identify Starlink rows (case-insensitive, robust)
        starlink_names = [n for n in df_filtered['isp_label'].unique() if 'starlink' in str(n).lower()]
        other_names = [n for n in df_filtered['isp_label'].unique() if n not in starlink_names]
        # Sort: Starlink first, then others alphabetically by ASName
        def asname_sort_key(label):
            return label.split(' - ', 1)[1] if ' - ' in label else label
        ordered_names = starlink_names + sorted(other_names, key=asname_sort_key)
        df_filtered['isp_label'] = pd.Categorical(df_filtered['isp_label'], categories=ordered_names, ordered=True)
        # Color map: Starlink red, others gray
        color_map = {n: self.color_scheme['starlink'] for n in starlink_names}
        for n in other_names:
            color_map[n] = '#888888'
        fig = go.Figure()
        for name in ordered_names:
            if name not in df_filtered['isp_label'].cat.categories:
                continue
            color = color_map.get(name, '#888888')
            group = df_filtered[df_filtered['isp_label'] == name]
            if group.empty:
                continue
            fig.add_trace(go.Box(
                x=[name]*len(group),
                y=group[column],
                name=str(name),
                marker_color=color,
                boxpoints='outliers',
                showlegend=(name in starlink_names),
                legendgroup='Starlink' if name in starlink_names else 'Other',
            ))
        if not starlink_names:
            title = f"[No Starlink data for this location] {title}"
        # Human-friendly axis labels
        axis_label_map = {
            'download': 'Download Speed (Mbps)',
            'upload': 'Upload Speed (Mbps)',
            'latencyMs': 'Download Latency (ms)',
            'upload_latency': 'Upload Latency (ms)',
            'loss': 'Download Packet Loss Ratio (%)',
            'upload_loss': 'Upload Packet Loss Ratio (%)',
        }
        x_label = 'ASN - ISP Name'
        y_label = axis_label_map.get(column, column)
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            margin=dict(l=40, r=40, t=60, b=60),
            template='plotly_white',
            legend=dict(itemsizing='constant', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        # If loss, show y-axis as percent
        if 'loss' in column:
            fig.update_yaxes(tickformat='.1%')
        fig = self._format_axes(fig, x_title=x_label, y_title=y_label)
        fig.update_layout(width=None, height=None)
        return fig

    def create_speed_comparison(self, 
                              mlab_data: pd.DataFrame,
                              cloudflare_data: pd.DataFrame,
                              title: str = "Speed Test Comparison") -> go.Figure:
        """
        Create a comparison of speed test results from different sources.
        
        Args:
            mlab_data (pd.DataFrame): M-Lab NDT data
            cloudflare_data (pd.DataFrame): Cloudflare speed test data
            title (str): Plot title
        
        Returns:
            go.Figure: Plotly figure
        """
        # Pre-process data to reduce size
        mlab_data = mlab_data[['group_type', 'download', 'clientCity', 'clientCountry']].copy()
        cloudflare_data = cloudflare_data[['group_type', 'download', 'clientCity', 'clientCountry']].copy()
        
        # Create subplot with 2 rows
        fig = self.create_subplot(
            rows=2,
            cols=1,
            subplot_titles=("M-Lab NDT", "Cloudflare Speed Test"),
            vertical_spacing=0.1
        )
        
        # M-Lab NDT box plot
        fig.add_trace(
            go.Box(
                x=mlab_data['group_type'],
                y=mlab_data['download'],
                name='M-Lab NDT',
                marker_color=self.color_scheme['starlink'],
                boxpoints='outliers',  # Only show outliers to reduce data points
                customdata=mlab_data[['clientCity', 'clientCountry']],  # Add location data for hover
                hovertemplate=(
                    "<b>%{x}</b><br>" +
                    "Download: %{y:.2f} Mbps<br>" +
                    "City: %{customdata[0]}<br>" +
                    "Country: %{customdata[1]}<br>" +
                    "<extra></extra>"
                )
            ),
            row=1, col=1
        )
        
        # Cloudflare box plot
        fig.add_trace(
            go.Box(
                x=cloudflare_data['group_type'],
                y=cloudflare_data['download'],
                name='Cloudflare',
                marker_color=self.color_scheme['other'],
                boxpoints='outliers',  # Only show outliers to reduce data points
                customdata=cloudflare_data[['clientCity', 'clientCountry']],  # Add location data for hover
                hovertemplate=(
                    "<b>%{x}</b><br>" +
                    "Download: %{y:.2f} Mbps<br>" +
                    "City: %{customdata[0]}<br>" +
                    "Country: %{customdata[1]}<br>" +
                    "<extra></extra>"
                )
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title=title,
            showlegend=False,
            updatemenus=[
                dict(
                    type="dropdown",
                    direction="down",
                    x=0.1,
                    y=1.1,
                    showactive=True,
                    xanchor="left",
                    yanchor="top",
                    buttons=[
                        dict(
                            args=[{"visible": [True, True]}],
                            label="All Locations",
                            method="update"
                        ),
                        *[
                            dict(
                                args=[
                                    {
                                        "visible": [
                                            mlab_data['clientCity'] == city,
                                            cloudflare_data['clientCity'] == city
                                        ]
                                    }
                                ],
                                label=city,
                                method="update"
                            )
                            for city in mlab_data['clientCity'].unique()
                        ]
                    ]
                )
            ],
            width=None, height=None
        )
        
        # Update y-axis labels
        fig.update_yaxes(title_text="Download Speed (Mbps)", row=1, col=1)
        fig.update_yaxes(title_text="Download Speed (Mbps)", row=2, col=1)
        fig = self._format_axes(fig, x_title="ISP", y_title="Download Speed (Mbps)")
        return fig

    def create_latency_comparison(self,
                                mlab_data: pd.DataFrame,
                                cloudflare_data: pd.DataFrame,
                                title: str = "Latency Comparison") -> go.Figure:
        """
        Create a comparison of latency results from different sources.
        
        Args:
            mlab_data (pd.DataFrame): M-Lab NDT data
            cloudflare_data (pd.DataFrame): Cloudflare speed test data
            title (str): Plot title
        
        Returns:
            go.Figure: Plotly figure
        """
        # Create subplot with 2 rows
        fig = self.create_subplot(
            rows=2,
            cols=1,
            subplot_titles=("M-Lab NDT", "Cloudflare Speed Test"),
            vertical_spacing=0.1
        )
        
        # M-Lab NDT box plot
        fig.add_trace(
            go.Box(
                x=mlab_data['group_type'],
                y=mlab_data['MinRTT'],
                name='M-Lab NDT',
                marker_color=self.color_scheme['starlink']
            ),
            row=1, col=1
        )
        
        # Cloudflare box plot
        fig.add_trace(
            go.Box(
                x=cloudflare_data['group_type'],
                y=cloudflare_data['latencyMs'],
                name='Cloudflare',
                marker_color=self.color_scheme['other']
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title=title,
            showlegend=False,
            width=None, height=None
        )
        
        # Update y-axis labels
        fig.update_yaxes(title_text="Latency (ms)", row=1, col=1)
        fig.update_yaxes(title_text="Latency (ms)", row=2, col=1)
        fig = self._format_axes(fig, x_title="ISP", y_title="Latency (ms)")
        return fig

    def create_geographic_speed_map(self,
                                  data: pd.DataFrame,
                                  title: str = "Geographic Speed Distribution") -> go.Figure:
        """
        Create a geographic map showing speed distribution.
        
        Args:
            data (pd.DataFrame): Combined speed test data
            title (str): Plot title
        
        Returns:
            go.Figure: Plotly figure
        """
        # Calculate average speed by location
        location_speeds = data.groupby(['clientCity', 'clientCountry', 'group_type']).agg({
            'MeanThroughputMbps': 'mean',
            'download': 'mean'
        }).reset_index()
        
        # Create the geographic plot
        fig = px.scatter_geo(
            location_speeds,
            lat='clientLat',
            lon='clientLon',
            color='group_type',
            size='MeanThroughputMbps',
            hover_name='clientCity',
            hover_data=['clientCountry', 'MeanThroughputMbps'],
            color_discrete_map={
                'Starlink': self.color_scheme['starlink'],
                'Other': self.color_scheme['other']
            }
        )
        
        # Update layout
        fig.update_layout(
            title=title,
            geo=dict(
                scope='world',
                showland=True,
                landcolor='rgb(243, 243, 243)',
                countrycolor='rgb(204, 204, 204)'
            ),
            width=None, height=None
        )
        fig = self._format_axes(fig)
        return fig

    def create_time_series_analysis(self,
                                  data: pd.DataFrame,
                                  date_col: str = 'date',
                                  title: str = "Speed Test Performance Over Time") -> go.Figure:
        """
        Create a time series analysis of speed test performance.
        
        Args:
            data (pd.DataFrame): Combined speed test data
            date_col (str): Date column name
            title (str): Plot title
        
        Returns:
            go.Figure: Plotly figure
        """
        # Create subplot with 2 rows
        fig = self.create_subplot(
            rows=2,
            cols=1,
            subplot_titles=("Download Speed", "Latency"),
            vertical_spacing=0.1
        )
        
        # Download speed time series
        fig.add_trace(
            go.Scatter(
                x=data[date_col],
                y=data['MeanThroughputMbps'],
                name='Download Speed',
                line=dict(color=self.color_scheme['starlink'])
            ),
            row=1, col=1
        )
        
        # Latency time series
        fig.add_trace(
            go.Scatter(
                x=data[date_col],
                y=data['MinRTT'],
                name='Latency',
                line=dict(color=self.color_scheme['other'])
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title=title,
            showlegend=True,
            width=None, height=None
        )
        
        # Update y-axis labels
        fig.update_yaxes(title_text="Download Speed (Mbps)", row=1, col=1)
        fig.update_yaxes(title_text="Latency (ms)", row=2, col=1)
        fig = self._format_axes(fig, x_title="Date")
        return fig

if __name__ == "__main__":
    # Example usage
    visualizer = SpeedTestVisualizer()
    
    # Load your data
    # mlab_data = pd.read_csv('path/to/mlab_data.csv')
    # cloudflare_data = pd.read_csv('path/to/cloudflare_data.csv')
    
    # Create and save visualizations
    # speed_comparison = visualizer.create_speed_comparison(mlab_data, cloudflare_data)
    # visualizer.save_figure(speed_comparison, 'speed_comparison')
    
    # latency_comparison = visualizer.create_latency_comparison(mlab_data, cloudflare_data)
    # visualizer.save_figure(latency_comparison, 'latency_comparison') 