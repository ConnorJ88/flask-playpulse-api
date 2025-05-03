# routes/players.py
from flask import Blueprint, request, jsonify
from services.data_collection import PlayerDataCollector

player_routes = Blueprint('player_routes', __name__)

@player_routes.route('/search', methods=['GET'])
def search_players():
    """Search for players by name"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    try:
        collector = PlayerDataCollector()
        collector.player_name = query
        results = []
        
        if collector.find_player():
            # Return the matched player
            results.append({
                'id': collector.player_id,
                'name': collector.full_name,
                'team': 'Unknown',  # You may need to extend your data collector to get this
                'position': 'Unknown'  # Same here
            })
            
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/validate/<int:player_id>', methods=['GET'])
def validate_player(player_id):
    """Validate if a player ID exists"""
    try:
        collector = PlayerDataCollector(player_id=player_id)
        exists = collector._verify_player_id()
        
        if exists:
            return jsonify({'valid': True, 'name': collector.full_name})
        else:
            return jsonify({'valid': False}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<int:player_id>', methods=['GET'])
def get_player(player_id):
    """Get player details by ID"""
    try:
        collector = PlayerDataCollector(player_id=player_id)
        
        if not collector._verify_player_id():
            return jsonify({'error': 'Player not found'}), 404
        
        # Return basic player info
        return jsonify({
            'id': collector.player_id,
            'name': collector.full_name,
            'team': 'Unknown',  # Would need to be added to your data collector
            'position': 'Unknown'  # Same here
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@player_routes.route('/<int:player_id>/performances', methods=['GET'])
def get_player_performances(player_id):
    """Get player performance metrics"""
    try:
        collector = PlayerDataCollector(player_id=player_id)
        
        if not collector.collect_player_data():
            return jsonify({'error': 'Failed to collect player data'}), 404
        
        if not collector.calculate_performance_metrics():
            return jsonify({'error': 'Failed to calculate performance metrics'}), 500
        
        # Convert performance metrics to JSON
        performances = collector.performance_metrics.to_dict(orient='records')
        
        return jsonify(performances)
    except Exception as e:
        return jsonify({'error': str(e)}), 500