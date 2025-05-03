from statsbombpy import sb
import pandas as pd
import numpy as np
import time
import warnings
warnings.filterwarnings('ignore')

class PlayerDataCollector:
    def __init__(self, player_id=None, player_name=None, max_matches=15):
        """Initialize the data collector with either player ID or name."""
        self.player_id = player_id
        self.player_name = player_name
        self.max_matches = max_matches
        self.player_events = None
        self.player_matches = None
        self.performance_metrics = None
        self.full_name = None
        self.anomaly_threshold = 2.0  # Z-score threshold for anomaly detection
        
    def find_player(self):
        """Find player ID if only name is provided."""
        if self.player_id is not None:
            return self._verify_player_id()
        
        if self.player_name is None:
            print("Error: No player name or ID provided")
            return False
        
        print(f"Searching for player: {self.player_name}...")
        start_time = time.time()
        
        # Get competitions (prioritize more recent ones)
        competitions = sb.competitions()
        competitions = competitions.sort_values('season_id', ascending=False)
        
        # Limit to checking at most 5 competitions to save time
        checked_competitions = 0
        
        for _, comp in competitions.iterrows():
            if checked_competitions >= 5:
                break
                
            try:
                matches = sb.matches(competition_id=comp['competition_id'], season_id=comp['season_id'])
                if matches.empty:
                    continue
                    
                checked_competitions += 1
                print(f"Checking {comp['competition_name']} {comp['season_name']}...")
                
                # Check just one match from this competition
                match_id = matches.iloc[0]['match_id']
                events = sb.events(match_id=match_id)
                
                # Get all players
                players = events[['player_id', 'player']].dropna().drop_duplicates()
                
                # Search for name
                for _, player in players.iterrows():
                    if isinstance(player['player'], str) and self.player_name.lower() in player['player'].lower():
                        search_time = time.time() - start_time
                        self.player_id = player['player_id']
                        self.full_name = player['player']
                        print(f"Found player: {self.full_name} with ID: {self.player_id}")
                        print(f"Search completed in {search_time:.2f} seconds")
                        return True
            except Exception as e:
                print(f"Error searching in competition: {e}")
                continue
        
        print(f"Player '{self.player_name}' not found. Please check the spelling or try a different player.")
        print(f"Search completed in {time.time() - start_time:.2f} seconds")
        return False
    
    def _verify_player_id(self):
        """Verify a player ID exists in the dataset."""
        print(f"Verifying player ID: {self.player_id}, type: {type(self.player_id)}")
        import os
        os.environ['STATSBOMB_API'] = 'open'
    
        # Ensure player_id is a float (StatsBomb IDs are always floats)
        if not isinstance(self.player_id, float):
            try:
                self.player_id = float(self.player_id)
                print(f"Converted player_id to float: {self.player_id}")
            except (ValueError, TypeError):
                print(f"Invalid player ID format: {self.player_id}")
                return False
    
        # Try to find the player in available competitions
        try:
            competitions = sb.competitions()
            if competitions is None or competitions.empty:
                print("Failed to retrieve competitions")
                return False
        
            competitions = competitions.sort_values('season_id', ascending=False)
            checked_competitions = 0
        
            for _, comp in competitions.iterrows():
                if checked_competitions >= 15:  # Limit to 15 competitions to avoid too long searches
                    break
                
                try:
                    matches = sb.matches(competition_id=comp['competition_id'], season_id=comp['season_id'])
                    if matches is None or matches.empty:
                        continue
                
                    checked_competitions += 1
                    print(f"Checking competition: {comp['competition_name']} {comp['season_name']}")
                
                    # Check first few matches
                    for idx, match in matches.head(3).iterrows():
                        match_id = match['match_id']
                        try:
                            events = self._throttled_request(sb.events, match_id=match_id)
                            if events is None or events.empty:
                                continue
                        
                            # Important: Use exact equality for float comparison
                            player_info = events[events['player_id'] == self.player_id][['player_id', 'player']].drop_duplicates()
                            if not player_info.empty:
                                self.full_name = player_info.iloc[0]['player']
                                print(f"Found player {self.full_name} (ID: {self.player_id})")
                                return True
                        except Exception as e:
                            print(f"Error checking match {match_id}: {str(e)}")
                            continue
                except Exception as e:
                    print(f"Error checking competition: {str(e)}")
                    continue
        
            print(f"Player ID {self.player_id} not found after checking {checked_competitions} competitions")
            return False
        except Exception as e:
            print(f"Error during player verification: {str(e)}")
            return False
    
    def collect_player_data(self):
        """Collect player match and event data."""
        # First ensure we have a player ID and name
        if self.player_id is None:
            if not self.find_player():
                print("Failed to find player. Please try again with a valid name or ID.")
                return False
        else:
            # If we have an ID but no name yet, verify the ID to get the name
            if self.full_name is None and not self._verify_player_id():
                print("Failed to verify player ID. Please try again with a valid ID.")
                return False
        
        # Double-check that we have the player's name
        if self.full_name is None:
            print("No player name found. Something went wrong during player verification.")
            return False
            
        print(f"Getting data for {self.full_name} (ID: {self.player_id})...")
        start_time = time.time()
        
        # Get competitions (prioritize more recent ones)
        competitions = sb.competitions()
        competitions = competitions.sort_values('season_id', ascending=False)
        
        # Track matches where we've found the player
        player_matches = []
        all_player_events = pd.DataFrame()
        matches_found = 0
        
        # To assess team performance (for detecting anomalies)
        team_performances = {}
        
        # Go through competitions from most recent
        for _, comp in competitions.iterrows():
            if matches_found >= self.max_matches:
                break
                
            comp_id = comp['competition_id']
            season_id = comp['season_id']
            
            try:
                # Get matches for this competition
                matches = sb.matches(competition_id=comp_id, season_id=season_id)
                
                # Sort matches by date (most recent first)
                matches['match_date'] = pd.to_datetime(matches['match_date'])
                matches = matches.sort_values('match_date', ascending=False)
                
                # Process each match
                for _, match in matches.iterrows():
                    if matches_found >= self.max_matches:
                        break
                        
                    match_id = match['match_id']
                    
                    try:
                        # Get events for this match
                        events = sb.events(match_id=match_id)
                        
                        # Check if player is in this match
                        player_events = events[events['player_id'] == self.player_id]
                        
                        if not player_events.empty:
                            # Player found in this match
                            matches_found += 1
                            print(f"Found match {matches_found}/{self.max_matches}: {match['home_team']} vs {match['away_team']} ({match['match_date'].date()})")
                            
                            # Add match info
                            player_events['match_id'] = match_id
                            player_events['match_date'] = match['match_date']
                            player_events['competition'] = comp['competition_name']
                            player_events['season'] = comp['season_name']
                            player_events['home_team'] = match['home_team']
                            player_events['away_team'] = match['away_team']
                            
                            # Determine player's team
                            if len(player_events) > 0:
                                first_event = player_events.iloc[0]
                                if 'team' in first_event and isinstance(first_event['team'], str):
                                    player_team = first_event['team']
                                    player_events['player_team'] = player_team
                                    
                                    # Calculate team stats for anomaly detection
                                    team_events = events[events['team'] == player_team]
                                    
                                    # Simple team metrics
                                    team_passes = team_events[team_events['type'] == 'Pass']
                                    total_team_passes = len(team_passes)
                                    completed_team_passes = sum(team_passes['pass_outcome'].isna())
                                    team_pass_completion = completed_team_passes / total_team_passes if total_team_passes > 0 else 0
                                    
                                    # Save team performance metrics for this match
                                    team_performances[match_id] = {
                                        'team': player_team,
                                        'total_passes': total_team_passes,
                                        'pass_completion': team_pass_completion,
                                        'total_events': len(team_events)
                                    }
                                else:
                                    print(f"Warning: Could not determine player's team for match {match_id}")
                            
                            # Add to collections
                            all_player_events = pd.concat([all_player_events, player_events])
                            
                            # Save match info
                            player_matches.append({
                                'match_id': match_id,
                                'match_date': match['match_date'],
                                'competition': comp['competition_name'],
                                'season': comp['season_name'],
                                'home_team': match['home_team'],
                                'away_team': match['away_team']
                            })
                            
                    except Exception as e:
                        print(f"Error with match {match_id}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error with competition {comp_id}-{season_id}: {e}")
                continue
        
        # Create DataFrame of matches
        matches_df = pd.DataFrame(player_matches)
        
        processing_time = time.time() - start_time
        print(f"Data collection completed in {processing_time:.2f} seconds")
        
        if matches_found > 0:
            print(f"Found {matches_found} matches with player participation")
            self.player_events = all_player_events
            self.player_matches = matches_df
            self.team_performances = team_performances
            return True
        else:
            print(f"No matches found for {self.full_name}. The player might not have recent match data available.")
            return False
    
    def calculate_performance_metrics(self):
        """Calculate performance metrics for each match and filter anomalies."""
        if self.player_events is None or self.player_matches is None:
            print("No player data available. Run collect_player_data() first.")
            return False
        
        metrics = []
        
        # Calculate metrics for each match
        for _, match in self.player_matches.iterrows():
            match_id = match['match_id']
            match_events = self.player_events[self.player_events['match_id'] == match_id]
            
            # Basic event counts
            total_events = len(match_events)
            
            # Pass metrics
            passes = match_events[match_events['type'] == 'Pass']
            total_passes = len(passes)
            completed_passes = sum(passes['pass_outcome'].isna())
            pass_completion_rate = completed_passes / total_passes if total_passes > 0 else 0
            
            # Shot metrics
            shots = match_events[match_events['type'] == 'Shot']
            total_shots = len(shots)
            goals = len(shots[shots['shot_outcome'] == 'Goal'])
            
            # Defensive actions
            defensive_actions = len(match_events[match_events['type'].isin(['Interception', 'Block', 'Clearance', 'Pressure', 'Tackle'])])
            
            # Team performance context (if available)
            team_perf = None
            team_pass_completion = None
            if hasattr(self, 'team_performances') and match_id in self.team_performances:
                team_perf = self.team_performances[match_id]
                team_pass_completion = team_perf['pass_completion']
            
            # Create metrics dictionary
            match_metrics = {
                'match_id': match_id,
                'match_date': match['match_date'],
                'competition': match['competition'],
                'season': match['season'],
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'total_events': total_events,
                'total_passes': total_passes,
                'completed_passes': completed_passes,
                'pass_completion_rate': pass_completion_rate,
                'total_shots': total_shots,
                'goals': goals,
                'defensive_actions': defensive_actions,
                'team_pass_completion': team_pass_completion  # Will be None if team data not available
            }
            
            metrics.append(match_metrics)
        
        # Create metrics DataFrame and sort by date (oldest to newest for time series)
        self.performance_metrics = pd.DataFrame(metrics)
        
        # Check for and handle anomalies
        self._detect_and_handle_anomalies()
        
        # Sort by date after removing anomalies
        self.performance_metrics = self.performance_metrics.sort_values('match_date')
        
        # Add a match sequence number (for easier time series indexing)
        self.performance_metrics['match_num'] = range(1, len(self.performance_metrics) + 1)
        
        print(f"Calculated performance metrics for {len(self.performance_metrics)} matches after filtering anomalies")
        return True
    # Add to data_collection.py
    def _throttled_request(self, func, *args, **kwargs):
        """Throttle requests to StatsBomb API to avoid overwhelming it"""
        max_retries = 3
        retry_delay = 1  # seconds
    
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Request failed, retrying in {retry_delay} seconds: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise e

    def _detect_and_handle_anomalies(self):
        """Detect and handle anomalous performances."""
        if self.performance_metrics is None or len(self.performance_metrics) < 4:
            print("Not enough data to detect anomalies")
            return
        
        print("\nAnalyzing for performance anomalies...")
        
        # Key metrics to check for anomalies
        metrics_to_check = ['pass_completion_rate', 'total_events', 'defensive_actions']
        anomalous_matches = set()
        
        # Find anomalies in each metric using z-scores
        for metric in metrics_to_check:
            values = self.performance_metrics[metric].values
            mean = np.mean(values)
            std = np.std(values)
            
            if std == 0:  # Skip if no variation (prevents division by zero)
                continue
                
            # Calculate z-scores
            z_scores = np.abs((values - mean) / std)
            
            # Find matches with high z-scores (potential anomalies)
            for i, z in enumerate(z_scores):
                if z > self.anomaly_threshold:
                    match_id = self.performance_metrics.iloc[i]['match_id']
                    match_date = self.performance_metrics.iloc[i]['match_date']
                    teams = f"{self.performance_metrics.iloc[i]['home_team']} vs {self.performance_metrics.iloc[i]['away_team']}"
                    
                    print(f"Potential anomaly detected: Match on {match_date.date()} ({teams})")
                    print(f"  {metric.replace('_', ' ').title()}: Value {values[i]:.2f}, Z-score: {z:.2f}")
                    
                    anomalous_matches.add(match_id)
        
        # Check for team performance anomalies
        if 'team_pass_completion' in self.performance_metrics.columns:
            team_values = self.performance_metrics['team_pass_completion'].dropna().values
            
            if len(team_values) > 3:  # Need some minimum data
                team_mean = np.mean(team_values)
                team_std = np.std(team_values)
                
                if team_std > 0:
                    for i, row in self.performance_metrics.iterrows():
                        if pd.isna(row['team_pass_completion']):
                            continue
                            
                        team_z = np.abs((row['team_pass_completion'] - team_mean) / team_std)
                        
                        if team_z > self.anomaly_threshold:
                            match_date = row['match_date']
                            teams = f"{row['home_team']} vs {row['away_team']}"
                            
                            print(f"Team performance anomaly: Match on {match_date.date()} ({teams})")
                            print(f"  Team Pass Completion: {row['team_pass_completion']:.2f}, Z-score: {team_z:.2f}")
                            
                            anomalous_matches.add(row['match_id'])
        
        # Remove anomalous matches
        if anomalous_matches:
            original_count = len(self.performance_metrics)
            self.performance_metrics = self.performance_metrics[~self.performance_metrics['match_id'].isin(anomalous_matches)]
            removed_count = original_count - len(self.performance_metrics)
            
            print(f"Removed {removed_count} anomalous match(es) from analysis")
        else:
            print("No significant anomalies detected")
            
        return