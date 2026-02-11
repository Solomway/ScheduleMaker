import time
from datetime import datetime, timedelta
import csv_code 
import DFS_algorithm
import os
from typing import Union
from typing import Dict
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

"""
Main Application Server
Handles all web requests, user authentication, and the scheduling algorithm.
Written by: Cameron Solomway
"""
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

"""
Loads initial data from CSV files into memory when the server starts.
"""
employees = csv_code.read_employees("employees.csv")

shifts = csv_code.read_shifts("shifts.csv")

accounts = csv_code.readAccounts("accounts.csv")

current_user = None


"""
Takes a start date and length to create a new employee work schedule.
"""
class ScheduleParams(BaseModel):
    start_date: str
    num_days: int

@app.post("/generate")
def generate(params: ScheduleParams):
    start_date_str = params.start_date
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

    num_Days = params.num_days
    
    result = dfs_schedule_helper(start_date, num_Days)
    
    if result:
        return {"status": "success", "schedule": result}
    return {"status": "error", "message": "Could not generate schedule"}

"""
Returns a list of employees that belong specifically to the logged-in user.
"""
@app.get("/view_emps")
def view_employees():
    global current_user, employees, shifts
    if current_user is None:
        return {"status": "error", "message": "Not logged in"}
    
    user_shift_names = []
    for shift_obj in shifts:
        if str(shift_obj.get('owner_id')) == str(current_user):
            user_shift_names.append(shift_obj['shift_name'])
    
    user_employees = []
    for emp in employees:
        if str(emp.get('owner_id')) == str(current_user):
            emp_data = {
                "id": emp['id'],
                "name": emp['name'],
                "hours_per_week": emp.get('hours_per_week', 0), 
                "vacation": emp.get('vacation', []),
                "availability": {}
            }
            
            full_availability = emp.get('availability', {})
            for shift_name in user_shift_names:
                emp_data["availability"][shift_name] = full_availability.get(shift_name, 1)
                
            user_employees.append(emp_data)

    return {"status": "success", "employees": user_employees}

"""
Returns a list of all shifts created by the current user to display in the UI.
"""
@app.get("/view_shifts")
def get_shifts_table():
    if current_user is None:
        return {"status": "error", "message": "Not logged in"}

    user_shifts = [shift for shift in shifts if shift.get('owner_id') == current_user]
    return {"status": "success", "shift_table": user_shifts}


"""
Returns a list of all employees created by the current user to display in the UI.
"""
@app.get("/get_employees")
def get_employees():
    if current_user is None:
        return {"status": "error", "message": "Not logged in"}

    user_employees = [employee for employee in employees if employee.get('owner_id') == current_user]
    return user_employees


"""
Fetches the raw shift data for internal system logic and dropdown menus.
"""
@app.get("/get_shifts")
def get_shifts():
    if current_user is None:
        return {"status": "error", "message": "Not logged in"}

    user_shifts = [shift for shift in shifts if shift.get('owner_id') == current_user]
    return {"shifts": user_shifts}


"""
Creates a new employee record and links it to the current user's account.
"""
class EmployeeInfo(BaseModel):
    name: str
    hours_per_week: int
    availability: Dict[str, int]

@app.post("/add_employee")
def add_emp(emp: EmployeeInfo):
    global employees
    new_id = len(employees) + 1
    new_emp = {
        "owner_id": current_user,
        "id": new_id,
        "name": emp.name,
        "hours_per_week": emp.hours_per_week,
        "vacation": [],
        "availability": emp.availability
    }
    employees.append(new_emp)
    csv_code.save_employees_csv(employees)

    return {"status": "success", "message": f"Added {emp.name} successfully!"}

"""
Permanently removes an employee from the system and updates the database.
"""
class EmpID(BaseModel):
    emp_id: int

@app.post("/remove_employee")
def remove_emp(param: EmpID):
    global employees
    for employee in employees:
        if employee['id'] == param.emp_id:
            employees.remove(employee)
            name = employee['name']
            csv_code.save_employees_csv(employees)
    return {"status": "success", "message": f"Successfully Removed {name} with Employee ID={param.emp_id}."}


"""
Adds a new work shift (like 'Morning' or 'Afternoon') to the user's profile.
"""
class ShiftInfo(BaseModel):
    name: str
    start: str
    end: str
    min_emp: int
    max_emp: int

