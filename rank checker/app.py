from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
import re
import json
import os
import pandas as pd
import traceback
from werkzeug.utils import secure_filename
import io
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this-in-production'

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
DATA_FILE = 'colleges_data.json'
ADMIN_CREDENTIALS_FILE = 'admin_credentials.json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Default admin credentials (change these in production)
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

def load_admin_credentials():
    """Load admin credentials from file or create default"""
    try:
        if os.path.exists(ADMIN_CREDENTIALS_FILE):
            with open(ADMIN_CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default credentials
            salt = secrets.token_hex(16)
            hashed_password = hashlib.sha256((DEFAULT_ADMIN_PASSWORD + salt).encode()).hexdigest()
            credentials = {
                "username": DEFAULT_ADMIN_USERNAME,
                "password_hash": hashed_password,
                "salt": salt
            }
            with open(ADMIN_CREDENTIALS_FILE, 'w') as f:
                json.dump(credentials, f, indent=2)
            return credentials
    except Exception as e:
        print(f"Error loading admin credentials: {e}")
        return None

def verify_password(password, stored_hash, salt):
    """Verify password against stored hash"""
    try:
        hashed_input = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed_input == stored_hash
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def admin_required(f):
    """Decorator to require admin authentication"""
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in as admin to access this page', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Load data functions (keep your existing code)
def load_colleges_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"institutes": []}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {"institutes": []}

def save_colleges_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

# Initialize data
colleges_data = load_colleges_data()
admin_credentials = load_admin_credentials()

# Process data with error handling
def process_colleges_data():
    colleges = []
    try:
        for institute in colleges_data["institutes"]:
            for branch in institute.get("branches", []):
                college = {
                    "name": institute["name"],
                    "inst_code": institute["inst_code"],
                    "place": institute["place"],
                    "branch": branch["name"],
                    "branch_code": branch["branch_code"],
                    "tuition_fee": branch.get("tuition_fee", "Not Available"),
                    "affiliated_to": branch.get("affiliated_to", "Not Specified"),
                    "cutoffs": branch.get("cutoffs", {}),
                    "college_type": institute["college_type"],
                    "co_ed": institute["co_ed"],
                    "year_established": institute.get("year_established", "N/A"),
                    "website": institute.get("website", ""),
                    "facilities": ", ".join(institute.get("facilities", [])),
                    "seats": branch.get("seats", "N/A"),
                    "duration": branch.get("duration", "N/A")
                }
                colleges.append(college)
        return colleges
    except Exception as e:
        print(f"Error processing college data: {e}")
        return []

colleges = process_colleges_data()

