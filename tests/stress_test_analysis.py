import concurrent.futures
import urllib.request
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
ENDPOINTS = [
    "/analysis/completion",
    "/analysis/visualizations/priority",
    "/analysis/visualizations/completion-trends",
    "/analysis/visualizations/delay",
    "/analysis/visualizations/scatter-duration",
    "/analysis/visualizations/daily-tasks"
]

def hit_endpoint(endpoint):
    url = f"{BASE_URL}{endpoint}"
    try:
        start_time = time.time()
        with urllib.request.urlopen(url, timeout=10) as response:
            status = response.getcode()
            duration = time.time() - start_time
            return f"PASS: {endpoint} ({status}) in {duration:.2f}s"
    except Exception as e:
        return f"FAIL: {endpoint} -> {str(e)}"

def run_stress_test(num_requests=20):
    print(f"Starting stress test with {num_requests} concurrent requests...")
    
    # We use a large number of workers to simulate high concurrency
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        # Repeat the endpoints to get to num_requests
        tasks = [ENDPOINTS[i % len(ENDPOINTS)] for i in range(num_requests)]
        results = list(executor.map(hit_endpoint, tasks))
    
    for res in results:
        print(res)
    
    fail_count = sum(1 for r in results if "FAIL" in r)
    if fail_count == 0:
        print("\nSUCCESS: All concurrent requests completed without deadlock!")
        return True
    else:
        print(f"\nFAILURE: {fail_count} requests failed.")
        return False

if __name__ == "__main__":
    # Small delay to ensure server is ready if this script is run immediately after starting the server
    time.sleep(2)
    if not run_stress_test():
        sys.exit(1)
