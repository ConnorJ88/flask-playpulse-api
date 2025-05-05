# Add these optimizations to the top of your services/data_collection.py file

import gc
import os
import time
import warnings
from statsbombpy import sb

# Disable matplotlib font cache
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.size'] = 10

# Disable StatsBomb warnings
warnings.filterwarnings('ignore')

# Memory-efficient pandas settings
import pandas as pd
pd.options.mode.chained_assignment = None  # Disable chained assignment warning
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

# For the PlayerDataCollector class, add these methods:

def _clear_unused_data(self):
    """Clear unused large data structures to save memory."""
    if not hasattr(self, 'optimize_memory') or self.optimize_memory:
        # Clean up large data structures when no longer needed
        if hasattr(self, 'team_performances'):
            del self.team_performances
            
        # Force garbage collection
        gc.collect()

def collect_player_data(self):
    """Memory-optimized data collection."""
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
    
    # Memory optimization settings
    checked_competitions = 0
    max_competitions_to_check = 3  # Reduced from 5
    
    # Go through competitions from most recent
    for _, comp in competitions.iterrows():
        if matches_found >= self.max_matches or checked_competitions >= max_competitions_to_check:
            break
            
        comp_id = comp['competition_id']
        season_id = comp['season_id']
        
        try:
            # Get matches for this competition
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
            
            if matches.empty:
                continue
                
            checked_competitions += 1
            
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
            
        # Clear memory after processing each competition
        gc.collect()
    
    # Create DataFrame of matches
    matches_df = pd.DataFrame(player_matches)
    
    processing_time = time.time() - start_time
    print(f"Data collection completed in {processing_time:.2f} seconds")
    print(f"Found {matches_found} matches with player participation")
    
    if matches_found > 0:
        self.player_events = all_player_events
        self.player_matches = matches_df
        return True
    else:
        print("No matches found for player")
        return False

def calculate_performance_metrics(self):
    """Memory-optimized metrics calculation."""
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
            'defensive_actions': defensive_actions
        }
        
        metrics.append(match_metrics)
    
    # Create metrics DataFrame and sort by date (oldest to newest for time series)
    self.performance_metrics = pd.DataFrame(metrics)
    self.performance_metrics = self.performance_metrics.sort_values('match_date')
    
    # Add a match sequence number (for easier time series indexing)
    self.performance_metrics['match_num'] = range(1, len(self.performance_metrics) + 1)
    
    # Clean up large data structures to free memory
    if hasattr(self, 'optimize_memory') and self.optimize_memory:
        # Keep only the final performance metrics
        self.player_events = None
        gc.collect()
    
    print(f"Calculated performance metrics for {len(self.performance_metrics)} matches")
    return True