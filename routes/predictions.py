# routes/predictions.py
from flask import Blueprint, request, jsonify
from app import cache
from tasks import collect_player_data_task

prediction_routes = Blueprint('prediction_routes', __name__)

@prediction_routes.route('/player/<player_id>', methods=['GET'])
def predict_player_performance(player_id):
    """Predict player performance using async processing"""
    try:
        # Check if data already available in cache
        cache_key = f"player_data_{player_id}"
        player_data = cache.get(cache_key)
        
        if player_data and player_data.get('predictions'):
            # Return the prediction portion only
            return jsonify(player_data['predictions'])
        
        # Check if processing already in progress
        job_key = f"player_job_{player_id}"
        job_id = cache.get(job_key)
        
        if job_id:
            # Job already in progress
            return jsonify({
                'status': 'processing',
                'message': 'Data is being processed',
                'job_id': job_id
            }), 202
        
        # Start new processing task
        max_matches = int(request.args.get('max_matches', 7))
        task = collect_player_data_task.delay(player_id, max_matches)
        
        # Cache the job ID
        cache.set(job_key, task.id, timeout=600)  # 10 minutes
        
        return jsonify({
            'status': 'processing',
            'message': 'Performance prediction started',
            'job_id': task.id
        }), 202
        
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500