import csv
from datetime import datetime

class Employee:
    def __init__(self, owner_id, id, name, days_off, max_hours, availability):
        self.owner_id = owner_id
        self.id = id
        self.name = name
        self.days_off = days_off  # list of strings
        self.max_hours = max_hours
        self.availability = availability  # dict {shift_name: 1/0}

class Shift:
    def __init__(self, owner_id, id, name, hours, required_employees, max_employees):
        self.owner_id = owner_id
        self.id = id
        self.name = name
        self.hours = hours
        self.required_employees = required_employees
        self.max_employees = max_employees

class Account:
    def __init__(self, owner_id, username, email, password, employees, shifts):
        self.owner_id = owner_id
        self.username = username
        self.email = email
        self.password = password
        self.employees = employees
        self.shifts = shifts
        
"""
Reads the employees CSV and converts the data into a list of dictionaries.
"""
def read_employees(file_path):
    employees = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for ignore, row in enumerate(reader, start=1):
            # Parse days_off column into list of [start, end]
            days_off_list = []
            if row['days_off']:
                parts = row['days_off'].split(',')
                for p in parts:
                    p = p.strip()
                    if "to" in p:
                        start, end = p.split("to")
                        days_off_list.append([start.strip(), end.strip()])
                    else:
                        # single day off
                        days_off_list.append([p, p])

            # Parse availability
            availability = {}
            for shift_name in reader.fieldnames[5:]:
                val = row.get(shift_name, '').strip()
                availability[shift_name] = int(val) if val != '' else 1

            employees.append({
                "owner_id": row['owner_id'],
                "id": int(row['id']),
                "name": row['name'],
                "hours_per_week": int(row['max_hours_per_week']),
                "vacation": days_off_list,
                "availability": availability
            })
    return employees


"""
Saves the current employee list and their availability back to the CSV file.
"""
def save_employees_csv(employees, file_path="employees.csv"):
    if not employees:
        return
    fieldnames = ['owner_id', 'id', 'name', 'max_hours_per_week', 'days_off']
    shift_names = set()
    for emp in employees:
        shift_names.update(emp['availability'].keys())    
    fieldnames.extend(sorted(list(shift_names)))

    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for emp in employees:
            row = {
                'owner_id': emp['owner_id'],
                'id': emp['id'],
                'name': emp['name'],
                'max_hours_per_week': emp['hours_per_week'],
                'days_off': ", ".join([f"{v[0]} to {v[1]}" if v[0] != v[1] else v[0] for v in emp['vacation']])
            }
            row.update(emp['availability'])
            writer.writerow(row)

"""
Parses the shifts CSV and prepares the shift data for the scheduling algorithm.
"""
def read_shifts(file_path):
    shifts = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            shifts.append({
                'owner_id': row['owner_id'],
                "shift_id": int(row['shift_id']),
                "shift_name": row['shift_name'],
                "start": row['start'],
                "end": row['end'],
                "min_employees": int(row['min_employees']),
                "max_employees": int(row['max_employees'])
            })
    return shifts


"""
Saves the shift definitions (names, times, and requirements) to the CSV file.
"""
def save_shifts_csv(shifts, file_path="shifts.csv"):
    fieldnames = ['owner_id', 'shift_id', 'shift_name', 'start', 'end', 'min_employees', 'max_employees']
    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in shifts:
            writer.writerow({
                'owner_id': s['owner_id'],
                'shift_id': s['shift_id'],
                'shift_name': s['shift_name'],
                'start': s['start'],
                'end': s['end'],
                'min_employees': s['min_employees'],
                'max_employees': s['max_employees']
            })


"""
Loads a list of statutory holidays from a CSV file to be used by the scheduler.
"""
def read_holidays(filename):
    holidays = []
    with open(filename, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            date, name = row
            holidays.append([date, name])
    return holidays

"""
Exports the final generated schedule to a CSV file for record-keeping.
"""
def write_schedule(schedule, file_path):
    # schedule is a list of dicts: {'date': ..., 'shift': ..., 'employee': ...}
    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['date', 'shift', 'employee'])
        writer.writeheader()
        writer.writerows(schedule)

"""
Loads user account credentials from the accounts CSV.
"""
def readAccounts(filepath):
    accounts = []
    with open(filepath, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            accounts.append({
                "owner_id": row['owner_id'],
                "username": row['username'],
                "email": row["email"],
                "password": row['password']
            })
    return accounts

"""
Saves new or updated user account information to the database.
"""
def saveAccounts(accounts, filepath):
    fieldnames = ['owner_id', 'username', 'email', 'password']
    with open(filepath, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames)
        writer.writeheader()
        for account in accounts:
            writer.writerow({
                'owner_id': account['owner_id'],
                "username": account['username'],
                "email": account["email"],
                "password": account['password']
            })