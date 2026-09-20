from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .decorators import role_required
from .models import Stream, Member, Session, Attendance, OrganizerStream, Achievement, User, Student, StudentAttendance
import csv
from django.http import HttpResponse
from django.db.models import Count, Q
from django.contrib.auth.hashers import make_password

@login_required
def dashboard(request):
    """
    Shows a different message depending on the logged-in user's role.
    The @login_required decorator automatically redirects anyone
    not logged in to the login page — we don't have to check that manually.
    """
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
    Shows, per stream, each member's attendance count and percentage
    across all sessions held for that stream (optionally filtered by date range).
    Available to all logged-in roles (Admin, Organizer, Viewer) for visibility.
    """
    streams = Stream.objects.all()
    stream_id = request.GET.get('stream')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    selected_stream = None
    report_rows = []

    if stream_id:
        selected_stream = get_object_or_404(Stream, id=stream_id)

        sessions = Session.objects.filter(stream=selected_stream)
        if start_date:
            sessions = sessions.filter(session_date__gte=start_date)
        if end_date:
            sessions = sessions.filter(session_date__lte=end_date)

        total_sessions = sessions.count()
        members = selected_stream.members.all()

        for member in members:
            present_count = Attendance.objects.filter(
                member=member, session__in=sessions, status='present'
            ).count()

            percentage = round((present_count / total_sessions) * 100, 1) if total_sessions > 0 else 0

            report_rows.append({
                'member': member,
                'present_count': present_count,
                'total_sessions': total_sessions,
                'percentage': percentage,
            })

        # Sort worst-attendance-first, so problem cases are immediately visible.
        report_rows.sort(key=lambda row: row['percentage'])

    return render(request, 'core/attendance_report.html', {
        'streams': streams,
        'selected_stream': selected_stream,
        'report_rows': report_rows,
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

@role_required('admin', 'organizer')
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