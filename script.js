// Helper function to extract cookies by name natively from the browser document session
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}


/*
Initiates the scheduling algorithm on the server and handles the display of the final results or errors.
*/
async function generateSchedule() {
    // Fresh dynamic lookup from localStorage
    const loggedInUserId = localStorage.getItem('userID');
    if (!loggedInUserId) {
        alert("Session missing. Please log in.");
        return;
    }

    const data = {
        owner_id: parseInt(getCookie('userID')),
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

    const hasData = employee_data && employee_data.length > 0;
    const firstEmployee = hasData ? employee_data[0] : null;
    const shiftNames = firstEmployee ? Object.keys(firstEmployee.availability || {}) : [];

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

    if (!hasData) {
        const totalColumns = 4 + shiftNames.length; 
        html += `
            <tr>
                <td colspan="${totalColumns}" style="text-align: center;">No employees found.</td>
            </tr>`;
    } 
    else {
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
    }

    html += `</tbody></table>`;
    container.innerHTML = html;
}

/*
Creates the UI table for viewing all current shift configurations, including start/end times and staffing requirements.
*/
async function renderShiftTable(shift_data) {
    const outputContainer = document.getElementById('ShiftviewOutput');
    if (!outputContainer) return;

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
                <td colspan="4" style="text-align: center;">No shifts found.</td>
            </tr>`;
    } 
    else {
        for (const shift of shift_data) {
            const sID = shift.shift_id;
            const sName = shift.shift_name;
            const minEmp = shift.min_employees;
            const maxEmp = shift.max_employees;

            try {
                const response = await fetch('/convertFromMilitaryTime', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ 
                        startTime: shift.start, 
                        endTime: shift.end 
                    })
                });
                
                const shiftTimes = await response.json(); 
                
                html += `
                    <tr>
                        <td>${sID}</td>
                        <td><strong>${sName}</strong></td>
                        <td>${shiftTimes[0]} - ${shiftTimes[1]}</td>
                        <td>${minEmp} to ${maxEmp}</td>
                    </tr>`;
            } catch (err) {
                html += `
                    <tr>
                        <td>${sID}</td>
                        <td><strong>${sName}</strong></td>
                        <td>${shift.start} - ${shift.end}</td>
                        <td>${minEmp} to ${maxEmp}</td>
                    </tr>`;
            }
        }
    }

    html += `</tbody></table>`;
    outputContainer.innerHTML = html;
}

/*
Retrieves the list of employees from the backend server and triggers the rendering of the employee table.
*/
// A reliable helper function to safely look up your user session
function getAuthenticatedUserId() {
    const id = localStorage.getItem('userID');
    if (!id || id === "null" || id === "undefined") {
        return null;
    }
    return id;
}

async function fetch_employees() {
    const loggedInUserId = getCookie('userID') || localStorage.getItem('userID');
    if (!loggedInUserId) return;

    const response = await fetch(`/view_emps/${loggedInUserId}`);
    const result = await response.json();

    if (result.status === "success" && result.employees) {
        renderEmployeeTable(result.employees);
    }
}

async function fetch_shifts() {
    const loggedInUserId = getCookie('userID') || localStorage.getItem('userID');
    if (!loggedInUserId) return;

    const response = await fetch(`/view_shifts/${loggedInUserId}`);
    const result = await response.json();

    if (result.status === "success" && result.shift_table) {
        renderShiftTable(result.shift_table);
    }
}

async function loadShiftCheckboxes() {
    const container = document.getElementById('shiftCheckboxes');
    if (!container) return;
    container.innerHTML = ""; 

    const loggedInUserId = getCookie('userID');
    if (!loggedInUserId) return;

    const response = await fetch(`/view_shifts/${loggedInUserId}`);
    const result = await response.json();

    if (result.status === "success" && result.shift_table) {
        result.shift_table.forEach(shift => {
            const label = document.createElement('label');
            label.innerHTML = `
                <input type="checkbox" value="${shift.shift_id}"> 
                ${shift.shift_name}
            `;
            container.appendChild(label);
            container.appendChild(document.createElement('br'));
        });
    }
}

/*
Collects new employee data from the frontend form and sends it to the server to be saved.
*/
async function addShift() {
    // Fresh dynamic lookup from localStorage
    const loggedInUserId = localStorage.getItem('userID');
    if (!loggedInUserId) {
        alert("Session missing. Please log in.");
        return;
    }

    const name = document.getElementById('shift_name').value;
    const start = document.getElementById('start_time').value;
    const end = document.getElementById('end_time').value;
    const minEmp = document.getElementById('min_employees').value;
    const maxEmp = document.getElementById('max_employees').value;

    if (!name || !start || !end || !minEmp || !maxEmp) {
        alert("Please fill out all shift details.");
        return;
    }

    const payload = {
        owner_id: parseInt(getCookie('userID')),
        name: name,
        start_time: start,
        end_time: end,
        min_employees: parseInt(minEmp),
        max_employees: parseInt(maxEmp)
    };

    const response = await fetch('/add_shift', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });

    const result = await response.json();
    if (result.status === "success") {
        const msg = document.getElementById('popupMessage');
        const popup = document.getElementById('statusPopup');
        if (msg && popup) {
            msg.innerText = `Successfully added shift: ${payload.name}`;
            popup.style.display = "flex";
        } else {
            alert("Shift Added Successfully!");
            location.reload();
        }
    } else {
        alert(result.message || "Failed to add shift");
    }
}


async function add_emp() {
    const loggedInUserId = localStorage.getItem('userID');
    if (!loggedInUserId) {
        alert("Session missing. Please log in.");
        return;
    }

    const name = document.getElementById('emp_name').value;
    const hours = parseInt(document.getElementById('desired_hours').value);
    
    const availability = {};
    const checkboxes = document.querySelectorAll('#shiftCheckboxes input[type="checkbox"]');
    checkboxes.forEach(cb => {
        availability[cb.value] = cb.checked ? 1 : 0;
    });

    const payload = {
        owner_id: parseInt(getCookie('userID')),
        name: name,
        hours_per_week: hours,
        availability: availability
    };

    const response = await fetch('/add_employee', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });

    const result = await response.json();
    if (result.status === "success") {
        alert("Employee Added Successfully!");
        location.reload();
    } else {
        alert(result.message || "Failed to add employee");
    }
}

/*
Sends a request to the server to delete a specific employee from the system by their ID.
*/
async function remove_emp() {
    const loggedInUserId = localStorage.getItem('userID');

    const data = {
        owner_id: parseInt(getCookie('userID')),
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
    const loggedInUserId = localStorage.getItem('userID');

    const data = {
        owner_id: parseInt(getCookie('userID')),
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
    const loggedInUserId = localStorage.getItem('userID');

    const data = {
        owner_id: parseInt(getCookie('userID')),
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
    
    const loggedInUserId = localStorage.getItem('userID') || getCookie('userID');
    if (!loggedInUserId) return;

    const [empResponse, shiftResponse] = await Promise.all([
        fetch(`/view_emps/${loggedInUserId}`),
        fetch(`/view_shifts/${loggedInUserId}`)
    ]);
    
    const empResult = await empResponse.json(); 
    const shiftData = await shiftResponse.json(); 

    if (empResult.status === "error" || shiftData.status === "error") {
        alert("Access Denied: Please sign in first.");
        window.location.href = 'index.html';
        return;
    }

    const employees = empResult.employees || [];
    const shifts = shiftData.shift_table || [];
    const container = document.getElementById('availabilityContainer');
    container.innerHTML = ''; 

    employees.forEach(emp => {
        let shiftHtml = '';
        shifts.forEach(shift => {
            const sName = shift.shift_name;
            const isChecked = (emp.availability && emp.availability[sName] === 1) ? 'checked' : '';
            
            shiftHtml += `
                <label style="margin-right:10px; color: black;">
                    <input type="checkbox" class="avail-check" 
                           data-empid="${emp.id}" 
                           data-shiftname="${sName}" ${isChecked}>
                    ${sName}
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
async function setAllAvailability() {
    const checkboxes = document.querySelectorAll('#availabilityContainer .avail-check');
    const allUpdates = {};

    checkboxes.forEach(cb => {
        const empId = cb.getAttribute('data-empid');
        const shiftName = cb.getAttribute('data-shiftname');
        const isChecked = cb.checked ? 1 : 0; // 1 for available, 0 for unavailable

        if (!allUpdates[empId]) {
            allUpdates[empId] = { availability: {} };
        }
        allUpdates[empId].availability[shiftName] = isChecked;
    });

    if (Object.keys(allUpdates).length === 0) {
        alert("No availability data found to update.");
        return;
    }

    const response = await fetch('/update_availability', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            updates: allUpdates 
        })
    });

    const result = await response.json();
    if (result.status === "success") {
        document.getElementById('availabilityPopup').style.display = 'none';
        alert("Availability updated successfully!");
        location.reload(); 
    } else {
        alert("Failed to update availability: " + (result.message || JSON.stringify(result.detail)));
    }
}

