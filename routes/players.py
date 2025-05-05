# routes/players.py - Optimized for memory efficiency and stability
from flask import Blueprint, request, jsonify, current_app
import time
import json
import threading
import functools
import os
import gc
from services.data_collection import PlayerDataCollector

player_routes = Blueprint('player_routes', __name__)

# Simple in-memory cache - store only essential player data, not full objects
# Format: {player_id: {'data': [...], 'timestamp': time.time()}}
player_cache = {}
active_jobs = {}  # Track ongoing background jobs

def cleanup_memory():
    """Force garbage collection to free memory."""
    gc.collect()

# Background processing function
def process_player_data_in_background(player_id):
    """Process player data in background thread with memory optimization."""
    try:
        print(f"Starting background processing for player: {player_id}")
        # Create collector but set max matches to a reasonable number to limit memory use
        collector = PlayerDataCollector(player_id=player_id, max_matches=5)
        
        # Update job status
        active_jobs[player_id] = {'status': 'collecting', 'progress': 0, 'message': 'Finding player data...'}
        
        # Step 1: Collect player data (this is usually the slow part)
        if not collector.collect_player_data():
            active_jobs[player_id] = {'status': 'failed', 'message': 'Failed to collect player data'}
            cleanup_memory()
            return
            
        # Update status
        active_jobs[player_id] = {'status': 'processing', 'progress': 50, 'message': 'Calculating metrics...'}
        
        # Step 2: Calculate performance metrics
        if not collector.calculate_performance_metrics():
            active_jobs[player_id] = {'status': 'failed', 'message': 'Failed to calculate performance metrics'}
            cleanup_memory()
            return
        
        # Step 3: Extract only the necessary data for caching
        # Convert to simple dict to reduce memory usage (not the full pandas DataFrame)
        performances = collector.performance_metrics.to_dict(orient='records')
        
        # Save to cache
        player_cache[player_id] = {
            'data': performances,
            'timestamp': time.time()
        }
        
        # Update job status
        active_jobs[player_id] = {
            'status': 'completed', 
            'data': performances,
            'message': 'Data processing complete'
        }
        
        # Important: Clean up the large collector object to free memory
        del collector
        cleanup_memory()
        
        print(f"Background processing completed for player: {player_id}")
    except Exception as e:
        print(f"Error in background processing for player {player_id}: {e}")
        active_jobs[player_id] = {'status': 'failed', 'message': f'Processing error: {str(e)}'}
        cleanup_memory()

@player_routes.route('/<player_id>', methods=['GET'])
def get_player(player_id):
    """Get player details by ID - memory-efficient version"""
    print(f"API received player_id: {player_id}, type: {type(player_id)}")
    
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        print(f"Converted to float: {player_id_float}")
        
        # Create a minimal collector just for verification - no data loading yet
        collector = PlayerDataCollector(player_id=player_id_float)
        
        print(f"Verifying player ID: {player_id_float}")
        exists = collector._verify_player_id()
        print(f"Player verification result: {exists}")
        
        if not exists:
            print(f"Player not found with ID: {player_id_float}")
            return jsonify({'error': 'Player not found'}), 404
        
        # Return basic player info
        response = {
            'id': collector.player_id,
            'name': collector.full_name,
            'team': 'Unknown',  # Would need to be added to your data collector
            'position': 'Unknown'  # Same here
        }
        
        # Clean up to save memory
        del collector
        cleanup_memory()
        
        return jsonify(response)
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/validate/<player_id>', methods=['GET'])
def validate_player(player_id):
    """Validate if a player ID exists - memory-efficient version"""
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        
        # Create minimal collector
        collector = PlayerDataCollector(player_id=player_id_float)
        exists = collector._verify_player_id()
        
        # Get result and clean up
        result = {'valid': exists}
        if exists:
            result['name'] = collector.full_name
            
        del collector
        cleanup_memory()
        
        if exists:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances', methods=['GET'])
