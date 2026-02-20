/*
Initiates the scheduling algorithm on the server and handles the display of the final results or errors.
*/
async function generateSchedule() {
    const data = {
        start_date: document.getElementById('startDate').value,
        num_days: parseInt(document.getElementById('num_days').value)
    };

    const response = await fetch('/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    
    if (result.status === "success") {
        renderScheduleTable(result.schedule);
    } else {
        document.getElementById('scheduleOutput').innerHTML = `<p style="color:red;">Error: ${result.message}</p>`;
    }
}

/*
Generates the HTML structure to display the finalized schedule in a readable table format on the web page.
*/
function renderScheduleTable(scheduleData) {
    let html = `
        <table class="schedule-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Shift</th>
                    <th>Assigned Employees</th>
                </tr>
            </thead>
            <tbody>`;

    for (const [date, shifts] of Object.entries(scheduleData)) {
        const dateObj = new Date(date + 'T00:00:00');
        const formattedDate = dateObj.toLocaleDateString('en-GB').split('/').join('-');
        const dayName = dateObj.toLocaleDateString('en-CA', { weekday: 'long' });

        for (const [shiftName, emps] of Object.entries(shifts)) {
            const empList = emps.length > 0 ? emps.join(", ") : "<em>No one assigned</em>";
            
            html += `
                <tr>
                    <td>${formattedDate} - <strong>${dayName}</strong></td>
                    <td><strong>${shiftName}</strong></td>
                    <td>${empList}</td>
                </tr>`;
        }
    }

    html += `</tbody></table>`;
    document.getElementById('scheduleOutput').innerHTML = html;
}


/*
Dynamically builds a table displaying all employee details, including their IDs, hours, and availability.
*/
function renderEmployeeTable(employee_data) {
    const container = document.getElementById('EmpviewOutput');
    if (!container) return;

    if (!employee_data || employee_data.length === 0) {
        container.innerHTML = "<p>No employees found for this account.</p>";
        return;
    }

    const firstEmployee = employee_data[0];
    const shiftNames = Object.keys(firstEmployee.availability || {});

    let html = `
        <table class="schedule-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Hrs/Wk</th>
                    ${shiftNames.map(name => `<th>${name.toUpperCase()}</th>`).join('')}
                    <th>Vacation</th>
                </tr>
            </thead>
            <tbody>`;

    employee_data.forEach(employee => {
        const vacationStrings = employee.vacation.map(range => {
            const startDate = range[0];
            const endDate = range[1];
            return startDate === endDate ? startDate : `${startDate} to ${endDate}`;
        });

        html += `
            <tr>
                <td>${employee.id}</td>
                <td><strong>${employee.name}</strong></td>
                <td>${employee.hours_per_week}</td>
                ${shiftNames.map(name => {
                    const isAvailable = employee.availability[name] === 1;
                    return `<td>${isAvailable ? "Yes" : "No"}</td>`;
                }).join('')}
                <td><small>${vacationStrings.join(", ") || "None"}</small></td>
            </tr>`;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
}

/*
Creates the UI table for viewing all current shift configurations, including start/end times and staffing requirements.
*/
function renderShiftTable(shift_data) {
    let html = `
        <table class="schedule-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Shift Name</th>
                    <th>Times</th>
                    <th>Staffing (Min/Max)</th>
                </tr>
            </thead>
            <tbody>`;

    if (!shift_data || shift_data.length === 0) {
        html += `
            <tr>
                <td>
                    No shifts found.
                </td>
            </tr>`;
    } 
    else {
        shift_data.forEach(shift => {
            html += `
                <tr>
                    <td>${shift.shift_id}</td>
                    <td><strong>${shift.shift_name}</strong></td>
                    <td>${shift.start} - ${shift.end}</td>
                    <td>${shift.min_employees} to ${shift.max_employees}</td>
                </tr>`;
        });
    }

    html += `</tbody></table>`;
    document.getElementById('ShiftviewOutput').innerHTML = html;
}

/*
Retrieves the list of employees from the backend server and triggers the rendering of the employee table.
*/
async function fetch_employees(){
    const response = await fetch('/view_emps');

    const result = await response.json();

    if (result.status === "success") {
        renderEmployeeTable(result.employees);
    }
    
}

/*
Collects new employee data from the frontend form and sends it to the server to be saved.
*/
async function add_emp() {
    const name = document.getElementById('emp_name').value;
    const hours = parseInt(document.getElementById('desired_hours').value);
    const availability = {};
    const checkboxes = document.querySelectorAll('#shiftCheckboxes input[type="checkbox"]');
    
    checkboxes.forEach(box => {
    if (box.checked) {
        availability[box.value] = 1;
    } else {
        availability[box.value] = 0;
    }
    })

    const data = {
        name: name,
        hours_per_week: hours,
        availability: availability
    };

    const response = await fetch('/add_employee', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    location.reload();
}

/*
Retrieves the list of all defined shifts from the server to be displayed in the UI.
*/
async function fetch_shifts(){
    const response = await fetch('/view_shifts');

    const result = await response.json();

    if (result.status === "success") {
        renderShiftTable(result.shift_table);
    }
}

/*
Populates the frontend form with checkboxes for each available shift to manage employee availability.
*/
async function loadShiftCheckboxes() {
    const response = await fetch('/get_shifts');
    const data = await response.json();
    const container = document.getElementById('shiftCheckboxes');

    data.shifts.forEach(shift => {
        container.innerHTML += `
            <div class="shift-option">
                <input type="checkbox" id="shift_${shift.shift_name}" name="availability" value="${shift.shift_name}">
                <label for="shift_${shift.shift_name}">${shift.shift_name} (${shift.start} - ${shift.end})</label>
            </div>
        `;
    });
}

/*
Sends a request to the server to delete a specific employee from the system by their ID.
*/
async function remove_emp() {
    const data = {
        emp_id: parseInt(document.getElementById('emp_id').value),
    };

    const response = await fetch('/remove_employee', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    location.reload();
}

/*
Collects shift details from the UI and sends them to the backend to create a new work slot.
*/
async function add_shift(){
    const data = {
        name: document.getElementById('shift_name').value,
        start: document.getElementById('start_time').value,
        end: document.getElementById('end_time').value,
        min_emp: parseInt(document.getElementById('min_emp').value),
        max_emp: parseInt(document.getElementById('max_emp').value)
    }

    const response = await fetch('/add_shift', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result.status === "success") {
        document.getElementById('popupMessage').innerText = `Successfully added the ${data['name']} shift.`;
        document.getElementById('statusPopup').style.display = "block";
    } else {
        alert("Error adding shift");
    }
}

/*
Triggers the removal of a specific shift from the database and updates the UI.
*/
async function remove_shift() {
    const data = {
        shift_id: parseInt(document.getElementById('shift_id').value),
    };

    const response = await fetch('/remove_shift', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    location.reload();
}

/*
Fetches live data and opens a modal window to manage availability settings for all employees at once.
*/
async function openAvailabilityPopup() {
    const statusPopup = document.getElementById('statusPopup');
    if (statusPopup) statusPopup.style.display = 'none';
    
    const [empResponse, shiftResponse] = await Promise.all([
        fetch('/get_employees'),
        fetch('/get_shifts')
    ]);
    
    const employees = await empResponse.json(); 
    const shiftData = await shiftResponse.json(); 

    if (employees.status === "error" || shiftData.status === "error") {
        alert("Access Denied: Please sign in first.");
        window.location.href = 'index.html';
        return;
    }

    const shifts = shiftData.shifts;
    const container = document.getElementById('availabilityContainer');
    container.innerHTML = ''; 

    employees.forEach(emp => {
        let shiftHtml = '';
        shifts.forEach(shift => {
            const isChecked = (emp.availability && emp.availability[shift.shift_name] === 1) ? 'checked' : '';
            
            shiftHtml += `
                <label style="margin-right:10px; color: black;">
                    <input type="checkbox" class="avail-check" 
                           data-empid="${emp.id}" 
                           data-shiftname="${shift.shift_name}" ${isChecked}>
                    ${shift.shift_name}
                </label>`;
        });

        container.innerHTML += `
            <div class="emp-row" style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #ddd; color: black;">
                <strong>ID: ${emp.id} - ${emp.name}</strong>
                <div class="shift-grid">${shiftHtml}</div>
            </div>`;
    });

    document.getElementById('availabilityPopup').style.display = 'block';
}

/*
Submits the updated availability status for all employees across all shifts to the backend.
*/
async function saveAllAvailability() {
    const checkboxes = document.querySelectorAll('.avail-check');
    const updates = {};

    checkboxes.forEach(box => {
        const empId = box.dataset.empid;
        const shiftName = box.dataset.shiftname;
        
        if (!updates[empId]) {
            updates[empId] = { availability: {} };
        }
        updates[empId].availability[shiftName] = box.checked ? 1 : 0;
    });

    const response = await fetch('/update_availability', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ updates: updates })
    });

    const result = await response.json();
    if (result.status === "success") {
        location.reload(); 
    }
}

/*
Submits a new vacation date range for an employee to ensure they aren't scheduled during that time.
*/
async function submitVacation() {
    const data = {
        emp_id: parseInt(document.getElementById('vac_emp_id').value),
        start_date: document.getElementById('start_date').value,
        end_date: document.getElementById('end_date').value
    };

    const response = await fetch('/add_vacation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result.status === "success") {
        location.reload(); 
    }
}

let currentDeleteEmpId = null;

/*
Fetches an employee's current vacations and displays them in a selectable list for removal.
*/
async function remove_vacation() {
    const empId = document.getElementById('emp_id_vac').value;
    if (!empId) return alert("Please enter an Employee ID");

    const response = await fetch('/get_employees');
    const employees = await response.json(); 
    
    const emp = employees.find(e => String(e.id) === String(empId));
    
    if (!emp || !emp.vacation || emp.vacation.length === 0) {
        alert("No vacations found for this employee.");
        return;
    }

    currentDeleteEmpId = empId;
    const container = document.getElementById('vacationContainer');
    
    let listHtml = '<div style="text-align: left; color: black; padding: 10px;">';
    
    emp.vacation.forEach((vac, index) => {
        let start = vac[0];
        let end = vac[1];
        let display = (start === end) ? start : start + " to " + end;

        listHtml += '<div style="margin-bottom: 12px;">';
        listHtml += '  <input type="radio" name="vacSelect" id="v' + index + '" value="' + index + '">';
        listHtml += '  <label for="v' + index + '" style="margin-left: 10px; cursor: pointer;">' + display + '</label>';
        listHtml += '</div>';
    });
    
    listHtml += '</div>';

    container.innerHTML = listHtml;
    document.getElementById('delVacationPopup').style.display = 'flex';
}

/*
Removes a specifically selected vacation entry from the employee's history.
*/
async function deleteVacation() {
    // Find which radio button the user clicked
    const selectedRadio = document.querySelector('input[name="vacSelect"]:checked');

    const data = { 
        emp_id: parseInt(currentDeleteEmpId), 
        vac_index: parseInt(selectedRadio.value) 
    };

    const response = await fetch('/delete_vacation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    
    if (result.status === "success") {
        location.reload(); 
    } else {
        alert("Error: " + result.message);
    }
}

/*
Authenticates a user by sending their username and password to the server for verification.
*/
async function signIn() {
    const accountData = {
        username: document.getElementById('uname').value,
        password: document.getElementById('pword').value
    };
    const response = await fetch('/signIn', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(accountData)
    });
    const result = await response.json();
    if (result.status === "success") {
        const msg = document.getElementById('popupMessage');
        const popup = document.getElementById('statusPopup');
        msg.innerText = `${accountData.username} has successfully been logged in.`;
        popup.style.display = "flex";
    } else {
        alert(result.message);
    }
}

/*
Sends account information for the guest account into sign in function
*/
async function signInGuest(){
    const accountData = {
        username: 'guest',
        password: '123'
    }
    const response = await fetch('/signIn', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(accountData)
    });
    const result = await response.json();
    if (result.status === "success") {
        const msg = document.getElementById('popupMessage');
        const popup = document.getElementById('statusPopup');
        msg.innerText = `Successfully logged into guest account.`;
        popup.style.display = "flex";
    } else {
        alert(result.message);
    }
}

/*
Registers a new user account with the provided credentials and updates the system status.
*/
async function createAccount() {
    const data = {
        username: document.getElementById('reg_uname').value,
        email: document.getElementById('e_mail').value,
        password: document.getElementById('reg_pword').value,
        password_check: document.getElementById('pwordCheck').value
    }

    const response = await fetch('/createAccount', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    })

    const result = await response.json();
    if (result.status === "success") {
        const msg = document.getElementById('popupMessage');
        const popup = document.getElementById('statusPopup');
        msg.innerText = `You have successfully created an account with the username:${data.username}`;
        popup.style.display = "flex";
    } 
    else {
        alert(result.message);
    }
}

/*
Quickly sets all employees to 'Available' for a newly created shift.
*/
async function setAllAvailability() {
    const shiftName = document.getElementById('shift_name').value;
    
    const empResponse = await fetch('/get_employees');
    const employees = await empResponse.json();

    const allUpdates = {};

    employees.forEach(emp => {
        allUpdates[emp.id] = {
            availability: {
                [shiftName]: 1 
            }
        };
    });

    const response = await fetch('/update_availability', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ updates: allUpdates })
    });

    const result = await response.json();
    if (result.status === "success") {
        document.getElementById('statusPopup').style.display = 'none';
        location.reload(); 
    } else {
        alert("Failed to update availability for all employees.");
    }
}

window.onload = function() {
    fetch_employees();
    fetch_shifts();
    loadShiftCheckboxes();
};