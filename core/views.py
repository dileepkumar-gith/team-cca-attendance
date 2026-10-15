from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .decorators import role_required
from .models import (
    Stream, Member, Session, Attendance, OrganizerStream, Achievement, User,
    Student, StudentAttendance, StudentAchievement,
    Event, EventOrganizer, EventStudentAttendance, EventMemberAttendance,
)
import csv
from django.http import HttpResponse
from django.db.models import Count, Q
from django.contrib.auth.hashers import make_password

def can_manage_event(user, event):
    """Admin: any event. Organizer: their own stream's events OR events they're specifically assigned to."""
    if user.role == 'admin':
        return True
    if event.stream and OrganizerStream.objects.filter(organizer=user, stream=event.stream).exists():
        return True
    if EventOrganizer.objects.filter(organizer=user, event=event).exists():
        return True
    return False
from .models import Event, EventOrganizer, EventStudentAttendance, EventMemberAttendance


@role_required('admin')
def event_add(request):
    """Admin-only: create a new event."""
    streams = Stream.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        event_date = request.POST.get('event_date')
        if name and event_date:
            event = Event.objects.create(
                name=name,
                description=request.POST.get('description', '').strip(),
                event_date=event_date,
                event_time=request.POST.get('event_time') or None,
                venue=request.POST.get('venue', '').strip(),
                stream_id=request.POST.get('stream') or None,
                created_by=request.user,
            )
            messages.success(request, f"Event '{name}' created.")
            return redirect('event_detail', event_id=event.id)
        messages.error(request, "Name and date are required.")
    return render(request, 'core/event_form.html', {'streams': streams})


@login_required
def event_list(request):
    """
    Everyone can view the event list. Organizers can filter to just
    their own assigned events using ?mine=1.
    """
    show_mine = request.GET.get('mine') == '1'
    events = Event.objects.all().order_by('-event_date')

    if show_mine and request.user.role != 'admin':
        my_streams = Stream.objects.filter(organizers__organizer=request.user)
        my_event_ids = EventOrganizer.objects.filter(organizer=request.user).values_list('event_id', flat=True)
        events = events.filter(Q(stream__in=my_streams) | Q(id__in=my_event_ids)).distinct()

    return render(request, 'core/event_list.html', {'events': events, 'show_mine': show_mine})

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    can_manage = can_manage_event(request.user, event)
    return render(request, 'core/event_detail.html', {'event': event, 'can_manage': can_manage})


@login_required
def event_mark_attendance(request, event_id):
    """
    Mark Student + Member attendance for one event.
    Admin: any event. Organizer: only events tied to their stream or assigned to them directly.
    """
    event = get_object_or_404(Event, id=event_id)
    if not can_manage_event(request.user, event):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You are not authorized to manage this event.")

    # Participants: everyone in the event's stream (if set), otherwise everyone club-wide.
    if event.stream:
        students = list(event.stream.students.all())
        members = list(event.stream.members.all())
    else:
        students = list(Student.objects.all())
        members = list(Member.objects.all())

    existing_student = {a.student_id: a.status for a in EventStudentAttendance.objects.filter(event=event)}
    existing_member = {a.member_id: a.status for a in EventMemberAttendance.objects.filter(event=event)}
    for s in students:
        s.existing_status = existing_student.get(s.id, 'absent')
    for m in members:
        m.existing_status = existing_member.get(m.id, 'absent')

    if request.method == 'POST':
        for s in students:
            status = request.POST.get(f'student_{s.id}', 'absent')
            EventStudentAttendance.objects.update_or_create(
                event=event, student=s, defaults={'status': status, 'marked_by': request.user}
            )
        for m in members:
            status = request.POST.get(f'member_{m.id}', 'absent')
            EventMemberAttendance.objects.update_or_create(
                event=event, member=m, defaults={'status': status, 'marked_by': request.user}
            )
        messages.success(request, f"Attendance saved for {event.name}.")
        return redirect('event_mark_attendance', event_id=event.id)

    return render(request, 'core/event_mark_attendance.html', {
        'event': event, 'students': students, 'members': members,
    })

