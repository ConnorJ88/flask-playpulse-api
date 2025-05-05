
from flask import Blueprint, request, jsonify, current_app
import time
import json
import threading
import os
import gc
from services.data_collection import PlayerDataCollector

# Updated visualization imports that don't cause memory issues
from services.ml_models import PlayerPerformancePredictor
import numpy as np

player_routes = Blueprint('player_routes', __name__)

# In-memory cache
_player_cache = {}
_performance_cache = {}
_active_jobs = {}

# Disable matplotlib font caching to prevent memory issues
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
matplotlib.rcParams['font.family'] = 'sans-serif'  # Use a standard font
matplotlib.rcParams['font.size'] = 10  # Smaller size
matplotlib.rcParams['figure.dpi'] = 72  # Lower resolution

# Utility to clean up memory
def cleanup_memory():
    """Force garbage collection to free memory."""
    gc.collect()

# Background processing function with reduced number of matches
def process_player_data(player_id):
    """Process player data in background with memory optimizations."""
    try:
        job_id = str(player_id)
        _active_jobs[job_id] = {
            'status': 'starting',
            'message': 'Initializing data collection...'
        }
        
        # Create collector with memory optimizations
        collector = PlayerDataCollector(player_id=player_id, max_matches=5)
        
        # Step 1: Verify player exists
        _active_jobs[job_id] = {
            'status': 'verifying',
            'message': 'Verifying player ID...'
        }
        if not collector.find_player():
            _active_jobs[job_id] = {
                'status': 'failed',
                'message': f'Player not found with ID: {player_id}'
            }
            cleanup_memory()
            return
        
        # Step 2: Collect data
        _active_jobs[job_id] = {
            'status': 'collecting',
            'message': f'Finding match data for {collector.full_name}...'
        }
        if not collector.collect_player_data():
            _active_jobs[job_id] = {
                'status': 'failed', 
                'message': 'Failed to collect player data'
            }
            cleanup_memory()
            return
            
        # Step 3: Calculate metrics
        _active_jobs[job_id] = {
            'status': 'processing',
            'message': 'Calculating performance metrics...'
        }
        if not collector.calculate_performance_metrics():
            _active_jobs[job_id] = {
                'status': 'failed',
                'message': 'Failed to calculate performance metrics'
            }
            cleanup_memory()
            return
        
        # Step 4: Extract and format data
        performance_data = collector.performance_metrics.to_dict(orient='records')
        
        # Save processed data to caches
        _performance_cache[str(player_id)] = {
            'data': performance_data,
            'timestamp': time.time(),
            'name': collector.full_name
        }
        
        # Update job status to complete
        _active_jobs[job_id] = {
            'status': 'completed',
            'message': 'Data processing complete',
            'data': performance_data
        }
        
        # Clean up to free memory
        del collector
        cleanup_memory()
        
    except Exception as e:
        job_id = str(player_id)
        _active_jobs[job_id] = {
            'status': 'failed',
            'message': f'Error: {str(e)}'
        }
        cleanup_memory()

# Modified player routes to use the optimized processing and caching
@player_routes.route('/<player_id>', methods=['GET'])
def get_player(player_id):
    """Get player details by ID with memory optimization."""
    print(f"API received player_id: {player_id}, type: {type(player_id)}")
    
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        print(f"Converted to float: {player_id_float}")
        
        # Check if player data is cached
        if str(player_id_float) in _performance_cache:
            cached_data = _performance_cache[str(player_id_float)]
            return jsonify({
                'id': player_id_float,
                'name': cached_data.get('name', 'Unknown'),
                'team': 'Unknown',
                'position': 'Unknown'
            })
        
        # Create a minimal collector just for player verification
        collector = PlayerDataCollector(player_id=player_id_float)
        
        print(f"Verifying player ID: {player_id_float}")
        exists = collector._verify_player_id()
        print(f"Player verification result: {exists}")
        
        if not exists:
            print(f"Player not found with ID: {player_id_float}")
            return jsonify({'error': 'Player not found'}), 404
        
        # Get the minimal info we need
        result = {
            'id': collector.player_id,
            'name': collector.full_name,
            'team': 'Unknown',
            'position': 'Unknown'
        }
        
        # Clean up to free memory
        del collector
        cleanup_memory()
        
        return jsonify(result)
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances', methods=['GET'])
def get_player_performances(player_id):
    """Get player performance metrics with optimized processing."""
    try:
        # Convert to float
        player_id_float = float(player_id)
        str_id = str(player_id_float)
        
        # Check if data is already cached
        if str_id in _performance_cache:
            print(f"Returning cached performance data for player {player_id_float}")
            return jsonify(_performance_cache[str_id]['data'])
        
        # Check if processing is already in progress
        if str_id in _active_jobs:
            job_status = _active_jobs[str_id]
            
            # If job completed, return the data
            if job_status.get('status') == 'completed':
                if 'data' in job_status:
                    return jsonify(job_status['data'])
            
            # Otherwise return current status
            message = job_status.get('message', 'Processing in progress...')
            return jsonify({
                'status': job_status.get('status', 'processing'),
                'message': message
            }), 202
        
        # Start processing in the background
        thread = threading.Thread(
            target=process_player_data,
            args=(player_id_float,)
        )
        thread.daemon = True
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
    """Check the status of a performance data processing job."""
    try:
        str_id = str(float(player_id))
        
        # If job is active, return its status
        if str_id in _active_jobs:
            return jsonify(_active_jobs[str_id])
            
        # If data is cached, job is implicitly complete
        if str_id in _performance_cache:
            return jsonify({
                'status': 'completed',
                'message': 'Data processing complete',
                'data': _performance_cache[str_id]['data']
            })
            
        # No job found
        return jsonify({
            'status': 'not_found',
            'message': 'No processing job found for this player'
        })
        
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/predictions', methods=['GET'])
def predict_player_performance(player_id):
    """Generate performance predictions with memory optimizations."""
    try:
        player_id_float = float(player_id)
        str_id = str(player_id_float)
        
        # Check if we have performance data
        if str_id not in _performance_cache:
            # Check if job is running
            if str_id in _active_jobs and _active_jobs[str_id].get('status') != 'failed':
                return jsonify({
                    'status': 'processing',
                    'message': 'Performance data is still being processed'
                }), 202
            
            return jsonify({'error': 'No performance data available'}), 404
            
        # Get performance data
        performances = _performance_cache[str_id]['data']
        
        if not performances or len(performances) < 2:
            return jsonify({'error': 'Not enough performance data for predictions'}), 400
            
        # Sort by match number
        performances.sort(key=lambda p: p.get('match_num', 0))
        
        # Get last two performances
        last_perf = performances[-1]
        second_last_perf = performances[-2]
        
        # Memory-efficient way to calculate trends without using ML models
        metrics = ['pass_completion_rate', 'total_events', 'total_passes', 'defensive_actions']
        predictions = []
        
        for metric in metrics:
            if metric in last_perf and metric in second_last_perf and second_last_perf[metric] != 0:
                # Calculate percentage change
                change = (last_perf[metric] - second_last_perf[metric]) / second_last_perf[metric]
                
                # Apply damping factor
                damping = 0.7
                predicted_change = change * damping
                
                # Predict next value
                predicted_value = last_perf[metric] * (1 + predicted_change)
                
                # Add to predictions
                predictions.append({
                    'metric_type': metric,
                    'current_value': last_perf[metric],
                    'predicted_value': predicted_value,
                    'percentage_change': predicted_change
                })
        
        return jsonify(predictions)
        
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500