import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .alerts import send_alert
from .forms import BloodRequestForm, DonorForm, SignupForm
from .matching import rank_donors
from .models import BLOOD_GROUPS, CAN_DONATE_TO, BloodRequest, Donor, DonorResponse


# ---------------------------------------------------------------- helpers

def get_donor(user):
    """Returns the donor profile of a logged-in user, or None."""
    if user.is_authenticated and Donor.objects.filter(user=user).exists():
        return user.donor
    return None


def sort_by_urgency(requests):
    """Critical first, then urgent, then planned. Same urgency: earliest date first."""
    order = {"critical": 0, "urgent": 1, "normal": 2}
    return sorted(requests, key=lambda r: (order[r.urgency], r.needed_by))


# ------------------------------------------------------------------ pages

def home(request):
    open_requests = BloodRequest.objects.filter(status="open")
    most_urgent = sort_by_urgency(open_requests)[:3]
    return render(request, "core/home.html", {"urgent": most_urgent})


def signup(request):
    if request.method == "POST":
        user_form = SignupForm(request.POST)
        donor_form = DonorForm(request.POST)
        if user_form.is_valid() and donor_form.is_valid():
            user = user_form.save()                 # creates the login account
            donor = donor_form.save(commit=False)   # donor details, not saved yet
            donor.user = user                       # link the donor to the account
            donor.save()
            login(request, user)
            messages.success(request, "Welcome to BloodLink! You are registered as a " + donor.blood_group + " donor.")
            return redirect("dashboard")
    else:
        user_form = SignupForm()
        donor_form = DonorForm()
    return render(request, "core/signup.html", {"user_form": user_form, "donor_form": donor_form})


@login_required
def dashboard(request):
    donor = get_donor(request.user)
    my_requests = BloodRequest.objects.filter(posted_by=request.user)

    my_responses = []
    can_help = []
    if donor:
        my_responses = DonorResponse.objects.filter(donor=donor)
        # open requests this donor's blood group can help with
        matching = BloodRequest.objects.filter(
            status="open",
            blood_group__in=CAN_DONATE_TO[donor.blood_group],
        ).exclude(posted_by=request.user).exclude(responses__donor=donor)
        can_help = sort_by_urgency(matching)[:5]

    return render(request, "core/dashboard.html", {
        "donor": donor,
        "my_requests": my_requests,
        "my_responses": my_responses,
        "can_help": can_help,
    })


@login_required
def profile_edit(request):
    donor = get_donor(request.user)
    if request.method == "POST":
        form = DonorForm(request.POST, instance=donor)
        if form.is_valid():
            donor = form.save(commit=False)
            donor.user = request.user
            donor.save()
            messages.success(request, "Profile saved.")
            return redirect("dashboard")
    else:
        form = DonorForm(instance=donor)
    return render(request, "core/profile_form.html", {"form": form, "is_new": donor is None})


def request_list(request):
    # This page is empty at first. jQuery fills it using api_requests (static/core/js/requests.js)
    return render(request, "core/request_list.html", {"groups": BLOOD_GROUPS})


@login_required
def request_create(request):
    if request.method == "POST":
        form = BloodRequestForm(request.POST)
        if form.is_valid():
            blood_request = form.save(commit=False)
            blood_request.posted_by = request.user
            blood_request.save()

            # tell the Node.js server so every open browser gets a live alert
            send_alert("new_request", blood_request.to_dict())

            count = len(rank_donors(blood_request))
            messages.success(request, "Request posted. We found " + str(count) + " eligible donors who can help.")
            return redirect("request_detail", pk=blood_request.id)
    else:
        form = BloodRequestForm()
    return render(request, "core/request_form.html", {"form": form})


def request_detail(request, pk):
    blood_request = get_object_or_404(BloodRequest, pk=pk)
    donor = get_donor(request.user)

    # is the person viewing this page the one who posted it (or an admin)?
    is_owner = request.user == blood_request.posted_by or request.user.is_staff

    my_response = None
    can_donate = False
    if donor:
        my_response = DonorResponse.objects.filter(request=blood_request, donor=donor).first()
        can_donate = blood_request.blood_group in CAN_DONATE_TO[donor.blood_group]

    matches = []
    if blood_request.status == "open":
        matches = rank_donors(blood_request)

    return render(request, "core/request_detail.html", {
        "br": blood_request,
        "is_owner": is_owner,
        "donor": donor,
        "my_response": my_response,
        "can_donate": can_donate,
        "responses": blood_request.responses.all(),
        "compatible_groups": ", ".join(blood_request.compatible_groups),
        "match_count": len(matches),
        "matches": matches[:10],   # owner sees the top 10
    })


@login_required
@require_POST
def request_set_status(request, pk):
    blood_request = get_object_or_404(BloodRequest, pk=pk)
    # only the person who posted the request can change it
    if request.user != blood_request.posted_by and not request.user.is_staff:
        return HttpResponseForbidden("You can't change someone else's request.")

    new_status = request.POST.get("status")
    if new_status in ["open", "fulfilled", "closed"]:
        blood_request.status = new_status
        blood_request.save()
        messages.success(request, "Request marked as " + new_status + ".")
        if new_status == "fulfilled":
            send_alert("fulfilled", blood_request.to_dict())
    return redirect("request_detail", pk=pk)


