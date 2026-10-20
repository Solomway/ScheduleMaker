from datetime import datetime, timedelta
import csv

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
def is_employee_available(employee, current_date_str, shift_name):
    # Convert date string to weekday (5 = Saturday, 6 = Sunday)
    date_obj = datetime.strptime(current_date_str, "%Y-%m-%d")
    weekday = date_obj.weekday()

    availability = employee.get('availability', {})

    # Base Shift Check
    if availability.get(shift_name, 1) == 0:
        return False

    # Weekend Shift Checks
    if weekday == 5:  # Saturday
        sat_key = f"{shift_name} - Saturday"
        if availability.get(sat_key, 1) == 0:
            return False

    elif weekday == 6:  # Sunday
        sun_key = f"{shift_name} - Sunday"
        if availability.get(sun_key, 1) == 0:
            return False

    # Check vacation dates...
    for vac in employee.get('vacation', []):
        if vac[0] <= current_date_str <= vac[1]:
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


"""
Loads a list of statutory holidays from a CSV file to be used by the scheduler.
"""
def read_holidays(filename="statHolidays.csv"):
    holidays = []
    with open(filename, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            date, name = row
            holidays.append([date, name])
    return holidays

holidays = read_holidays()

"""
Calculates how many total shift slots this week the employee 
is validly available to work. Lower score = More constrained employee.
"""
def get_eligibility_score(employee, day_indices, day_index, num_days, shifts_list):
    score = 0
    for d_idx in range(day_index, num_days):
        current_date_str = day_indices[d_idx]
        for shift in shifts_list:
            shift_name = shift['shift_name']
            if is_employee_available(employee, current_date_str, shift_name):
                score += 1
    return score

"""
Returns True if the employee was assigned a shift on the day directly before current_date_str.
"""
def worked_previous_day(emp_name, current_date_str, day_indices, schedule):
    curr_idx = day_indices.index(current_date_str)
    if curr_idx == 0:
        return False  # First day of the schedule
    
    prev_date_str = day_indices[curr_idx - 1]
    
    # Check if emp_name worked any shift on the previous day
    for shift_name, assigned_list in schedule[prev_date_str].items():
        if emp_name in assigned_list:
            return True
            
    return False