# Categories mapping
categories = {
    "OC": ["OC_BOYS", "OC_GIRLS"],
    "BC-A": ["BC_A_BOYS", "BC_A_GIRLS"],
    "BC-B": ["BC_B_BOYS", "BC_B_GIRLS"],
    "BC-C": ["BC_C_BOYS", "BC_C_GIRLS"],
    "BC-D": ["BC_D_BOYS", "BC_D_GIRLS"],
    "BC-E": ["BC_E_BOYS", "BC_E_GIRLS"],
    "SC": ["SC_BOYS", "SC_GIRLS"],
    "ST": ["ST_BOYS", "ST_GIRLS"],
    "EWS": ["EWS_GEN_OU", "EWS_GIRLS_OU"]
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_college_stats():
    """Get statistics about colleges data"""
    total_colleges = len(colleges_data["institutes"])
    total_branches = sum(len(institute.get("branches", [])) for institute in colleges_data["institutes"])
    return total_colleges, total_branches

def create_template_excel():
    """Create and return an Excel template file in the specified format"""
    try:
        # Create sample template data in the exact order specified
        template_data = {
            'Inst Code': ['AARM', 'AARM', 'COLLEGE2'],
            'Institute Name': [
                'AAR MAHAVEER ENGINEERING COLLEGE', 
                'AAR MAHAVEER ENGINEERING COLLEGE', 
                'ANOTHER ENGINEERING COLLEGE'
            ],
            'Place': ['BANDLAGUDA', 'BANDLAGUDA', 'HYDERABAD'],
            'Dist Code': ['HYD', 'HYD', 'RNG'],
            'Co Education': ['COED', 'COED', 'COED'],
            'College Type': ['PVT', 'PVT', 'PVT'],
            'Year of Estab': [2010, 2010, 2015],
            'Branch Code': ['CSE', 'ECE', 'CSE'],
            'Branch Name': [
                'COMPUTER SCIENCE AND ENGINEERING', 
                'ELECTRONICS AND COMMUNICATION ENGINEERING',
                'COMPUTER SCIENCE AND ENGINEERING'
            ],
            'OC BOYS': [26588, 54242, 15000],
            'OC GIRLS': [29938, 54242, 18000],
            'BC_A BOYS': [52666, 101521, 25000],
            'BC_A GIRLS': [62471, 101521, 28000],
            'BC_B BOYS': [38568, 76946, 22000],
            'BC_B GIRLS': [38568, 85866, 24000],
            'BC_C BOYS': [26588, 54242, 20000],
            'BC_C GIRLS': [108434, 54242, 23000],
            'BC_D BOYS': [38368, 75251, 21000],
            'BC_D GIRLS': [38368, 82142, 23500],
            'BC_E BOYS': [53852, 134835, 30000],
            'BC_E GIRLS': [53852, 134835, 32000],
            'SC BOYS': [70513, 125763, 45000],
            'SC GIRLS': [75671, 125763, 48000],
            'ST BOYS': [70477, 119658, 44000],
            'ST GIRLS': [83930, 174032, 47000],
            'EWS GEN OU': [30771, 82588, 19000],
            'EWS GIRLS OU': [38034, 82588, 21000],
            'Tuition Fee': [60000, 55000, 50000],
            'Affiliated To': ['JNTUH', 'JNTUH', 'JNTUK']
        }
        
        # Create DataFrame with the exact column order
        df = pd.DataFrame(template_data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Template', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Template']
            
            # Style the header row
            from openpyxl.styles import Font, PatternFill, Alignment
            header_font = Font(bold=True, color="FFFFFF", size=12)
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Set row height for header
            worksheet.row_dimensions[1].height = 25
        
        output.seek(0)
        return output
        
    except Exception as e:
        print(f"Error creating template: {e}")
        traceback.print_exc()
        return None

def process_excel_file(filepath):
    """
    Process Excel file and return (success, message)
    Handles the specific column format provided
    """
    try:
        print(f"Processing Excel file: {filepath}")
        
        # Read Excel file
        df = pd.read_excel(filepath)
        print(f"Excel file loaded successfully. Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        # Map the expected column names to our internal format
        column_mapping = {
            'Inst Code': 'inst_code',
            'Institute Name': 'institute_name', 
            'Place': 'place',
            'Dist Code': 'dist_code',
            'Co Education': 'co_ed',
            'College Type': 'college_type',
            'Year of Estab': 'year_established',
            'Branch Code': 'branch_code',
            'Branch Name': 'branch_name',
            'OC BOYS': 'OC_BOYS',
            'OC GIRLS': 'OC_GIRLS',
            'BC_A BOYS': 'BC_A_BOYS',
            'BC_A GIRLS': 'BC_A_GIRLS',
            'BC_B BOYS': 'BC_B_BOYS',
            'BC_B GIRLS': 'BC_B_GIRLS',
            'BC_C BOYS': 'BC_C_BOYS',
            'BC_C GIRLS': 'BC_C_GIRLS',
            'BC_D BOYS': 'BC_D_BOYS',
            'BC_D GIRLS': 'BC_D_GIRLS',
            'BC_E BOYS': 'BC_E_BOYS',
            'BC_E GIRLS': 'BC_E_GIRLS',
            'SC BOYS': 'SC_BOYS',
            'SC GIRLS': 'SC_GIRLS',
            'ST BOYS': 'ST_BOYS',
            'ST GIRLS': 'ST_GIRLS',
            'EWS GEN OU': 'EWS_GEN_OU',
            'EWS GIRLS OU': 'EWS_GIRLS_OU',
            'Tuition Fee': 'tuition_fee',
            'Affiliated To': 'affiliated_to'
        }
        
        # Rename columns to internal format
        df_renamed = df.rename(columns=column_mapping)
        
        # Check required columns
        required_columns = ['inst_code', 'institute_name', 'place', 'dist_code', 'co_ed', 
                           'college_type', 'branch_code', 'branch_name', 'tuition_fee']
        
        missing_columns = [col for col in required_columns if col not in df_renamed.columns]
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Convert DataFrame to our required format
        institutes = []
        
        # Group by institute
        for inst_code, group in df_renamed.groupby('inst_code'):
            print(f"Processing institute: {inst_code}")
            
            institute_data = {
                "inst_code": inst_code,
                "name": group['institute_name'].iloc[0],
                "place": group['place'].iloc[0],
                "dist_code": group['dist_code'].iloc[0],
                "co_ed": group['co_ed'].iloc[0],
                "college_type": group['college_type'].iloc[0],
                "year_established": int(group['year_established'].iloc[0]) if 'year_established' in group.columns and pd.notna(group['year_established'].iloc[0]) else 0,
                "branches": []
            }
            
            # Process branches
            branch_count = 0
            for _, row in group.iterrows():
                branch_data = {
                    "branch_code": row['branch_code'],
                    "name": row['branch_name'],
                    "tuition_fee": int(row['tuition_fee']) if pd.notna(row['tuition_fee']) else 0,
                    "affiliated_to": row.get('affiliated_to', 'JNTUH') if 'affiliated_to' in row and pd.notna(row.get('affiliated_to')) else 'JNTUH',
                    "cutoffs": {}
                }
                
                # Add cutoff ranks
                cutoff_columns = [col for col in row.index if col in [
                    'OC_BOYS', 'OC_GIRLS', 'BC_A_BOYS', 'BC_A_GIRLS', 
                    'BC_B_BOYS', 'BC_B_GIRLS', 'BC_C_BOYS', 'BC_C_GIRLS',
                    'BC_D_BOYS', 'BC_D_GIRLS', 'BC_E_BOYS', 'BC_E_GIRLS',
                    'SC_BOYS', 'SC_GIRLS', 'ST_BOYS', 'ST_GIRLS',
                    'EWS_GEN_OU', 'EWS_GIRLS_OU'
                ]]
                
                for col in cutoff_columns:
                    if col in row and pd.notna(row[col]):
                        try:
                            branch_data["cutoffs"][col] = int(row[col])
                        except (ValueError, TypeError):
                            try:
                                clean_value = str(row[col]).strip()
                                if clean_value and clean_value != 'nan':
                                    branch_data["cutoffs"][col] = int(float(clean_value))
                            except:
                                branch_data["cutoffs"][col] = 0
                
                institute_data["branches"].append(branch_data)
                branch_count += 1
            
            institutes.append(institute_data)
            print(f"Added institute {inst_code} with {branch_count} branches")
        
        print(f"Processed {len(institutes)} institutes total")
        
        # Update the data
        colleges_data["institutes"] = institutes
        
        # Save to JSON file
        if save_colleges_data(colleges_data):
            return True, f"Successfully processed {len(institutes)} institutes with {sum(len(inst['branches']) for inst in institutes)} branches"
        else:
            return False, "Failed to save data to file"
        
    except Exception as e:
        error_msg = f"Error processing Excel file: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return False, error_msg

# Public Routes
@app.route('/')
def index():
    try:
        branch_names = sorted(list(set(college["branch"] for college in colleges)))
        return render_template('index.html', 
                            categories=categories.keys(), 
                            branch_names=branch_names,
                            college_types=sorted(list(set(college["college_type"] for college in colleges))))
    except Exception as e:
        print(f"Error in index route: {e}")
        return "An error occurred", 500

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid or missing JSON data"}), 400
            
        rank_str = data.get('rank', '')
        selected_category = data.get('category', '')
        selected_branch = data.get('branch', '')
        college_type = data.get('college_type', '')
        
        if not rank_str:
            return jsonify({"error": "Rank parameter is required"}), 400
            
        try:
            rank = int(rank_str)
            if rank <= 0:
                return jsonify({"error": "Rank must be a positive integer"}), 400
        except ValueError:
            return jsonify({"error": "Rank must be a valid integer"}), 400
        
        # Calculate bounds
        threshold = max(1000, int(rank * 0.1))
        lower_bound = max(1, rank - threshold)
        upper_bound = rank + threshold
        
        results = []
        
        for college in colleges:
            # Apply filters
            if selected_branch and college["branch"] != selected_branch:
                continue
            if college_type and college["college_type"] != college_type:
                continue
                
            cutoffs = college.get("cutoffs", {})
            
            if selected_category:
                # Search only in selected category
                category_keys = categories.get(selected_category, [])
                for cutoff_key in category_keys:
                    if cutoff_key in cutoffs:
                        try:
                            cutoff_rank = int(cutoffs[cutoff_key])
                            if lower_bound <= cutoff_rank <= upper_bound:
                                result = create_result(college, cutoff_rank, selected_category, cutoff_key)
                                results.append(result)
                        except (ValueError, TypeError):
                            continue
            else:
                # Search in all categories
                for category, cutoff_keys in categories.items():
                    for cutoff_key in cutoff_keys:
                        if cutoff_key in cutoffs:
                            try:
                                cutoff_rank = int(cutoffs[cutoff_key])
                                if lower_bound <= cutoff_rank <= upper_bound:
                                    result = create_result(college, cutoff_rank, category, cutoff_key)
                                    results.append(result)
                            except (ValueError, TypeError):
                                continue
        
        # Sort results by proximity to the input rank
        results.sort(key=lambda x: abs(x["cutoff_rank"] - rank))
        
        return jsonify({
            "success": True,
            "count": len(results),
            "results": results
        })
        
    except Exception as e:
        app.logger.error(f"Error in search route: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "Please try again later"
        }), 500

def create_result(college, cutoff_rank, category, cutoff_key):
    """Helper function to create a result dictionary"""
    return {
        "name": college.get("name", ""),
        "inst_code": college.get("inst_code", ""),
        "branch": college.get("branch", ""),
        "branch_code": college.get("branch_code", ""),
        "cutoff_rank": cutoff_rank,
        "category": category,
        "gender": "GIRLS" if "GIRLS" in cutoff_key else "BOYS",
        "tuition_fee": college.get("tuition_fee", 0),
        "affiliated_to": college.get("affiliated_to", ""),
        "college_type": college.get("college_type", ""),
        "co_ed": college.get("co_ed", ""),
        "place": college.get("place", ""),
        "year_established": college.get("year_established", ""),
        "website": college.get("website", ""),
        "facilities": college.get("facilities", ""),
        "seats": college.get("seats", ""),
        "duration": college.get("duration", "")
    }

# Admin Authentication Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # If already logged in, redirect to admin dashboard
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('admin_login.html')
        
        # Verify credentials
        if (admin_credentials and 
            username == admin_credentials.get('username') and 
            verify_password(password, admin_credentials.get('password_hash'), admin_credentials.get('salt'))):
            
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('admin_login.html')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('admin_login'))