@login_required
@require_POST
def response_set_status(request, pk):
    response = get_object_or_404(DonorResponse, pk=pk)
    if request.user != response.request.posted_by and not request.user.is_staff:
        return HttpResponseForbidden("You can't change this.")

    new_status = request.POST.get("status")
    if new_status in ["pledged", "confirmed", "declined"]:
        response.status = new_status
        response.save()
        # if the donor actually donated, their 90-day waiting period starts today
        if new_status == "confirmed":
            response.donor.last_donation = timezone.localdate()
            response.donor.save()
        messages.success(request, "Updated " + response.donor.full_name + ".")
    return redirect("request_detail", pk=response.request.id)


def find_donors(request):
    # This page is an AngularJS app. It loads its data from api_donors (static/core/js/finder.js)
    return render(request, "core/find_donors.html")


# ------------------------------------------------- JSON API (used by AJAX)

@require_GET
def api_stats(request):
    by_group = {}
    for group, label in BLOOD_GROUPS:
        by_group[group] = Donor.objects.filter(blood_group=group).count()

    return JsonResponse({
        "donors": Donor.objects.count(),
        "available": Donor.objects.filter(is_available=True).count(),
        "open_requests": BloodRequest.objects.filter(status="open").count(),
        "critical": BloodRequest.objects.filter(status="open", urgency="critical").count(),
        "lives_touched": DonorResponse.objects.filter(status="confirmed").count(),
        "by_group": by_group,
    })


@require_GET
def api_requests(request):
    """Example: GET /api/requests/?city=Jaipur&group=O-&urgency=critical&status=open"""
    city = request.GET.get("city", "")
    group = request.GET.get("group", "")
    urgency = request.GET.get("urgency", "")
    status = request.GET.get("status", "open")

    results = BloodRequest.objects.all()
    if city:
        results = results.filter(city__icontains=city)
    if group == "mine":
        donor = get_donor(request.user)
        if donor:
            results = results.filter(blood_group__in=CAN_DONATE_TO[donor.blood_group])
    elif group:
        results = results.filter(blood_group=group)
    if urgency:
        results = results.filter(urgency=urgency)
    if status != "all":
        results = results.filter(status=status)

    data = []
    for blood_request in sort_by_urgency(results):
        data.append(blood_request.to_dict())
    return JsonResponse({"count": len(data), "results": data})


@require_GET
def api_donors(request):
    """List of donors for the Find donors page. Phone numbers are NOT included."""
    data = []
    for donor in Donor.objects.all():
        names = donor.full_name.split()
        short_name = names[0]
        if len(names) > 1:
            short_name = names[0] + " " + names[-1][0] + "."   # "Rahul S."
        data.append({
            "id": donor.id,
            "name": short_name,
            "blood_group": donor.blood_group,
            "city": donor.city,
            "available": donor.is_available,
            "eligible": donor.is_eligible,
            "verified": donor.is_verified,
            "donations": donor.donations_count,
            "next_eligible": str(donor.next_eligible_date),
            "can_donate_to": CAN_DONATE_TO[donor.blood_group],
        })
    return JsonResponse({"count": len(data), "results": data})


@login_required
@require_POST
def api_respond(request, pk):
    """A donor clicks "I can donate". Called with jQuery AJAX."""
    blood_request = get_object_or_404(BloodRequest, pk=pk)
    donor = get_donor(request.user)

    # check everything first and send back an error message if something is wrong
    error = None
    if donor is None:
        error = "Complete your donor profile first."
    elif blood_request.status != "open":
        error = "This request is no longer open."
    elif blood_request.posted_by == request.user:
        error = "You can't respond to your own request."
    elif blood_request.blood_group not in CAN_DONATE_TO[donor.blood_group]:
        error = donor.blood_group + " can't donate to " + blood_request.blood_group + "."
    elif not donor.is_eligible:
        error = "You'll be eligible again on " + str(donor.next_eligible_date) + "."
    elif DonorResponse.objects.filter(request=blood_request, donor=donor).exists():
        error = "You've already responded to this request."

    if error:
        return JsonResponse({"ok": False, "error": error}, status=400)

    # read the JSON body sent by jQuery: {"message": "..."}
    body = json.loads(request.body or "{}")
    message = body.get("message", "")[:200]

    DonorResponse.objects.create(request=blood_request, donor=donor, message=message)

    alert = blood_request.to_dict()
    alert["donor"] = donor.full_name.split()[0]
    send_alert("pledge", alert)

    return JsonResponse({
        "ok": True,
        "request": blood_request.to_dict(),
        "contact_phone": blood_request.contact_phone,
        "message": "Thank you! The family has been notified. Please call them to coordinate.",
    })


@login_required
@require_POST
def api_toggle_availability(request):
    donor = get_donor(request.user)
    if donor is None:
        return JsonResponse({"ok": False, "error": "No donor profile."}, status=400)
    donor.is_available = not donor.is_available   # switch True <-> False
    donor.save()
    return JsonResponse({"ok": True, "available": donor.is_available})
