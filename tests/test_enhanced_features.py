import urllib.request
import urllib.error
import json
import sys
import base64

BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def make_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header('Content-Type', 'application/json')
    
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.data = json_data
        
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            body = response.read()
            content_type = response.headers.get('Content-Type', '')
            
            if body:
                if 'application/json' in content_type:
                    return status_code, json.loads(body)
                else:
                    return status_code, body.decode('utf-8')
            return status_code, None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 500, str(e)

def test_enhanced_features():
    failed = False
    
    # 1. User Management
    log("Testing User Management...", "START")
    user_payload = {
        "username": "batman_test",
        "email": "wayne_test@gotham.com",
        "full_name": "Bruce Wayne"
    }
    
    # Try create user (handle 400 if exists from previous run)
    status, response = make_request("POST", "/users/", user_payload)
    user_id = None
    
    if status == 201:
        user_id = response['user_id']
        log(f"User created: ID {user_id}", "PASS")
    elif status == 400:
        log("User already exists, fetching...", "INFO")
        # Fetch existing to get ID
        status, users = make_request("GET", "/users/")
        for u in users:
            if u['username'] == "batman_test":
                user_id = u['user_id']
                break
        log(f"Found existing user ID: {user_id}", "PASS")
    else:
        log(f"Failed to create/find user: {response}", "FAIL")
        return

    if not user_id:
        log("Could not resolve user_id", "FAIL")
        return

    # 2. Task with Assignment
    log("Testing Task Assignment...", "START")
    task_payload = {
        "name": "Save Gotham",
        "description": "Stop the Joker",
        "due_date": "2026-12-25",
        "priority": "high",
        "assigned_user_id": user_id
    }
    
    status, task_response = make_request("POST", "/tasks/", task_payload)
    if status == 201 and task_response.get('assigned_user_id') == user_id:
        task_id = task_response['task_id']
        log(f"Task created with assignment: ID {task_id}", "PASS")
    else:
        log(f"Failed to assign task: {task_response}", "FAIL")
        failed = True
        return # Stop if task creation failed

    # 3. Manual Notification
    log("Testing Manual Notification...", "START")
    status, notify_response = make_request("POST", f"/tasks/{task_id}/notify")
    if status == 200:
        log("Notification triggered successfully", "PASS")
    else:
        log(f"Notification failed: {notify_response}", "FAIL")
        failed = True

    # 4. New Visualizations
    log("Testing New Visualizations...", "START")
    vis_endpoints = [
        "/analysis/visualizations/scatter-duration",
        "/analysis/visualizations/daily-tasks"
    ]
    
    for endpoint in vis_endpoints:
        status, response = make_request("GET", endpoint)
        if status == 200 and "image_base64" in response:
            # check if base64 is valid length
            if len(response["image_base64"]) > 100:
                log(f"Endpoint {endpoint} returned valid image", "PASS")
            else:
                log(f"Endpoint {endpoint} returned empty/short image", "WARN")
        else:
             log(f"Endpoint {endpoint} failed: {status}", "FAIL")
             failed = True

    # 5. Data Cleaning
    log("Testing Data Cleaning...", "START")
    # Insert duplicate task to test cleaning
    make_request("POST", "/tasks/", task_payload) # Duplicate of 'Save Gotham'
    make_request("POST", "/tasks/", task_payload) # Triplicate
    
    status, clean_response = make_request("POST", "/analysis/clean-data")
    if status == 200 and clean_response.get('status') == 'success':
        log(f"Data cleaning executed: {clean_response.get('cleaned_items')}", "PASS")
    else:
        log(f"Data cleaning failed: {clean_response}", "FAIL")
        failed = True

    if failed:
        sys.exit(1)
    else:
        print("\nAll enhanced features verified successfully.")

if __name__ == "__main__":
    test_enhanced_features()
