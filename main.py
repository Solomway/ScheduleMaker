import time
from datetime import datetime, timedelta
import DFS_algorithm
import os
import bcrypt
from typing import Dict, Optional
from fastapi import FastAPI, Response, Cookie
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Field, SQLModel, Session, create_engine, select
from contextlib import asynccontextmanager


"""DATABASE SECTION"""
# 1. Accounts Table
class UserAccount(SQLModel, table=True):
    accountID: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str
    password: str

# 2. Employees Table
class EmployeeRow(SQLModel, table=True):
    employee_id: Optional[int] = Field(default=None, primary_key=True)
    accountID: int = Field(foreign_key="useraccount.accountID") # Maps back to the User table
    name: str
    hours_per_week: int

# 3. Shifts Table
class ShiftRow(SQLModel, table=True):
    shift_ID: Optional[int] = Field(default=None, primary_key=True)
    accountID: int = Field(foreign_key="useraccount.accountID") # Maps back to the User table
    name: str
    start_time: str
    end_time: str
    min_employees: int
    max_employees: int

# 4. Child Table: Employee Availability 
class EmployeeAvailabilityRow(SQLModel, table=True):
    availability_id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employeerow.employee_id") # Connects directly to parent employee
    shift_name: str 
    is_available: int = Field(default=1) # 1 for available, 0 for unavailable

# 5. Child Table: Employee Vacations
class EmployeeVacationRow(SQLModel, table=True):
    vacation_id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employeerow.employee_id") # Connects directly to parent employee
    start_date: str # "2026-06-01"
    end_date: str   

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})




"""
Main Application Server
Handles all web requests, user authentication, and the scheduling algorithm.
"""
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Everything before 'yield' runs on application startup
    SQLModel.metadata.create_all(engine)
    yield
    # Everything after 'yield' runs on shutdown (if needed)

app = FastAPI(lifespan=lifespan)



"""
Takes a start date and length to create a new employee work schedule.
"""
class ScheduleParams(BaseModel):
    owner_id: int
    start_date: str
    num_days: int

@app.post("/generate")
def generate(params: ScheduleParams):
    result = generate_schedule(params.start_date, params.num_days, params.owner_id)
    if "error" in result:
        return {"status": "error", "message": result["error"]}
    return result

"""
Returns a list of employees that belong specifically to the logged-in user.
"""
@app.get("/view_emps/{user_id}")
def view_employees(user_id: int):
    with Session(engine) as session:
        # 1. Fetch all shifts created by the account
        shift_statement = select(ShiftRow).where(ShiftRow.accountID == user_id)
        user_shifts = session.exec(shift_statement).all()
        
        # 2. Fetch all parent employee rows belonging to this account
        employee_statement = select(EmployeeRow).where(EmployeeRow.accountID == user_id)
        db_employees = session.exec(employee_statement).all()
        
        users_employees = []

        # 3. Iterate through each employee row safely
        for emp in db_employees:
            # Fetch child table vacations specifically for emp 
            vac_stmt = select(EmployeeVacationRow).where(EmployeeVacationRow.employee_id == emp.employee_id)
            db_vac = session.exec(vac_stmt).all()
            vacation_list = [[v.start_date, v.end_date] for v in db_vac]

            # Fetch their custom availabilities from the child table
            avail_statement = select(EmployeeAvailabilityRow).where(EmployeeAvailabilityRow.employee_id == emp.employee_id)
            db_availabilities = session.exec(avail_statement).all()
            
            # Map the database records back into a dictionary shape for JS code {"Morning Shift": 1, "Night Shift": 0}
            availability_dict = {row.shift_name: row.is_available for row in db_availabilities}
            
            # If a new shift was created but this employee doesn't have an availability entered for it yet, default to available
            for shift in user_shifts:
                if shift.name not in availability_dict:
                    availability_dict[shift.name] = 1
            
            emp_data = {
                "id": emp.employee_id,
                "name": emp.name,
                "hours_per_week": emp.hours_per_week,
                "vacation": vacation_list, 
                "availability": availability_dict
            }
            users_employees.append(emp_data)

    return {"status": "success", "employees": users_employees}

