from django.urls import reverse

ALL_STAFF = {'admin', 'organizer', 'viewer', 'dairy'}

# (label, bootstrap-icon, url name, roles allowed to see it, other url names that should highlight it)
NAV_ITEMS = [
    ('Dashboard', 'bi-speedometer2', 'dashboard', ALL_STAFF, ()),
    ('My Attendance', 'bi-person-check', 'my_student_profile', {'student'}, ()),
    ('Members', 'bi-people', 'member_list', ALL_STAFF,
     ('member_detail', 'member_add', 'member_edit', 'member_delete', 'add_achievement')),
    ('Mark Committee Attendance', 'bi-clipboard-check', 'mark_attendance', {'admin'}, ()),
    ('Mark Student Attendance', 'bi-check2-square', 'mark_student_attendance', {'admin', 'organizer'}, ()),
    ('Attendance Report', 'bi-bar-chart-line', 'attendance_report', ALL_STAFF, ()),
    ('Events', 'bi-calendar-event', 'event_list', ALL_STAFF,
     ('event_detail', 'event_add', 'event_mark_attendance', 'event_report',
      'event_delete', 'event_assign_organizer', 'event_remove_organizer')),
    ('Report Downloads', 'bi-download', 'report_downloads', {'admin', 'dairy'}, ()),
    ('Create Committee Login', 'bi-person-plus', 'create_login', {'admin'}, ()),
    ('Create Student Login', 'bi-mortarboard', 'create_student_login', {'admin'}, ()),
    ('My Profile', 'bi-person-circle', 'my_profile', ALL_STAFF, ()),
]


def sidebar(request):
    """Adds `sidebar_items` (the menu for this user's role) to every template."""
    user = request.user
    if not user.is_authenticated:
        return {}

    match = getattr(request, 'resolver_match', None)
    current = match.url_name if match else ''

    items = []
    for label, icon, url_name, roles, also_active in NAV_ITEMS:
        if user.role in roles:
            items.append({
                'label': label,
                'icon': icon,
                'url': reverse(url_name),
                'active': current == url_name or current in also_active,
            })
    return {'sidebar_items': items}