function closeAvailabilityPopup() {
    const pop = document.getElementById('availabilityPopup');
    if (pop) pop.style.display = 'none';
}

/*
Submits a new vacation date range for an employee to ensure they aren't scheduled during that time.
*/
async function submitVacation() {
    const loggedInUserId = localStorage.getItem('userID') || getCookie('userID');
    if (!loggedInUserId) {
        alert("Please log in first.");
        return;
    }
    
    const empIdInput = document.getElementById('vac_emp_id').value;
    const startDateInput = document.getElementById('start_date').value;
    const endDateInput = document.getElementById('end_date').value;

    if (!empIdInput || !startDateInput || !endDateInput) {
        alert("Please fill out all vacation fields.");
        return;
    }

    const data = {
        owner_id: parseInt(getCookie('userID') || loggedInUserId, 10),
        emp_id: parseInt(empIdInput, 10),  // Links child vacation row to parent employee row
        start_date: startDateInput,
        end_date: endDateInput
    };

    const response = await fetch('/add_vacation', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();
    if (result.status === "success") {
        alert("Vacation added successfully!");
        location.reload(); // Refreshes table to show the new dates
    } else {
        alert(result.message || "Failed to add vacation.");
    }
}

let currentDeleteEmpId = null;

/*
Fetches an employee's current vacations and displays them in a selectable list for removal.
*/
async function remove_vacation() {
    const empId = document.getElementById('emp_id_vac').value;
    if (!empId) return alert("Please enter an Employee ID");

    const loggedInUserId = localStorage.getItem('userID');
    if (!loggedInUserId) return;

    const response = await fetch(`/get_employees/${loggedInUserId}`);
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
    const loggedInUserId = localStorage.getItem('userID');
    if (!loggedInUserId) return;

    const selectedRadio = document.querySelector('input[name="vacSelect"]:checked');
    if (!selectedRadio) {
        alert("Please select a vacation slot to delete.");
        return;
    }

    const data = { 
        owner_id: parseInt(getCookie('userID')),
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
        alert("Vacation removed safely.");
        location.reload();
    } else {
        alert(result.message || "Deletion error.");
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
        localStorage.setItem('userID', result.accountID);
        localStorage.setItem('username', result.username);

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
        localStorage.setItem('userID', result.accountID);
        localStorage.setItem('username', result.username)

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
        localStorage.setItem('userID', result.accountID);
        localStorage.setItem('username', document.getElementById('uname').value);


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
Clears user session memory and redirects back to the login screen
*/
function signOut() {
    localStorage.removeItem('userID');
    localStorage.removeItem('username');
    
    document.cookie = "userID=; expires=Thu, 01 Jan 2020 00:00:00 UTC; path=/;";

    window.location.href = 'homepage.html';
}


/*
Grabs the username out of browser memory and writes it directly into the HTML span tag
*/
async function loadUser(){
    const username = localStorage.getItem('username');
    const userContainer = document.getElementById('currentUser');
    
    if (userContainer) {
        userContainer.innerText = username ? username : "Not Logged In"; // If username is not retrieved then add "not logged in" to screen
    }
}

window.onload = function() {
    loadUser(); 
    fetch_employees();
    fetch_shifts();
    loadShiftCheckboxes();
};