@app.post("/add_shift")
def add_shift(param: ShiftInfo):
    global shifts
    global employees
    if not shifts:
        new_id = 1
    else:
        new_id = max(int(s['shift_id']) for s in shifts) + 1

    new_shift = {
        "owner_id": current_user,
        "shift_id": new_id,
        "shift_name": param.name,
        "start": param.start,
        "end": param.end,
        "min_employees": param.min_emp,
        "max_employees": param.max_emp
    }
    
    shifts.append(new_shift)
    csv_code.save_shifts_csv(shifts)
    csv_code.save_employees_csv(employees)
    
    return {"status": "success", "message": f"Shift '{param.name}' with ID={new_id} added successfully!"}


"""
Deletes a shift and automatically cleans it out of every employee's availability.
"""
class ShiftID(BaseModel):
    shift_id: int

@app.post("/remove_shift")
def remove_shift(param: ShiftID):
    global shifts
    for shift in shifts:
        if int(shift['shift_id']) == param.shift_id:
            sname = shift['shift_name']
            for emp in employees:
                if shift["shift_name"] in emp["availability"]:
                    del emp["availability"][shift["shift_name"]]
            shifts.remove(shift)
            csv_code.save_shifts_csv(shifts)
            csv_code.save_employees_csv(employees)
            return {"status": "success", "message": f"Successfully Removed {sname} (ID: {param.shift_id})."}
            
    return {"status": "error", "message": f"Error: Shift ID {param.shift_id} not found."}

"""
Updates the availability (Yes/No) for multiple employees across different shifts at once.
"""
class BulkUpdate(BaseModel):
    updates: Dict[str, Dict]

@app.post("/update_availability")
def update_all_availability(data: BulkUpdate):
    global employees
    
    for emp_id_str, update_info in data.updates.items():
        emp_id = int(emp_id_str)
        new_avail = update_info['availability']
        
        for emp in employees:
            if emp['id'] == emp_id:
                emp['availability'].update(new_avail)
                break
    
    csv_code.save_employees_csv(employees)
    return {"status": "success"}

"""
Saves a specific date range where an employee is marked as unavailable to work.
"""
class VacationInfo(BaseModel):
    emp_id: int
    start_date: str
    end_date: str

@app.post("/add_vacation")
def add_vacation(info: VacationInfo):
    global employees
    
    # Validate date formats
    try:
        datetime.strptime(info.start_date, "%Y-%m-%d")
        datetime.strptime(info.end_date, "%Y-%m-%d")
    except ValueError:
        return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}

    for employee in employees:
        if employee['id'] == info.emp_id:
            # Append the range to the vacation list
            employee['vacation'].append([info.start_date, info.end_date])
            csv_code.save_employees_csv(employees)
            return {"status": "success", "message": f"Vacation added for {employee['name']}"}
            
    return {"status": "error", "message": "Employee ID not found."}


"""
Removes a specific vacation entry from an employee's history.
"""
class DeleteVacationRequest(BaseModel):
    emp_id: int
    vac_index: int

@app.post("/delete_vacation")
def delete_vacation(data: DeleteVacationRequest):
    global employees
    
    for employee in employees:
        # Match ID and make sure it belongs to the logged-in user
        if employee['id'] == data.emp_id and employee.get('owner_id') == current_user:
            
            # Check if the index of vacation actually exists in users vacation list
            if 0 <= data.vac_index < len(employee['vacation']):
                removed_val = employee['vacation'].pop(data.vac_index)
                
                # Save the changes to the CSV
                csv_code.save_employees_csv(employees)
                
                return {
                    "status": "success", 
                    "message": f"Successfully removed vacation: {removed_val}"
                }
            else:
                return {"status": "error", "message": "Invalid vacation selection."}
                
    return {"status": "error", "message": "Employee not found or access denied."}

"""
Verifies login credentials and starts a user session.
"""
class AccountInfo(BaseModel):
    username: str
    password: str

@app.post("/signIn")
def signIn(info: AccountInfo):
    global current_user
    for account in accounts:
        if info.username == account['username'] and info.password == account['password']: #User entered both parameters correctly
            csv_code.read_employees("employees.csv")
            csv_code.read_shifts("shifts.csv")
            current_user = account['owner_id']
            return {"status": "success", "message": f"{account['username']} has successfully signed in."}
        if info.username == account['username'] and info.password != account['password']:
            return {"status": "error", "message": "Please verify your password is entered correctly."}
    return {"status": "error", "message": f"{info.username} is not a valid username."}


