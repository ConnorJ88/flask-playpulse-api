# test_statsbomb.py
from statsbombpy import sb
import pandas as pd

def test_statsbomb_access():
    """Test StatsBomb API access"""
    print("Testing StatsBomb API access...")
    
    try:
        # Get competitions
        competitions = sb.competitions()
        if competitions is None or competitions.empty:
            print("Failed to retrieve competitions")
            return False
        
        print(f"SUCCESS: Retrieved {len(competitions)} competitions")
        print(f"Sample competitions: {competitions.head(3)}")
        
        # Try to get matches for first competition
        comp = competitions.iloc[0]
        comp_id = comp['competition_id']
        season_id = comp['season_id']
        
        print(f"Testing match retrieval for {comp['competition_name']} {comp['season_name']}...")
        matches = sb.matches(competition_id=comp_id, season_id=season_id)
        
        if matches is None or matches.empty:
            print(f"Failed to retrieve matches for competition {comp_id}-{season_id}")
            return False
        
        print(f"SUCCESS: Retrieved {len(matches)} matches")
        
        # Try to get events for first match
        match = matches.iloc[0]
        match_id = match['match_id']
        
        print(f"Testing event retrieval for match {match_id}...")
        events = sb.events(match_id=match_id)
        
        if events is None or events.empty:
            print(f"Failed to retrieve events for match {match_id}")
            return False
        
        print(f"SUCCESS: Retrieved {len(events)} events")
        
        # Get sample player
        player_events = events.dropna(subset=['player_id', 'player'])
        if player_events.empty:
            print("No players found in events")
            return False
        
        sample_player = player_events[['player_id', 'player']].drop_duplicates().iloc[0]
        print(f"Sample player: {sample_player['player']} (ID: {sample_player['player_id']})")
        
        return True
    except Exception as e:
        print(f"Error testing StatsBomb API: {str(e)}")
        return False

if __name__ == "__main__":
    test_statsbomb_access()