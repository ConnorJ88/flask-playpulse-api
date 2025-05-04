import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error
import warnings

class PlayerPerformancePredictor:
    def __init__(self, performance_metrics=None):
        """Initialize with performance metrics data."""
        self.performance_metrics = performance_metrics
        self.models = {}
        self.decline_threshold = 0.05  # 5% decline threshold
        # Updated best model types based on MSE and risk of overfitting
        self.best_model_types = {
            'pass_completion_rate': 'neural_network',  # MSE: 0.0053
            'total_events': 'neural_network',          # MSE: 0.0009
            'total_passes': 'random_forest',           # More reliable than DT with MSE: 0.0007
            'defensive_actions': 'neural_network'      # MSE: 0.0002
        }
    
    def set_metrics(self, performance_metrics):
        """Set the performance metrics data."""
        self.performance_metrics = performance_metrics
    
    def create_time_series_features(self, window_size=3):
        """Create time series features for ML models."""
        if self.performance_metrics is None:
            print("No performance metrics available.")
            return None, None, None, None, None
        
        # Select key metrics for prediction
        features = ['pass_completion_rate', 'total_events', 'total_passes', 'defensive_actions']
        
        # Get data
        data = self.performance_metrics[features].copy()
        
        # Normalize data
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(data)
        
        # Create X (input features) and y (target values) for ML models
        X, y = [], []
        
        # Use sliding window approach
        for i in range(window_size, len(scaled_data)):
            X.append(scaled_data[i-window_size:i])
            y.append(scaled_data[i])  # Predict all features
        
        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)
        
        # For non-sequential models, reshape X
        X_reshaped = X.reshape(X.shape[0], X.shape[1] * X.shape[2])
        
        return X, y, X_reshaped, scaler, features
    
    def train_models(self):
        """Train various models for performance prediction."""
        warnings.filterwarnings('ignore')  # Suppress warnings during training
        X, y, X_reshaped, scaler, feature_names = self.create_time_series_features()
        
        if X is None or len(X) < 4:  # Need some minimum amount of data
            print("Not enough time series data for modeling")
            return False
        
        # Split into train and test
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        X_train_reshaped = X_reshaped[:train_size]
        X_test_reshaped = X_reshaped[train_size:]
        
        print(f"Training models with {train_size} samples, testing with {len(X) - train_size} samples")
        
        # Dict to store models for each feature
        feature_models = {}
        best_models = {}
        
        # Train models for each feature/metric
        for i, feature in enumerate(feature_names):
            print(f"\nTraining models for {feature.replace('_', ' ').title()}:")
            
            # Extract target for this feature
            y_train_feature = y_train[:, i]
            y_test_feature = y_test[:, i]
            
            # Dictionary to track model performances
            model_performances = {}
            
            # 1. Neural Network - optimized for performance metrics
            model_nn = MLPRegressor(
                hidden_layer_sizes=(100, 50),  # Larger network
                activation='relu',
                solver='adam',
                max_iter=1000,  # More iterations
                alpha=0.001,    # Increased regularization to prevent overfitting
                learning_rate='adaptive',
                random_state=42,
                verbose=0
            )
            model_nn.fit(X_train_reshaped, y_train_feature)
            y_pred_nn = model_nn.predict(X_test_reshaped)
            mse_nn = mean_squared_error(y_test_feature, y_pred_nn)
            model_performances['neural_network'] = mse_nn
            
            # 2. Linear Regression
            model_lr = LinearRegression()
            model_lr.fit(X_train_reshaped, y_train_feature)
            y_pred_lr = model_lr.predict(X_test_reshaped)
            mse_lr = mean_squared_error(y_test_feature, y_pred_lr)
            model_performances['linear_regression'] = mse_lr
            
            # 3. Decision Tree - with safeguards against overfitting
            model_dt = DecisionTreeRegressor(
                max_depth=3,           # Reduced depth to prevent overfitting
                min_samples_split=3,   # Require more samples to split
                min_samples_leaf=2,    # Require more samples per leaf
                random_state=42
            )
            model_dt.fit(X_train_reshaped, y_train_feature)
            y_pred_dt = model_dt.predict(X_test_reshaped)
            mse_dt = mean_squared_error(y_test_feature, y_pred_dt)
            model_performances['decision_tree'] = mse_dt
            
            # 4. SVM - optimized for better performance
            model_svm = SVR(
                kernel='rbf',
                C=10.0,       # Increased from 1.0
                gamma='scale',
                epsilon=0.01   # Reduced from 0.1
            )
            model_svm.fit(X_train_reshaped, y_train_feature)
            y_pred_svm = model_svm.predict(X_test_reshaped)
            mse_svm = mean_squared_error(y_test_feature, y_pred_svm)
            model_performances['svm'] = mse_svm
            
            # 5. Random Forest - optimized with safeguards against overfitting
            model_rf = RandomForestRegressor(
                n_estimators=100,     # Moderate number of trees
                max_depth=5,          # Limited depth to prevent overfitting
                min_samples_split=2,
                min_samples_leaf=2,   # Require more samples per leaf
                max_features='sqrt',  # Use sqrt of features for splits
                random_state=42
            )
            model_rf.fit(X_train_reshaped, y_train_feature)
            y_pred_rf = model_rf.predict(X_test_reshaped)
            mse_rf = mean_squared_error(y_test_feature, y_pred_rf)
            model_performances['random_forest'] = mse_rf
            
            # Print MSE results
            print(f"  Neural Network - MSE: {mse_nn:.4f}")
            print(f"  Linear Regression - MSE: {mse_lr:.4f}")
            print(f"  Decision Tree - MSE: {mse_dt:.4f}")
            print(f"  SVM - MSE: {mse_svm:.4f}")
            print(f"  Random Forest - MSE: {mse_rf:.4f}")
            
            # Use our predefined best model type based on previous MSE analysis
            best_model_type = self.best_model_types.get(feature, 'neural_network')
            best_mse = model_performances[best_model_type]
            
            # Check for suspiciously low MSE (potential overfitting)
            if best_mse < 0.0001 and best_model_type == 'decision_tree':
                # Switch to a more robust model
                backup_model = 'random_forest' if model_performances['random_forest'] < model_performances['neural_network'] else 'neural_network'
                print(f"  ⚠️ Warning: Decision Tree MSE ({best_mse:.6f}) suggests overfitting")
                print(f"  → Switching to {backup_model.replace('_', ' ').title()} (MSE: {model_performances[backup_model]:.4f})")
                best_model_type = backup_model
                best_mse = model_performances[backup_model]
            
            print(f"  → Using {best_model_type.replace('_', ' ').title()} for {feature.replace('_', ' ').title()} prediction (MSE: {best_mse:.4f})")
            
            # Store all models for reference
            feature_models[feature] = {
                'neural_network': model_nn,
                'linear_regression': model_lr,
                'decision_tree': model_dt,
                'svm': model_svm,
                'random_forest': model_rf
            }
            
            # Store the best model for quick reference
            best_models[feature] = {
                'model_type': best_model_type,
                'model': feature_models[feature][best_model_type],
                'mse': best_mse
            }
        
        # Store all models and metadata
        self.models = {
            'feature_models': feature_models,
            'best_models': best_models,
            'scaler': scaler,
            'window_size': X_train.shape[1],
            'features': feature_names
        }
        
        return True
    
    # Update predict_next_performance method in services/ml_models.py to handle limited data better
