from datetime import datetime, timedelta
import csv_code

holidays = csv_code.read_holidays("statHolidays.csv")

"""
Calculates the total hours of a shift based on its start and end times.
"""
def get_shift_duration(shift):
    try:
        start_dt = datetime.strptime(shift['start'], "%I:%M%p")
        end_dt = datetime.strptime(shift['end'], "%I:%M%p")
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        return (end_dt - start_dt).total_seconds() / 3600
    except ValueError:
        return 8 

"""
Checks if an employee is eligible for a specific shift based on their availability and vacation.
"""
def is_employee_available(employee, date_str, shift_name):
    if employee.get("availability", {}).get(shift_name) != 1:
        return False
    
    for start_date_str, end_date_str in employee.get("vacation", []):
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        current_date = datetime.strptime(date_str, '%Y-%m-%d')
        if start_date <= current_date <= end_date:
            return False
        
    return True

"""
Verifies if an employee has already been assigned to a shift on a specific date.
"""
def is_scheduled_today(emp_name, date_str, schedule):
    for shift_name in schedule[date_str]:
        if emp_name in schedule[date_str][shift_name]:
            return True
    return False

