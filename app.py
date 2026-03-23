from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
from config import Config
from models import db, User, Complaint, ComplaintTracking, Feedback, Department, Category, Notification

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth_login'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper function for file upload
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ====================== CONTEXT PROCESSOR ======================
@app.context_processor
def utility_processor():
    from datetime import datetime
    import pytz
    
    def ist_time(dt=None):
        """Convert UTC to IST (Indian Standard Time)"""
        if dt is None:
            dt = datetime.utcnow()
        
        # Define timezones
        utc = pytz.timezone('UTC')
        ist = pytz.timezone('Asia/Kolkata')
        
        # If dt is naive (without timezone), assume it's UTC
        if dt.tzinfo is None:
            dt = utc.localize(dt)
        
        # Convert to IST
        ist_dt = dt.astimezone(ist)
        return ist_dt
    
    def format_ist(dt, format='%d %b %Y, %I:%M %p'):
        """Format datetime in IST"""
        if dt is None:
            return "N/A"
        try:
            ist_dt = ist_time(dt)
            return ist_dt.strftime(format)
        except:
            return str(dt)
    
    return {
        'now': datetime.now,
        'datetime': datetime,
        'ist_time': ist_time,
        'format_ist': format_ist,
        'current_time': ist_time()
    }

# ====================== NOTIFICATION FUNCTIONS ======================

def create_notification(user_id, complaint_id, message, type='info'):
    """Create a new notification for user"""
    notification = Notification(
        user_id=user_id,
        complaint_id=complaint_id,
        message=message,
        type=type
    )
    db.session.add(notification)
    db.session.commit()
    return notification

def notify_status_change(complaint, old_status, new_status, updated_by):
    """Send notification to student when complaint status changes"""
    
    # Different emoji/icons based on status
    if new_status == 'Resolved':
        message = f"✅ Great news! Your complaint #{complaint.complaint_id} has been RESOLVED!"
        type = 'success'
    elif new_status == 'Rejected':
        message = f"❌ Your complaint #{complaint.complaint_id} has been rejected. Please check remarks."
        type = 'danger'
    elif new_status == 'Escalated':
        message = f"⚠️ Your complaint #{complaint.complaint_id} has been ESCALATED to higher authority."
        type = 'warning'
    elif new_status == 'Assigned':
        message = f"📋 Your complaint #{complaint.complaint_id} has been assigned to {complaint.assigned_department}"
        type = 'info'
    elif new_status == 'Work in Progress':
        message = f"🔧 Good news! Work has started on your complaint #{complaint.complaint_id}"
        type = 'info'
    elif new_status == 'Under Review':
        message = f"👀 Your complaint #{complaint.complaint_id} is now under review"
        type = 'info'
    else:
        message = f"🔄 Your complaint #{complaint.complaint_id} status updated to: {new_status}"
        type = 'info'
    
    create_notification(
        user_id=complaint.student_id,
        complaint_id=complaint.id,
        message=message,
        type=type
    )

def time_ago(date):
    """Convert datetime to 'time ago' string"""
    now = datetime.utcnow()
    diff = now - date
    
    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    elif diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "just now"

# ====================== NOTIFICATION ROUTES ======================

@app.route('/notifications')
@login_required
def all_notifications():
    """View all notifications page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    # Get unread count
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return render_template('notifications/all.html',
                         notifications=notifications,
                         unread_count=unread_count)

@app.route('/api/notifications/all')
@login_required
def get_all_notifications_api():
    """API endpoint to get all notifications (for AJAX)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications.items],
        'total': notifications.total,
        'pages': notifications.pages,
        'current_page': notifications.page,
        'has_next': notifications.has_next,
        'has_prev': notifications.has_prev
    })

@app.route('/api/notifications')
@login_required
def get_notifications():
    """Get unread notifications for current user"""
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    return jsonify({
        'count': len(notifications),
        'notifications': [n.to_dict() for n in notifications]
    })

@app.route('/api/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Mark a single notification as read"""
    notification = Notification.query.get_or_404(notif_id)
    
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'All notifications marked as read'})

