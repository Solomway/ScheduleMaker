from datetime import datetime, timedelta
import alg_helper

"""
Uses a Depth-First Search approach to find a valid schedule that meets all minimum staffing requirements.
"""
def dfs_scheduling(schedule, employee_hours, day_indices, day_index, shift_index, slot_index, num_days,employees_list, shifts_list):
    # A valid schedule is found
    if day_index == num_days:
        return True 

    current_date_str = day_indices[day_index]
    

    is_holiday = False
    for holiday_entry in alg_helper.holidays:
        if holiday_entry[0] == current_date_str:
            is_holiday = True
            break
            
    # If it's a holiday, skip all shifts for the day and move to the next day.
    if is_holiday:
        print(f"NOTE: Skipping scheduling on holiday: {current_date_str}")
        
        # Weekly hours reset
        next_day_num = day_index + 1
        next_employee_hours = employee_hours

        if next_day_num > 0 and (next_day_num % 7) == 0:
            print(f"WEEKLY HOURS RESET AT DAY {next_day_num}.")
            
            next_employee_hours = {
                emp_id: {'current_hours': 0} 
                for emp_id, data in employee_hours.items()
            }

        return dfs_scheduling(schedule, next_employee_hours, day_indices, next_day_num, 0, 0, num_days,employees_list, shifts_list)


    # Move to the next shift or next day
    if shift_index >= len(shifts_list):
        next_day_index = day_index + 1
        
        # Weekly Hours Reset 
        next_employee_hours = employee_hours
        if next_day_index > 0 and (next_day_index % 7) == 0:
            print(f"WEEKLY HOURS RESET AT DAY {next_day_index}.")
            
            next_employee_hours = {
                emp_id: {'current_hours': 0} 
                for emp_id, data in employee_hours.items()
            }

        return dfs_scheduling(schedule, next_employee_hours, day_indices, next_day_index, 0, 0, num_days, employees_list, shifts_list)

    current_shift = shifts_list[shift_index]
    shift_name = current_shift['shift_name']
    min_employees = current_shift.get('min_employees', 0)


    # Move to the next shift if all mandatory slots for the current shift are filled
    if slot_index >= min_employees:
        return dfs_scheduling(schedule, employee_hours, day_indices, day_index, shift_index + 1, 0, num_days, employees_list, shifts_list)
    

    shift_duration = alg_helper.get_shift_duration(current_shift)

    # Iterate through all employees to find a valid assignment
    for employee in employees_list:
        emp_id = employee['id']
        emp_name = employee['name']
        
        # Constraint Check: Employee availability and vacation 
        if not alg_helper.is_employee_available(employee, current_date_str, shift_name):
            continue
        
        # Constraint Check: Weekly hours limit
        current_week_hours = employee_hours[emp_id]['current_hours']
        max_hours = employee['hours_per_week']
        
        if current_week_hours + shift_duration > max_hours:
            continue
            
        # Constraint Check: Already assigned to a shift on this day
        if emp_name in schedule[current_date_str][shift_name]:
             continue 
        
        # Constraint Check: Already assigned to another shift on this day
        is_already_scheduled_today = False
        for existing_shift_name in schedule[current_date_str]:
            if emp_name in schedule[current_date_str][existing_shift_name]:
                is_already_scheduled_today = True
                break
        if is_already_scheduled_today:
            continue

        
        # Update changes
        schedule[current_date_str][shift_name].append(emp_name)
        employee_hours[emp_id]['current_hours'] += shift_duration
        
        # Recursive Call 
        if dfs_scheduling(schedule, employee_hours, day_indices, day_index, shift_index, slot_index + 1, num_days,employees_list, shifts_list):
            return True # Solution found down this path

        # Dead end 
        schedule[current_date_str][shift_name].pop()
        employee_hours[emp_id]['current_hours'] -= shift_duration
        
    # If no employee can be assigned to this slot, backtracks to the previous slot/shift/day
    return False

"""
Iterates through a valid schedule to assign extra staff where possible without exceeding maximum hour limits.
"""
def scheduleMaximizer(schedule, employee_hours, day_indices, day_index, shift_index, slot_index, num_days, employees_list, shifts_list):
    shifts_map = {shift['shift_name']: shift for shift in shifts_list}

    # Process week by week (every 7 days)
    for week_start in range(0, num_days, 7):
        week_days = day_indices[week_start : week_start + 7]
        
        # Track hours just for this specific week to keep the fairness sort accurate
        current_week_hours = {emp['id']: 0.0 for emp in employees_list}
        for day in week_days:
            for s_name, assigned_names in schedule[day].items():
                shift_duration = alg_helper.get_shift_duration(shifts_map[s_name])
                for name in assigned_names:
                    # Find the ID for this name to update their week total
                    for employee in employees_list:
                        if employee['name'] == name:
                            current_week_hours[employee['id']] += shift_duration

        added_in_this_lap = True
        while added_in_this_lap:
            added_in_this_lap = False

            for day in week_days:
                is_holiday = False
                
                for holiday_entry in alg_helper.holidays:
                    if holiday_entry[0] == day:
                        is_holiday = True
                        break  

                if is_holiday:
                    continue

                for shift_name, assigned_emps in schedule[day].items():
                    shift_info = shifts_map[shift_name]
                    max_employees = shift_info.get('max_employees', 0)
                    shift_duration = alg_helper.get_shift_duration(shift_info)

                    if len(assigned_emps) < max_employees:
                        eligible_emps = []
                        for employee in employees_list:
                            # 1. Check if already in this shift or working today
                            if employee['name'] in assigned_emps: continue
                            if alg_helper.is_scheduled_today(employee['name'], day, schedule): continue
                            
                            # 2. Check Availability
                            if not alg_helper.is_employee_available(employee, day, shift_name): continue
                            
                            # 3. Check if they have room in their weekly hours
                            if current_week_hours[employee['id']] + shift_duration <= employee['hours_per_week']:
                                eligible_emps.append(employee)

                        if eligible_emps:
                            # Fairness Sort: Pick the person with the least hours in THIS week
                            eligible_emps.sort(key=lambda emp: current_week_hours[emp['id']])
                            top_candidate = eligible_emps[0]

                            assigned_emps.append(top_candidate['name'])
                            current_week_hours[top_candidate['id']] += shift_duration
                            added_in_this_lap = True 
                            
    return schedule