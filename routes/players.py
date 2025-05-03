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
    """Get player performance metrics"""
    try:
        # Convert player_id to float
        print(f"Performance request for player_id: {player_id}")
        player_id_float = float(player_id)
        
        # Create collector with timeout handling
        collector = PlayerDataCollector(player_id=player_id_float, max_matches=5)  # Reduce to 5 matches for speed
        
        # Add timeout handling
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Data collection timed out")
        
        # Set 45 second timeout for data collection
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(45)
        
        try:
            if not collector.collect_player_data():
                signal.alarm(0)  # Disable alarm
                return jsonify({'error': 'Failed to collect player data'}), 404
            
            if not collector.calculate_performance_metrics():
                signal.alarm(0)  # Disable alarm
                return jsonify({'error': 'Failed to calculate performance metrics'}), 500
            
            # Convert performance metrics to JSON
            performances = collector.performance_metrics.to_dict(orient='records')
            
            # Disable alarm
            signal.alarm(0)
            
            return jsonify(performances)
        except TimeoutError as e:
            print(f"Timeout during data collection: {e}")
            return jsonify({'error': 'Data collection timed out. Please try again.'}), 504
        finally:
            # Ensure alarm is disabled
            signal.alarm(0)
            
    except ValueError:
        return jsonify({'error': 'Invalid player ID format'}), 400
    except Exception as e:
        print(f"Error in get_player_performances: {e}")
        return jsonify({'error': str(e)}), 500