# Deployment Guide for Starlink Speedtest Dashboard

This guide provides step-by-step instructions for deploying the Starlink Speedtest Comparison Dashboard to various hosting platforms.

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard locally
python web_hosting.py --port 8080

# Access at http://localhost:8080
```

### Docker Deployment
```bash
# Build and run with Docker
docker-compose up --build

# Or build manually
docker build -t starlink-dashboard .
docker run -p 8080:8080 starlink-dashboard
```

## 🌐 Cloud Deployment Options

### 1. Heroku Deployment

#### Prerequisites
- Heroku CLI installed
- Heroku account

#### Steps
1. **Login to Heroku**
   ```bash
   heroku login
   ```

2. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

3. **Deploy to Heroku**
   ```bash
   git add .
   git commit -m "Deploy dashboard"
   git push heroku main
   ```

4. **Open the app**
   ```bash
   heroku open
   ```

#### Configuration
- The `Procfile` tells Heroku how to run the app
- `runtime.txt` specifies Python version
- Environment variables are automatically set

### 2. Railway Deployment

#### Prerequisites
- Railway account
- GitHub repository

#### Steps
1. **Connect to Railway**
   - Go to [Railway.app](https://railway.app)
   - Connect your GitHub account
   - Select your repository

2. **Deploy**
   - Railway will automatically detect the `railway.json` configuration
   - Deploy happens automatically on git push

3. **Access**
   - Railway provides a URL automatically
   - Check the deployment logs in Railway dashboard

### 3. Render Deployment

#### Prerequisites
- Render account
- GitHub repository

#### Steps
1. **Connect to Render**
   - Go to [Render.com](https://render.com)
   - Connect your GitHub account
   - Create a new Web Service

2. **Configure**
   - Select your repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python web_hosting.py --port $PORT`

3. **Deploy**
   - Render will use the `render.yaml` configuration
   - Automatic deployments on git push

### 4. Google Cloud Run

#### Prerequisites
- Google Cloud SDK
- Docker installed

#### Steps
1. **Build and push to Container Registry**
   ```bash
   # Build the image
   docker build -t gcr.io/YOUR_PROJECT_ID/starlink-dashboard .

   # Push to Container Registry
   docker push gcr.io/YOUR_PROJECT_ID/starlink-dashboard
   ```

2. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy starlink-dashboard \
     --image gcr.io/YOUR_PROJECT_ID/starlink-dashboard \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

### 5. AWS Elastic Beanstalk

#### Prerequisites
- AWS CLI configured
- EB CLI installed

#### Steps
1. **Initialize EB application**
   ```bash
   eb init starlink-dashboard --platform python-3.11
   ```

2. **Create environment**
   ```bash
   eb create starlink-dashboard-env
   ```

3. **Deploy**
   ```bash
   eb deploy
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8080` |
| `HOST` | Server host | `0.0.0.0` |
| `DEBUG` | Debug mode | `False` |

### Data Requirements

The dashboard requires pre-processed data files in the `data/processed/` directory:

- `mlab_boxplot_stats.csv`
- `cloudflare_boxplot_stats.csv`
- `cloudflare_state_aggregated.csv`
- `starlink_state_aggregated.csv`
- `location_maps.pkl`

### Performance Optimization

1. **Data Preprocessing**
   - Ensure data files are optimized for web loading
   - Use compressed formats where possible

2. **Caching**
   - The dashboard uses Panel's built-in caching
   - Consider adding Redis for production deployments

3. **CDN**
   - Use a CDN for static assets
   - Consider Cloudflare or AWS CloudFront

## 🛠️ Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Find process using port
   lsof -i :8080
   
   # Kill process
   kill -9 <PID>
   ```

2. **Memory issues**
   - Increase memory allocation in cloud platform
   - Optimize data loading in the dashboard

3. **Data loading errors**
   - Check file paths in `data/processed/`
   - Ensure all required CSV files exist

### Debug Mode

Run with debug mode for detailed logs:
```bash
python web_hosting.py --debug --port 8080
```

### Health Checks

The dashboard includes health check endpoints:
- `/` - Main dashboard
- `/health` - Health check endpoint

## 📊 Monitoring

### Logs
- Check application logs in your hosting platform
- Use logging to monitor dashboard usage

### Performance
- Monitor response times
- Track user interactions
- Monitor data loading performance

### Alerts
- Set up alerts for downtime
- Monitor error rates
- Track resource usage

## 🔒 Security

### Production Considerations

1. **HTTPS**
   - Enable HTTPS in your hosting platform
   - Use SSL certificates

2. **Access Control**
   - Consider adding authentication if needed
   - Restrict access to sensitive data

3. **Rate Limiting**
   - Implement rate limiting for API endpoints
   - Protect against abuse

## 📈 Scaling

### Horizontal Scaling
- Use load balancers
- Deploy multiple instances
- Use auto-scaling groups

### Vertical Scaling
- Increase memory allocation
- Use more powerful instances
- Optimize data structures

## 🆘 Support

For deployment issues:
1. Check the hosting platform's documentation
2. Review application logs
3. Test locally first
4. Check environment variables
5. Verify data files are present

## 📝 Notes

- The dashboard is designed to be lightweight and fast
- Pre-processed data ensures quick loading
- Panel provides excellent interactive capabilities
- The application is stateless and can be easily scaled
