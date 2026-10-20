"""Run with:  python manage.py test core"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .matching import rank_donors
from .models import BloodRequest, Donor, DonorResponse, compatible_donor_groups


def make_donor(username, group="O+", city="Jaipur", last=None, **kw):
    u = User.objects.create_user(username, password="pass12345")
    return Donor.objects.create(user=u, full_name=username.title() + " Test", blood_group=group, gender="F",
                                date_of_birth=date(2000, 1, 1), weight_kg=kw.get("weight", 60),
                                phone="9876543210", city=city, last_donation=last,
                                is_available=kw.get("available", True), is_verified=kw.get("verified", False))


class CompatibilityTests(TestCase):
    def test_universal_donor_and_recipient(self):
        self.assertEqual(compatible_donor_groups("O-"), ["O-"])
        self.assertEqual(len(compatible_donor_groups("AB+")), 8)
        self.assertCountEqual(compatible_donor_groups("B+"), ["O-", "O+", "B-", "B+"])


class MatchingTests(TestCase):
    def setUp(self):
        self.poster = User.objects.create_user("family", password="pass12345")
        self.req = BloodRequest.objects.create(
            posted_by=self.poster, patient_name="P", blood_group="O+", units_needed=2, hospital="H",
            city="Jaipur", contact_phone="9876543210", needed_by=date.today())

    def test_ranking_prefers_exact_group_and_same_city(self):
        make_donor("near_exact", "O+", "Jaipur")
        make_donor("near_compat", "O-", "Jaipur")
        make_donor("far_exact", "O+", "Delhi")
        names = [m["donor"].user.username for m in rank_donors(self.req)]
        self.assertEqual(names, ["near_exact", "near_compat", "far_exact"])

    def test_excludes_ineligible_incompatible_and_unavailable(self):
        make_donor("recent", "O+", last=date.today() - timedelta(days=20))
        make_donor("light", "O+", weight=40)
        make_donor("wrong_group", "A+")
        make_donor("busy", "O+", available=False)
        self.assertEqual(rank_donors(self.req), [])


class FlowTests(TestCase):
    def setUp(self):
        self.family = make_donor("family", "A+")
        self.helper = make_donor("helper", "O-")
        self.client.login(username="family", password="pass12345")
        self.client.post(reverse("request_create"), {
            "patient_name": "Ravi", "blood_group": "B+", "units_needed": 1, "hospital": "SMS",
            "city": "jaipur", "contact_phone": "9876500000", "urgency": "critical",
            "needed_by": date.today().isoformat(), "note": ""})
        self.req = BloodRequest.objects.get()

    def test_request_created_with_clean_city(self):
        self.assertEqual(self.req.city, "Jaipur")
        self.assertEqual(self.req.posted_by.username, "family")

    def test_pledge_then_confirm_resets_donor_clock(self):
        self.client.login(username="helper", password="pass12345")
        r = self.client.post(reverse("api_respond", args=[self.req.pk]), data='{"message": "coming"}',
                             content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["contact_phone"], "9876500000")
        # second pledge is refused
        r2 = self.client.post(reverse("api_respond", args=[self.req.pk]), content_type="application/json")
        self.assertEqual(r2.status_code, 400)

        self.client.login(username="family", password="pass12345")
        resp = DonorResponse.objects.get()
        self.client.post(reverse("response_set_status", args=[resp.pk]), {"status": "confirmed"})
        self.helper.refresh_from_db()
        self.assertEqual(self.helper.last_donation, date.today())
        self.assertFalse(self.helper.is_eligible)

    def test_incompatible_donor_cannot_pledge(self):
        make_donor("aplus", "A+")
        self.client.login(username="aplus", password="pass12345")
        r = self.client.post(reverse("api_respond", args=[self.req.pk]), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_api_never_exposes_phone_numbers(self):
        data = self.client.get(reverse("api_donors")).json()
        self.assertNotIn("9876543210", str(data))

    def test_only_owner_can_close(self):
        self.client.login(username="helper", password="pass12345")
        r = self.client.post(reverse("request_set_status", args=[self.req.pk]), {"status": "closed"})
        self.assertEqual(r.status_code, 403)
