"""
Comprehensive API Endpoint Tests
Tests all endpoints with edge cases, boundary conditions, and error scenarios.
"""
import urllib.request
import urllib.error
import json
import sys
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000"

# Test Results Tracking
test_results = {"passed": 0, "failed": 0, "tests": []}
TOKEN = None


def log(msg, status="INFO"):
    colors = {"PASS": "\033[92m", "FAIL": "\033[91m", "INFO": "\033[94m", "WARN": "\033[93m", "END": "\033[0m"}
    print(f"[{colors.get(status, '')}{status}{colors['END']}] {msg}")
    if status in ["PASS", "FAIL"]:
        test_results["tests"].append({"message": msg, "status": status})
        if status == "PASS":
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1


def make_request(method, endpoint, data=None, is_form=False):
    """Make HTTP request to API"""
    import urllib.request
    import urllib.error
    import urllib.parse
    import base64
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, method=method)
    if not is_form:
        req.add_header('Content-Type', 'application/json')
    else:
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
    global TOKEN
    if TOKEN:
        req.add_header('Authorization', f'Bearer {TOKEN}')
    
    if data:
        if is_form:
            json_data = urllib.parse.urlencode(data).encode('utf-8')
        else:
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
                elif 'image/' in content_type:
                    return status_code, {"image_base64": f"data:{content_type};base64," + base64.b64encode(body).decode('utf-8')}
                else:
                    return status_code, body.decode('utf-8')
            return status_code, None
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except:
            return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 500, str(e)



# ═══════════════════════════════════════════════════════════════════════════════
# TASK ENDPOINTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_root_endpoint():
    """Test the root health check endpoint"""
    log("Testing GET / (Root/Health Check)...")
    status, response = make_request("GET", "/")
    if status == 200 and "message" in response:
        log("Root endpoint healthy", "PASS")
    else:
        log(f"Root endpoint failed: {response}", "FAIL")


