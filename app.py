from flask import Flask, render_template_string, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import os

app = Flask(__name__)

LOGIN_URL = "https://asiet.etlab.app/user/login"

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

def get_attendance_data(username, password):
    print("Starting scraper in Docker container...")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-features=site-per-process")
    options.binary_location = "/opt/google/chrome/google-chrome"  # ✅ CHROME PATH

    driver = webdriver.Chrome(
        service=Service("/usr/bin/chromedriver"),  # ✅ CHROMEDRIVER PATH
        options=options
    )

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
        error_message = "An error occurred during scraping. It could be due to incorrect credentials or a change in the website structure."
    finally:
        print("Closing the scraper.")
        driver.quit()
    
    return scraped_data, error_message

# [Same HTML_TEMPLATE and route function from your original code]

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
