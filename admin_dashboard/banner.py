from django.shortcuts  import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db import models as db_models
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import Banner, DeliveryHub
from .forms  import BannerForm


# ─────────────────────────────────────────────
# HELPER — shared banner queryset logic
# ─────────────────────────────────────────────

def get_live_banners_for_hub(hub_id, page_slot):
    """
    Returns banners that are:
      - active
      - scoped to this hub OR global (hub=null)
      - for the correct page slot
    Applies is_live() schedule check in Python.
    Capped at 5 to avoid dumping everything on one page.
    """
    qs = Banner.objects.filter(
        is_active=True,
        page__in=[page_slot, 'all'],
    ).filter(
        db_models.Q(hub_id=hub_id) | db_models.Q(hub__isnull=True)
    ).select_related('hub').order_by('order', '-start_date')

    return [b for b in qs if b.is_live()][:5]


# ─────────────────────────────────────────────
# PUBLIC — used inside public_dashboard view
# ─────────────────────────────────────────────

def get_dashboard_banners(active_hub_id):
    return get_live_banners_for_hub(active_hub_id, 'shop')


# ─────────────────────────────────────────────
# CLICK TRACKING
# ─────────────────────────────────────────────

@require_POST
def banner_click(request, pk):
    """
    Increments click counter atomically then redirects.
    Using F() avoids race conditions under concurrent traffic.
    """
    Banner.objects.filter(pk=pk).update(
        click_count=db_models.F('click_count') + 1
    )
    banner = get_object_or_404(Banner, pk=pk)
    return redirect(banner.cta_url or '/shop/')


# ─────────────────────────────────────────────
# ADMIN — LIST
# ─────────────────────────────────────────────

@staff_member_required
def banner_list(request):

    qs = Banner.objects.select_related('hub').order_by('order', '-start_date')

    # filters
    hub_id      = request.GET.get('hub')
    page_slot   = request.GET.get('page')
    banner_type = request.GET.get('type')
    status      = request.GET.get('status')

    if hub_id:
        if hub_id == 'global':
            qs = qs.filter(hub__isnull=True)
        else:
            qs = qs.filter(hub_id=hub_id)

    if page_slot:
        qs = qs.filter(page=page_slot)

    if banner_type:
        qs = qs.filter(banner_type=banner_type)

    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)

    # pagination — 20 per page is enough for this admin view
    paginator = Paginator(qs, 20)
    page_obj  = paginator.get_page(request.GET.get('page_num', 1))

    context = {
        'page_obj':   page_obj,
        'banners':    page_obj.object_list,
        'hubs':       DeliveryHub.objects.filter(is_active=True).order_by('name'),
        'now':        timezone.now(),
        'page_choices':        Banner.PAGE_CHOICES,
        'type_choices':        Banner.TYPE_CHOICES,
        # preserve active filters in template
        'filter_hub':          hub_id      or '',
        'filter_page':         page_slot   or '',
        'filter_type':         banner_type or '',
        'filter_status':       status      or '',
    }
    return render(request, 'banners/banner_list.html', context)


# ─────────────────────────────────────────────
# ADMIN — CREATE
# ─────────────────────────────────────────────

@staff_member_required
def banner_create(request):
    form = BannerForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if form.is_valid():
            banner = form.save()
            messages.success(
                request,
                f'Banner "{banner.title}" created successfully.'
            )
            return redirect('banner_list')
        messages.error(request, 'Please fix the errors below.')

    return render(request, 'banners/banner_form.html', {
        'form':  form,
        'title': 'Create Banner',
    })


# ─────────────────────────────────────────────
# ADMIN — EDIT
# ─────────────────────────────────────────────

@staff_member_required
def banner_edit(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    form   = BannerForm(
        request.POST  or None,
        request.FILES or None,
        instance=banner,
    )

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Banner "{banner.title}" updated successfully.'
            )
            return redirect('banner_list')
        messages.error(request, 'Please fix the errors below.')

    return render(request, 'banners/banner_form.html', {
        'form':   form,
        'banner': banner,
        'title':  f'Edit — {banner.title}',
    })


# ─────────────────────────────────────────────
# ADMIN — DELETE
# ─────────────────────────────────────────────

@staff_member_required
def banner_delete(request, pk):
    banner = get_object_or_404(Banner, pk=pk)

    if request.method == 'POST':
        title = banner.title
        banner.delete()
        messages.success(request, f'Banner "{title}" deleted.')
        return redirect('banner_list')

    return render(request, 'banners/banner_confirm_delete.html', {
        'banner': banner,
    })


# ─────────────────────────────────────────────
# ADMIN — TOGGLE ACTIVE (AJAX-friendly)
# ─────────────────────────────────────────────

@staff_member_required
@require_POST
def banner_toggle(request, pk):
    banner           = get_object_or_404(Banner, pk=pk)
    banner.is_active = not banner.is_active
    banner.save(update_fields=['is_active'])
    status = 'activated' if banner.is_active else 'deactivated'
    messages.success(request, f'"{banner.title}" {status}.')
    return redirect('banner_list')


# ─────────────────────────────────────────────
# ADMIN — DUPLICATE
# ─────────────────────────────────────────────

@staff_member_required
@require_POST
def banner_duplicate(request, pk):
    """
    One-click duplicate — useful for running the same
    promo across multiple hubs without re-entering data.
    """
    original      = get_object_or_404(Banner, pk=pk)
    original.pk   = None          # clears PK → forces INSERT
    original.title = f'{original.title} (copy)'
    original.is_active    = False  # start inactive so admin can review
    original.click_count  = 0
    original.impression_count = 0
    original.save()
    messages.success(
        request,
        f'Duplicated as "{original.title}" — edit and activate when ready.'
    )
    return redirect('banner_edit', pk=original.pk)