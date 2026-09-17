from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .decorators import role_required
from .models import Stream, Member, Session, Attendance, OrganizerStream


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