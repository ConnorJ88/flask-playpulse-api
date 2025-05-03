# debug_player.py
import os
import sys

# Add the project root to the path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import using the correct path
from services.data_collection import PlayerDataCollector
from statsbombpy import sb

def test_player_by_id(player_id):
    """Test looking up a specific player ID"""
    print(f"=== Testing Player Lookup for ID: {player_id} ===")
    
    try:
        # Create collector
        collector = PlayerDataCollector(player_id=player_id)
        
        # Test StatsBomb API access first
        print("Testing StatsBomb API connection...")
        try:
            competitions = sb.competitions()
            if competitions is None or competitions.empty:
                print("❌ ERROR: Failed to retrieve competitions from StatsBomb API")
                return False
            
            print(f"✓ Successfully retrieved {len(competitions)} competitions")
        except Exception as e:
            print(f"❌ ERROR with StatsBomb API: {str(e)}")
            return False
        
        # Now try to verify the player
        print(f"Attempting to verify player ID: {player_id}")
        result = collector._verify_player_id()
        
        if result:
            print(f"✓ SUCCESS: Found player {collector.full_name} (ID: {collector.player_id})")
        else:
            print("❌ FAILED: Player not found through normal verification")
            
            # Try manual lookup in a few competitions
            print("\nAttempting manual lookup...")
            
            # Check more competitions
            for _, comp in competitions.head(10).iterrows():
                print(f"Checking {comp['competition_name']} {comp['season_name']}...")
                
                try:
                    matches = sb.matches(competition_id=comp['competition_id'], season_id=comp['season_id'])
                    if matches is None or matches.empty:
                        print(f"  No matches found for this competition")
                        continue
                    
                    # Check first match
                    match = matches.iloc[0]
                    match_id = match['match_id']
                    
                    print(f"  Checking match: {match['home_team']} vs {match['away_team']}")
                    events = sb.events(match_id=match_id)
                    
                    if events is None or events.empty:
                        print(f"  No events found for this match")
                        continue
                    
                    # Check for our player
                    player_events = events[events['player_id'] == player_id]
                    if not player_events.empty:
                        player_info = events[events['player_id'] == player_id][['player_id', 'player']].drop_duplicates()
                        player_name = player_info.iloc[0]['player']
                        print(f"✓ FOUND PLAYER: {player_name} (ID: {player_id}) in manual lookup!")
                        return True
                    
                    # List a few players from this match for reference
                    print("  Sample players from this match:")
                    sample_players = events[['player_id', 'player']].dropna().drop_duplicates().head(3)
                    for _, p in sample_players.iterrows():
                        print(f"    - ID: {p['player_id']} - {p['player']}")
                except Exception as e:
                    print(f"  Error with this competition/match: {str(e)}")
            
            print("❌ Player not found in manual lookup either")
            
    except Exception as e:
        print(f"❌ ERROR during lookup: {str(e)}")

# SET THE PLAYER ID HERE - just edit this line
PLAYER_ID = 5503

if __name__ == "__main__":
    test_player_by_id(PLAYER_ID)