import os
import subprocess
import datetime

# Create results directory if it doesn't exist
results_dir = "tests/performance/test_results/average_load"
os.makedirs(results_dir, exist_ok=True)

# Generate timestamp for results files
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Run Locust in headless mode with CSV output
subprocess.run([
    "locust",
    "-f", "tests/performance/locustfile.py",
    "--host=http://localhost:10000",
    "--users=50",
    "--spawn-rate=1",
    "--run-time=7m",
    "--headless",
    "--csv=" + os.path.join(results_dir, f"average_load_{timestamp}")
])

print(f"Average load test completed. Results saved to {results_dir}")