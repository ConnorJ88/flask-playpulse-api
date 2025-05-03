# routes/predictions.py
from flask import Blueprint, request, jsonify
import pandas as pd
from services.ml_models import PlayerPerformancePredictor
from services.data_collection import PlayerDataCollector

prediction_routes = Blueprint('prediction_routes', __name__)

@prediction_routes.route('/player/<int:player_id>', methods=['GET'])
def predict_player_performance(player_id):
    """Predict player performance"""
    try:
        # Collect player data
        collector = PlayerDataCollector(player_id=player_id)
        
        if not collector.collect_player_data():
            return jsonify({'error': 'Failed to collect player data'}), 404
        
        if not collector.calculate_performance_metrics():
            return jsonify({'error': 'Failed to calculate performance metrics'}), 500
        
        # Create predictor and train models
        predictor = PlayerPerformancePredictor(collector.performance_metrics)
        
        if not predictor.train_models():
            return jsonify({'error': 'Failed to train prediction models'}), 500
        
        # Make prediction
        ensemble_pred, perf_change = predictor.predict_next_performance()
        
        # Get current values
        current_metrics = collector.performance_metrics.iloc[-1].to_dict()
        
        # Prepare response - include predictions for all metrics
        response = {
            'pass_completion_rate': {
                'current_value': float(current_metrics['pass_completion_rate']),
                'predicted_value': float(ensemble_pred),
                'percentage_change': float(perf_change)
            }
        }
        
        # Add simplified predictions for other metrics
        for metric in ['total_events', 'total_passes', 'defensive_actions']:
            current_value = float(current_metrics[metric])
            # Simple prediction based on completion rate change (you may want to improve this)
            pred_value = current_value * (1 + perf_change)
            
            response[metric] = {
                'current_value': current_value,
                'predicted_value': float(pred_value),
                'percentage_change': float(perf_change)
            }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500