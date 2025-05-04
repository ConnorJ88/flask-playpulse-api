# routes/players.py
# routes/players.py
from flask import Blueprint, request, jsonify, current_app
from services.data_collection import PlayerDataCollector
import threading
import time
import json
import os
from datetime import datetime

# Simple in-memory cache
performance_cache = {}
job_status = {}

player_routes = Blueprint('player_routes', __name__)

def background_data_collection(player_id, max_matches=7):
    """Background task to collect and process player data"""
    try:
        # Set job as running
        job_status[player_id] = {
            'status': 'running',
            'start_time': time.time(),
            'message': 'Processing started'
        }
        
        # Convert ID to float
        player_id_float = float(player_id)
        
        # Create collector with reduced matches
        collector = PlayerDataCollector(player_id=player_id_float, max_matches=max_matches)
        
        # Collect data
        if not collector.collect_player_data():
            job_status[player_id] = {
                'status': 'failed',
                'end_time': time.time(),
                'message': 'Failed to collect player data'
            }
            return
            
        # Calculate metrics
        if not collector.calculate_performance_metrics():
            job_status[player_id] = {
                'status': 'failed',
                'end_time': time.time(),
                'message': 'Failed to calculate performance metrics'
            }
            return
        
        # Convert to dict
        performances = collector.performance_metrics.to_dict(orient='records')
        
        # Store in cache
        performance_cache[player_id] = {
            'data': performances,
            'timestamp': time.time(),
            'player_name': collector.full_name
        }
        
        # Update job status
        job_status[player_id] = {
            'status': 'completed',
            'end_time': time.time(),
            'message': 'Data processing completed'
        }
        
    except Exception as e:
        print(f"Error in background task: {e}")
        job_status[player_id] = {
            'status': 'failed',
            'end_time': time.time(),
            'message': str(e)
        }

@player_routes.route('/<player_id>', methods=['GET'])
def get_player(player_id):
    """Get player details by ID"""
    print(f"API received player_id: {player_id}, type: {type(player_id)}")
    
    try:
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
            'team': 'Unknown',
            'position': 'Unknown'
        })
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances', methods=['GET'])
def get_player_performances(player_id):
    """Get player performance metrics with background processing"""
    try:
        # Check if data is already cached
        if player_id in performance_cache:
            cache_age = time.time() - performance_cache[player_id]['timestamp']
            # If cache is less than 24 hours old, return it
            if cache_age < 86400:
                print(f"Returning cached data for player_id: {player_id}")
                return jsonify(performance_cache[player_id]['data'])
        
        # Check if job is already running
        if player_id in job_status and job_status[player_id]['status'] == 'running':
            start_time = job_status[player_id]['start_time']
            elapsed = time.time() - start_time
            
            return jsonify({
                'status': 'processing',
                'message': f'Data collection in progress (running for {elapsed:.1f} seconds)',
                'player_id': player_id
            }), 202
        
        # Start new background thread
        print(f"Performance request for player_id: {player_id}")
        max_matches = int(request.args.get('max_matches', 7))
        
        thread = threading.Thread(
            target=background_data_collection,
            args=(player_id, max_matches)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'processing',
            'message': 'Data collection started',
            'player_id': player_id
        }), 202
        
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances/status', methods=['GET'])
def get_performance_job_status(player_id):
    """Check status of a background job"""
    try:
        # Check if data is already cached
        if player_id in performance_cache:
            cache_age = time.time() - performance_cache[player_id]['timestamp']
            # If cache is less than 24 hours old, consider it valid
            if cache_age < 86400:
                return jsonify({
                    'status': 'completed',
                    'data': performance_cache[player_id]['data']
                })
        
        # Check job status
        if player_id in job_status:
            status_info = job_status[player_id]
            
            if status_info['status'] == 'completed':
                # Job completed successfully
                return jsonify({
                    'status': 'completed',
                    'data': performance_cache.get(player_id, {}).get('data', [])
                })
            elif status_info['status'] == 'failed':
                # Job failed
                return jsonify({
                    'status': 'failed',
                    'message': status_info['message']
                })
            else:
                # Job still running
                elapsed = time.time() - status_info['start_time']
                return jsonify({
                    'status': 'processing',
                    'message': f'Job is in progress (running for {elapsed:.1f} seconds)'
                })
        else:
            # No job found
            return jsonify({
                'status': 'not_found',
                'message': 'No processing job found for this player'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500