@role_required('admin')
def event_delete(request, event_id):
    """Admin-only: deletes an Event after confirmation."""
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        event_name = event.name
        event.delete()
        messages.success(request, f"Event '{event_name}' has been deleted.")
        return redirect('event_list')

    return render(request, 'core/event_confirm_delete.html', {'event': event})
    

@login_required
def event_report(request, event_id):
    """Attendance summary for one event: totals and percentage."""
    event = get_object_or_404(Event, id=event_id)

    student_total = EventStudentAttendance.objects.filter(event=event).count()
    student_present = EventStudentAttendance.objects.filter(event=event, status='present').count()
    member_total = EventMemberAttendance.objects.filter(event=event).count()
    member_present = EventMemberAttendance.objects.filter(event=event, status='present').count()

    context = {
        'event': event,
        'student_records': EventStudentAttendance.objects.filter(event=event).select_related('student'),
        'member_records': EventMemberAttendance.objects.filter(event=event).select_related('member'),
        'student_total': student_total, 'student_present': student_present,
        'student_pct': round((student_present / student_total) * 100, 1) if student_total else 0,
        'member_total': member_total, 'member_present': member_present,
        'member_pct': round((member_present / member_total) * 100, 1) if member_total else 0,
    }
    return render(request, 'core/event_report.html', context)
    
@login_required
def dashboard(request):
    """Students go straight to their own dashboard; everyone else sees the role-based dashboard."""
    if request.user.role == 'student':
        return redirect('my_student_profile')
    return render(request, 'core/dashboard.html')

@login_required
def member_list(request):
    """
    Shows all members, with optional search by name or roll number.
    All logged-in roles (Admin, Organizer, Viewer) can view this list.
    """
    query = request.GET.get('q', '').strip()
    members = Member.objects.all().order_by('full_name')

    if query:
        members = members.filter(full_name__icontains=query) | members.filter(roll_number__icontains=query)

    return render(request, 'core/member_list.html', {'members': members, 'query': query})


@login_required
def member_detail(request, member_id):
    """
    Shows one member's full profile: streams, attendance history, achievements.
    All logged-in roles can view this.
    """
    member = get_object_or_404(Member, id=member_id)
    attendance_records = member.attendance_records.select_related('session', 'session__stream').order_by('-session__session_date')
    achievements = member.achievements.all().order_by('-date_awarded')

    return render(request, 'core/member_detail.html', {
        'member': member,
        'attendance_records': attendance_records,
        'achievements': achievements,
    })


@role_required('admin')
def add_achievement(request, member_id):
    """
    Only Admins can add achievements. Organizers and Viewers are blocked.
    """
    member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        date_awarded = request.POST.get('date_awarded')

        if title and date_awarded:
            Achievement.objects.create(
                member=member,
                title=title,
                description=description,
                date_awarded=date_awarded,
                added_by=request.user,
            )
            messages.success(request, f"Achievement added for {member.full_name}.")
            return redirect('member_detail', member_id=member.id)
        else:
            messages.error(request, "Title and date are required.")

    return render(request, 'core/add_achievement.html', {'member': member})
@role_required('admin')
def member_add(request):
    """Admin-only: create a new Member."""
    streams = Stream.objects.all()

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        branch = request.POST.get('branch', '').strip()
        year = request.POST.get('year')
        roll_number = request.POST.get('roll_number', '').strip()
        phone = request.POST.get('phone', '').strip()
        position = request.POST.get('position', '').strip()
        stream_ids = request.POST.getlist('streams')

        if full_name and branch and year and roll_number:
            member = Member.objects.create(
                full_name=full_name, branch=branch, year=year,
                roll_number=roll_number, phone=phone, position=position,
            )
            member.streams.set(stream_ids)
            messages.success(request, f"{full_name} added successfully.")
            return redirect('member_detail', member_id=member.id)
        else:
            messages.error(request, "Full name, branch, year, and roll number are required.")

    return render(request, 'core/member_form.html', {'streams': streams, 'member': None})


