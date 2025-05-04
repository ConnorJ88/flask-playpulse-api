# app.py
from flask import Flask
from flask_cors import CORS
import os
from flask_caching import Cache
from celery_config import make_celery

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure cache
app.config.update(
    CACHE_TYPE='simple',
    CACHE_DEFAULT_TIMEOUT=86400,  # 24 hours
    CACHE_THRESHOLD=500  # Maximum number of items
)
cache = Cache(app)

# Configure Celery
app.config.update(
    CELERY_BROKER_URL=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_RESULT_SERIALIZER='json',
    CELERY_TIMEZONE='UTC',
    CELERY_TASK_RESULT_EXPIRES=3600,  # 1 hour
)
celery = make_celery(app)

# Import routes
from routes.players import player_routes
from routes.predictions import prediction_routes

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
    app.run(host='0.0.0.0', port=port)