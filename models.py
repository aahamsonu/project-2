from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    registration_no = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    program = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, admin, staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    complaints = db.relationship('Complaint', back_populates='student', lazy=True, foreign_keys='Complaint.student_id')
    assigned_complaints = db.relationship('Complaint', back_populates='assigned_staff', lazy=True, foreign_keys='Complaint.assigned_to')
    notifications = db.relationship('Notification', back_populates='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(50), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Complaint Details
    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    image_path = db.Column(db.String(200))
    
    # Status & Tracking
    status = db.Column(db.String(50), default='Pending')
    priority = db.Column(db.String(20), default='Medium')
    
    # Assignment
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_department = db.Column(db.String(100))
    assigned_date = db.Column(db.DateTime)
    
    # Timeline
    estimated_completion_date = db.Column(db.DateTime)
    actual_completion_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Auto escalation
    escalated_at = db.Column(db.DateTime)
    escalation_count = db.Column(db.Integer, default=0)
    
    # Relationships
    student = db.relationship('User', back_populates='complaints', foreign_keys=[student_id])
    assigned_staff = db.relationship('User', back_populates='assigned_complaints', foreign_keys=[assigned_to])
    tracking_updates = db.relationship('ComplaintTracking', back_populates='complaint', lazy=True, cascade='all, delete-orphan')
    feedback = db.relationship('Feedback', back_populates='complaint', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='complaint', lazy=True, cascade='all, delete-orphan')
    
    def generate_complaint_id(self):
        """Generate unique complaint ID: CMP-YYYY-XXXXX"""
        year = datetime.now().year
        last_complaint = Complaint.query.filter(Complaint.complaint_id.like(f'CMP-{year}-%')).order_by(Complaint.id.desc()).first()
        
        if last_complaint:
            last_num = int(last_complaint.complaint_id.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f'CMP-{year}-{new_num:05d}'
    
    def check_escalation(self):
        """Check if complaint needs escalation"""
        if self.status in ['Resolved', 'Rejected']:
            return False
        
        if self.estimated_completion_date:
            time_passed = datetime.utcnow() - self.created_at
            if time_passed.total_seconds() > 48 * 3600:
                if not self.escalated_at or (datetime.utcnow() - self.escalated_at).total_seconds() > 24 * 3600:
                    self.status = 'Escalated'
                    self.escalated_at = datetime.utcnow()
                    self.escalation_count += 1
                    return True
        return False

class ComplaintTracking(db.Model):
    __tablename__ = 'complaint_tracking'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    remarks = db.Column(db.Text)
    updated_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    complaint = db.relationship('Complaint', back_populates='tracking_updates')

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    complaint = db.relationship('Complaint', back_populates='feedback')

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), default='info')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - using back_populates instead of backref
    user = db.relationship('User', back_populates='notifications')
    complaint = db.relationship('Complaint', back_populates='notifications')
    
    def __repr__(self):
        return f'<Notification {self.id}: {self.message[:20]}>'
    
    def to_dict(self):
        """Convert notification to dictionary"""
        from datetime import datetime
        now = datetime.utcnow()
        diff = now - self.created_at
        
        # Calculate time ago
        if diff.days > 365:
            time_ago = f"{diff.days // 365} years ago"
        elif diff.days > 30:
            time_ago = f"{diff.days // 30} months ago"
        elif diff.days > 0:
            time_ago = f"{diff.days} days ago"
        elif diff.seconds > 3600:
            time_ago = f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            time_ago = f"{diff.seconds // 60} minutes ago"
        else:
            time_ago = "just now"
        
        return {
            'id': self.id,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'complaint_id': self.complaint.complaint_id if self.complaint else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': time_ago
        }

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    head = db.Column(db.String(100))
    description = db.Column(db.Text)
    est_resolution_time = db.Column(db.Integer, default=2)
    
    # Relationships
    categories = db.relationship('Category', back_populates='department', lazy=True)
    
    def __repr__(self):
        return f'<Department {self.name}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    subcategories = db.Column(db.Text)
    
    # Relationships
    department = db.relationship('Department', back_populates='categories')