# app.py
# Final version for Render deployment.

from flask import Flask, render_template_string, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import os

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Configuration ---
LOGIN_URL = "https://asiet.etlab.app/user/login"

# --- Attendance Calculation Functions ---
def calculate_current_percentage(attended, total):
    if total == 0: return 0.0
    return (attended / total) * 100

def classes_needed_for_target(attended, total, target_percentage):
    if calculate_current_percentage(attended, total) >= target_percentage: return 0
    classes_to_attend = 0
    while True:
        classes_to_attend += 1
        new_attended = attended + classes_to_attend
        new_total = total + classes_to_attend
        if calculate_current_percentage(new_attended, new_total) >= target_percentage:
            return classes_to_attend

def classes_to_bunk(attended, total, target_percentage):
    if calculate_current_percentage(attended, total) < target_percentage: return 0
    bunkable_classes = 0
    while True:
        new_total = total + bunkable_classes + 1
        if calculate_current_percentage(attended, new_total) < target_percentage:
            return bunkable_classes
        bunkable_classes += 1

# --- Web Scraping Function ---
def get_attendance_data(username, password):
    print("Starting scraper in Docker container...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # --- THIS LINE IS THE FIX FOR THE RUNTIME ERROR ---
    options.add_argument("--disable-features=site-per-process")
    
    # This is how Selenium finds the pre-installed Chrome in the container
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 25)
    scraped_data = {}
    error_message = None

    try:
        print(f"Navigating to login page: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        username_field = wait.until(EC.presence_of_element_located((By.ID, "LoginForm_username")))
        username_field.send_keys(username)
        password_field = driver.find_element(By.ID, "LoginForm_password")
        password_field.send_keys(password)
        login_button = driver.find_element(By.NAME, "yt0")
        login_button.click()
        print("Clicked login button.")
        
        wait.until(EC.presence_of_element_located((By.ID, "breadcrumb")))
        print("Successfully logged in.")
        attendance_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Attendance")))
        attendance_link.click()
        print("Clicked 'Attendance' link.")
        
        wait.until(EC.presence_of_element_located((By.ID, "itsthetable")))
        print("Attendance table found. Parsing data...")
        time.sleep(2)

        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        
        subject_attendance = {}
        attendance_table = soup.find('table', id='itsthetable')
        
        if attendance_table:
            period_cells = attendance_table.find_all('td', class_=['present', 'absent'])
            for cell in period_cells:
                link = cell.find('a')
                if link:
                    subject_name = link.find(text=True, recursive=False).strip()
                    if subject_name:
                        if subject_name not in subject_attendance:
                            subject_attendance[subject_name] = {'attended': 0, 'total': 0}
                        subject_attendance[subject_name]['total'] += 1
                        if 'present' in cell.get('class', []):
                            subject_attendance[subject_name]['attended'] += 1
            scraped_data = subject_attendance
            print("Successfully parsed all attendance data.")
        else:
            error_message = "Could not find the attendance table after logging in."

    except Exception as e:
        print(f"An error occurred: {e}")
        error_message = f"An error occurred during scraping. It could be due to incorrect credentials or a change in the website's structure. Please check your details and try again."
    finally:
        print("Closing the scraper.")
        driver.quit()
    
    return scraped_data, error_message

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Attendance Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .card {
            background-color: white;
            border-radius: 0.75rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .loader {
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 2rem auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">
    <div class="container mx-auto p-4 md:p-8 max-w-4xl">
        <header class="text-center mb-8">
            <h1 class="text-4xl font-bold text-gray-900">College Attendance Tracker</h1>
            <p class="text-lg text-gray-600 mt-2">Enter your credentials to check your attendance status.</p>
        </header>
        <div class="card p-8 mb-8">
            <form method="post" id="attendance-form">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label for="username" class="block text-sm font-medium text-gray-700 mb-1">Username</label>
                        <input type="text" name="username" id="username" required class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition">
                    </div>
                    <div>
                        <label for="password" class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                        <input type="password" name="password" id="password" required class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition">
                    </div>
                </div>
                <div class="mt-6">
                    <label for="target" class="block text-sm font-medium text-gray-700 mb-1">Target Attendance (%)</label>
                    <input type="number" name="target" id="target" value="75" required class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition">
                </div>
                <div class="mt-8 text-center">
                    <button type="submit" class="w-full md:w-auto bg-blue-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-blue-700 transition-transform transform hover:scale-105 focus:outline-none focus:ring-4 focus:ring-blue-300">
                        Fetch Attendance
                    </button>
                </div>
            </form>
        </div>
        <div id="loader-container" class="hidden text-center">
            <div class="loader"></div>
            <p class="text-gray-600">Fetching your data... This might take a moment.</p>
        </div>
        <div id="results-container">
            {% if error %}
                <div class="card p-6 bg-red-100 border border-red-300 text-red-800">
                    <h3 class="font-bold text-lg">Error</h3>
                    <p>{{ error }}</p>
                </div>
            {% endif %}
            {% if results %}
                <h2 class="text-2xl font-bold text-center mb-6">Attendance Report (Target: {{ target }}%)</h2>
                <div class="overflow-x-auto">
                    <table class="min-w-full bg-white rounded-lg shadow">
                        <thead class="bg-gray-200">
                            <tr>
                                <th class="text-left font-semibold text-gray-700 p-4">Subject</th>
                                <th class="text-center font-semibold text-gray-700 p-4">Status</th>
                                <th class="text-center font-semibold text-gray-700 p-4">Percentage</th>
                                <th class="text-left font-semibold text-gray-700 p-4">Action Required</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">
                            {% for subject, data in results.items() %}
                                <tr>
                                    <td class="p-4 font-medium">{{ subject }}</td>
                                    <td class="p-4 text-center">{{ data.attended }} / {{ data.total }}</td>
                                    <td class="p-4 text-center">
                                        <span class="font-bold {% if data.percentage < target %}text-red-600{% else %}text-green-600{% endif %}">
                                            {{ "%.2f"|format(data.percentage) }}%
                                        </span>
                                    </td>
                                    <td class="p-4">
                                        {% if data.percentage < target %}
                                            <span class="text-red-600">Attend next <strong>{{ data.needed }}</strong> class(es)</span>
                                        {% else %}
                                            <span class="text-green-600">You can bunk <strong>{{ data.bunks_available }}</strong> class(es)</span>
                                        {% endif %}
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% endif %}
        </div>
    </div>
    <script>
        document.getElementById('attendance-form').addEventListener('submit', function() {
            document.getElementById('loader-container').classList.remove('hidden');
            document.getElementById('results-container').innerHTML = '';
        });
    </script>
</body>
</html>
"""

# --- Flask Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        target = float(request.form.get('target', 75.0))
        course_data, error_message = get_attendance_data(username, password)
        if error_message:
            return render_template_string(HTML_TEMPLATE, error=error_message)
        results = {}
        for subject, data in course_data.items():
            attended = data['attended']
            total = data['total']
            percentage = calculate_current_percentage(attended, total)
            results[subject] = {
                'attended': attended,
                'total': total,
                'percentage': percentage,
                'needed': classes_needed_for_target(attended, total, target) if percentage < target else 0,
                'bunks_available': classes_to_bunk(attended, total, target) if percentage >= target else 0
            }
        return render_template_string(HTML_TEMPLATE, results=results, target=target)
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
