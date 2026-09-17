from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for TEAM CCA.
    Every login account belongs to a real student (linked via Member),
    and has a role that controls what they're allowed to do in the app.
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        ORGANIZER = 'organizer', 'Organizer'
        VIEWER = 'viewer', 'Viewer'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    def __str__(self):
        return f"{self.username} ({self.role})"


class Stream(models.Model):
    """One of the 4 fixed streams: Arts, Dance, Dramatics, Singing."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    """
    A student member of TEAM CCA.
    Committee members (Admin/Organizer/Viewer) are linked here via 'user';
    most regular members will have no login account at all (user=None).
    """
    class Year(models.IntegerChoices):
        FIRST = 1, '1st Year'
        SECOND = 2, '2nd Year'
        THIRD = 3, '3rd Year'
        FOURTH = 4, '4th Year'

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='member_profile',
        null=True, blank=True,
        help_text="Linked login account, if this member has one"
    )
    full_name = models.CharField(max_length=100)
    branch = models.CharField(max_length=50)
    year = models.PositiveSmallIntegerField(choices=Year.choices)
    roll_number = models.CharField(max_length=30, unique=True)
    phone = models.CharField(max_length=15, blank=True)
    position = models.CharField(
        max_length=100, blank=True,
        help_text="e.g. Main Coordinator, Arts Stream Organizer, Diary Maintenance, Core Member"
    )
    joined_date = models.DateField(auto_now_add=True)
    streams = models.ManyToManyField(Stream, related_name='members')

    def __str__(self):
        return f"{self.full_name} ({self.roll_number})"

class OrganizerStream(models.Model):
    """Links an Organizer (User) to the stream(s) they manage."""
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organizer_streams')
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='organizers')

    class Meta:
        unique_together = ('organizer', 'stream')

    def __str__(self):
        return f"{self.organizer.username} → {self.stream.name}"


class Session(models.Model):
    """One specific stream's meeting on one specific date (Tue/Wed/Sat)."""
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name='sessions')
    session_date = models.DateField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sessions_created')

    class Meta:
        unique_together = ('stream', 'session_date')

    def __str__(self):
        return f"{self.stream.name} - {self.session_date}"


class Attendance(models.Model):
    """One attendance record: a member's status for one session."""
    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendance_records')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABSENT)
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'member')

    def __str__(self):
        return f"{self.member.full_name} - {self.session} - {self.status}"


class Achievement(models.Model):
    """An achievement recorded against a member's profile."""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_awarded = models.DateField()
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='achievements_added')

    def __str__(self):
        return f"{self.title} - {self.member.full_name}"