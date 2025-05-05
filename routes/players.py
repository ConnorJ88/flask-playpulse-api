from flask import Blueprint, request, jsonify
from services.data_collection import PlayerDataCollector
import os
import pickle
import time

player_routes = Blueprint('player_routes', __name__)

# Cache helper functions
def get_cached_data(cache_file, max_age_hours=24):
    """Get data from cache if available and not too old."""
    try:
        if os.path.exists(cache_file):
            cache_age = time.time() - os.path.getmtime(cache_file)
            # Use cache if not too old
            if cache_age < max_age_hours * 60 * 60:
                print(f"Loading from cache: {cache_file}")
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
    except Exception as e:
        print(f"Error reading cache: {e}")
    return None

def save_to_cache(cache_file, data):
    """Save data to cache file."""
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
        print(f"Saved to cache: {cache_file}")
        return True
    except Exception as e:
        print(f"Error saving to cache: {e}")
        return False

@player_routes.route('/<player_id>', methods=['GET'])
def get_player(player_id):
    """Get player details by ID with caching"""
    print(f"API received player_id: {player_id}, type: {type(player_id)}")
    
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        print(f"Converted to float: {player_id_float}")
        
        # Check cache first
        cache_dir = "cache/players"
        cache_file = f"{cache_dir}/{player_id_float}.pkl"
        cached_data = get_cached_data(cache_file, max_age_hours=168)  # 7 days
        
        if cached_data:
            print(f"Returning cached data for player_id: {player_id_float}")
            return jsonify(cached_data)
        
        # If not in cache, fetch from API
        collector = PlayerDataCollector(player_id=player_id_float)
        
        print(f"Verifying player ID: {player_id_float}")
        exists = collector._verify_player_id()
        print(f"Player verification result: {exists}")
        
        if not exists:
            print(f"Player not found with ID: {player_id_float}")
            return jsonify({'error': 'Player not found'}), 404
        
        # Return basic player info
        player_data = {
            'id': collector.player_id,
            'name': collector.full_name,
            'team': 'Unknown',  # Would need to be added to your data collector
            'position': 'Unknown'  # Same here
        }
        
        # Save to cache
        save_to_cache(cache_file, player_data)
        
        return jsonify(player_data)
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        print(f"Error in get_player: {e}")
        return jsonify({'error': str(e)}), 500

@player_routes.route('/validate/<player_id>', methods=['GET'])
def validate_player(player_id):
    """Validate if a player ID exists with caching"""
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        
        # Check cache first
        cache_dir = "cache/validations"
        cache_file = f"{cache_dir}/{player_id_float}.pkl"
        cached_data = get_cached_data(cache_file, max_age_hours=336)  # 14 days
        
        if cached_data:
            print(f"Returning cached validation for player_id: {player_id_float}")
            return jsonify(cached_data)
        
        collector = PlayerDataCollector(player_id=player_id_float)
        exists = collector._verify_player_id()
        
        result = {'valid': exists}
        if exists:
            result['name'] = collector.full_name
        
        # Save to cache
        save_to_cache(cache_file, result)
        
        if exists:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        print(f"Error validating player ID: {e}")
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances', methods=['GET'])
def get_player_performances(player_id):
    """Get player performance metrics with caching"""
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        
        # Check cache first
        cache_dir = "cache/performances"
        cache_file = f"{cache_dir}/{player_id_float}.pkl"
        cached_data = get_cached_data(cache_file, max_age_hours=48)  # 2 days
        
        if cached_data:
            print(f"Returning cached performances for player_id: {player_id_float}")
            return jsonify(cached_data)
        
        print(f"Collecting performance data for player_id: {player_id_float}")
        collector = PlayerDataCollector(player_id=player_id_float, max_matches=15)
        
        if not collector.collect_player_data():
            return jsonify({'error': 'Failed to collect player data'}), 404
        
        if not collector.calculate_performance_metrics():
            return jsonify({'error': 'Failed to calculate performance metrics'}), 500
        
        # Convert performance metrics to JSON
        performances = collector.performance_metrics.to_dict(orient='records')
        
        # Save to cache
        save_to_cache(cache_file, performances)
        
        return jsonify(performances)
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        print(f"Error in get_player_performances: {e}")
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances/status', methods=['GET'])
def get_performance_status(player_id):
    """Check status of performance data collection"""
    try:
        player_id_float = float(player_id)
        
        # Check if cached data exists
        cache_dir = "cache/performances"
        cache_file = f"{cache_dir}/{player_id_float}.pkl"
        
        if os.path.exists(cache_file):
            cache_age = time.time() - os.path.getmtime(cache_file)
            hours_old = cache_age / 3600
            
            data_size = os.path.getsize(cache_file) / 1024  # Size in KB
            
            return jsonify({
                'status': 'available',
                'cached': True,
                'cache_age_hours': round(hours_old, 2),
                'data_size_kb': round(data_size, 2),
                'player_id': player_id_float
            })
        
        return jsonify({
            'status': 'unavailable',
            'message': 'Performance data not cached, will be collected on request',
            'player_id': player_id_float
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500