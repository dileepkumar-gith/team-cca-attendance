from django.contrib import admin
from .models import User, Stream, Member, OrganizerStream, Session, Attendance, Achievement, Student, StudentAttendance

admin.site.register(User)
admin.site.register(Stream)
admin.site.register(Member)
admin.site.register(OrganizerStream)
admin.site.register(Session)
admin.site.register(Attendance)
admin.site.register(Achievement)
admin.site.register(Student)
admin.site.register(StudentAttendance)