def get_player_performances(player_id):
    """Get player performance metrics with background processing and caching"""
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        
        # 1. Check if data is already in cache
        if player_id_float in player_cache:
            print(f"Returning cached data for player {player_id_float}")
            return jsonify(player_cache[player_id_float]['data'])
        
        # 2. Check if processing is already in progress
        if player_id_float in active_jobs:
            job_status = active_jobs[player_id_float]
            
            # If job completed, return the data
            if job_status.get('status') == 'completed' and 'data' in job_status:
                return jsonify(job_status['data'])
                
            # If job is in progress or failed, return appropriate status
            message = job_status.get('message', 'Processing in progress')
            status_code = 202 if job_status.get('status') != 'failed' else 500
            return jsonify({'status': job_status.get('status'), 'message': message}), status_code
        
        # 3. Start a new background job
        active_jobs[player_id_float] = {
            'status': 'starting', 
            'progress': 0,
            'message': 'Initiating data collection'
        }
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_player_data_in_background,
            args=(player_id_float,)
        )
        thread.daemon = True  # Thread will exit when main program exits
        thread.start()
        
        return jsonify({
            'status': 'processing',
            'message': 'Data collection started'
        }), 202
        
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances/status', methods=['GET'])
def get_performance_status(player_id):
    """Check the status of background processing job"""
    try:
        player_id_float = float(player_id)
        
        # If job is active, return its status
        if player_id_float in active_jobs:
            return jsonify(active_jobs[player_id_float])
            
        # If data is in cache, job is implicitly complete
        if player_id_float in player_cache:
            return jsonify({
                'status': 'completed',
                'data': player_cache[player_id_float]['data'],
                'message': 'Data processing complete'
            })
            
        # No job found
        return jsonify({
            'status': 'not_found',
            'message': 'No active processing job found for this player'
        }), 404
            
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Implement a simple prediction endpoint based on previous performances
@player_routes.route('/<player_id>/predictions', methods=['GET'])
def predict_player_performance(player_id):
    """Generate simple performance predictions based on existing data"""
    try:
        player_id_float = float(player_id)
        
        # Check if we have performance data
        if player_id_float not in player_cache and player_id_float not in active_jobs:
            return jsonify({'error': 'No performance data available'}), 404
            
        # Get performance data
        performances = None
        if player_id_float in player_cache:
            performances = player_cache[player_id_float]['data']
        elif player_id_float in active_jobs and active_jobs[player_id_float].get('status') == 'completed':
            performances = active_jobs[player_id_float].get('data')
        else:
            return jsonify({'error': 'Performance data not ready yet'}), 202
            
        if not performances or len(performances) < 2:
            return jsonify({'error': 'Not enough performance data for predictions'}), 400
            
        # Sort performances by match_num to ensure chronological order
        performances = sorted(performances, key=lambda p: p.get('match_num', 0))
        
        # Get last two performances to calculate trend
        last_perf = performances[-1]
        second_last_perf = performances[-2]
        
        # Calculate percentage changes
        metrics = ['pass_completion_rate', 'total_events', 'total_passes', 'defensive_actions']
        predictions = {}
        
        for metric in metrics:
            if metric in last_perf and metric in second_last_perf and second_last_perf[metric] != 0:
                # Calculate percentage change
                change = (last_perf[metric] - second_last_perf[metric]) / second_last_perf[metric]
                
                # Apply damping factor to avoid extreme predictions
                damping_factor = 0.7
                predicted_change = change * damping_factor
                
                # Calculate predicted value
                predicted_value = last_perf[metric] * (1 + predicted_change)
                
                # Store prediction
                predictions[metric] = {
                    'metric_type': metric,
                    'current_value': last_perf[metric],
                    'predicted_value': predicted_value,
                    'percentage_change': predicted_change
                }
        
        return jsonify(list(predictions.values()))
        
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Cache maintenance endpoint
@player_routes.route('/maintenance/clear-cache', methods=['POST'])
def clear_cache():
    """Admin endpoint to clear the cache"""
    try:
        # Require admin key for security
        auth_key = request.headers.get('X-Admin-Key')
        if not auth_key or auth_key != os.environ.get('ADMIN_KEY', 'development_key'):
            return jsonify({'error': 'Unauthorized'}), 401
            
        # Clear caches
        player_cache.clear()
        
        # Don't clear active jobs - that could lead to orphaned threads
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500