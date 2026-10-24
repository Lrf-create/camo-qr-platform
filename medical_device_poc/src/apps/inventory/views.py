from __future__ import annotations

from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render

from apps.inventory.forms import InstrumentBoxForm, InstrumentTypeForm
from apps.inventory.models import BoxInventory, InstrumentBox, InstrumentType
from apps.inventory.services import (
    can_edit_box_inventory,
    create_box_with_default_inventory,
    create_instrument_type_with_default_inventory,
    delete_box,
    delete_instrument_type,
    parse_inventory_quantities,
    save_box_inventory,
)


@login_required
def instrument_types(request):
    inventory_summary = {
        row["instrument_type_id"]: row
        for row in BoxInventory.objects.values("instrument_type_id").annotate(
            total_num=Sum("expected_num"),
            box_count=Count("box", distinct=True),
        )
    }
    instrument_rows = []
    for instrument_type in InstrumentType.objects.order_by("type_code"):
        summary = inventory_summary.get(instrument_type.id, {})
        instrument_rows.append(
            {
                "instrument_type": instrument_type,
                "total_num": summary.get("total_num") or 0,
                "box_count": summary.get("box_count") or 0,
            }
        )
    return render(request, "inventory/instrument_types.html", {"instrument_rows": instrument_rows})


@login_required
def create_instrument_type(request):
    if request.method == "POST":
        form = InstrumentTypeForm(request.POST)
        if form.is_valid():
            create_instrument_type_with_default_inventory(form.save(commit=False))
            messages.success(request, "器械种类已创建。")
            return redirect("inventory:instrument_types")
    else:
        form = InstrumentTypeForm()
    return render(
        request,
        "inventory/instrument_type_form.html",
        {"form": form, "form_title": "新增器械种类", "submit_label": "创建"},
    )


@login_required
def edit_instrument_type(request, instrument_type_id: int):
    instrument_type = get_object_or_404(InstrumentType, id=instrument_type_id)
    if request.method == "POST":
        form = InstrumentTypeForm(request.POST, instance=instrument_type)
        if form.is_valid():
            form.save()
            messages.success(request, "器械种类已保存。")
            return redirect("inventory:instrument_types")
    else:
        form = InstrumentTypeForm(instance=instrument_type)
    return render(
        request,
        "inventory/instrument_type_form.html",
        {"form": form, "form_title": "编辑器械种类", "submit_label": "保存"},
    )


@login_required
def delete_instrument_type_view(request, instrument_type_id: int):
    instrument_type = get_object_or_404(InstrumentType, id=instrument_type_id)
    if request.method == "POST":
        success, message = delete_instrument_type(instrument_type)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    return redirect("inventory:instrument_types")


@login_required
def boxes(request):
    boxes_qs = InstrumentBox.objects.prefetch_related("inventory_items__instrument_type").order_by("box_code")
    status_counts = {
        row["status"]: row["total"]
        for row in InstrumentBox.objects.values("status").annotate(total=Count("id"))
    }
    context = {
        "boxes": boxes_qs,
        "status_counts": [
            {"status": status, "label": label, "count": status_counts.get(status, 0)}
            for status, label in InstrumentBox.BoxStatus.choices
        ],
    }
    return render(request, "inventory/boxes.html", context)


@login_required
def create_box(request):
    if request.method == "POST":
        form = InstrumentBoxForm(request.POST)
        if form.is_valid():
            create_box_with_default_inventory(form.save(commit=False))
            messages.success(request, "器械框已创建。")
            return redirect("inventory:boxes")
    else:
        form = InstrumentBoxForm()
    return render(
        request,
        "inventory/box_form.html",
        {"form": form, "form_title": "新增器械框", "submit_label": "创建", "box": None},
    )


@login_required
def edit_box(request, box_id: int):
    box = get_object_or_404(InstrumentBox, id=box_id)
    if request.method == "POST":
        form = InstrumentBoxForm(request.POST, instance=box)
        if form.is_valid():
            form.save()
            messages.success(request, "器械框资料已保存。")
            return redirect("inventory:boxes")
    else:
        form = InstrumentBoxForm(instance=box)
    return render(
        request,
        "inventory/box_form.html",
        {"form": form, "form_title": "编辑器械框", "submit_label": "保存", "box": box},
    )


@login_required
def delete_box_view(request, box_id: int):
    box = get_object_or_404(InstrumentBox, id=box_id)
    if request.method == "POST":
        success, message = delete_box(box)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
    return redirect("inventory:boxes")


@login_required
def edit_box_inventory(request, box_id: int):
    box = get_object_or_404(
        InstrumentBox.objects.prefetch_related("inventory_items__instrument_type"),
        id=box_id,
    )
    is_editable = can_edit_box_inventory(box)
    instrument_types = list(InstrumentType.objects.order_by("type_code"))
    existing_items = {item.instrument_type_id: item for item in box.inventory_items.all()}

    if request.method == "POST":
        if not is_editable:
            messages.error(request, "只有在库状态的器械框可以修改配置。")
            return redirect("inventory:edit_box_inventory", box_id=box.id)

        quantities, errors = parse_inventory_quantities(request.POST, instrument_types)
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            save_box_inventory(box, instrument_types, quantities)
            messages.success(request, "器械框配置已保存。")
            return redirect("inventory:boxes")
    else:
        quantities = {
            instrument_type.id: existing_items.get(instrument_type.id).expected_num
            if instrument_type.id in existing_items
            else 0
            for instrument_type in instrument_types
        }

    rows = [
        {
            "instrument_type": instrument_type,
            "num": quantities.get(instrument_type.id, 0),
            "field_name": f"num_{instrument_type.id}",
        }
        for instrument_type in instrument_types
    ]
    context = {
        "box": box,
        "rows": rows,
        "is_editable": is_editable,
    }
    return render(request, "inventory/edit_box_inventory.html", context)


@login_required
def status_query(request):
    summary = defaultdict(lambda: {"IN_STOCK": 0, "OUTBOUND": 0, "INBOUND": 0, "total": 0})
    inventory_rows = BoxInventory.objects.select_related("box", "instrument_type").order_by(
        "instrument_type__type_code",
        "box__box_code",
    )
    for item in inventory_rows:
        row = summary[item.instrument_type_id]
        row["instrument_type"] = item.instrument_type
        row[item.box.status] += item.expected_num
        row["total"] += item.expected_num

    status_rows = []
    for instrument_type in InstrumentType.objects.order_by("type_code"):
        row = summary[instrument_type.id]
        row.setdefault("instrument_type", instrument_type)
        status_rows.append(row)

    return render(request, "inventory/status_query.html", {"status_rows": status_rows})
