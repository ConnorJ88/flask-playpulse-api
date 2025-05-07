from locust import HttpUser, task, between
import random

class PlayPulseUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def get_player_details(self):
        player_id = random.choice([1, 2, 3, 4, 5])
        self.client.get(f"/api/players/{player_id}")
    
    @task(2)
    def get_performances(self):
        player_id = random.choice([1, 2, 3, 4, 5])
        self.client.get(f"/api/players/{player_id}/performances")
    
    @task(1)
    def get_predictions(self):
        player_id = random.choice([1, 2, 3, 4, 5])
        self.client.get(f"/api/players/{player_id}/predictions")