@role_required('admin')
def member_edit(request, member_id):
    """Admin-only: edit an existing Member."""
    member = get_object_or_404(Member, id=member_id)
    streams = Stream.objects.all()

    if request.method == 'POST':
        member.full_name = request.POST.get('full_name', '').strip()
        member.branch = request.POST.get('branch', '').strip()
        member.year = request.POST.get('year')
        member.roll_number = request.POST.get('roll_number', '').strip()
        member.phone = request.POST.get('phone', '').strip()
        member.position = request.POST.get('position', '').strip()
        member.save()
        member.streams.set(request.POST.getlist('streams'))

        messages.success(request, f"{member.full_name} updated successfully.")
        return redirect('member_detail', member_id=member.id)

    return render(request, 'core/member_form.html', {'streams': streams, 'member': member})
@role_required('admin')
def member_delete(request, member_id):
    """
    Admin-only: deletes a Member after confirmation.
    Shows a warning page first (GET), only deletes on actual confirmation (POST).
    """
    member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        member_name = member.full_name
        member.delete()
        messages.success(request, f"{member_name} has been permanently deleted.")
        return redirect('member_list')

    return render(request, 'core/member_confirm_delete.html', {'member': member})

@login_required
def attendance_report(request):
    """
    Shows, per stream, both committee Members' and Students' attendance
    percentage across all sessions held for that stream (optionally date-filtered).
    Available to all logged-in roles (Admin, Organizer, Viewer) for visibility.
    """
    streams = Stream.objects.all()
    stream_id = request.GET.get('stream')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    selected_stream = None
    member_rows = []
    student_rows = []

    if stream_id:
        selected_stream = get_object_or_404(Stream, id=stream_id)

        sessions = Session.objects.filter(stream=selected_stream)
        if start_date:
            sessions = sessions.filter(session_date__gte=start_date)
        if end_date:
            sessions = sessions.filter(session_date__lte=end_date)

        total_sessions = sessions.count()

        for member in selected_stream.members.all():
            present_count = Attendance.objects.filter(
                member=member, session__in=sessions, status='present'
            ).count()
            percentage = round((present_count / total_sessions) * 100, 1) if total_sessions > 0 else 0
            member_rows.append({
                'name': member.full_name, 'roll_number': member.roll_number,
                'present_count': present_count, 'total_sessions': total_sessions,
                'percentage': percentage,
            })
        member_rows.sort(key=lambda row: row['percentage'])

        for student in selected_stream.students.all():
            present_count = StudentAttendance.objects.filter(
                student=student, session__in=sessions, status='present'
            ).count()
            percentage = round((present_count / total_sessions) * 100, 1) if total_sessions > 0 else 0
            student_rows.append({
                'name': student.full_name, 'roll_number': student.roll_number,
                'present_count': present_count, 'total_sessions': total_sessions,
                'percentage': percentage,
            })
        student_rows.sort(key=lambda row: row['percentage'])

    return render(request, 'core/attendance_report.html', {
        'streams': streams,
        'selected_stream': selected_stream,
        'member_rows': member_rows,
        'student_rows': student_rows,
        'start_date': start_date,
        'end_date': end_date,
    })

@login_required
def attendance_report_csv(request):
    """
    Same data as attendance_report, but returned as a downloadable CSV file
    instead of an HTML page.
    """
    stream_id = request.GET.get('stream')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    selected_stream = get_object_or_404(Stream, id=stream_id)

    sessions = Session.objects.filter(stream=selected_stream)
    if start_date:
        sessions = sessions.filter(session_date__gte=start_date)
    if end_date:
        sessions = sessions.filter(session_date__lte=end_date)

    total_sessions = sessions.count()
    members = selected_stream.members.all()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{selected_stream.name}_attendance_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Member Name', 'Roll Number', 'Sessions Present', 'Total Sessions', 'Percentage'])

    for member in members:
        present_count = Attendance.objects.filter(
            member=member, session__in=sessions, status='present'
        ).count()
        percentage = round((present_count / total_sessions) * 100, 1) if total_sessions > 0 else 0
        writer.writerow([member.full_name, member.roll_number, present_count, total_sessions, percentage])

    return response