"""
Returns a list of all shifts created by the current user to display in the UI.
"""
@app.get("/view_shifts/{user_id}")
def get_shifts_table(user_id: int):
    with Session(engine) as session:
        statement = select(ShiftRow).where(ShiftRow.accountID == user_id)
        db_shifts = session.exec(statement).all()
        
        user_shifts = []
        for shift in db_shifts:
            user_shifts.append({
                "shift_id": shift.shift_ID,
                "owner_id": shift.accountID,
                "shift_name": shift.name,
                "start": shift.start_time,
                "end": shift.end_time,
                "min_employees": shift.min_employees,
                "max_employees": shift.max_employees
            })
            
    return {"status": "success", "shift_table": user_shifts}

"""
Returns a list of all employees created by the current user to display in the UI.
"""
@app.get("/get_employees/{user_id}")
def get_employees(user_id: int):
    with Session(engine) as session:
        statement = select(EmployeeRow).where(EmployeeRow.accountID == user_id)
        db_employees = session.exec(statement).all()
        
        # Format the database objects into raw dictionary dictionaries for script.js
        user_employees = []
        for emp in db_employees:
            user_employees.append({
                "id": emp.employee_id,
                "accountID": emp.accountID,
                "name": emp.name,
                "hours_per_week": emp.hours_per_week
            })
    return user_employees


"""
Fetches the raw shift data for internal system logic and dropdown menus.
"""
@app.get("/get_shifts/{user_id}")
def get_shifts(user_id: int):
    with Session(engine) as session:
        statement = select(ShiftRow).where(ShiftRow.accountID == user_id)
        db_shifts = session.exec(statement).all()
        
        user_shifts = []
        for s in db_shifts:
            user_shifts.append({
                "shift_id": s.shift_ID,
                "owner_id": s.accountID,
                "shift_name": s.name,
                "start": s.start_time,
                "end": s.end_time,
                "min_employees": s.min_employees,
                "max_employees": s.max_employees
            })
    return {"shifts": user_shifts}


"""
Creates a new employee record and links it to the current user's account.
"""
class EmployeeInfo(BaseModel):
    owner_id: int
    name: str
    hours_per_week: int
    availability: Dict[str, int]

@app.post("/add_employee")
async def add_employee(emp_data: EmployeeInfo, userID: Optional[str] = Cookie(None)):
    owner_id = emp_data.owner_id if emp_data.owner_id else (int(userID) if userID else None)
    
    if not owner_id:
        return {"status": "error", "message": "Authentication cookie missing. Please log in again."}

    with Session(engine) as session:
        new_emp = EmployeeRow(
            accountID=owner_id, 
            name=emp_data.name, 
            hours_per_week=emp_data.hours_per_week
        )
        session.add(new_emp)
        session.commit()
        session.refresh(new_emp)

        # Map shift profiles based on the frontend checkboxes
        for shift_id_str, status in emp_data.availability.items():
            # Query for the shift name using the shift ID
            shift_stmt = select(ShiftRow).where(ShiftRow.shift_ID == int(shift_id_str))
            target_shift = session.exec(shift_stmt).first()
            
            if target_shift:
                new_avail = EmployeeAvailabilityRow(
                    employee_id=new_emp.employee_id,
                    shift_name=target_shift.name,  # Saves the shift name string to match validation rules
                    is_available=int(status)
                )
                session.add(new_avail)
        session.commit()
    return {"status": "success"}


"""
Permanently removes an employee from the system and updates the database.
"""
class EmpID(BaseModel):
    owner_id: int
    emp_id: int