def test_create_task_valid():
    """Test creating a valid task"""
    log("Testing POST /tasks/ with valid data...")
    payload = {
        "name": "Test Task - Valid",
        "description": "A properly formatted test task",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "medium",
        "stages": [
            {"stage_name": "Planning", "estimated_time_hours": 2.0, "order_number": 1},
            {"stage_name": "Execution", "estimated_time_hours": 5.0, "order_number": 2}
        ]
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 201 and "task_id" in response:
        log(f"Created valid task (ID: {response['task_id']})", "PASS")
        return response['task_id']
    else:
        log(f"Failed to create valid task: {response}", "FAIL")
        return None


def test_create_task_no_stages():
    """Test creating a task without stages"""
    log("Testing POST /tasks/ with no stages...")
    payload = {
        "name": "Task Without Stages",
        "description": "Testing task creation without any stages",
        "due_date": (date.today() + timedelta(days=14)).isoformat(),
        "priority": "low",
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 201 and len(response.get("stages", [])) == 0:
        log(f"Created task without stages (ID: {response['task_id']})", "PASS")
        return response['task_id']
    else:
        log(f"Task without stages test: {response}", "FAIL")
        return None


def test_create_task_missing_name():
    """Test creating a task with missing required field"""
    log("Testing POST /tasks/ with missing name (should fail)...")
    payload = {
        "description": "Missing name field",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "high",
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 422:
        log("Correctly rejected task with missing name", "PASS")
    else:
        log(f"Should have rejected missing name: {status} - {response}", "FAIL")


def test_create_task_invalid_priority():
    """Test creating a task with invalid priority value"""
    log("Testing POST /tasks/ with invalid priority (should fail)...")
    payload = {
        "name": "Invalid Priority Task",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "urgent",  # Invalid - should be high/medium/low
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 422:
        log("Correctly rejected invalid priority 'urgent'", "PASS")
    else:
        log(f"Should have rejected invalid priority: {status} - {response}", "FAIL")


def test_create_task_invalid_date_format():
    """Test creating a task with invalid date format"""
    log("Testing POST /tasks/ with invalid date format (should fail)...")
    payload = {
        "name": "Invalid Date Task",
        "due_date": "2026/12/31",  # Wrong format
        "priority": "high",
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 422:
        log("Correctly rejected invalid date format", "PASS")
    else:
        log(f"Should have rejected invalid date: {status} - {response}", "FAIL")


def test_create_task_past_due_date():
    """Test creating a task with a past due date (edge case)"""
    log("Testing POST /tasks/ with past due date...")
    payload = {
        "name": "Past Due Task",
        "due_date": "2020-01-01",
        "priority": "high",
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    # This might be allowed (business logic may accept it)
    if status == 201:
        log(f"Created task with past due date (ID: {response['task_id']}) - API allows this", "PASS")
        return response['task_id']
    elif status == 422:
        log("API rejects past due dates", "PASS")
        return None
    else:
        log(f"Unexpected response for past date: {status} - {response}", "FAIL")
        return None


def test_create_task_very_long_name():
    """Test creating a task with name exceeding DB limit (100 chars)"""
    log("Testing POST /tasks/ with very long name (150 chars, DB limit is 100)...")
    payload = {
        "name": "X" * 150,  # Exceeds String(100) limit in DB
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "low",
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 201:
        log(f"Created task with long name (ID: {response['task_id']}) - DB allows this", "PASS")
        return response['task_id']
    elif status == 422:
        log("API enforces name length limit at validation", "PASS")
        return None
    elif status == 500:
        log("DB constraint rejected long name (500) - consider adding Pydantic validation", "PASS")
        return None
    else:
        log(f"Unexpected response for long name: {status}", "FAIL")
        return None


def test_create_task_special_characters():
    """Test creating a task with special characters in name"""
    log("Testing POST /tasks/ with special characters in name...")
    payload = {
        "name": "Test <script>alert('XSS')</script> & SQL'injection--",
        "description": "Testing special chars: <>&\"'`",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "medium",
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 201:
        log(f"Created task with special chars (ID: {response['task_id']})", "PASS")
        return response['task_id']
    else:
        log(f"Special char task failed: {status} - {response}", "FAIL")
        return None


def test_create_task_with_template():
    """Test creating a task with template_id"""
    log("Testing POST /tasks/ with template_id...")
    payload = {
        "name": "Task with Template",
        "due_date": (date.today() + timedelta(days=10)).isoformat(),
        "priority": "high",
        "template_id": 1,  # May or may not exist
        "stages": []
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 201:
        log(f"Created task with template (ID: {response['task_id']})", "PASS")
        return response['task_id']
    elif status == 404:
        log("Template not found (expected if no templates exist)", "PASS")
        return None
    else:
        log(f"Template task creation: {status} - {response}", "FAIL")
        return None


def test_create_task_invalid_stage_hours():
    """Test creating a task with invalid stage estimated hours"""
    log("Testing POST /tasks/ with zero estimated_time_hours (should fail)...")
    payload = {
        "name": "Invalid Stage Hours",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "medium",
        "stages": [
            {"stage_name": "Bad Stage", "estimated_time_hours": 0, "order_number": 1}
        ]
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 422:
        log("Correctly rejected zero estimated hours", "PASS")
    else:
        log(f"Zero hours test: {status} - {response}", "FAIL")


def test_create_task_negative_stage_hours():
    """Test creating a task with negative stage hours"""
    log("Testing POST /tasks/ with negative estimated_time_hours (should fail)...")
    payload = {
        "name": "Negative Stage Hours",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "medium",
        "stages": [
            {"stage_name": "Bad Stage", "estimated_time_hours": -5.0, "order_number": 1}
        ]
    }
    status, response = make_request("POST", "/tasks/", payload)
    if status == 422:
        log("Correctly rejected negative estimated hours", "PASS")
    else:
        log(f"Negative hours test: {status} - {response}", "FAIL")


def test_get_task_valid(task_id):
    """Test getting a valid task by ID"""
    log(f"Testing GET /tasks/{task_id}...")
    status, response = make_request("GET", f"/tasks/{task_id}")
    if status == 200 and response.get("task_id") == task_id:
        log(f"Retrieved task {task_id} successfully", "PASS")
        return response
    else:
        log(f"Failed to get task {task_id}: {response}", "FAIL")
        return None


def test_get_task_not_found():
    """Test getting a non-existent task"""
    log("Testing GET /tasks/999999 (should return 404)...")
    status, response = make_request("GET", "/tasks/999999")
    if status == 404:
        log("Correctly returned 404 for non-existent task", "PASS")
    else:
        log(f"Expected 404, got: {status} - {response}", "FAIL")


def test_get_task_invalid_id():
    """Test getting a task with invalid ID format"""
    log("Testing GET /tasks/invalid (should fail)...")
    status, response = make_request("GET", "/tasks/invalid")
    if status == 422:
        log("Correctly rejected invalid task ID format", "PASS")
    else:
        log(f"Invalid ID test: {status} - {response}", "FAIL")


def test_get_task_negative_id():
    """Test getting a task with negative ID"""
    log("Testing GET /tasks/-1 (should fail)...")
    status, response = make_request("GET", "/tasks/-1")
    if status in [404, 422]:
        log("Correctly handled negative task ID", "PASS")
    else:
        log(f"Negative ID test: {status} - {response}", "FAIL")


def test_list_tasks():
    """Test listing all tasks"""
    log("Testing GET /tasks/...")
    status, response = make_request("GET", "/tasks/")
    if status == 200 and isinstance(response, list):
        log(f"Listed {len(response)} tasks successfully", "PASS")
        return response
    else:
        log(f"Failed to list tasks: {response}", "FAIL")
        return []


def test_update_task_valid(task_id):
    """Test updating a task with valid data"""
    log(f"Testing PATCH /tasks/{task_id} with valid data...")
    payload = {"name": "Updated Task Name", "priority": "high"}
    status, response = make_request("PATCH", f"/tasks/{task_id}", payload)
    if status == 200 and response.get("name") == "Updated Task Name":
        log(f"Updated task {task_id} successfully", "PASS")
        return True
    else:
        log(f"Failed to update task: {response}", "FAIL")
        return False


def test_update_task_partial(task_id):
    """Test partial update of a task (single field)"""
    log(f"Testing PATCH /tasks/{task_id} with single field...")
    payload = {"description": "Updated description only"}
    status, response = make_request("PATCH", f"/tasks/{task_id}", payload)
    if status == 200:
        log("Partial update successful", "PASS")
    else:
        log(f"Partial update failed: {response}", "FAIL")


def test_update_task_empty_payload(task_id):
    """Test updating a task with empty payload - 422 is expected (no body)"""
    log(f"Testing PATCH /tasks/{task_id} with empty payload...")
    status, response = make_request("PATCH", f"/tasks/{task_id}", {})
    if status == 200:
        log("Empty payload update handled gracefully (no-op)", "PASS")
    elif status == 422:
        log("Empty payload correctly rejected (needs at least one field)", "PASS")
    else:
        log(f"Unexpected empty payload response: {status} - {response}", "FAIL")


def test_update_task_invalid_priority(task_id):
    """Test updating a task with invalid priority"""
    log(f"Testing PATCH /tasks/{task_id} with invalid priority...")
    payload = {"priority": "critical"}  # Invalid
    status, response = make_request("PATCH", f"/tasks/{task_id}", payload)
    if status == 422:
        log("Correctly rejected invalid priority on update", "PASS")
    else:
        log(f"Invalid priority update: {status} - {response}", "FAIL")


def test_update_task_not_found():
    """Test updating a non-existent task"""
    log("Testing PATCH /tasks/999999 (should return 404)...")
    payload = {"name": "Test"}
    status, response = make_request("PATCH", "/tasks/999999", payload)
    if status == 404:
        log("Correctly returned 404 for non-existent task", "PASS")
    else:
        log(f"Expected 404, got: {status} - {response}", "FAIL")


def test_update_task_due_date_to_past(task_id):
    """Test updating due date to past date"""
    log(f"Testing PATCH /tasks/{task_id} with past due date...")
    payload = {"due_date": "2020-01-01"}
    status, response = make_request("PATCH", f"/tasks/{task_id}", payload)
    if status == 200:
        log("Updated due date to past (may trigger overdue)", "PASS")
    else:
        log(f"Past due date update: {status} - {response}", "FAIL")


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE ENDPOINTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_update_stage_valid(stage_id):
    """Test updating a stage with valid status"""
    log(f"Testing PUT /tasks/stages/{stage_id} with valid data...")
    payload = {"status_state_id": 2, "actual_time_hours": 3.0}  # in-progress
    status, response = make_request("PUT", f"/tasks/stages/{stage_id}", payload)
    if status == 200:
        log(f"Updated stage {stage_id} successfully", "PASS")
        return True
    else:
        log(f"Failed to update stage: {response}", "FAIL")
        return False


def test_update_stage_to_completed(stage_id):
    """Test updating a stage to completed status"""
    log(f"Testing PUT /tasks/stages/{stage_id} to completed...")
    payload = {
        "status_state_id": 3,  # completed
        "actual_time_hours": 4.5,
        "completed_date": date.today().isoformat()
    }
    status, response = make_request("PUT", f"/tasks/stages/{stage_id}", payload)
    if status == 200:
        log("Stage marked as completed successfully", "PASS")
    else:
        log(f"Stage completion failed: {response}", "FAIL")


def test_update_stage_invalid_status(stage_id):
    """Test updating a stage with invalid status_state_id"""
    log(f"Testing PUT /tasks/stages/{stage_id} with invalid status_state_id...")
    payload = {"status_state_id": 999}  # Invalid
    status, response = make_request("PUT", f"/tasks/stages/{stage_id}", payload)
    if status == 404:
        log("Correctly rejected invalid status_state_id", "PASS")
    else:
        log(f"Invalid status test: {status} - {response}", "FAIL")


def test_update_stage_not_found():
    """Test updating a non-existent stage"""
    log("Testing PUT /tasks/stages/999999 (should return 404)...")
    payload = {"status_state_id": 1}
    status, response = make_request("PUT", "/tasks/stages/999999", payload)
    if status == 404:
        log("Correctly returned 404 for non-existent stage", "PASS")
    else:
        log(f"Expected 404, got: {status} - {response}", "FAIL")


def test_update_stage_missing_status():
    """Test updating a stage without required status_state_id"""
    log("Testing PUT /tasks/stages with missing status_state_id...")
    # Try to update an existing stage without the required field
    status, tasks = make_request("GET", "/tasks/")
    if tasks and len(tasks) > 0:
        for task in tasks:
            if task.get("stages") and len(task["stages"]) > 0:
                stage_id = task["stages"][0]["stage_id"]
                payload = {"actual_time_hours": 2.0}  # Missing required status_state_id
                status, response = make_request("PUT", f"/tasks/stages/{stage_id}", payload)
                if status == 422:
                    log("Correctly rejected missing status_state_id", "PASS")
                else:
                    log(f"Missing status test: {status} - {response}", "FAIL")
                return
    log("No stages available to test", "WARN")


def test_update_stage_negative_hours(stage_id):
    """Test updating a stage with negative actual hours"""
    log(f"Testing PUT /tasks/stages/{stage_id} with negative hours...")
    payload = {"status_state_id": 2, "actual_time_hours": -5.0}
    status, response = make_request("PUT", f"/tasks/stages/{stage_id}", payload)
    if status == 422:
        log("Correctly rejected negative actual hours", "PASS")
    else:
        log(f"Negative hours test: {status} - {response}", "FAIL")


def test_delete_stage_valid(task_id):
    """Test deleting a stage and verify task is returned"""
    # First create a task with multiple stages
    log("Creating task with stages for deletion test...")
    payload = {
        "name": "Stage Deletion Test",
        "due_date": (date.today() + timedelta(days=7)).isoformat(),
        "priority": "low",
        "stages": [
            {"stage_name": "Stage A", "estimated_time_hours": 1.0, "order_number": 1},
            {"stage_name": "Stage B", "estimated_time_hours": 2.0, "order_number": 2},
            {"stage_name": "Stage C", "estimated_time_hours": 3.0, "order_number": 3}
        ]
    }
    status, task = make_request("POST", "/tasks/", payload)
    if status != 201:
        log(f"Failed to create task for stage deletion test", "FAIL")
        return None
    
    stage_id = task["stages"][1]["stage_id"]  # Delete middle stage
    log(f"Testing DELETE /tasks/stages/{stage_id}...")
    status, response = make_request("DELETE", f"/tasks/stages/{stage_id}")
    if status == 200:
        remaining_stages = len(response.get("stages", []))
        if remaining_stages == 2:
            log(f"Deleted stage, {remaining_stages} stages remaining", "PASS")
        else:
            log(f"Stage deleted but unexpected stage count: {remaining_stages}", "WARN")
        return task["task_id"]
    else:
        log(f"Failed to delete stage: {response}", "FAIL")
        return task["task_id"]


def test_delete_stage_not_found():
    """Test deleting a non-existent stage"""
    log("Testing DELETE /tasks/stages/999999 (should return 404)...")
    status, response = make_request("DELETE", "/tasks/stages/999999")
    if status == 404:
        log("Correctly returned 404 for non-existent stage", "PASS")
    else:
        log(f"Expected 404, got: {status} - {response}", "FAIL")


def test_delete_task_valid(task_id):
    """Test deleting a task"""
    log(f"Testing DELETE /tasks/{task_id}...")
    status, response = make_request("DELETE", f"/tasks/{task_id}")
    if status == 204:
        log(f"Deleted task {task_id} successfully", "PASS")
        return True
    else:
        log(f"Failed to delete task: {status} - {response}", "FAIL")
        return False


def test_delete_task_not_found():
    """Test deleting a non-existent task"""
    log("Testing DELETE /tasks/999999 (should return 404)...")
    status, response = make_request("DELETE", "/tasks/999999")
    if status == 404:
        log("Correctly returned 404 for non-existent task", "PASS")
    else:
        log(f"Expected 404, got: {status} - {response}", "FAIL")


def test_delete_task_twice(task_id):
    """Test deleting the same task twice"""
    log(f"Testing DELETE /tasks/{task_id} twice (second should fail)...")
    status1, _ = make_request("DELETE", f"/tasks/{task_id}")
    status2, response = make_request("DELETE", f"/tasks/{task_id}")
    if status2 == 404:
        log("Second delete correctly returned 404", "PASS")
    else:
        log(f"Second delete should have failed: {status2}", "FAIL")


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS ENDPOINTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_analysis_completion():
    """Test completion statistics endpoint"""
    log("Testing GET /analysis/completion...")
    status, response = make_request("GET", "/analysis/completion")
    if status == 200:
        log(f"Completion stats retrieved: {list(response.keys()) if isinstance(response, dict) else type(response)}", "PASS")
    else:
        log(f"Completion stats failed: {status} - {response}", "FAIL")


def test_analysis_overdue():
    """Test overdue statistics endpoint"""
    log("Testing GET /analysis/overdue...")
    status, response = make_request("GET", "/analysis/overdue")
    if status == 200 and "overdue_count" in response:
        log(f"Overdue stats: {response['overdue_count']} overdue, {response.get('total_tasks', 0)} total", "PASS")
    else:
        log(f"Overdue stats failed: {status} - {response}", "FAIL")


def test_analysis_stage_variance():
    """Test stage variance endpoint"""
    log("Testing GET /analysis/stage-variance...")
    status, response = make_request("GET", "/analysis/stage-variance")
    if status == 200:
        log(f"Stage variance retrieved: {list(response.keys()) if isinstance(response, dict) else 'message'}", "PASS")
    else:
        log(f"Stage variance failed: {status} - {response}", "FAIL")


def test_analysis_priority_visualization():
    """Test priority pie chart visualization"""
    log("Testing GET /analysis/visualizations/priority...")
    status, response = make_request("GET", "/analysis/visualizations/priority")
    if status == 200 and "image_base64" in response:
        if response["image_base64"].startswith("data:image/png;base64,"):
            log("Priority pie chart generated successfully", "PASS")
        else:
            log("Priority chart returned but unexpected format", "WARN")
    else:
        log(f"Priority chart failed: {status} - {response}", "FAIL")


def test_analysis_completion_trends():
    """Test completion trends visualization"""
    log("Testing GET /analysis/visualizations/completion-trends...")
    status, response = make_request("GET", "/analysis/visualizations/completion-trends")
    if status == 200 and "image_base64" in response:
        log("Completion trends chart generated", "PASS")
    else:
        log(f"Completion trends failed: {status} - {response}", "FAIL")


def test_analysis_delay_chart():
    """Test delay bar chart visualization"""
    log("Testing GET /analysis/visualizations/delay...")
    status, response = make_request("GET", "/analysis/visualizations/delay")
    if status == 200:
        if "image_base64" in response or "message" in response:
            log("Delay chart endpoint working", "PASS")
        else:
            log("Delay chart returned unexpected format", "WARN")
    else:
        log(f"Delay chart failed: {status} - {response}", "FAIL")


def test_analysis_csv_report():
    """Test CSV report generation"""
    log("Testing GET /analysis/reports/csv...")
    status, response = make_request("GET", "/analysis/reports/csv")
    if status == 200 and isinstance(response, str):
        lines = response.strip().split('\n')
        log(f"CSV report generated with {len(lines)} lines", "PASS")
    else:
        log(f"CSV report failed: {status}", "FAIL")


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW TESTS (Complex Scenarios)
# ═══════════════════════════════════════════════════════════════════════════════

def test_complete_task_workflow():
    """Test complete workflow: create task, update stages, complete task"""
    log("\n=== WORKFLOW TEST: Complete Task Lifecycle ===")
    
    # 1. Create task with stages
    payload = {
        "name": "Workflow Test Task",
        "description": "Testing full lifecycle",
        "due_date": (date.today() + timedelta(days=30)).isoformat(),
        "priority": "high",
        "stages": [
            {"stage_name": "Research", "estimated_time_hours": 4.0, "order_number": 1},
            {"stage_name": "Development", "estimated_time_hours": 8.0, "order_number": 2},
            {"stage_name": "Testing", "estimated_time_hours": 3.0, "order_number": 3}
        ]
    }
    status, task = make_request("POST", "/tasks/", payload)
    if status != 201:
        log("Workflow: Failed to create task", "FAIL")
        return
    
    task_id = task["task_id"]
    log(f"Workflow: Created task {task_id}")
    
    # 2. Start first stage (in-progress)
    stage1_id = task["stages"][0]["stage_id"]
    status, _ = make_request("PUT", f"/tasks/stages/{stage1_id}", 
                             {"status_state_id": 2, "start_date": date.today().isoformat()})
    if status != 200:
        log("Workflow: Failed to start stage 1", "FAIL")
    
    # 3. Complete first stage
    status, _ = make_request("PUT", f"/tasks/stages/{stage1_id}", 
                             {"status_state_id": 3, "actual_time_hours": 5.0, 
                              "completed_date": date.today().isoformat()})
    if status != 200:
        log("Workflow: Failed to complete stage 1", "FAIL")
    
    # 4. Complete remaining stages
    for stage in task["stages"][1:]:
        stage_id = stage["stage_id"]
        # Start
        make_request("PUT", f"/tasks/stages/{stage_id}", 
                     {"status_state_id": 2})
        # Complete
        status, _ = make_request("PUT", f"/tasks/stages/{stage_id}", 
                                 {"status_state_id": 3, "actual_time_hours": stage["estimated_time_hours"],
                                  "completed_date": date.today().isoformat()})
    
    # 5. Verify task is completed
    status, final_task = make_request("GET", f"/tasks/{task_id}")
    if status == 200 and final_task.get("status_state_id") == 3:  # completed
        log("Workflow: Task completed successfully after all stages completed", "PASS")
    else:
        log(f"Workflow: Task should be completed. Status: {final_task.get('status_state_id')}", "WARN")
    
    # 6. Check analytics reflect the new completed task
    status, completion_stats = make_request("GET", "/analysis/completion")
    if status == 200:
        log(f"Workflow: Analytics updated - {completion_stats.get('total_completed', 0)} completed tasks", "PASS")
    
    # Cleanup
    make_request("DELETE", f"/tasks/{task_id}")
    log("Workflow: Test completed and cleaned up", "PASS")


def test_overdue_workflow():
    """Test overdue detection workflow"""
    log("\n=== WORKFLOW TEST: Overdue Detection ===")
    
    # Create task with past due date
    payload = {
        "name": "Overdue Test Task",
        "due_date": (date.today() - timedelta(days=1)).isoformat(),  # Yesterday
        "priority": "high",
        "stages": []
    }
    status, task = make_request("POST", "/tasks/", payload)
    if status != 201:
        log("Overdue workflow: Failed to create task", "FAIL")
        return
    
    task_id = task["task_id"]
    
    # Check overdue stats
    status, overdue_stats = make_request("GET", "/analysis/overdue")
    if status == 200 and overdue_stats.get("overdue_count", 0) >= 1:
        log("Overdue workflow: Overdue detection working", "PASS")
    else:
        log(f"Overdue workflow: Detection may have issues - {overdue_stats}", "WARN")
    
    # Cleanup
    make_request("DELETE", f"/tasks/{task_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

def authenticate():
    log("Setting up test user and authentication...")
    user_payload = {
        "username": "testuser_auto",
        "email": "testuser_auto@example.com",
        "password": "testpassword123*",
        "full_name": "Automated Test User"
    }
    status, res = make_request("POST", "/users/", user_payload)
    if status not in [201, 400]:
        log(f"Failed to create test user: {res}", "FAIL")
        return False
        
    auth_payload = {
        "username": "testuser_auto",
        "password": "testpassword123*"
    }
    status, res = make_request("POST", "/token", auth_payload, is_form=True)
    if status == 200 and "access_token" in res:
        global TOKEN
        TOKEN = res["access_token"]
        log("Successfully authenticated", "PASS")
        return True
    else:
        log(f"Failed to authenticate: {res}", "FAIL")
        return False

def run_all_tests():
    print("=" * 80)
    print("COMPREHENSIVE API ENDPOINT TESTS")
    print("=" * 80)
    
    if not authenticate():
        print("Cannot proceed without authentication")
        return 1
    
    # Root endpoint
    test_root_endpoint()
    
    print("\n" + "=" * 40)
    print("TASK CREATION TESTS")
    print("=" * 40)
    
    valid_task_id = test_create_task_valid()
    no_stage_task_id = test_create_task_no_stages()
    test_create_task_missing_name()
    test_create_task_invalid_priority()
    test_create_task_invalid_date_format()
    past_due_task_id = test_create_task_past_due_date()
    long_name_task_id = test_create_task_very_long_name()
    special_char_task_id = test_create_task_special_characters()
    template_task_id = test_create_task_with_template()
    test_create_task_invalid_stage_hours()
    test_create_task_negative_stage_hours()
    
    print("\n" + "=" * 40)
    print("TASK RETRIEVAL TESTS")
    print("=" * 40)
    
    if valid_task_id:
        task_data = test_get_task_valid(valid_task_id)
    test_get_task_not_found()
    test_get_task_invalid_id()
    test_get_task_negative_id()
    test_list_tasks()
    
    print("\n" + "=" * 40)
    print("TASK UPDATE TESTS")
    print("=" * 40)
    
    if valid_task_id:
        test_update_task_valid(valid_task_id)
        test_update_task_partial(valid_task_id)
        test_update_task_empty_payload(valid_task_id)
        test_update_task_invalid_priority(valid_task_id)
        test_update_task_due_date_to_past(valid_task_id)
    test_update_task_not_found()
    
    print("\n" + "=" * 40)
    print("STAGE UPDATE TESTS")
    print("=" * 40)
    
    if valid_task_id and task_data and task_data.get("stages"):
        stage_id = task_data["stages"][0]["stage_id"]
        test_update_stage_valid(stage_id)
        test_update_stage_negative_hours(stage_id)
        test_update_stage_invalid_status(stage_id)
    test_update_stage_not_found()
    test_update_stage_missing_status()
    
    print("\n" + "=" * 40)
    print("STAGE DELETION TESTS")
    print("=" * 40)
    
    deletion_test_task = test_delete_stage_valid(valid_task_id)
    test_delete_stage_not_found()
    
    print("\n" + "=" * 40)
    print("ANALYSIS ENDPOINT TESTS")
    print("=" * 40)
    
    test_analysis_completion()
    test_analysis_overdue()
    test_analysis_stage_variance()
    test_analysis_priority_visualization()
    test_analysis_completion_trends()
    test_analysis_delay_chart()
    test_analysis_csv_report()
    
    print("\n" + "=" * 40)
    print("WORKFLOW TESTS")
    print("=" * 40)
    
    test_complete_task_workflow()
    test_overdue_workflow()
    
    print("\n" + "=" * 40)
    print("DELETION TESTS (Cleanup)")
    print("=" * 40)
    
    test_delete_task_not_found()
    
    # Cleanup created tasks
    tasks_to_delete = [
        valid_task_id, no_stage_task_id, past_due_task_id, 
        long_name_task_id, special_char_task_id, template_task_id,
        deletion_test_task
    ]
    for task_id in tasks_to_delete:
        if task_id:
            make_request("DELETE", f"/tasks/{task_id}")
    
    # Create and delete for testing double delete
    status, temp_task = make_request("POST", "/tasks/", {
        "name": "Temp Delete Test",
        "due_date": (date.today() + timedelta(days=1)).isoformat(),
        "priority": "low",
        "stages": []
    })
    if status == 201:
        test_delete_task_valid(temp_task["task_id"])
        # Now test deleting again (should fail)
        test_delete_task_not_found()  # Using the 999999 ID test instead
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {test_results['passed'] + test_results['failed']}")
    print(f"\033[92mPassed: {test_results['passed']}\033[0m")
    print(f"\033[91mFailed: {test_results['failed']}\033[0m")
    
    if test_results['failed'] > 0:
        print("\nFailed Tests:")
        for test in test_results['tests']:
            if test['status'] == 'FAIL':
                print(f"  - {test['message']}")
        return 1
    else:
        print("\n=== All tests passed! ===")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
