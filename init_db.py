from app import app, db
from models import User, Department, Category
import json
from datetime import datetime

def init_database():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create departments
        departments = [
            {'name': 'Hostel Department', 'head': 'Mr. Sharma', 'est_resolution_time': 2},
            {'name': 'Library Department', 'head': 'Ms. Patel', 'est_resolution_time': 3},
            {'name': 'Maintenance Department', 'head': 'Mr. Kumar', 'est_resolution_time': 1},
            {'name': 'IT Department', 'head': 'Mr. Reddy', 'est_resolution_time': 1},
            {'name': 'Mess Department', 'head': 'Mr. Singh', 'est_resolution_time': 1},
            {'name': 'Examination Department', 'head': 'Dr. Verma', 'est_resolution_time': 4},
            {'name': 'Accounts Department', 'head': 'Mrs. Gupta', 'est_resolution_time': 2},
            {'name': 'Transport Department', 'head': 'Mr. Khan', 'est_resolution_time': 2},
        ]
        
        for dept_data in departments:
            dept = Department.query.filter_by(name=dept_data['name']).first()
            if not dept:
                dept = Department(**dept_data)
                db.session.add(dept)
        
        db.session.commit()
        
        # Create categories with subcategories
        categories_data = [
            {
                'name': 'Hostel',
                'department': 'Hostel Department',
                'subcategories': ['Water Problem', 'Fan Issue', 'Bed Problem', 'Chair/Table Problem', 'Electricity', 'Washroom', 'Others']
            },
            {
                'name': 'Library',
                'department': 'Library Department',
                'subcategories': ['Book Availability', 'Issue/Return Problem', 'Library Timing', 'Computer System', 'Others']
            },
            {
                'name': 'Classroom',
                'department': 'Maintenance Department',
                'subcategories': ['Broken Bench', 'Projector Not Working', 'Smart Board Problem', 'Fan/Light Issue', 'AC Problem', 'Others']
            },
            {
                'name': 'Mess',
                'department': 'Mess Department',
                'subcategories': ['Food Quality', 'Drinking Water', 'Seat Problem', 'Hygiene', 'Menu Issue', 'Others']
            },
            {
                'name': 'Examination',
                'department': 'Examination Department',
                'subcategories': ['Admit Card Issue', 'Result Problem', 'Internal Marks', 'Exam Schedule', 'Hall Ticket', 'Others']
            },
            {
                'name': 'Fees',
                'department': 'Accounts Department',
                'subcategories': ['Payment Failed', 'Receipt Not Generated', 'Wrong Fee Amount', 'Scholarship Issue', 'Others']
            },
            {
                'name': 'Transport',
                'department': 'Transport Department',
                'subcategories': ['Bus Timing', 'Bus Route', 'Driver Issue', 'Bus Condition', 'Stop Location', 'Others']
            },
            {
                'name': 'IT Services',
                'department': 'IT Department',
                'subcategories': ['WiFi Issue', 'Email Problem', 'ERP Access', 'Computer Lab', 'Printer Issue', 'Others']
            }
        ]
        
        for cat_data in categories_data:
            dept = Department.query.filter_by(name=cat_data['department']).first()
            if dept:
                category = Category.query.filter_by(name=cat_data['name']).first()
                if not category:
                    category = Category(
                        name=cat_data['name'],
                        department_id=dept.id,
                        subcategories=json.dumps(cat_data['subcategories'])
                    )
                    db.session.add(category)
        
        # Create admin user
        admin = User.query.filter_by(registration_no='ADMIN001').first()
        if not admin:
            admin = User(
                registration_no='ADMIN001',
                name='System Administrator',
                email='admin@cutm.ac.in',
                mobile='1234567890',
                program='Administration',
                branch='Admin',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Create sample staff users
        staff_data = [
            {'reg_no': 'STAFF001', 'name': 'Rahul Sharma', 'email': 'rahul.sharma@cutm.ac.in', 'dept': 'Hostel Department'},
            {'reg_no': 'STAFF002', 'name': 'Priya Patel', 'email': 'priya.patel@cutm.ac.in', 'dept': 'Library Department'},
            {'reg_no': 'STAFF003', 'name': 'Amit Kumar', 'email': 'amit.kumar@cutm.ac.in', 'dept': 'IT Department'},
        ]
        
        for staff in staff_data:
            existing = User.query.filter_by(registration_no=staff['reg_no']).first()
            if not existing:
                user = User(
                    registration_no=staff['reg_no'],
                    name=staff['name'],
                    email=staff['email'],
                    mobile='9876543210',
                    program='Staff',
                    branch=staff['dept'],
                    role='staff'
                )
                user.set_password('staff123')
                db.session.add(user)
        
        # Create sample student
        student = User.query.filter_by(registration_no='CUTM2025001').first()
        if not student:
            student = User(
                registration_no='CUTM2025001',
                name='Aaham Student',
                email='aaham@cutm.ac.in',
                mobile='9999999999',
                program='B.Tech',
                branch='CSE',
                role='student'
            )
            student.set_password('student123')
            db.session.add(student)
        
        db.session.commit()
        print("Database initialized successfully!")

if __name__ == '__main__':
    init_database()