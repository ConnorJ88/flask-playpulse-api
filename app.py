# app.py
from flask import Flask
from flask_cors import CORS
import os

from flask_caching import Cache

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure cache
cache_config = {
    'CACHE_TYPE': 'simple',  # Use 'simple' for in-memory caching
    'CACHE_DEFAULT_TIMEOUT': 3600,  # Default cache timeout in seconds (1 hour)
    'CACHE_THRESHOLD': 500  # Maximum number of items the cache will store
}
cache = Cache(app, config=cache_config)

# Import routes
from routes.players import player_routes
from routes.predictions import prediction_routes


# Set longer timeout for worker processes
os.environ['GUNICORN_CMD_ARGS'] = "--timeout 120"  # Increase to 120 seconds

# Register blueprints
app.register_blueprint(player_routes, url_prefix='/api/players')
app.register_blueprint(prediction_routes, url_prefix='/api/predictions')

# Root endpoint for health check
@app.route('/')
def index():
    return {
        'status': 'online',
        'name': 'PlayPulse API',
        'version': '1.0.0'
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, timeout=120)