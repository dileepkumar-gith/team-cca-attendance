from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from core.models import Stream, Member, Session, Attendance, OrganizerStream

User = get_user_model()


class StreamModelTests(TestCase):
    def test_stream_str_returns_name(self):
        """A Stream's string representation should just be its name."""
        stream = Stream.objects.create(name="Dance")
        self.assertEqual(str(stream), "Dance")


class AttendanceModelTests(TestCase):
    def setUp(self):
        """
        setUp() runs before EVERY test method in this class.
        We create shared test data here so each test starts from a clean, known state.
        """
        self.stream = Stream.objects.create(name="Dance")
        self.member = Member.objects.create(
            full_name="Test Member", branch="CSE", year=3, roll_number="TEST001"
        )
        self.member.streams.add(self.stream)
        self.session = Session.objects.create(stream=self.stream, session_date="2026-09-20")

    def test_attendance_created_successfully(self):
        """A basic attendance record should save correctly."""
        attendance = Attendance.objects.create(
            session=self.session, member=self.member, status="present"
        )
        self.assertEqual(attendance.status, "present")

    def test_duplicate_attendance_for_same_session_and_member_fails(self):
        """
        NEGATIVE TEST: our unique_together constraint from Day 2 should prevent
        two Attendance rows for the same member + session.
        """
        Attendance.objects.create(session=self.session, member=self.member, status="present")
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(session=self.session, member=self.member, status="absent")

class MarkAttendanceAccessTests(TestCase):
    """
    Tests the core security rule from Day 4:
    an Organizer can only mark attendance for their assigned stream(s).
    """

    def setUp(self):
        self.dance = Stream.objects.create(name="Dance")
        self.singing = Stream.objects.create(name="Singing")

        self.organizer = User.objects.create_user(
            username="danceorg", password="testpass123", role="organizer"
        )
        OrganizerStream.objects.create(organizer=self.organizer, stream=self.dance)

        self.viewer = User.objects.create_user(
            username="testviewer", password="testpass123", role="viewer"
        )

        self.client = Client()

    def test_organizer_can_access_their_own_stream(self):
        """POSITIVE TEST: organizer should be able to load their assigned stream."""
        self.client.login(username="danceorg", password="testpass123")
        response = self.client.get(f"/attendance/mark/?stream={self.dance.id}&session_date=2026-09-20")
        self.assertEqual(response.status_code, 200)

    def test_organizer_cannot_access_unassigned_stream(self):
        """
        NEGATIVE TEST: organizer assigned only to Dance should get a 404
        when trying to access Singing's data directly by URL.
        """
        self.client.login(username="danceorg", password="testpass123")
        response = self.client.get(f"/attendance/mark/?stream={self.singing.id}&session_date=2026-09-20")
        self.assertEqual(response.status_code, 404)

    def test_viewer_cannot_access_mark_attendance_at_all(self):
        """NEGATIVE TEST: Viewers should be blocked from this page entirely (403)."""
        self.client.login(username="testviewer", password="testpass123")
        response = self.client.get("/attendance/mark/")
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        """NEGATIVE TEST: someone not logged in at all should be redirected, not shown the page."""
        response = self.client.get("/attendance/mark/")
        self.assertEqual(response.status_code, 302)  # redirect to login

    def test_viewer_cannot_access_specific_stream_either(self):
        """
        NEGATIVE TEST: even with a valid stream ID in the URL,
        a Viewer should still be blocked (403) — role check happens
        before the stream-ownership check.
        """
        self.client.login(username="testviewer", password="testpass123")
        response = self.client.get(f"/attendance/mark/?stream={self.dance.id}&session_date=2026-09-20")
        self.assertEqual(response.status_code, 403)



