# Finds the best donors for a blood request and gives each one a score out of 100.
#
# Scoring:
#   exact blood group      35 points   (compatible but different group: 15)
#   same city as hospital  30 points
#   verified donor         10 points
#   past donations          5 points each, maximum 15
#   well rested            10 points if never donated or 180+ days ago, else 5

from .models import Donor


def score_donor(donor, blood_request):
    score = 0
    reasons = []

    if donor.blood_group == blood_request.blood_group:
        score = score + 35
        reasons.append("Exact blood group")
    else:
        score = score + 15
        reasons.append("Compatible (" + donor.blood_group + " → " + blood_request.blood_group + ")")

    if donor.city.lower() == blood_request.city.lower():
        score = score + 30
        reasons.append("Same city")

    if donor.is_verified:
        score = score + 10
        reasons.append("Verified donor")

    past = donor.donations_count
    if past > 0:
        score = score + min(past * 5, 15)
        reasons.append(str(past) + " past donation(s)")

    days = donor.days_since_donation
    if days is None or days >= 180:
        score = score + 10
        reasons.append("Well rested")
    else:
        score = score + 5

    return score, reasons


def rank_donors(blood_request):
    # Step 1: use the database to get donors with a compatible group who are available
    donors = Donor.objects.filter(
        blood_group__in=blood_request.compatible_groups,
        is_available=True,
    ).exclude(user=blood_request.posted_by)

    # Step 2: skip donors who already responded or are not eligible today, score the rest
    results = []
    for donor in donors:
        already_responded = donor.responses.filter(request=blood_request).exists()
        if already_responded or not donor.is_eligible:
            continue
        score, reasons = score_donor(donor, blood_request)
        results.append({"donor": donor, "score": score, "reasons": reasons})

    # Step 3: highest score first
    results.sort(key=lambda item: item["score"], reverse=True)
    return results