# Admin Routes (Protected)
@app.route('/admin')
@admin_required
def admin_dashboard():
    total_colleges, total_branches = get_college_stats()
    return render_template('admin.html', 
                         total_colleges=total_colleges,
                         total_branches=total_branches,
                         colleges_data=colleges_data,
                         username=session.get('admin_username'))

@app.route('/admin/upload', methods=['GET', 'POST'])
@admin_required
def admin_upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                success, message = process_excel_file(filepath)
                
                if success:
                    flash(f'Data uploaded successfully! {message}', 'success')
                    global colleges_data, colleges
                    colleges_data = load_colleges_data()
                    colleges = process_colleges_data()
                else:
                    flash(f'Error processing Excel file: {message}', 'error')
                
                if os.path.exists(filepath):
                    os.remove(filepath)
                
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload Excel files only (.xlsx, .xls)', 'error')
            return redirect(request.url)
    
    total_colleges, total_branches = get_college_stats()
    return render_template('upload.html',
                         total_colleges=total_colleges,
                         total_branches=total_branches,
                         colleges_data=colleges_data)

@app.route('/admin/download-template')
@admin_required
def download_template():
    try:
        template_file = create_template_excel()
        if template_file:
            return send_file(
                template_file,
                as_attachment=True,
                download_name='EAPCET_College_Data_Template.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('Error creating template file', 'error')
            return redirect(url_for('admin_upload'))
    except Exception as e:
        flash(f'Error downloading template: {str(e)}', 'error')
        return redirect(url_for('admin_upload'))

@app.route('/admin/data')
@admin_required
def admin_data():
    return jsonify(colleges_data)

@app.route('/admin/clear', methods=['POST'])
@admin_required
def admin_clear():
    try:
        colleges_data["institutes"] = []
        if save_colleges_data(colleges_data):
            global colleges
            colleges = process_colleges_data()
            flash('All data cleared successfully!', 'success')
        else:
            flash('Error clearing data', 'error')
    except Exception as e: 
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/stats')
@admin_required
def admin_stats():
    total_colleges, total_branches = get_college_stats()
    return jsonify({
        'total_colleges': total_colleges,
        'total_branches': total_branches,
        'data_entries': len(colleges_data['institutes'])
    })

if __name__ == '__main__':
    app.run(debug=True)