@app.post("/remove_employee")
def remove_emp(param: EmpID):
    with Session(engine) as session:
        # 1. Fetch the employee record that belongs to this specific account
        statement = select(EmployeeRow).where(
            EmployeeRow.employee_id == param.emp_id, 
            EmployeeRow.accountID == param.owner_id
        )
        employee = session.exec(statement).first()
        
        if employee:
            name = employee.name
            
            # 2. Clean up their records from child tables first to avoid orphan rows
            avail_statement = select(EmployeeAvailabilityRow).where(EmployeeAvailabilityRow.employee_id == param.emp_id)
            for row in session.exec(avail_statement).all():
                session.delete(row)
                
            vac_statement = select(EmployeeVacationRow).where(EmployeeVacationRow.employee_id == param.emp_id)
            for row in session.exec(vac_statement).all():
                session.delete(row)
                
            # 3. Delete the parent employee row
            session.delete(employee)
            session.commit()
            return {"status": "success", "message": f"Successfully Removed {name} with Employee ID={param.emp_id}."}
            
    return {"status": "error", "message": f"Employee ID {param.emp_id} not found."}



"""
Adds a new work shift (like 'Morning' or 'Afternoon') to the user's profile.
"""
class ShiftInfo(BaseModel):
    owner_id: int
    name: str
    start: str
    end: str
    min_emp: int
    max_emp: int

@app.post("/add_shift")
async def add_shift(shift_data: ShiftInfo, userID: Optional[str] = Cookie(None)):
    owner_id = shift_data.owner_id if shift_data.owner_id else (int(userID) if userID else None)
    
    if not owner_id:
        return {"status": "error", "message": "Authentication cookie missing. Please log in again."}

    with Session(engine) as session:
        new_shift = ShiftRow(
            accountID=owner_id,
            name=shift_data.name,
            start_time=shift_data.start,
            end_time=shift_data.end,
            min_employees=shift_data.min_emp,
            max_employees=shift_data.max_emp
        )
        session.add(new_shift)
        session.commit()
    return {"status": "success"}

"""
Deletes a shift and automatically cleans it out of every employee's availability.
"""
class ShiftID(BaseModel):
    owner_id: int
    shift_id: int


@app.post("/remove_shift")
def remove_shift(param: ShiftID):
    with Session(engine) as session:
        # 1. Find the shift row belonging to this user
        statement = select(ShiftRow).where(
            ShiftRow.shift_ID == param.shift_id,
            ShiftRow.accountID == param.owner_id
        )
        shift = session.exec(statement).first()
        
        if shift:
            shift_name = shift.name
            
            # 2. Cascade delete preferences matching this shift name across all employees belonging to this account
            emp_statement = select(EmployeeRow).where(EmployeeRow.accountID == param.owner_id)
            user_employees = session.exec(emp_statement).all()
            emp_ids = [e.employee_id for e in user_employees]
            
            if emp_ids:
                avail_statement = select(EmployeeAvailabilityRow).where(
                    EmployeeAvailabilityRow.employee_id.in_(emp_ids),
                    EmployeeAvailabilityRow.shift_name == shift_name
                )
                for row in session.exec(avail_statement).all():
                    session.delete(row)
            
            # 3. Delete the shift itself
            session.delete(shift)
            session.commit()
            return {"status": "success", "message": f"Successfully Removed {shift_name} (ID: {param.shift_id})."}
            
    return {"status": "error", "message": f"Error: Shift ID {param.shift_id} not found."}




"""
Updates the availability (Yes/No) for multiple employees across different shifts at once.
"""
class AvailabilityUpdates(BaseModel):
    updates: Dict[str, Dict[str, Dict[str, int]]]

