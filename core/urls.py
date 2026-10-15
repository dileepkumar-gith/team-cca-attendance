from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('attendance/mark/', views.mark_attendance, name='mark_attendance'),
    path('members/', views.member_list, name='member_list'),
path('members/<int:member_id>/', views.member_detail, name='member_detail'),
path('members/<int:member_id>/add-achievement/', views.add_achievement, name='add_achievement'),
path('members/add/', views.member_add, name='member_add'),
path('members/<int:member_id>/edit/', views.member_edit, name='member_edit'),
path('members/<int:member_id>/delete/', views.member_delete, name='member_delete'),
path('reports/attendance/', views.attendance_report, name='attendance_report'),
path('reports/attendance/csv/', views.attendance_report_csv, name='attendance_report_csv'),
path('my-profile/', views.my_profile, name='my_profile'),
path('users/create/', views.create_login, name='create_login'),
path('attendance/mark-students/', views.mark_student_attendance, name='mark_student_attendance'),
path('events/', views.event_list, name='event_list'),
path('events/add/', views.event_add, name='event_add'),
path('events/<int:event_id>/', views.event_detail, name='event_detail'),
path('events/<int:event_id>/mark/', views.event_mark_attendance, name='event_mark_attendance'),
path('events/<int:event_id>/report/', views.event_report, name='event_report'),
path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
path('users/create-student/', views.create_student_login, name='create_student_login'),
path('my-attendance/', views.my_student_profile, name='my_student_profile'),
path('students/<int:student_id>/add-achievement/', views.add_student_achievement, name='add_student_achievement'),
]