@login_required
def my_profile(request):
    """
    Shows the logged-in user's own Member profile: streams, attendance, achievements.
    Works for any role, as long as their User account is linked to a Member (Day 2/6's `user` field).
    """
    member = getattr(request.user, 'member_profile', None)

    if member is None:
        return render(request, 'core/my_profile_unlinked.html')

    attendance_records = member.attendance_records.select_related(
        'session', 'session__stream'
    ).order_by('-session__session_date')
    achievements = member.achievements.all().order_by('-date_awarded')

    return render(request, 'core/member_detail.html', {
        'member': member,
        'attendance_records': attendance_records,
        'achievements': achievements,
        'is_own_profile': True,
    })

@role_required('admin')
def create_login(request):
    """
    Admin-only: creates a new login (User) and links it to an existing,
    not-yet-linked Member in a single step.
    """
    # Only show members who don't already have a login account.
    unlinked_members = Member.objects.filter(user__isnull=True).order_by('full_name')

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        role = request.POST.get('role')

        member = get_object_or_404(Member, id=member_id, user__isnull=True)

        if not username or not password or not role:
            messages.error(request, "Member, username, password, and role are all required.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
        else:
            new_user = User.objects.create(
                username=username,
                password=make_password(password),
                role=role,
            )
            member.user = new_user
            member.save()

            messages.success(
                request,
                f"Login created for {member.full_name} — username: {username}, role: {new_user.get_role_display()}."
            )
            return redirect('member_detail', member_id=member.id)

    return render(request, 'core/create_login.html', {
        'unlinked_members': unlinked_members,
        'roles': User.Role.choices,
    })

@role_required('admin')
def mark_attendance(request):
    user = request.user

    if user.role == 'admin':
        allowed_streams = Stream.objects.all()
    else:
        allowed_streams = Stream.objects.filter(organizers__organizer=user)

    selected_stream = None
    selected_date = None
    members = []

    stream_id = request.GET.get('stream') or request.POST.get('stream')
    session_date = request.GET.get('session_date') or request.POST.get('session_date')

    if stream_id and session_date:
        selected_stream = get_object_or_404(allowed_streams, id=stream_id)
        selected_date = session_date
        members = list(selected_stream.members.all())

        existing_session = Session.objects.filter(stream=selected_stream, session_date=selected_date).first()
        existing_statuses = {}
        if existing_session:
            existing_statuses = {
                a.member_id: a.status for a in Attendance.objects.filter(session=existing_session)
            }
        for member in members:
            member.existing_status = existing_statuses.get(member.id, 'present')

    if request.method == 'POST' and selected_stream:
        session, created = Session.objects.get_or_create(
            stream=selected_stream,
            session_date=selected_date,
            defaults={'created_by': user},
        )

        for member in members:
            status = request.POST.get(f'status_{member.id}', 'absent')
            Attendance.objects.update_or_create(
                session=session,
                member=member,
                defaults={'status': status},
            )

        messages.success(request, f"Attendance saved for {selected_stream.name} on {selected_date}.")
        return redirect(f"{request.path}?stream={selected_stream.id}&session_date={selected_date}")

    context = {
        'allowed_streams': allowed_streams,
        'selected_stream': selected_stream,
        'selected_date': selected_date,
        'members': members,
        'today': date.today().isoformat(),
    }
    return render(request, 'core/mark_attendance.html', context)

@role_required('admin', 'organizer')
def mark_student_attendance(request):
    user = request.user

    if user.role == 'admin':
        allowed_streams = Stream.objects.all()
    else:
        allowed_streams = Stream.objects.filter(organizers__organizer=user)

    selected_stream = None
    selected_date = None
    students = []

    stream_id = request.GET.get('stream') or request.POST.get('stream')
    session_date = request.GET.get('session_date') or request.POST.get('session_date')

    if stream_id and session_date:
        selected_stream = get_object_or_404(allowed_streams, id=stream_id)
        selected_date = session_date
        students = list(selected_stream.students.all())

        existing_session = Session.objects.filter(stream=selected_stream, session_date=selected_date).first()
        existing_statuses = {}
        if existing_session:
            existing_statuses = {
                a.student_id: a.status for a in StudentAttendance.objects.filter(session=existing_session)
            }
        for student in students:
            student.existing_status = existing_statuses.get(student.id, 'present')

    if request.method == 'POST' and selected_stream:
        session, created = Session.objects.get_or_create(
            stream=selected_stream,
            session_date=selected_date,
            defaults={'created_by': user},
        )

        for student in students:
            status = request.POST.get(f'status_{student.id}', 'absent')
            StudentAttendance.objects.update_or_create(
                session=session,
                student=student,
                defaults={'status': status},
            )

        messages.success(request, f"Student attendance saved for {selected_stream.name} on {selected_date}.")
        return redirect(f"{request.path}?stream={selected_stream.id}&session_date={selected_date}")

    context = {
        'allowed_streams': allowed_streams,
        'selected_stream': selected_stream,
        'selected_date': selected_date,
        'students': students,
        'today': date.today().isoformat(),
    }
    return render(request, 'core/mark_student_attendance.html', context)  
@role_required('admin')
def create_student_login(request):
    """Admin-only: creates a login (role=student) and links it to an existing, not-yet-linked Student."""
    unlinked_students = Student.objects.filter(user__isnull=True).order_by('full_name')

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        student = get_object_or_404(Student, id=student_id, user__isnull=True)

        if not username or not password:
            messages.error(request, "Student, username, and password are all required.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' is already taken.")
        else:
            new_user = User.objects.create(username=username, password=make_password(password), role='student')
            student.user = new_user
            student.save()
            messages.success(request, f"Login created for {student.full_name} — username: {username}.")
            return redirect('dashboard')

    return render(request, 'core/create_student_login.html', {'unlinked_students': unlinked_students})

@role_required('student')
def my_student_profile(request):
    """A Student's own read-only dashboard: regular attendance, event attendance, achievements."""
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        return render(request, 'core/my_profile_unlinked.html')

    regular_records = StudentAttendance.objects.filter(student=student).select_related('session', 'session__stream')
    event_records = EventStudentAttendance.objects.filter(student=student).select_related('event')
    achievements = student.achievements.all().order_by('-date_awarded')

    total_regular = regular_records.count()
    present_regular = regular_records.filter(status='present').count()
    regular_pct = round((present_regular / total_regular) * 100, 1) if total_regular else 0

    this_month_records = regular_records.filter(
        session__session_date__year=date.today().year,
        session__session_date__month=date.today().month,
    )
    this_month_total = this_month_records.count()
    this_month_present = this_month_records.filter(status='present').count()
    this_month_pct = round((this_month_present / this_month_total) * 100, 1) if this_month_total else 0

    total_events = event_records.count()
    present_events = event_records.filter(status='present').count()
    event_pct = round((present_events / total_events) * 100, 1) if total_events else 0

    return render(request, 'core/my_student_profile.html', {
        'student': student,
        'regular_records': regular_records.order_by('-session__session_date'),
        'event_records': event_records.order_by('-event__event_date'),
        'achievements': achievements,
        'regular_pct': regular_pct, 'present_regular': present_regular, 'total_regular': total_regular,
        'this_month_pct': this_month_pct, 'this_month_present': this_month_present, 'this_month_total': this_month_total,
        'event_pct': event_pct, 'present_events': present_events, 'total_events': total_events,
    })


@role_required('admin')
def add_student_achievement(request, student_id):
    """Admin-only: add an achievement to a Student's profile."""
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        date_awarded = request.POST.get('date_awarded')
        if title and date_awarded:
            StudentAchievement.objects.create(
                student=student, title=title,
                description=request.POST.get('description', '').strip(),
                date_awarded=date_awarded, added_by=request.user,
            )
            messages.success(request, f"Achievement added for {student.full_name}.")
            return redirect('dashboard')
        messages.error(request, "Title and date are required.")
    return render(request, 'core/add_student_achievement.html', {'student': student})