@app.post("/update_availability")
def update_availability(payload: AvailabilityUpdates):
    with Session(engine) as session:
        # payload.updates looks like: {"emp_id": {"availability": {"Shift Name": 1}}}
        for emp_id_str, data in payload.updates.items():
            try:
                emp_id = int(emp_id_str)
            except ValueError:
                continue # Skip invalid data keys like "null" or "undefined"

            # 1. Clear existing availability records for this specific employee
            delete_statement = select(EmployeeAvailabilityRow).where(EmployeeAvailabilityRow.employee_id == emp_id)
            existing_records = session.exec(delete_statement).all()
            for record in existing_records:
                session.delete(record)
            
            # Flush the deletions to make room for new records
            session.commit()

            # 2. Extract the fresh shift mappings sent by the frontend
            availability_dict = data.get("availability", {})

            # 3. Insert a fresh row for each shift checkbox value
            for shift_name, status in availability_dict.items():
                new_availability = EmployeeAvailabilityRow(
                    employee_id=emp_id,
                    shift_name=shift_name,
                    is_available=int(status)  # Converts boolean/int cleanly to database storage
                )
                session.add(new_availability)
        
        # Commit all changes to the database permanently
        session.commit()
        
    return {"status": "success"}

"""
Saves a specific date range where an employee is marked as unavailable to work.
"""
class VacationInfo(BaseModel):
    owner_id: int
    emp_id: int
    start_date: str
    end_date: str

@app.post("/add_vacation")
def add_vacation(param: VacationInfo):
    with Session(engine) as session:
        # 1. Create a new row entry directly in the vacation child table
        new_vacation = EmployeeVacationRow(
            employee_id=param.emp_id, # Target employee ID from frontend payload
            start_date=param.start_date,
            end_date=param.end_date
        )
        session.add(new_vacation)
        session.commit()
        
    return {"status": "success", "message": "Vacation added successfully!"}


@app.post("/delete_vacation")
def delete_vacation(param: VacationInfo):
    with Session(engine) as session:
        # 1. Query for the exact row matching the employee ID and specified dates
        statement = select(EmployeeVacationRow).where(
            EmployeeVacationRow.employee_id == param.emp_id,
            EmployeeVacationRow.start_date == param.start_date,
            EmployeeVacationRow.end_date == param.end_date
        )
        vacation_row = session.exec(statement).first()
        
        # 2. If found, delete the row from the database
        if vacation_row:
            session.delete(vacation_row)
            session.commit()
            return {"status": "success", "message": "Vacation deleted successfully!"}
            
    return {"status": "error", "message": "Vacation record not found."}


"""SIGN-IN/ACCOUNT INFO"""

"""
Verifies login credentials and starts a user session.
"""
class AccountInfo(BaseModel):
    username: str
    password: str

@app.post("/signIn")
async def sign_in(account_data: AccountInfo, response: Response): # Add response here
    with Session(engine) as session:
        statement = select(UserAccount).where(UserAccount.username == account_data.username)
        user = session.exec(statement).first()
        
        if user:
            entered_password = account_data.password.encode('utf-8')
            stored_password = user.password.encode('utf-8')
            if bcrypt.checkpw(entered_password, stored_password):
                # Set a session cookie containing the user's account ID
                response.set_cookie(key="userID",value=str(user.accountID), path="/")
                return {
                    "status": "success", 
                    "accountID": user.accountID, 
                    "username": user.username
                    }
            
        return {"status": "error", "message": "Invalid username or password."}

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
    if info.password != info.password_check:
        return {"status": "error", "message": "Passwords do not match."}
        
    with Session(engine) as session:
        # Check if username is already taken
        statement = select(UserAccount).where(UserAccount.username == info.username)
        existing = session.exec(statement).first()
        if existing:
            return {"status": "error", "message": f"Username:{info.username} is already in use."}
            
        # Encrypt password
        password_bytes = info.password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password_bytes = bcrypt.hashpw(password_bytes, salt)
        encrypted_password = hashed_password_bytes.decode('utf-8')


        # Insert new account row
        new_account = UserAccount(
            username=info.username,
            email=info.email,
            password=encrypted_password
        )
        session.add(new_account)
        session.commit()
        session.refresh(new_account)
        
        return {
            "status": "success", 
            "message": f"Account {info.username} created successfully!",
            "user_id": new_account.accountID
        }


################################
#       Other Functions        #
################################
class ShiftTime(BaseModel):
    startTime: str
    endTime: str

