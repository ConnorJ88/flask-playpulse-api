# tasks.py
from app import celery, cache
from services.data_collection import PlayerDataCollector
from services.ml_models import PlayerPerformancePredictor
import pandas as pd
import time
import traceback

@celery.task(bind=True, max_retries=2)
def collect_player_data_task(self, player_id, max_matches=7):
    """Celery task to collect and analyze player data asynchronously"""
    try:
        print(f"Starting data collection task for player_id: {player_id}")
        start_time = time.time()
        
        # Convert ID to float
        player_id_float = float(player_id)
        
        # Create collector with specified matches
        collector = PlayerDataCollector(player_id=player_id_float, max_matches=max_matches)
        
        # Step 1: Collect player data
        print(f"Collecting data for player_id: {player_id}")
        if not collector.collect_player_data():
            print(f"Failed to collect data for player_id: {player_id}")
            return {
                "status": "error",
                "message": "Failed to collect player data",
                "player_id": player_id
            }
            
        # Step 2: Calculate performance metrics
        print(f"Calculating metrics for player_id: {player_id}")
        if not collector.calculate_performance_metrics():
            print(f"Failed to calculate metrics for player_id: {player_id}")
            return {
                "status": "error",
                "message": "Failed to calculate performance metrics",
                "player_id": player_id
            }
        
        # Get player info and metrics
        performances = collector.performance_metrics.to_dict(orient='records')
        player_name = collector.full_name
        
        # Step 3: Generate predictions
        print(f"Training prediction models for player_id: {player_id}")
        predictor = PlayerPerformancePredictor(collector.performance_metrics)
        
        prediction_results = None
        if predictor.train_models():
            print(f"Predicting performance for player_id: {player_id}")
            predictions, changes = predictor.predict_next_performance()
            
            # Format predictions
            prediction_results = {
                "metrics": {},
                "declining_metrics": []
            }
            
            # Process each prediction
            for metric, pred_value in predictions.items():
                change = changes[metric]
                prediction_results["metrics"][metric] = {
                    "current_value": float(collector.performance_metrics[metric].iloc[-1]),
                    "predicted_value": float(pred_value),
                    "percentage_change": float(change)
                }
                
                # Check for decline
                if change <= -0.05:  # 5% threshold
                    prediction_results["declining_metrics"].append({
                        "metric": metric,
                        "change": float(change)
                    })
        
        # Prepare result
        result = {
            "status": "success",
            "player_id": player_id,
            "player_name": player_name,
            "matches_found": len(performances),
            "performances": performances,
            "predictions": prediction_results,
            "processing_time": time.time() - start_time
        }
        
        # Cache the result
        cache_key = f"player_data_{player_id}"
        cache.set(cache_key, result, timeout=86400)  # Cache for 24 hours
        
        # Remove job flag
        job_key = f"player_job_{player_id}"
        cache.delete(job_key)
        
        print(f"Data processing task completed in {time.time() - start_time:.2f} seconds")
        return result
        
    except Exception as e:
        print(f"Error in data collection task: {e}")
        print(traceback.format_exc())
        
        # Retry on failure
        if self.request.retries < self.max_retries:
            return self.retry(exc=e, countdown=5)
        
        return {
            "status": "error",
            "message": str(e),
            "player_id": player_id
        }