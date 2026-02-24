import urllib.request
import urllib.error
import json
import sys

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

def test_api():
    failed = False
    
    # 1. Create Task
    log("Testing POST /tasks/ ...")
    payload = {
        "name": "Integration Test Task",
        "description": "Created by automated test script",
        "due_date": "2026-12-31",
        "priority": "medium",
        "stages": [
            {"stage_name": "Test Stage 1", "estimated_time_hours": 1.0, "order_number": 1},
            {"stage_name": "Test Stage 2", "estimated_time_hours": 2.0, "order_number": 2}
        ]
    }
    
    status, response = make_request("POST", "/tasks/", payload)
    
    if status == 201:
        task_id = response['task_id']
        log(f"Task created successfully. ID: {task_id}", "PASS")
    else:
        log(f"Failed to create task: {response}", "FAIL")
        return

    # 2. Get Task
    log(f"Testing GET /tasks/{task_id} ...")
    status, response = make_request("GET", f"/tasks/{task_id}")
    if status == 200:
        log("Fetched task successfully", "PASS")
    else:
        log(f"Failed to fetch task: {response}", "FAIL")
        failed = True

    # 3. Update Task (PATCH)
    log(f"Testing PATCH /tasks/{task_id} ...")
    update_payload = {"name": "Updated Test Task", "priority": "high"}
    status, response = make_request("PATCH", f"/tasks/{task_id}", update_payload)
    
    if status == 200 and response['name'] == "Updated Test Task":
        log("Updated task successfully", "PASS")
    else:
        log(f"Failed to update task: {response}", "FAIL")
        failed = True

    # 4. Update Stage (PUT)
    # Get first stage id from previous GET or assume created
    # We need to re-fetch the task to be sure of stage IDs if needed, but we have the create response
    # task['stages'] from create response
    # Wait, the create response has stages.
    
    # We need to access the 'response' variable from the create step properly. 
    # Let's just re-fetch to be safe on data structure
    status, task_data = make_request("GET", f"/tasks/{task_id}")
    stage_id = task_data['stages'][0]['stage_id']
    
    log(f"Testing PUT /tasks/stages/{stage_id} ...")
    stage_update_payload = {"status_state_id": 1, "actual_time_hours": 1.5} 
    status, response = make_request("PUT", f"/tasks/stages/{stage_id}", stage_update_payload)
    
    if status == 200:
        log("Updated stage successfully", "PASS")
    else:
        log(f"Failed to update stage: {response}", "FAIL")
        failed = True

    # 5. Analysis Endpoints
    analysis_endpoints = [
        "/analysis/completion",
        "/analysis/overdue",
        "/analysis/visualizations/priority",
        "/analysis/visualizations/completion-trends",
        "/analysis/reports/csv",
        "/analysis/stage-variance",
        "/analysis/visualizations/delay"
    ]
    
    for endpoint in analysis_endpoints:
        log(f"Testing GET {endpoint} ...")
        status, response = make_request("GET", endpoint)
        if status == 200:
            log(f"Endpoint {endpoint} operational", "PASS")
        else:
            log(f"Endpoint {endpoint} failed: {status}. Response: {response}", "FAIL")
            failed = True

    # 6. Delete Stage
    log(f"Testing DELETE /tasks/stages/{stage_id} ...")
    status, response = make_request("DELETE", f"/tasks/stages/{stage_id}")
    if status == 200:
        log("Deleted stage successfully", "PASS")
    else:
        log(f"Failed to delete stage: {response}", "FAIL")
        failed = True

    # 7. Delete Task
    log(f"Testing DELETE /tasks/{task_id} ...")
    status, response = make_request("DELETE", f"/tasks/{task_id}")
    if status == 204:
        log("Deleted task successfully", "PASS")
    else:
        log(f"Failed to delete task: {response}", "FAIL")
        failed = True

    if failed:
        sys.exit(1)
    else:
        print("\nAll tests passed successfully.")

if __name__ == "__main__":
    test_api()
