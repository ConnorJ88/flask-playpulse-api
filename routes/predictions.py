from flask import Blueprint, request, jsonify
import pandas as pd
from services.ml_models import PlayerPerformancePredictor
from services.data_collection import PlayerDataCollector
import os
import pickle
import time
import random

prediction_routes = Blueprint('prediction_routes', __name__)

# Cache helper functions (same as in players.py)
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

def generate_simple_predictions(performance_metrics):
    """Generate simple predictions when not enough data for ML models."""
    print("Generating simple predictions based on available data")
    
    # Get latest performance data
    latest_metrics = performance_metrics.iloc[-1]
    
    # Create a simple response with basic predictions (small random variations)
    response = {}
    for metric in ['pass_completion_rate', 'total_events', 'total_passes', 'defensive_actions']:
        # Random change between -5% and +5%
        change = (random.random() * 0.1) - 0.05
        current_value = float(latest_metrics[metric])
        
        response[metric] = {
            'current_value': current_value,
            'predicted_value': current_value * (1 + change),
            'percentage_change': change
        }
    
    return response

@prediction_routes.route('/player/<int:player_id>', methods=['GET'])
def predict_player_performance(player_id):
    """Predict player performance with caching"""
    try:
        print(f"Prediction request received for player {player_id}")
        
        # Check cache first
        cache_dir = "cache/predictions"
        cache_file = f"{cache_dir}/{player_id}.pkl"
        cached_data = get_cached_data(cache_file, max_age_hours=24)  # 1 day
        
        if cached_data:
            print(f"Returning cached predictions for player_id: {player_id}")
            return jsonify(cached_data)
        
        # Collect player data (use cached performances if available)
        perf_cache_file = f"cache/performances/{player_id}.pkl"
        cached_performances = get_cached_data(perf_cache_file, max_age_hours=48)
        
        if cached_performances:
            print(f"Using cached performances for predictions - player_id: {player_id}")
            # Convert back to DataFrame
            import pandas as pd
            performances_df = pd.DataFrame(cached_performances)
            
            # Check if we have enough data for ML prediction
            if len(performances_df) < 4:
                print(f"Not enough match data for ML prediction: {len(performances_df)} matches")
                response = generate_simple_predictions(performances_df)
                save_to_cache(cache_file, response)
                return jsonify(response)
                
            # Create predictor with the cached metrics
            predictor = PlayerPerformancePredictor(performances_df)
        else:
            print(f"No cached performances, collecting fresh data for player {player_id}")
            collector = PlayerDataCollector(player_id=player_id, max_matches=15)
            
            if not collector.collect_player_data():
                return jsonify({'error': 'Failed to collect player data'}), 404
            
            if not collector.calculate_performance_metrics():
                return jsonify({'error': 'Failed to calculate performance metrics'}), 500
            
            # Check if we have enough data for ML prediction
            if len(collector.performance_metrics) < 4:
                print(f"Not enough match data for ML prediction: {len(collector.performance_metrics)} matches")
                response = generate_simple_predictions(collector.performance_metrics)
                save_to_cache(cache_file, response)
                return jsonify(response)
                
            # Create predictor with the collected metrics
            predictor = PlayerPerformancePredictor(collector.performance_metrics)
        
        # Train models
        print("Training prediction models...")
        if not predictor.train_models():
            return jsonify({'error': 'Failed to train prediction models'}), 500
        
        # Make prediction
        print("Generating predictions...")
        predictions, perf_changes = predictor.predict_next_performance()
        
        if predictions is None:
            return jsonify({'error': 'Failed to generate predictions'}), 500
            
        # Format the response
        response = {}
        for metric, pred_value in predictions.items():
            # Get the current value
            if cached_performances:
                current_value = float(performances_df[metric].iloc[-1])
            else:
                current_value = float(collector.performance_metrics[metric].iloc[-1])
                
            change = perf_changes[metric]
            
            response[metric] = {
                'current_value': current_value,
                'predicted_value': float(pred_value),
                'percentage_change': float(change)
            }
        
        # Save predictions to cache
        save_to_cache(cache_file, response)
        
        return jsonify(response)
    except Exception as e:
        print(f"ERROR in prediction endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500