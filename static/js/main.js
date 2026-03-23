// Main JavaScript for CUTM Complaint Portal

// Notification System
// Notification Manager Class को अपडेट करें

class NotificationManager {
    constructor() {
        this.checkInterval = 30000;
        this.soundPlayed = false;
        this.init();
    }
    
    init() {
        this.loadNotifications();
        this.startPolling();
        this.setupEventListeners();
    }
    
    loadNotifications() {
        $.getJSON('/api/notifications', (data) => {
            this.updateNotificationBadge(data.count);
            this.renderNotifications(data.notifications);
        }).fail(() => {
            console.log('Failed to load notifications');
        });
    }
    
    updateNotificationBadge(count) {
        const badge = $('.notification-badge');
        if (count > 0) {
            badge.text(count).show();
            $('.mark-all-read').show();
            
            // Update page title
            document.title = `(${count}) CUTM Complaint Portal`;
            
            // Animate bell
            $('#notificationBell i').addClass('bell-animate');
            setTimeout(() => {
                $('#notificationBell i').removeClass('bell-animate');
            }, 1000);
        } else {
            badge.hide();
            $('.mark-all-read').hide();
            document.title = 'CUTM Complaint Portal';
        }
    }
    
    renderNotifications(notifications) {
        const list = $('.notification-list');
        
        if (notifications.length === 0) {
            list.html('<div class="text-center text-muted py-4"><i class="fas fa-bell-slash fa-2x mb-2"></i><br>No new notifications</div>');
            return;
        }
        
        let html = '';
        notifications.forEach(notif => {
            const bgClass = this.getNotificationClass(notif.type);
            html += `
                <div class="dropdown-item notification-item ${bgClass}" data-id="${notif.id}" data-complaint="${notif.complaint_id}">
                    <div class="d-flex align-items-start">
                        <div class="flex-grow-1">
                            <p class="mb-1 small">${notif.message}</p>
                            <small class="text-muted"><i class="far fa-clock me-1"></i>${notif.time_ago}</small>
                        </div>
                        <button class="btn btn-sm btn-link mark-read p-0 ms-2" onclick="event.stopPropagation(); markNotificationRead(${notif.id})">
                            <i class="fas fa-check-circle text-success"></i>
                        </button>
                    </div>
                </div>
            `;
        });
        
        // Add "View All" link at bottom
        html += `
            <div class="dropdown-divider"></div>
            <div class="text-center p-2">
                <a href="{{ url_for('all_notifications') }}" class="text-decoration-none small">
                    <i class="fas fa-bell me-1"></i>View All Notifications
                </a>
            </div>
        `;
        
        list.html(html);
        
        // Play sound if new notifications
        if (notifications.length > 0 && !this.soundPlayed) {
            this.playSound();
            this.soundPlayed = true;
            setTimeout(() => { this.soundPlayed = false; }, 5000);
        }
    }
    
    getNotificationClass(type) {
        switch(type) {
            case 'success': return 'notification-success';
            case 'danger': return 'notification-danger';
            case 'warning': return 'notification-warning';
            default: return 'notification-info';
        }
    }
    
    playSound() {
        // Optional: Play sound
        // const audio = new Audio('/static/sounds/notification.mp3');
        // audio.play().catch(e => console.log('Sound play failed:', e));
    }
    
    startPolling() {
        setInterval(() => {
            this.checkNewNotifications();
        }, this.checkInterval);
    }
    
    checkNewNotifications() {
        $.getJSON('/api/notifications/check-new', (data) => {
            if (data.new_count > 0) {
                this.loadNotifications();
            }
        });
    }
    
    setupEventListeners() {
        // Mark all as read
        $('.mark-all-read').click(() => {
            $.post('/api/notifications/mark-all-read', () => {
                this.loadNotifications();
                showToast('All notifications marked as read', 'success');
            });
        });
        
        // Show notifications dropdown
        $('#notificationBell').click(() => {
            this.loadNotifications();
        });
        
        // Click on notification to go to complaint
        $(document).on('click', '.notification-item', function(e) {
            if (!$(e.target).closest('.mark-read').length) {
                const complaintId = $(this).data('complaint');
                if (complaintId) {
                    window.location.href = `/student/complaint-tracking/${complaintId}`;
                }
            }
        });
    }
}

// Global function to mark notification read
window.markNotificationRead = function(id) {
    $.post(`/api/notifications/mark-read/${id}`, () => {
        if (window.notificationManager) {
            window.notificationManager.loadNotifications();
        }
    });
};

// Show toast message
window.showToast = function(message, type = 'info') {
    const toast = `
        <div class="position-fixed bottom-0 end-0 p-3" style="z-index: 9999">
            <div class="toast show align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        </div>
    `;
    $('body').append(toast);
    setTimeout(() => $('.toast').toast('hide'), 3000);
};

