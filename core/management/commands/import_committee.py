from django.core.management.base import BaseCommand
from core.models import Member, Stream


# Real committee data based on the roster you shared.
# Format: (full_name, roll_number, branch, year, position, stream_names)
COMMITTEE_DATA = [
    ("M. Dileep Kumar", "Y23ADS474", "DS", 4, "Main Coordinator", []),
    ("M. Prasanna", "Y23AEC513", "ECE", 4, "Main Coordinator", []),
    ("CH.N.V. Harini", "Y23ADS419", "DS", 4, "Main Coordinator", []),
    ("K. Sanjana", "Y23ACS482", "CSE", 4, "Event Organizer", []),
    ("B. Dileep", "Y23ACS408", "CSE", 4, "Event Organizer / Insta Handler", []),
    ("S. Prasad", "Y23AME417", "Mech", 4, "Event Organizer", []),
    ("P. Sai Suma Sri", "Y23ACM461", "AIML", 4, "Arts Stream Organizer", ["Arts"]),
    ("N. Harsha Vardhan", "L24AEE501", "EEE", 4, "Dance Stream Organizer", ["Dance"]),
    ("S. Durga Praveen", "L24AME449", "Mech", 4, "Dramatics Stream Organizer / Property Manager", ["Dramatics"]),
    ("K. Ravi Kishore", "Y23ADS459", "DS", 4, "Singing Stream Organizer", ["Singing"]),
    ("K. Renuka", "Y23AIT460", "IT", 4, "Insta Handler / Dance Property Manager", ["Dance"]),
    ("M. Varshitha", "Y23ACM447", "AIML", 4, "Insta Handler / Arts Property Manager", ["Arts"]),
    ("D. Aswini", "Y23AIT425", "IT", 4, "Diary Maintenance", []),
    ("B. Jahnavi", "Y23ACS409", "CSE", 4, "Diary Maintenance", []),
    ("B. Sonali", "Y23ACS410", "CSE", 4, "Core Member", []),
    ("N. Anusha", "Y23AIT472", "IT", 4, "Core Member", []),
    ("Ch. Deekshitha Lakshmi", "Y23ACS422", "CSE", 4, "Core Member", []),
   
]


class Command(BaseCommand):
    help = "Bulk-imports the TEAM CCA committee roster into the Member table."

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for full_name, roll_number, branch, year, position, stream_names in COMMITTEE_DATA:
            member, created = Member.objects.get_or_create(
                roll_number=roll_number,
                defaults={
                    'full_name': full_name,
                    'branch': branch,
                    'year': year,
                    'position': position,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {full_name} ({roll_number})"))
            else:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(f"Already exists, skipped: {full_name} ({roll_number})"))

            if stream_names:
                streams = Stream.objects.filter(name__in=stream_names)
                member.streams.set(streams)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created_count} members created, {skipped_count} already existed."
        ))