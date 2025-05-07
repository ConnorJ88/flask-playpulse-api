# debug_player_lookup.py
from services.data_collection import PlayerDataCollector
import sys

def test_player_lookup(player_id=None, player_name=None):
    """Test player lookup functionality"""
    print("=== Testing Player Lookup ===")
    
    if player_id:
        # Clean the input to ensure it's a valid float
        try:
            cleaned_id = player_id.strip()
            float_id = float(cleaned_id)
            print(f"Looking up player by ID: {float_id}")
            collector = PlayerDataCollector(player_id=float_id)
            result = collector._verify_player_id()
        except ValueError as e:
            print(f"Error: Invalid player ID format - {e}")
            return
    elif player_name:
        print(f"Looking up player by name: {player_name}")
        collector = PlayerDataCollector(player_name=player_name)
        result = collector.find_player()
    else:
        print("Error: Must provide either player_id or player_name")
        return
    
    if result:
        print(f"SUCCESS: Found player {collector.full_name} (ID: {collector.player_id})")
    else:
        print("FAILED: Player not found")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_player_lookup.py [id|name] value")
        sys.exit(1)
    
    lookup_type = sys.argv[1].lower()
    value = sys.argv[2]
    
    if lookup_type == "id":
        test_player_lookup(player_id=value)
    elif lookup_type == "name":
        test_player_lookup(player_name=value)
    else:
        print("Invalid lookup type. Use 'id' or 'name'")