"""
Registers a new user and saves their credentials to the database.
"""
class NewAccountInfo(BaseModel):
    username: str
    email: str
    password: str
    password_check: str

@app.post("/createAccount")
def createAccount(info: NewAccountInfo):
    global current_user
    global accounts
    csv_code.readAccounts("accounts.csv")
    for account in accounts:
        if info.username == account['username']: # No Dupe Usernames
            return {"status": "error", "message": f"Username:{account['username']} is already in use."}
    if info.password == info.password_check: # User entered both password fields correctly 
        new_owner_id = len(accounts) + 1 # Create AccountID 
        new_account = {
            "owner_id": new_owner_id,
            "username": info.username,
            "email": info.email,
            "password": info.password,
            "employees": [], 
            "shifts": []
        }
        accounts.append(new_account)
        current_user = new_owner_id

        csv_code.saveAccounts(accounts, "accounts.csv")
        csv_code.read_employees("employees.csv")
        csv_code.read_shifts("shifts.csv")

        return {"status": "success", "message": f"The account {info.username} has been created."}
    else:
        return {"status": "error", "message": f"ERROR: Ensure your passwords match."}




################################
#       Other Functions        #
################################

"""
Sets up the logic and data structures needed for the algorithm to run the schedule.
"""
def dfs_schedule_helper(start_date, num_days):
    if not shifts or not employees: return None

    schedule = {}
    day_indices = []
    
    # Initialize the schedule structure
    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        date_str = current_date.strftime('%Y-%m-%d')
        schedule[date_str] = {}
        day_indices.append(date_str)
        for shift in shifts:
            schedule[date_str][shift['shift_name']] = [] 
            
    # Create employee hour tracker {emp_id: {'current_hours': 0}}
    employee_hours = {
        emp['id']: {'current_hours': 0, 'max_hours': emp['hours_per_week']}
        for emp in employees
    }
    
    print("\nStarting DFS to generate Schedule...")
    
    DFS_success = DFS_algorithm.dfs_scheduling(schedule, employee_hours, day_indices, 0, 0, 0, num_days, employees, shifts)

    if DFS_success:
        print("DFS Minimums Met. Running Maximizer...")
        DFS_algorithm.scheduleMaximizer(schedule, employee_hours, day_indices, 0, 0, 0, num_days, employees, shifts)
        return schedule
    else:
        print("DFS failed to find a valid schedule.")
        return None

    
"""
Formats the final generated schedule and saves it as a readable text file.
"""
def save_combined_schedules_to_file(combined_schedules, filename="schedule.txt"):
    shifts_map = {s['name']: s for s in shifts}
    separator = "\n" + "="*80 + "\n"
    
    with open(filename, "w") as f:
        print("\n--- SCHEDULE RESULTS ---")
        
        for name, schedule in combined_schedules.items():
            f.write(separator)
            f.write(f"*** {name} ***\n")
            f.write(separator)
            
            print(f"\n*** {name} ***\n")
            
            for date, shifts_on_date in schedule.items():
                date_header = f"Date: {date} ({datetime.strptime(date, '%Y-%m-%d').strftime('%A')})\n"
                f.write(date_header)
                print(date_header.strip())
                
                for shift_name, employees_list in shifts_on_date.items():
                    min_emp = shifts_map[shift_name].get('min_employees', 0)
                    emp_str = ", ".join(employees_list)
                    
                    line = f"  {shift_name} (Min: {min_emp}): {emp_str or 'UNASSIGNED'}\n"
                    f.write(line)
                    print(line.strip())
            
            f.write("\n")
            print("\n")
            
    print(f"Schedule data successfully saved to {filename}")


"""
A wrapper function that calculates the algorithm's runtime and handles errors.
"""
def generate_schedule(start_date_str: str, num_days: int):
    if not shifts or not employees:
        return {"error": "No shifts or employees to schedule."}

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}
        
    start_time = time.time()
    dfs_schedule = dfs_schedule_helper(start_date, num_days)
    end_time = time.time()
    
    if dfs_schedule:
        return {
            "status": "success",
            "runtime": round(end_time - start_time, 4),
            "schedule": dfs_schedule
        }
    return {"error": "Algorithm failed to find a schedule."}

"""
Serves the main frontend page when the website is first loaded.
"""
@app.get("/")
async def read_index():
    return FileResponse('index.html')

app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)