@app.route('/api/notifications/delete/<int:notif_id>', methods=['DELETE'])
@login_required
def delete_notification(notif_id):
    """Delete a notification"""
    notification = Notification.query.get_or_404(notif_id)
    
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/notifications/clear-all', methods=['POST'])
@login_required
def clear_all_notifications():
    """Delete all notifications for current user"""
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'All notifications cleared'})

@app.route('/api/notifications/check-new')
@login_required
def check_new_notifications():
    """Check if there are new notifications (for polling)"""
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({'new_count': count})

# ====================== AUTHENTICATION ROUTES ======================

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/auth/login', methods=['GET', 'POST'])
def auth_login():
    if request.method == 'POST':
        reg_no = request.form.get('registration_no')
        password = request.form.get('password')
        
        user = User.query.filter_by(registration_no=reg_no).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Login successful!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid registration number or password', 'danger')
    
    return render_template('auth/login.html')

@app.route('/auth/register', methods=['GET', 'POST'])
def auth_register():
    if request.method == 'POST':
        # Check if user already exists
        existing = User.query.filter(
            (User.registration_no == request.form.get('registration_no')) |
            (User.email == request.form.get('email'))
        ).first()
        
        if existing:
            flash('Registration number or email already exists!', 'danger')
            return redirect(url_for('auth_register'))
        
        # Create new user
        user = User(
            registration_no=request.form.get('registration_no'),
            name=request.form.get('name'),
            email=request.form.get('email'),
            mobile=request.form.get('mobile'),
            program=request.form.get('program'),
            branch=request.form.get('branch'),
            role='student'
        )
        user.set_password(request.form.get('password'))
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth_login'))
    
    return render_template('auth/register.html')

@app.route('/auth/logout')
@login_required
def auth_logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ====================== STUDENT ROUTES ======================

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    complaints = Complaint.query.filter_by(student_id=current_user.id).order_by(Complaint.created_at.desc()).limit(5).all()
    
    stats = {
        'total': Complaint.query.filter_by(student_id=current_user.id).count(),
        'pending': Complaint.query.filter_by(student_id=current_user.id, status='Pending').count(),
        'in_progress': Complaint.query.filter_by(student_id=current_user.id, status='Work in Progress').count(),
        'resolved': Complaint.query.filter_by(student_id=current_user.id, status='Resolved').count()
    }
    
    # Get unread notifications count
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    return render_template('student/dashboard.html', 
                         complaints=complaints, 
                         stats=stats,
                         unread_notifications=unread_notifications)