def predict_next_performance(self):
    """Predict next performance and check for decline with fallback for limited data."""
    if not self.models:
        print("Models not trained. Run train_models() first.")
        return None, None
    
    if self.performance_metrics is None or len(self.performance_metrics) < 3:
        print("Not enough performance data for prediction")
        return None, None
    
    # If we have limited data (3-4 matches), use simple predictions
    if len(self.performance_metrics) < 5:
        print("Using simple prediction with limited data")
        
        predictions = {}
        changes = {}
        
        # Get the features we want to predict
        features = ['pass_completion_rate', 'total_events', 'total_passes', 'defensive_actions']
        
        # Calculate simple predictions based on average trend
        for feature in features:
            values = self.performance_metrics[feature].values
            
            # Calculate average change over available matches
            changes_between_matches = [values[i] - values[i-1] for i in range(1, len(values))]
            avg_change = sum(changes_between_matches) / len(changes_between_matches)
            
            # Predict next value
            current_value = values[-1]
            next_value = current_value + avg_change
            
            # Calculate percentage change
            perc_change = avg_change / current_value if current_value != 0 else 0
            
            # Store predictions
            predictions[feature] = next_value
            changes[feature] = perc_change
        
        return predictions, changes
    
    # Get most recent data for full prediction
    recent_data = self.performance_metrics[self.models['features']].tail(self.models['window_size']).values
    
    # Scale the data
    scaled_data = self.models['scaler'].transform(recent_data)
    
    # Prepare input for models (2D)
    X_reshaped = scaled_data.reshape(1, scaled_data.shape[0] * scaled_data.shape[1])
    
    # Make predictions for each feature using the best model
    predictions = {}
    changes = {}
    declining_features = []
    
    print("\nPerformance Predictions:")
    
    for feature in self.models['features']:
        # Get the best model for this feature
        best_model_info = self.models['best_models'][feature]
        best_model = best_model_info['model']
        model_type = best_model_info['model_type']
        
        # Get prediction from the best model
        prediction = best_model.predict(X_reshaped)[0]
        
        # Get current feature value
        feature_idx = self.models['features'].index(feature)
        current_value = scaled_data[-1, feature_idx]
        
        # Calculate percentage change
        perc_change = (prediction - current_value) / current_value if current_value != 0 else 0
        
        # Store results
        predictions[feature] = prediction
        changes[feature] = perc_change
        
        # Format feature name for display
        display_name = feature.replace('_', ' ').title()
        
        # Print prediction for this feature
        print(f"{display_name} (using {model_type.replace('_', ' ').title()}):")
        print(f"  Current: {current_value:.4f}")
        print(f"  Predicted: {prediction:.4f}")
        print(f"  Change: {perc_change:.2%}")
        
        # Check for decline
        if perc_change <= -self.decline_threshold:
            declining_features.append((feature, perc_change))
    
    # Alert for any declining features
    if declining_features:
        self._alert_decline(declining_features)
    else:
        print("\nNo significant performance decline predicted.")
    
    return predictions, changes
    
    def _alert_decline(self, declining_features):
        """Send an alert when predicted decrease is by 5% or more in any feature."""
        print("\n" + "!" * 50)
        print("ALERT: Performance Decline Predicted")
        
        for feature, change in declining_features:
            display_name = feature.replace('_', ' ').title()
            print(f"- {display_name}: Predicted decline of {abs(change):.2%}")
        
        print("\nThese declines exceed the threshold of 5%")
        print("Recommendation: Consider monitoring player workload or providing additional support")
        print("!" * 50)
    
    def visualize_performance(self, player_name=None):
        """Visualize player performance over time and predictions."""
        if self.performance_metrics is None:
            print("No performance metrics available")
            return
        
        plt.figure(figsize=(14, 12))
        
        # Plot 1: Pass completion rate over time
        ax1 = plt.subplot(2, 2, 1)
        plt.plot(self.performance_metrics['match_num'], self.performance_metrics['pass_completion_rate'], 'b-o')
        
        # If we have predictions, show them
        if hasattr(self, 'models') and self.models and 'best_models' in self.models:
            # Add prediction point if available
            if 'pass_completion_rate' in self.models['best_models']:
                # Get last point
                last_x = self.performance_metrics['match_num'].iloc[-1]
                last_y = self.performance_metrics['pass_completion_rate'].iloc[-1]
                
                # Get prediction
                feature = 'pass_completion_rate'
                feature_idx = self.models['features'].index(feature)
                recent_data = self.performance_metrics[self.models['features']].tail(self.models['window_size']).values
                scaled_data = self.models['scaler'].transform(recent_data)
                X_reshaped = scaled_data.reshape(1, scaled_data.shape[0] * scaled_data.shape[1])
                
                # Predict using best model
                best_model = self.models['best_models'][feature]['model']
                prediction_scaled = best_model.predict(X_reshaped)[0]
                
                # Convert from normalized scale back to original scale
                current_val = self.performance_metrics['pass_completion_rate'].iloc[-1]
                current_scaled = scaled_data[-1, feature_idx]
                
                # Simple ratio conversion to estimate the real value
                prediction_ratio = prediction_scaled / current_scaled if current_scaled != 0 else 1
                prediction = current_val * prediction_ratio
                
                # Show prediction as a star point
                plt.plot([last_x + 1], [prediction], 'r*', markersize=10, label='Prediction')
                
                # Add arrow to show trend
                plt.annotate('', xy=(last_x + 1, prediction), xytext=(last_x, last_y),
                            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
        
        plt.title('Pass Completion Rate Over Time')
        plt.xlabel('Match Number')
        plt.ylabel('Pass Completion Rate')
        plt.grid(True)
        if hasattr(plt, 'legend'):
            plt.legend()
        
        # Plot 2: Total events over time
        plt.subplot(2, 2, 2)
        plt.plot(self.performance_metrics['match_num'], self.performance_metrics['total_events'], 'g-o')
        
        # If we have predictions, show them for total events
        if hasattr(self, 'models') and self.models and 'best_models' in self.models:
            if 'total_events' in self.models['best_models']:
                last_x = self.performance_metrics['match_num'].iloc[-1]
                last_y = self.performance_metrics['total_events'].iloc[-1]
                
                feature = 'total_events'
                feature_idx = self.models['features'].index(feature)
                best_model = self.models['best_models'][feature]['model']
                
                # Use the same X_reshaped from above
                prediction_scaled = best_model.predict(X_reshaped)[0]
                
                # Convert to original scale
                current_val = self.performance_metrics['total_events'].iloc[-1]
                current_scaled = scaled_data[-1, feature_idx]
                prediction_ratio = prediction_scaled / current_scaled if current_scaled != 0 else 1
                prediction = current_val * prediction_ratio
                
                # Show prediction
                plt.plot([last_x + 1], [prediction], 'r*', markersize=10, label='Prediction')
                plt.annotate('', xy=(last_x + 1, prediction), xytext=(last_x, last_y),
                            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
        
        plt.title('Total Events Over Time')
        plt.xlabel('Match Number')
        plt.ylabel('Total Events')
        plt.grid(True)
        if hasattr(plt, 'legend'):
            plt.legend()
        
        # Plot 3: Defensive actions over time
        plt.subplot(2, 2, 3)
        plt.plot(self.performance_metrics['match_num'], self.performance_metrics['defensive_actions'], 'r-o')
        
        # Add prediction for defensive actions
        if hasattr(self, 'models') and self.models and 'best_models' in self.models:
            if 'defensive_actions' in self.models['best_models']:
                last_x = self.performance_metrics['match_num'].iloc[-1]
                last_y = self.performance_metrics['defensive_actions'].iloc[-1]
                
                feature = 'defensive_actions'
                feature_idx = self.models['features'].index(feature)
                best_model = self.models['best_models'][feature]['model']
                
                prediction_scaled = best_model.predict(X_reshaped)[0]
                
                # Convert to original scale
                current_val = self.performance_metrics['defensive_actions'].iloc[-1]
                current_scaled = scaled_data[-1, feature_idx]
                prediction_ratio = prediction_scaled / current_scaled if current_scaled != 0 else 1
                prediction = current_val * prediction_ratio
                
                # Show prediction
                plt.plot([last_x + 1], [prediction], 'r*', markersize=10, label='Prediction')
                plt.annotate('', xy=(last_x + 1, prediction), xytext=(last_x, last_y),
                            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
        
        plt.title('Defensive Actions Over Time')
        plt.xlabel('Match Number')
        plt.ylabel('Defensive Actions')
        plt.grid(True)
        if hasattr(plt, 'legend'):
            plt.legend()
        
        # Plot 4: Total passes over time
        plt.subplot(2, 2, 4)
        plt.plot(self.performance_metrics['match_num'], self.performance_metrics['total_passes'], 'c-o', label='Total Passes')
        
        # Add prediction for total passes
        if hasattr(self, 'models') and self.models and 'best_models' in self.models:
            if 'total_passes' in self.models['best_models']:
                last_x = self.performance_metrics['match_num'].iloc[-1]
                last_y = self.performance_metrics['total_passes'].iloc[-1]
                
                feature = 'total_passes'
                feature_idx = self.models['features'].index(feature)
                best_model = self.models['best_models'][feature]['model']
                
                prediction_scaled = best_model.predict(X_reshaped)[0]
                
                # Convert to original scale
                current_val = self.performance_metrics['total_passes'].iloc[-1]
                current_scaled = scaled_data[-1, feature_idx]
                prediction_ratio = prediction_scaled / current_scaled if current_scaled != 0 else 1
                prediction = current_val * prediction_ratio
                
                # Show prediction
                plt.plot([last_x + 1], [prediction], 'r*', markersize=10, label='Prediction')
                plt.annotate('', xy=(last_x + 1, prediction), xytext=(last_x, last_y),
                            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
        
        plt.title('Total Passes Over Time')
        plt.xlabel('Match Number')
        plt.ylabel('Passes')
        plt.legend()
        plt.grid(True)
        
        if player_name:
            plt.suptitle(f'Performance Metrics for {player_name}', fontsize=16)
            
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)
        plt.show()