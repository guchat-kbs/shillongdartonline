from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from django.db import transaction

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth.models import User

from django.shortcuts import get_object_or_404

from .models import Entry
from .serializers import EntrySerializer

from django.contrib.auth.decorators import login_required


def is_master(user):
    return (
        user.is_authenticated
        and user.groups.filter(name="Master").exists()
    )


@login_required
def home(request):

    if is_master(request.user):
        return redirect("master")

    return render(request, "home.html")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def entries_api(request):

    today = timezone.localdate()

    if request.method == "GET":

        entry_type = request.query_params.get("type", "FR").upper()

        if entry_type not in ["FR", "SR"]:
            return Response(
                {"error": "Invalid entry type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entries = list(
            Entry.objects
            .filter(
                business_date=today,
                entry_type=entry_type,
                owner=request.user,
            )
            .order_by("-created_at")
        )

        serializer = EntrySerializer(entries, many=True)

        # Sum in Python from the rows we already fetched instead of
        # issuing a second SUM(...) query — one DB round trip
        # instead of two.
        total = sum(
            (entry.amount for entry in entries),
            Decimal("0"),
        )

        return Response({
            "entry_type": entry_type,
            "date": today,
            "entries": serializer.data,
            "grand_total": total,
        })

    # POST

    data = request.data

    if not isinstance(data, list):
        return Response(
            {"error": "Expected a list of entries."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(data) == 0:
        return Response(
            {"error": "No entries provided."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(data) > 15:
        return Response(
            {"error": "Maximum 15 entries allowed at once."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    created_items = []

    for item in data:

        entry_type = item.get("entry_type", "").upper()

        if entry_type not in ["FR", "SR"]:
            return Response(
                {"error": "Invalid entry type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EntrySerializer(
            data={
                "entry_type": entry_type,
                "number": item.get("number", ""),
                "amount": item.get("amount"),
            }
        )

        serializer.is_valid(raise_exception=True)

        created_items.append(
            Entry(
                owner=request.user,
                entry_type=entry_type,
                number=serializer.validated_data["number"],
                amount=serializer.validated_data["amount"],
                business_date=today,
            )
        )

    with transaction.atomic():

        created_entries = Entry.objects.bulk_create(
            created_items
        )

    return Response(
        EntrySerializer(
            created_entries,
            many=True,
        ).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def house_api(request):

    data = request.data

    if not isinstance(data, list):
        return Response(
            {"error": "Expected a list of House entries."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(data) == 0:
        return Response(
            {"error": "No House entries provided."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(data) > 3:
        return Response(
            {"error": "Maximum 3 House entries allowed at once."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    today = timezone.localdate()

    entries_to_create = []

    for item in data:

        entry_type = item.get("entry_type", "").upper()
        house = str(item.get("house", "")).strip()
        amount = item.get("amount")

        if entry_type not in ["FR", "SR"]:
            return Response(
                {"error": "Invalid entry type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not house.isdigit() or len(house) != 1:
            return Response(
                {"error": "House must be a single digit from 0 to 9."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for ending in range(10):

            number = f"{house}{ending}"

            entries_to_create.append(
                Entry(
                    owner=request.user,
                    entry_type=entry_type,
                    number=number,
                    amount=amount,
                    business_date=today,
                )
            )

    with transaction.atomic():

        created_entries = Entry.objects.bulk_create(
            entries_to_create
        )

    return Response(
        {
            "message": (
                f"{len(created_entries)} entries created successfully."
            ),
            "entries": EntrySerializer(
                created_entries,
                many=True,
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ending_api(request):

    data = request.data

    if not isinstance(data, list):
        return Response(
            {"error": "Expected a list of Ending entries."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(data) == 0:
        return Response(
            {"error": "No Ending entries provided."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(data) > 3:
        return Response(
            {"error": "Maximum 3 Ending entries allowed at once."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    today = timezone.localdate()

    entries_to_create = []

    for item in data:

        entry_type = item.get("entry_type", "").upper()
        ending = str(item.get("ending", "")).strip()
        amount = item.get("amount")

        if entry_type not in ["FR", "SR"]:
            return Response(
                {"error": "Invalid entry type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ending.isdigit() or len(ending) != 1:
            return Response(
                {
                    "error":
                    "Ending must be a single digit from 0 to 9."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for house in range(10):

            number = f"{house}{ending}"

            entries_to_create.append(
                Entry(
                    owner=request.user,
                    entry_type=entry_type,
                    number=number,
                    amount=amount,
                    business_date=today,
                )
            )

    with transaction.atomic():

        created_entries = Entry.objects.bulk_create(
            entries_to_create
        )

    return Response(
        {
            "message": (
                f"{len(created_entries)} entries created successfully."
            ),
            "entries": EntrySerializer(
                created_entries,
                many=True,
            ).data,
        },
        status=status.HTTP_201_CREATED,
    )

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_entry(request, pk):

    today = timezone.localdate()

    entry = get_object_or_404(
        Entry,
        id=pk,
        business_date=today,
        owner=request.user,
    )

    entry.delete()

    return Response(
        {
            "message": "Entry deleted successfully."
        },
        status=status.HTTP_200_OK,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def master_total_api(request):

    if not request.user.groups.filter(
        name="Master"
    ).exists():

        return Response(
            {"error": "Master access required."},
            status=status.HTTP_403_FORBIDDEN,
        )


    entry_type = request.query_params.get(
        "type",
        "FR",
    ).upper()


    if entry_type not in ["FR", "SR"]:

        return Response(
            {"error": "Invalid entry type."},
            status=status.HTTP_400_BAD_REQUEST,
        )


    today = timezone.localdate()

    # Master totals must use the same user population as USERS DATA:
    # only users who are NOT in the Master group.
    # This keeps FR/SR entry counts and amounts consistent with
    # the totals shown in USERS DATA.
    normal_user_ids = (
        User.objects
        .exclude(groups__name="Master")
        .values_list("id", flat=True)
    )

    base_qs = Entry.objects.filter(
        business_date=today,
        owner_id__in=normal_user_ids,
    )

    # Per-number breakdown, computed in the database with a single
    # GROUP BY instead of pulling every row and summing in Python.
    # Only numbers that actually have entries are returned.
    number_breakdown = (
        base_qs
        .filter(entry_type=entry_type)
        .values("number")
        .annotate(
            total_amount=Sum("amount"),
            total_entries=Count("id"),
        )
    )

    by_number = {
        row["number"].strip().zfill(2): {
            "total_amount": row["total_amount"] or 0,
            "total_entries": row["total_entries"],
        }
        for row in number_breakdown
    }

    # FR and SR totals in a single query via conditional aggregation,
    # instead of two separate round trips.
    totals = base_qs.aggregate(
        fr_total=Sum("amount", filter=Q(entry_type="FR")),
        sr_total=Sum("amount", filter=Q(entry_type="SR")),
    )

    fr_total = totals["fr_total"] or 0
    sr_total = totals["sr_total"] or 0
    overall_total = fr_total + sr_total

    total = fr_total if entry_type == "FR" else sr_total

    return Response({
        "entry_type": entry_type,
        "date": today,
        "grand_total": total,
        "fr_total": fr_total,
        "sr_total": sr_total,
        "overall_total": overall_total,
        "by_number": by_number,
    })



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def master_users_data_api(request):

    if not request.user.groups.filter(
        name="Master"
    ).exists():

        return Response(
            {"error": "Master access required."},
            status=status.HTTP_403_FORBIDDEN,
        )


    today = timezone.localdate()


    # Get all registered users except Master users.
    users = (
        User.objects
        .exclude(groups__name="Master")
        .order_by("username")
    )


    # Aggregate today's entries for every user
    # in one database query.
    user_totals = (
        Entry.objects
        .filter(
            business_date=today
        )
        .values("owner_id")
        .annotate(
            total_entries=Count("id"),
            total_amount=Sum("amount"),

            fr_entries=Count(
                "id",
                filter=Q(entry_type="FR")
            ),

            fr_total=Sum(
                "amount",
                filter=Q(entry_type="FR")
            ),

            sr_entries=Count(
                "id",
                filter=Q(entry_type="SR")
            ),

            sr_total=Sum(
                "amount",
                filter=Q(entry_type="SR")
            ),
        )
    )


    totals_by_user = {
        item["owner_id"]: item
        for item in user_totals
    }


    users_data = []


    for user in users:

        data = totals_by_user.get(
            user.id,
            {}
        )


        users_data.append({
            "username": user.username,

            "fr_entries":
                data.get("fr_entries", 0)
                or 0,

            "fr_total":
                data.get("fr_total", 0)
                or 0,

            "sr_entries":
                data.get("sr_entries", 0)
                or 0,

            "sr_total":
                data.get("sr_total", 0)
                or 0,

            "total_entries":
                data.get("total_entries", 0)
                or 0,

            "total_amount":
                data.get("total_amount", 0)
                or 0,
        })


    return Response({
        "date": today,
        "users": users_data,
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_all_entries_api(request):

    if not request.user.groups.filter(name="Master").exists():
        return Response(
            {"error": "Master access required."},
            status=status.HTTP_403_FORBIDDEN,
        )

    confirmation = str(
        request.data.get("confirmation", "")
    ).strip()

    if confirmation != "DELETE ALL DATA":
        return Response(
            {
                "error": (
                    'Confirmation failed. '
                    'You must enter "DELETE ALL DATA".'
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    deleted_count, _ = Entry.objects.all().delete()

    return Response(
        {
            "message": "All entry data has been permanently deleted.",
            "deleted_entries": deleted_count,
        },
        status=status.HTTP_200_OK,
    )