# routes/players.py
from flask import Blueprint, request, jsonify
from services.data_collection import PlayerDataCollector

player_routes = Blueprint('player_routes', __name__)

@player_routes.route('/<player_id>', methods=['GET'])
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
        
        # Rest of your code...
        
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

@player_routes.route('/validate/<player_id>', methods=['GET'])
def validate_player(player_id):
    """Validate if a player ID exists"""
    try:
        # Convert player_id to float
        player_id_float = float(player_id)
        
        collector = PlayerDataCollector(player_id=player_id_float)
        exists = collector._verify_player_id()
        
        if exists:
            return jsonify({'valid': True, 'name': collector.full_name})
        else:
            return jsonify({'valid': False}), 404
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<player_id>/performances', methods=['GET'])
def get_player_performances(player_id):
    """Get player performance metrics with timeouts and retries"""
    try:
        from flask import current_app
        import time
        
        # Convert player_id to float
        player_id_float = float(player_id)
        
        # Add query parameter to control max matches
        max_matches = request.args.get('max_matches', default=10, type=int)
        max_matches = min(max_matches, 8)  # Cap at 8 to prevent timeouts
        
        # Start collector with reduced max_matches
        collector = PlayerDataCollector(player_id=player_id_float, max_matches=max_matches)
        
        # First attempt with 8 matches
        start_time = time.time()
        print(f"Performance request for player_id: {player_id}")
        
        success = collector.collect_player_data()
        
        if not success:
            # If first attempt failed with timeout, retry with fewer matches
            if hasattr(collector, 'timeout_occurred') and collector.timeout_occurred:
                print("Request failed, retrying with fewer matches")
                collector.max_matches = 5  # Reduce matches further
                success = collector.collect_player_data()
                
                if not success:
                    return jsonify({'error': 'Failed to collect player data after retry'}), 500
            else:
                return jsonify({'error': 'Failed to collect player data'}), 404
        
        if not collector.calculate_performance_metrics():
            return jsonify({'error': 'Failed to calculate performance metrics'}), 500
        
        # Convert performance metrics to JSON
        performances = collector.performance_metrics.to_dict(orient='records')
        
        # Log processing time
        processing_time = time.time() - start_time
        print(f"Performance request completed in {processing_time:.2f} seconds")
        
        return jsonify(performances)
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500