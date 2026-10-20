from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse

# (value saved in database, text shown to the user)
BLOOD_GROUPS = [
    ("A+", "A+"), ("A-", "A−"), ("B+", "B+"), ("B-", "B−"),
    ("AB+", "AB+"), ("AB-", "AB−"), ("O+", "O+"), ("O-", "O−"),
]

# Which groups each donor group can give blood to
CAN_DONATE_TO = {
    "O-": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+": ["O+", "A+", "B+", "AB+"],
    "A-": ["A-", "A+", "AB-", "AB+"],
    "A+": ["A+", "AB+"],
    "B-": ["B-", "B+", "AB-", "AB+"],
    "B+": ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}


def compatible_donor_groups(patient_group):
    """Returns the list of donor groups that can give blood to this patient."""
    result = []
    for donor_group in CAN_DONATE_TO:
        if patient_group in CAN_DONATE_TO[donor_group]:
            result.append(donor_group)
    return result


# Phone number must be 10 digits and start with 6, 7, 8 or 9
phone_validator = RegexValidator(r"^[6-9]\d{9}$", "Enter a valid 10-digit Indian mobile number.")


class Donor(models.Model):
    GENDERS = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="donor")
    full_name = models.CharField(max_length=100)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    gender = models.CharField(max_length=1, choices=GENDERS)
    date_of_birth = models.DateField()
    weight_kg = models.PositiveSmallIntegerField(validators=[MinValueValidator(30), MaxValueValidator(250)])
    phone = models.CharField(max_length=10, validators=[phone_validator])
    city = models.CharField(max_length=60)
    last_donation = models.DateField(null=True, blank=True)
    is_available = models.BooleanField(default=True, help_text="Donor is willing to be contacted right now")
    is_verified = models.BooleanField(default=False, help_text="Checked by a BloodLink moderator")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name + " (" + self.blood_group + ", " + self.city + ")"

    @property
    def age(self):
        today = date.today()
        age = today.year - self.date_of_birth.year
        # subtract 1 if the birthday hasn't come yet this year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            age = age - 1
        return age

    @property
    def days_since_donation(self):
        if self.last_donation is None:
            return None
        return (date.today() - self.last_donation).days

    @property
    def next_eligible_date(self):
        if self.last_donation is None:
            return date.today()
        next_date = self.last_donation + timedelta(days=90)
        if next_date < date.today():
            return date.today()
        return next_date

    @property
    def is_eligible(self):
        """Rules: age 18 to 65, weight at least 45 kg, 90 days since the last donation."""
        if self.age < 18 or self.age > 65:
            return False
        if self.weight_kg < 45:
            return False
        if self.last_donation is not None and self.days_since_donation < 90:
            return False
        return True

    @property
    def donations_count(self):
        return self.responses.filter(status="confirmed").count()


class BloodRequest(models.Model):
    URGENCY = [("critical", "Critical (within hours)"), ("urgent", "Urgent (within 24 h)"), ("normal", "Planned")]
    STATUS = [("open", "Open"), ("fulfilled", "Fulfilled"), ("closed", "Closed")]

    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blood_requests")
    patient_name = models.CharField(max_length=100)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS)
    units_needed = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    hospital = models.CharField(max_length=150)
    city = models.CharField(max_length=60)
    contact_phone = models.CharField(max_length=10, validators=[phone_validator])
    urgency = models.CharField(max_length=10, choices=URGENCY, default="urgent")
    needed_by = models.DateField()
    note = models.TextField(blank=True, max_length=500)
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["status", "-created_at"]

    def __str__(self):
        return self.blood_group + " for " + self.patient_name + " at " + self.hospital

    def get_absolute_url(self):
        return reverse("request_detail", args=[self.id])

    @property
    def compatible_groups(self):
        return compatible_donor_groups(self.blood_group)

    @property
    def units_pledged(self):
        # count every response except the ones marked "not needed"
        return self.responses.exclude(status="declined").count()

    @property
    def progress_percent(self):
        percent = round(self.units_pledged * 100 / self.units_needed)
        return min(percent, 100)

    def to_dict(self):
        """Converts the request into a dictionary so it can be sent as JSON."""
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "blood_group": self.blood_group,
            "units_needed": self.units_needed,
            "units_pledged": self.units_pledged,
            "progress": self.progress_percent,
            "hospital": self.hospital,
            "city": self.city,
            "urgency": self.urgency,
            "urgency_label": self.get_urgency_display(),
            "status": self.status,
            "needed_by": str(self.needed_by),
            "url": self.get_absolute_url(),
        }


class DonorResponse(models.Model):
    STATUS = [("pledged", "Pledged"), ("confirmed", "Donated"), ("declined", "Not needed")]

    request = models.ForeignKey(BloodRequest, on_delete=models.CASCADE, related_name="responses")
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="responses")
    message = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pledged")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        # a donor can respond to the same request only once
        constraints = [
            models.UniqueConstraint(fields=["request", "donor"], name="one_response_per_donor"),
        ]

    def __str__(self):
        return self.donor.full_name + " -> request " + str(self.request_id)
