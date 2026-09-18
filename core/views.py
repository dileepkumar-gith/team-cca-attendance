from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .decorators import role_required
from .models import Stream, Member, Session, Attendance, OrganizerStream, Achievement

@login_required
def dashboard(request):
    """
    Shows a different message depending on the logged-in user's role.
    The @login_required decorator automatically redirects anyone
    not logged in to the login page — we don't have to check that manually.
    """
    return render(request, 'core/dashboard.html')


@role_required('admin', 'organizer')
def mark_attendance(request):
    user = request.user

    # Admins can mark attendance for any stream.
    # Organizers can only mark attendance for streams assigned to them.
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
        # SECURITY CHECK: even if someone manually edits the URL,
        # this ensures the selected stream is actually one they're allowed to use.
        selected_stream = get_object_or_404(allowed_streams, id=stream_id)
        selected_date = session_date
        members = selected_stream.members.all()

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