@app.post("/convertFromMilitaryTime")
def convertFromMilitaryTime(param: ShiftTime):
    startTimeObject = datetime.strptime(param.startTime, "%H:%M")
    endTimeObject = datetime.strptime(param.endTime, "%H:%M")
    convertedStartTimeObject = startTimeObject.strftime("%I:%M%p")
    convertedEndTimeObject = endTimeObject.strftime("%I:%M%p")
    return [convertedStartTimeObject, convertedEndTimeObject]
    


"""
Sets up the logic and data structures needed for the algorithm to run the schedule.
"""
def dfs_schedule_helper(start_date, num_days, user_employees, user_shifts):
    if not user_shifts or not user_employees: 
        return None

    schedule = {}
    day_indices = []
    
    # Initialize the schedule structure
    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        date_str = current_date.strftime('%Y-%m-%d')
        schedule[date_str] = {}
        day_indices.append(date_str)
        for shift in user_shifts:
            schedule[date_str][shift['shift_name']] = [] 
            
    # Create employee hour tracker {emp_id: {'current_hours': 0}}
    employee_hours = {
        emp['id']: {'current_hours': 0, 'max_hours': emp['hours_per_week']}
        for emp in user_employees
    }
    
    print("\nStarting DFS to generate Schedule...")
    
    DFS_success = DFS_algorithm.dfs_scheduling(schedule, employee_hours, day_indices, 0, 0, 0, num_days, user_employees, user_shifts)

    if DFS_success:
        print("DFS Minimums Met. Running Maximizer...")
        DFS_algorithm.scheduleMaximizer(schedule, employee_hours, day_indices, 0, 0, 0, num_days, user_employees, user_shifts)
        return schedule
    else:
        print("DFS failed to find a valid schedule.")
        return None

"""
A wrapper function that calculates the algorithm's runtime and handles errors.
"""
def generate_schedule(start_date_str: str, num_days: int, user_id: int):
    with Session(engine) as session:
        # 1. Fetch the user's raw shifts from the database
        shift_statement = select(ShiftRow).where(ShiftRow.accountID == user_id)
        db_shifts = session.exec(shift_statement).all()
        
        user_shifts = [{
            "owner_id": shift.accountID,
            "shift_id": shift.shift_ID,
            "shift_name": shift.name,
            "start": shift.start_time,
            "end": shift.end_time,
            "min_employees": shift.min_employees,
            "max_employees": shift.max_employees
        } for shift in db_shifts]

        # 2. Fetch the user's employees and rebuild their context maps
        emp_statement = select(EmployeeRow).where(EmployeeRow.accountID == user_id)
        db_employees = session.exec(emp_statement).all()
        
        user_emps = []
        for emp in db_employees:
            # Re-fetch child table preferences
            avail_stmt = select(EmployeeAvailabilityRow).where(EmployeeAvailabilityRow.employee_id == emp.employee_id)
            db_avail = session.exec(avail_stmt).all()
            availability_dict = {row.shift_name: row.is_available for row in db_avail}
            
            # Default missing checkmarks to available (1)
            for s in user_shifts:
                if s["shift_name"] not in availability_dict:
                    availability_dict[s["shift_name"]] = 1
                    
            # Re-fetch child table vacations
            vac_stmt = select(EmployeeVacationRow).where(EmployeeVacationRow.employee_id == emp.employee_id)
            db_vac = session.exec(vac_stmt).all()
            vacation_list = [[v.start_date, v.end_date] for v in db_vac]
            
            user_emps.append({
                "owner_id": emp.accountID,
                "id": emp.employee_id,
                "name": emp.name,
                "hours_per_week": emp.hours_per_week,
                "vacation": vacation_list,
                "availability": availability_dict
            })
    
    if not user_shifts or not user_emps:
        return {"error": "No shifts or employees to schedule."}

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}
        
    start_time = time.time()
    dfs_schedule = dfs_schedule_helper(start_date, num_days, user_emps, user_shifts)
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
    return FileResponse('homepage.html')



app.mount("/", StaticFiles(directory=".", html=True), name="static")



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)