@app.route('/student/register-complaint', methods=['GET', 'POST'])
@login_required
def register_complaint():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    
    if request.method == 'POST':
        try:
            # Create new complaint
            complaint = Complaint(student_id=current_user.id)
            complaint.complaint_id = complaint.generate_complaint_id()
            
            # Get form data
            category = request.form.get('category')
            subcategory = request.form.get('subcategory')
            
            if not category or not subcategory:
                flash('Please select both category and subcategory', 'danger')
                return redirect(url_for('register_complaint'))
            
            complaint.category = category
            complaint.subcategory = subcategory
            complaint.description = request.form.get('description')
            complaint.location = request.form.get('location')
            
            # File upload
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{complaint.complaint_id}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    complaint.image_path = filename
            
            # Department
            category_obj = Category.query.filter_by(name=complaint.category).first()
            if category_obj and category_obj.department:
                complaint.assigned_department = category_obj.department.name
            
            # Save complaint first
            db.session.add(complaint)
            db.session.flush()
            
            # Add tracking
            tracking = ComplaintTracking(
                complaint_id=complaint.id,
                status='Complaint Submitted',
                remarks='Complaint registered successfully',
                updated_by='System'
            )
            db.session.add(tracking)
            
            db.session.commit()
            
            flash(f'Complaint registered successfully! Your Complaint ID: {complaint.complaint_id}', 'success')
            return redirect(url_for('my_complaints'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering complaint: {str(e)}', 'danger')
            return redirect(url_for('register_complaint'))
    
    return render_template('student/register_complaint.html', categories=categories)

@app.route('/student/my-complaints')
@login_required
def my_complaints():
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    complaints = Complaint.query.filter_by(student_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    return render_template('student/my_complaints.html', complaints=complaints, now=datetime.now)

@app.route('/student/complaint-tracking/<complaint_id>')
@login_required
def complaint_tracking(complaint_id):
    complaint = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()
    
    # Check if user owns this complaint
    if complaint.student_id != current_user.id and current_user.role not in ['admin', 'staff']:
        flash('You are not authorized to view this complaint', 'danger')
        return redirect(url_for('index'))
    
    tracking_history = ComplaintTracking.query.filter_by(complaint_id=complaint.id).order_by(ComplaintTracking.created_at).all()
    
    # Calculate if delayed
    is_delayed = False
    if complaint.estimated_completion_date and complaint.status != 'Resolved':
        is_delayed = datetime.utcnow() > complaint.estimated_completion_date
    
    return render_template('student/complaint_tracking.html', 
                         complaint=complaint, 
                         tracking=tracking_history,
                         is_delayed=is_delayed,
                         now=datetime.now)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.email = request.form.get('email')
        current_user.mobile = request.form.get('mobile')
        
        if request.form.get('new_password'):
            current_user.set_password(request.form.get('new_password'))
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_profile'))
    
    return render_template('student/profile.html')

@app.route('/student/feedback/<complaint_id>', methods=['POST'])
@login_required
def submit_feedback(complaint_id):
    complaint = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()
    
    if complaint.student_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    feedback = Feedback.query.filter_by(complaint_id=complaint.id).first()
    if not feedback:
        feedback = Feedback(complaint_id=complaint.id)
    
    feedback.rating = rating
    feedback.comment = comment
    db.session.add(feedback)
    db.session.commit()
    
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('complaint_tracking', complaint_id=complaint.complaint_id))

# ====================== COMPLAINT PROCESS ROUTE ======================

@app.route('/student/complaint-process-flow')
@login_required
def complaint_process_flow():
    """Display complaint process flowchart"""
    if current_user.role != 'student':
        return redirect(url_for('index'))
    
    return render_template('student/complaint_process.html')

# ====================== ADMIN ROUTES ======================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    # Statistics
    total_complaints = Complaint.query.count()
    pending_complaints = Complaint.query.filter_by(status='Pending').count()
    in_progress = Complaint.query.filter(Complaint.status.in_(['Assigned', 'Under Review', 'Work in Progress'])).count()
    resolved = Complaint.query.filter_by(status='Resolved').count()
    
    # Recent complaints
    recent_complaints = Complaint.query.order_by(Complaint.created_at.desc()).limit(10).all()
    
    # Department wise stats
    dept_stats = []
    departments = Department.query.all()
    for dept in departments:
        count = Complaint.query.filter_by(assigned_department=dept.name).count()
        resolved_count = Complaint.query.filter_by(assigned_department=dept.name, status='Resolved').count()
        dept_stats.append({
            'name': dept.name,
            'total': count,
            'resolved': resolved_count,
            'pending': count - resolved_count
        })
    
    return render_template('admin/dashboard.html',
                         total_complaints=total_complaints,
                         pending_complaints=pending_complaints,
                         in_progress=in_progress,
                         resolved=resolved,
                         recent_complaints=recent_complaints,
                         dept_stats=dept_stats)

@app.route('/admin/complaints')
@login_required
def admin_complaints():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status', 'all')
    dept_filter = request.args.get('department', 'all')
    
    query = Complaint.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if dept_filter != 'all':
        query = query.filter_by(assigned_department=dept_filter)
    
    complaints = query.order_by(Complaint.created_at.desc()).all()
    departments = Department.query.all()
    
    return render_template('admin/all_complaints.html', 
                         complaints=complaints, 
                         departments=departments,
                         current_status=status_filter,
                         current_dept=dept_filter,
                         now=datetime.now)

@app.route('/admin/complaint/<int:complaint_id>')
@login_required
def admin_view_complaint(complaint_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    tracking = ComplaintTracking.query.filter_by(complaint_id=complaint.id).order_by(ComplaintTracking.created_at).all()
    staff_users = User.query.filter_by(role='staff').all()
    departments = Department.query.all()
    
    return render_template('admin/view_complaint.html',
                         complaint=complaint,
                         tracking=tracking,
                         staff_users=staff_users,
                         departments=departments)

@app.route('/admin/assign-complaint/<int:complaint_id>', methods=['POST'])
@login_required
def admin_assign_complaint(complaint_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    department = request.form.get('department')
    assigned_to = request.form.get('assigned_to')
    estimated_days = request.form.get('estimated_days', 2)
    
    # Calculate estimated completion date
    est_date = datetime.utcnow() + timedelta(days=int(estimated_days))
    
    complaint.assigned_department = department
    complaint.assigned_to = int(assigned_to) if assigned_to else None
    complaint.estimated_completion_date = est_date
    complaint.status = 'Assigned'
    complaint.assigned_date = datetime.utcnow()
    
    # Add tracking
    tracking = ComplaintTracking(
        complaint_id=complaint.id,
        status='Assigned to Department',
        remarks=f'Assigned to {department}. Estimated completion: {est_date.strftime("%d %b %Y")}',
        updated_by=current_user.name
    )
    db.session.add(tracking)
    
    # Create notification for student
    message = f"📋 Your complaint #{complaint.complaint_id} has been assigned to {department}. Expected completion by {est_date.strftime('%d %b %Y')}"
    create_notification(complaint.student_id, complaint.id, message, 'info')
    
    db.session.commit()
    
    flash('Complaint assigned successfully!', 'success')
    return redirect(url_for('admin_view_complaint', complaint_id=complaint.id))

@app.route('/admin/update-status/<int:complaint_id>', methods=['POST'])
@login_required
def admin_update_status(complaint_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    new_status = request.form.get('status')
    remarks = request.form.get('remarks')
    
    old_status = complaint.status
    complaint.status = new_status
    
    if new_status == 'Resolved':
        complaint.actual_completion_date = datetime.utcnow()
    
    # Add tracking
    tracking = ComplaintTracking(
        complaint_id=complaint.id,
        status=new_status,
        remarks=remarks or f'Status updated from {old_status} to {new_status}',
        updated_by=current_user.name
    )
    db.session.add(tracking)
    
    # Create notification for student
    notify_status_change(complaint, old_status, new_status, current_user.name)
    
    db.session.commit()
    
    flash('Complaint status updated!', 'success')
    return redirect(url_for('admin_view_complaint', complaint_id=complaint.id))

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    # Get statistics
    total_complaints = Complaint.query.count()
    pending_complaints = Complaint.query.filter_by(status='Pending').count()
    in_progress = Complaint.query.filter(Complaint.status.in_(['Assigned', 'Under Review', 'Work in Progress'])).count()
    resolved = Complaint.query.filter_by(status='Resolved').count()
    
    # Monthly data for charts
    months = []
    complaint_counts = []
    resolved_counts = []
    
    for i in range(5, -1, -1):
        date = datetime.now() - timedelta(days=30*i)
        month_name = date.strftime('%b %Y')
        months.append(month_name)
        
        start_date = datetime(date.year, date.month, 1)
        if date.month == 12:
            end_date = datetime(date.year + 1, 1, 1)
        else:
            end_date = datetime(date.year, date.month + 1, 1)
        
        count = Complaint.query.filter(
            Complaint.created_at >= start_date,
            Complaint.created_at < end_date
        ).count()
        
        resolved_count = Complaint.query.filter(
            Complaint.created_at >= start_date,
            Complaint.created_at < end_date,
            Complaint.status == 'Resolved'
        ).count()
        
        complaint_counts.append(count)
        resolved_counts.append(resolved_count)
    
    # Department performance
    dept_performance = []
    departments = Department.query.all()
    
    for dept in departments:
        dept_complaints = Complaint.query.filter_by(assigned_department=dept.name).all()
        total = len(dept_complaints)
        resolved_dept = len([c for c in dept_complaints if c.status == 'Resolved'])
        pending = total - resolved_dept
        
        resolved_complaints = [c for c in dept_complaints 
                              if c.actual_completion_date and c.assigned_date]
        
        avg_time = 0
        if resolved_complaints:
            total_days = sum([(c.actual_completion_date - c.assigned_date).days 
                            for c in resolved_complaints])
            avg_time = total_days / len(resolved_complaints)
        
        dept_performance.append({
            'name': dept.name,
            'total': total,
            'resolved': resolved_dept,
            'pending': pending,
            'avg_time': round(avg_time, 1)
        })
    
    return render_template('admin/analytics.html',
                         total_complaints=total_complaints,
                         pending_complaints=pending_complaints,
                         in_progress=in_progress,
                         resolved=resolved,
                         months=months,
                         complaint_counts=complaint_counts,
                         resolved_counts=resolved_counts,
                         dept_performance=dept_performance)

@app.route('/admin/overdue-complaints')
@login_required
def admin_overdue_complaints():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    complaints = Complaint.query.filter(Complaint.status.notin_(['Resolved', 'Rejected'])).all()
    overdue = []
    
    for complaint in complaints:
        if complaint.estimated_completion_date:
            if datetime.utcnow() > complaint.estimated_completion_date:
                overdue.append(complaint)
                complaint.check_escalation()
    
    db.session.commit()
    
    return render_template('admin/overdue_complaints.html', complaints=overdue, datetime=datetime)

# ====================== STAFF ROUTES ======================

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'staff':
        return redirect(url_for('index'))
    
    assigned_complaints = Complaint.query.filter_by(assigned_to=current_user.id).order_by(Complaint.created_at.desc()).all()
    
    stats = {
        'total': len(assigned_complaints),
        'pending': len([c for c in assigned_complaints if c.status in ['Assigned', 'Under Review']]),
        'in_progress': len([c for c in assigned_complaints if c.status == 'Work in Progress']),
        'resolved': len([c for c in assigned_complaints if c.status == 'Resolved'])
    }
    
    return render_template('staff/dashboard.html', complaints=assigned_complaints, stats=stats)

@app.route('/staff/update-status/<int:complaint_id>', methods=['POST'])
@login_required
def staff_update_status(complaint_id):
    if current_user.role != 'staff':
        return redirect(url_for('index'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if complaint.assigned_to != current_user.id:
        flash('You are not authorized to update this complaint', 'danger')
        return redirect(url_for('staff_dashboard'))
    
    new_status = request.form.get('status')
    remarks = request.form.get('remarks')
    
    old_status = complaint.status
    complaint.status = new_status
    
    if new_status == 'Resolved':
        complaint.actual_completion_date = datetime.utcnow()
    
    tracking = ComplaintTracking(
        complaint_id=complaint.id,
        status=new_status,
        remarks=remarks or f'Status updated by {current_user.name}',
        updated_by=current_user.name
    )
    db.session.add(tracking)
    
    notify_status_change(complaint, old_status, new_status, current_user.name)
    
    db.session.commit()
    
    flash('Status updated successfully!', 'success')
    return redirect(url_for('staff_dashboard'))

# ====================== API ROUTES ======================

@app.route('/api/subcategories/<category>')
def get_subcategories(category):
    cat = Category.query.filter_by(name=category).first()
    if cat and cat.subcategories:
        return jsonify({'subcategories': json.loads(cat.subcategories)})
    return jsonify({'subcategories': []})

@app.route('/api/check-escalations')
def check_escalations():
    """Background task to check for escalations"""
    if request.args.get('key') != 'cron-job-secret':
        return 'Unauthorized', 401
    
    complaints = Complaint.query.filter(Complaint.status.notin_(['Resolved', 'Rejected'])).all()
    escalated = []
    
    for complaint in complaints:
        if complaint.check_escalation():
            escalated.append(complaint.complaint_id)
    
    db.session.commit()
    return jsonify({'escalated': escalated, 'count': len(escalated)})

# ====================== ERROR HANDLERS ======================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)