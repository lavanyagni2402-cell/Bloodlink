# Loads demo data into the database.
#   python manage.py seed            add demo data
#   python manage.py seed --reset    delete everything first, then add demo data
#
# Logins it creates:
#   admin / admin123    (can open /admin)
#   demo  / demo1234    (O+ donor in Jaipur)
#   every other donor uses password donor1234

import json
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import BloodRequest, Donor, DonorResponse, compatible_donor_groups


class Command(BaseCommand):
    help = "Load demo donors and requests"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        if options["reset"]:
            DonorResponse.objects.all().delete()
            BloodRequest.objects.all().delete()
            Donor.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            print("Deleted old data.")

        today = date.today()

        # 1. admin account
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@bloodlink.local", "admin123")

        # 2. demo donor account
        if not User.objects.filter(username="demo").exists():
            demo = User.objects.create_user("demo", "demo@bloodlink.local", "demo1234")
            Donor.objects.create(user=demo, full_name="Demo Donor", blood_group="O+", gender="F",
                                 date_of_birth=date(2005, 3, 14), weight_kg=55, phone="9876543210",
                                 city="Jaipur", is_available=True, is_verified=True)

        # 3. donors from the JSON file
        with open("data/sample_data.json") as f:
            data = json.load(f)

        donors = []
        for d in data["donors"]:
            user = User.objects.filter(username=d["username"]).first()
            if user is None:
                user = User.objects.create_user(d["username"], d["username"] + "@example.com", "donor1234")
                last_donation = None
                if d["last_donation_days_ago"]:
                    last_donation = today - timedelta(days=d["last_donation_days_ago"])
                Donor.objects.create(
                    user=user, full_name=d["full_name"], blood_group=d["blood_group"], gender=d["gender"],
                    date_of_birth=date.fromisoformat(d["date_of_birth"]), weight_kg=d["weight_kg"],
                    phone=d["phone"], city=d["city"], last_donation=last_donation,
                    is_available=d["is_available"], is_verified=d["is_verified"],
                )
            donors.append(user.donor)

        # 4. blood requests from the JSON file (only if there are none yet)
        if BloodRequest.objects.exists():
            print("Requests already exist, skipped. Use --reset to start fresh.")
        else:
            for i, r in enumerate(data["requests"]):
                poster = donors[(i * 5) % len(donors)].user
                blood_request = BloodRequest.objects.create(
                    posted_by=poster, patient_name=r["patient_name"], blood_group=r["blood_group"],
                    units_needed=r["units_needed"], hospital=r["hospital"], city=r["city"],
                    contact_phone="98290" + str(10000 + i * 1371), urgency=r["urgency"],
                    needed_by=today + timedelta(days=r["needed_in_days"]), note=r["note"],
                )
                # add a few pledges so the progress bars aren't all empty
                pledges_to_add = min(i % 3, r["units_needed"] - 1)
                for donor in donors:
                    if pledges_to_add == 0:
                        break
                    if (donor.blood_group in compatible_donor_groups(blood_request.blood_group)
                            and donor.user != poster and donor.is_eligible):
                        DonorResponse.objects.create(request=blood_request, donor=donor, message="I can come today.")
                        pledges_to_add = pledges_to_add - 1

            # one request that was already fulfilled
            done = BloodRequest.objects.create(
                posted_by=donors[2].user, patient_name="Lakshmi Iyer", blood_group="O+", units_needed=1,
                hospital="Apollo Hospital", city="Bengaluru", contact_phone="9811122233",
                urgency="urgent", needed_by=today, status="fulfilled",
                note="Thank you to everyone who called!",
            )
            for donor in donors:
                if donor.blood_group in ["O+", "O-"] and donor.user != done.posted_by:
                    DonorResponse.objects.create(request=done, donor=donor, status="confirmed", message="On my way.")
                    break

        print("Done:", Donor.objects.count(), "donors and", BloodRequest.objects.count(), "requests.")
        print("Logins: admin / admin123, demo / demo1234")