// Initialize notification manager
$(document).ready(function() {
    if ($('#notificationBell').length) {
        window.notificationManager = new NotificationManager();
    }
});

function markNotificationRead(id) {
    $.post(`/api/notifications/mark-read/${id}`, () => {
        notificationManager.loadNotifications();
    });
}

$(document).ready(function() {
    
    // Initialize notification manager for logged in users
    if ($('#notificationBell').length) {
        window.notificationManager = new NotificationManager();
    }
    
    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // File upload preview
    $('#image-upload').change(function() {
        const file = this.files[0];
        if (file) {
            let reader = new FileReader();
            reader.onload = function(event) {
                $('#image-preview').html(`
                    <div class="mt-2 position-relative">
                        <img src="${event.target.result}" class="img-thumbnail" style="max-height: 200px;">
                        <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0" onclick="removeImage()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `);
            }
            reader.readAsDataURL(file);
        }
    });
    
    // Dynamic subcategory loading
    $('#category').change(function() {
        const category = $(this).val();
        if (category) {
            $.getJSON(`/api/subcategories/${category}`, function(data) {
                const subcategorySelect = $('#subcategory');
                subcategorySelect.empty();
                subcategorySelect.append('<option value="">Select Subcategory</option>');
                
                data.subcategories.forEach(function(subcat) {
                    subcategorySelect.append(`<option value="${subcat}">${subcat}</option>`);
                });
                
                subcategorySelect.prop('disabled', false);
            });
        }
    });
    
    // Complaint search functionality
    $('#search-complaint').on('keyup', function() {
        const value = $(this).val().toLowerCase();
        $('.complaint-row').filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
        });
    });
    
    // Status filter
    $('#status-filter').change(function() {
        const status = $(this).val();
        if (status === 'all') {
            $('.complaint-row').show();
        } else {
            $('.complaint-row').hide();
            $(`.complaint-row[data-status="${status}"]`).show();
        }
    });
    
    // Department filter
    $('#dept-filter').change(function() {
        const dept = $(this).val();
        if (dept === 'all') {
            $('.complaint-row').show();
        } else {
            $('.complaint-row').hide();
            $(`.complaint-row[data-department="${dept}"]`).show();
        }
    });
    
    // Show loading spinner on form submit
    $('form').submit(function() {
        if ($(this).valid()) {
            $('.spinner-wrapper').addClass('show');
        }
    });
    
    // Export to CSV
    $('#export-csv').click(function() {
        let csv = [];
        let rows = document.querySelectorAll('table tr');
        
        for (let i = 0; i < rows.length; i++) {
            let row = [], cols = rows[i].querySelectorAll('td, th');
            
            for (let j = 0; j < cols.length; j++) {
                row.push(cols[j].innerText);
            }
            
            csv.push(row.join(','));
        }
        
        downloadCSV(csv.join('\n'), 'complaints_report.csv');
    });
    
    // Print complaint
    $('#print-complaint').click(function() {
        window.print();
    });
    
    // Confirmation dialogs
    $('.confirm-action').click(function(e) {
        if (!confirm('Are you sure you want to proceed?')) {
            e.preventDefault();
        }
    });
    
    // Character counter for textarea
    $('textarea[maxlength]').each(function() {
        const textarea = $(this);
        const maxlength = textarea.attr('maxlength');
        const counter = $(`<small class="text-muted float-end">0/${maxlength}</small>`);
        
        textarea.after(counter);
        
        textarea.on('input', function() {
            const length = $(this).val().length;
            counter.text(`${length}/${maxlength}`);
            
            if (length > maxlength * 0.9) {
                counter.addClass('text-warning');
            } else {
                counter.removeClass('text-warning');
            }
        });
    });
    
    // Form validation
    $('form.needs-validation').each(function() {
        $(this).validate({
            errorClass: 'is-invalid',
            validClass: 'is-valid',
            errorPlacement: function(error, element) {
                error.addClass('invalid-feedback');
                element.closest('.mb-3').append(error);
            }
        });
    });
});

// Helper Functions
function removeImage() {
    $('#image-upload').val('');
    $('#image-preview').empty();
}

function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: 'text/csv'});
    const downloadLink = document.createElement('a');
    
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

function formatDate(date) {
    const d = new Date(date);
    return d.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Live time update function
function updateLiveTime() {
    const timeElements = document.querySelectorAll('.live-time');
    const now = new Date();
    const options = {
        timeZone: 'Asia/Kolkata',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    };
    const istTime = now.toLocaleString('en-IN', options);
    
    timeElements.forEach(el => {
        el.textContent = istTime;
    });
}

// Update every second
setInterval(updateLiveTime, 1000);

// अगर आपको specific elements पर live time चाहिए तो उन्हें class="live-time" दें