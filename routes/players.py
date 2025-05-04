# routes/players.py
from flask import Blueprint, request, jsonify, current_app
from services.data_collection import PlayerDataCollector
from app import cache
from tasks import collect_player_data_task
import time

player_routes = Blueprint('player_routes', __name__)

@player_routes.route('/<player_id>', methods=['GET'])
def get_player(player_id):
    """Get player details by ID"""
    try:
        print(f"API received player_id: {player_id}, type: {type(player_id)}")
        
        # Convert player_id to float
        player_id_float = float(player_id)
        print(f"Converted to float: {player_id_float}")
        
        collector = PlayerDataCollector(player_id=player_id_float)
        
        print(f"Verifying player ID: {player_id_float}")
        exists = collector._verify_player_id()
        print(f"Player verification result: {exists}")
        
        if not exists:
            print(f"Player not found with ID: {player_id_float}")
            return jsonify({'error': 'Player not found'}), 404
        
        # Return basic player info
        return jsonify({
            'id': collector.player_id,
            'name': collector.full_name,
            'team': 'Unknown',  # Would need to be added to your data collector
            'position': 'Unknown'  # Same here
        })
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances', methods=['GET'])
def get_player_performances(player_id):
    """Get player performance metrics with async processing"""
    try:
        # Force processing using the query parameter ?force=true
        force_processing = request.args.get('force', 'false').lower() == 'true'
        
        # Check if data is already cached
        cache_key = f"player_data_{player_id}"
        cached_data = None if force_processing else cache.get(cache_key)
        
        if cached_data:
            print(f"Returning cached data for player_id: {player_id}")
            return jsonify(cached_data["performances"])
        
        # Check if there's an active job
        job_key = f"player_job_{player_id}"
        job_id = cache.get(job_key)
        
        if job_id and not force_processing:
            # Job already in progress
            return jsonify({
                'status': 'processing',
                'message': 'Data collection is already in progress',
                'job_id': job_id
            }), 202
        
        # Get max matches param, default to 7
        max_matches = int(request.args.get('max_matches', 7))
        max_matches = min(max_matches, 10)  # Cap at 10 matches
        
        # Start new task
        print(f"Performance request for player_id: {player_id}")
        task = collect_player_data_task.delay(player_id, max_matches)
        
        # Cache the job ID
        cache.set(job_key, task.id, timeout=600)  # 10 minutes
        
        return jsonify({
            'status': 'processing',
            'message': 'Data collection started',
            'job_id': task.id,
            'max_matches': max_matches
        }), 202
        
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances/status/<job_id>', methods=['GET'])
def get_performance_job_status(player_id, job_id):
    """Check status of an async job"""
    try:
        # Check if results already cached
        cache_key = f"player_data_{player_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return jsonify({
                'status': 'completed',
                'data': cached_data
            })
        
        # Check job status
        task = collect_player_data_task.AsyncResult(job_id)
        
        if task.state == 'PENDING':
            return jsonify({
                'status': 'pending',
                'message': 'Job is in the queue'
            })
        elif task.state == 'FAILURE':
            return jsonify({
                'status': 'failed',
                'message': str(task.info)
            })
        elif task.state == 'SUCCESS':
            result = task.get()
            # Cache results if successful
            if result.get('status') == 'success':
                cache.set(cache_key, result, timeout=86400)  # 24 hours
            return jsonify({
                'status': 'completed',
                'data': result
            })
        else:
            # Still processing
            return jsonify({
                'status': 'processing',
                'message': 'Job is in progress'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@player_routes.route('/<player_id>/performances/cancel/<job_id>', methods=['POST'])
def cancel_performance_job(player_id, job_id):
    """Cancel an in-progress job"""
    try:
        # Remove job marker
        job_key = f"player_job_{player_id}"
        cache.delete(job_key)
        
        # Revoke task
        collect_player_data_task.AsyncResult(job_id).revoke(terminate=True)
        
        return jsonify({
            'status': 'cancelled',
            'message': 'Job cancelled successfully'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500