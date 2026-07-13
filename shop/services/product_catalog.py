from django.db.models import (Q,Avg,Count,Prefetch,)
from inventory.models import Inventory
from admin_dashboard.models import Product,ProductImage,ProductVariant

from decimal import Decimal


def _enrich_products(products):
    """
    Enrich prefetched products.

    Uses ONLY prefetched data.
    Executes ZERO additional queries.
    """

    for product in products:

        total_stock = 0

        best_inventory = None
        best_variant = None

        min_price = None

        for variant in getattr(product, "active_variants", []):

            inventories = getattr(
                variant,
                "hub_inventory",
                []
            )

            if not inventories:
                continue

            variant_stock = sum(
                inv.stock or 0
                for inv in inventories
            )

            total_stock += variant_stock

            valid_inventories = [
                inv
                for inv in inventories
                if inv.selling_price is not None
            ]

            if not valid_inventories:
                continue

            cheapest_inventory = min(
                valid_inventories,
                key=lambda x: x.selling_price
            )

            if (
                min_price is None
                or
                cheapest_inventory.selling_price < min_price
            ):
                min_price = cheapest_inventory.selling_price
                best_inventory = cheapest_inventory
                best_variant = variant

        # --------------------------------------------------
        # Basic
        # --------------------------------------------------

        product.total_stock = total_stock

        # product.min_price_value = (
        #     best_inventory.selling_price
        #     if best_inventory
        #     else None
        # )

        # product.default_variant_value = best_variant


        # Lowest selling price
        product.min_price_value = (
            best_inventory.selling_price
            if best_inventory
            else None
        )

        # Backward compatibility
        product.hub_price = product.min_price_value

        product.default_variant_value = best_variant

        if best_inventory:
            product.hub_mrp = best_inventory.mrp
        else:
            product.hub_mrp = None

        # --------------------------------------------------
        # Pricing
        # --------------------------------------------------

        if best_inventory:

            product.min_mrp_value = best_inventory.mrp

            product.discount_percentage = (
                best_inventory.discount_percentage
            )

            if (
                best_inventory.discount_percentage > 0
                and best_inventory.offer_label
            ):
                product.offer_label = best_inventory.get_offer_label_display()
            else:
                product.offer_label = ""

            product.has_offer = (
                best_inventory.discount_percentage > 0
            )

            product.save_amount = (
                best_inventory.mrp
                - best_inventory.selling_price
            )

            product.has_offer = (
                product.discount_percentage > 0
            )

        else:

            product.min_mrp_value = None
            product.discount_percentage = 0
            product.offer_label = ""
            product.save_amount = Decimal("0.00")
            product.has_offer = False

        # --------------------------------------------------
        # Image
        # --------------------------------------------------

        product.first_image = next(
            iter(product.product_images.all()),
            None
        )

    return products



# =========================================================
# HUB PRODUCTS
# =========================================================

def get_hub_products(hub, query=None, category_slug=None):

    # -----------------------------------------------------
    # INVENTORY FOR CURRENT HUB
    # -----------------------------------------------------

    # inventory_qs = Inventory.objects.select_related(
    #     "shop",
    #     "variant",
    #     "variant__product",
    # ).filter(
    #     shop__hub=hub,
    #     shop__is_active=True,
    # )


    inventory_qs = Inventory.objects.select_related(
        "shop",
        "variant",
        "variant__product",
    ).filter(
        shop__hub=hub,
        shop__is_active=True,
        selling_price__isnull=False,
    )

    # -----------------------------------------------------
    # BASE PRODUCTS
    # -----------------------------------------------------

    products = Product.objects.filter(
        is_active=True
    ).select_related(
        "category"
    )

    # -----------------------------------------------------
    # CATEGORY FILTER
    # -----------------------------------------------------

    if category_slug:
        products = products.filter(
            category__slug=category_slug
        )

    # -----------------------------------------------------
    # SEARCH FILTER
    # -----------------------------------------------------

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )

    # -----------------------------------------------------
    # RATINGS
    # -----------------------------------------------------

    products = products.annotate(
        avg_rating_value=Avg("ratings__score"),
        rating_count_value=Count("ratings", distinct=True),
    )

    # -----------------------------------------------------
    # PREFETCH
    # -----------------------------------------------------

    products = products.prefetch_related(

        Prefetch(
            "product_images",
            queryset=ProductImage.objects.all()
        ),

        Prefetch(
            "variants",
            queryset=ProductVariant.objects.filter(
                is_active=True
            ).prefetch_related(

                Prefetch(
                    "inventory_items",
                    queryset=inventory_qs,
                    to_attr="hub_inventory"
                )

            ),
            to_attr="active_variants"
        )
    )

    return _enrich_products(products)

# =========================================================
# SIMILAR PRODUCTS
# =========================================================

def get_similar_products(product, hub, limit=8):

    # inventory_qs = Inventory.objects.select_related(
    #     "shop",
    #     "variant",
    #     "variant__product",
    # ).filter(
    #     shop__hub=hub,
    #     shop__is_active=True,
    # )

    inventory_qs = Inventory.objects.select_related(
        "shop",
        "variant",
        "variant__product",
    ).filter(
        shop__hub=hub,
        shop__is_active=True,
        selling_price__isnull=False,
    )

    products = (
        Product.objects.filter(
            is_active=True,
            category=product.category,
        )
        .exclude(id=product.id)
        .select_related("category")
        .annotate(
            avg_rating_value=Avg("ratings__score"),
            rating_count_value=Count("ratings", distinct=True),
        )
        .prefetch_related(

            Prefetch(
                "product_images",
                queryset=ProductImage.objects.all(),
            ),

            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(
                    is_active=True
                ).prefetch_related(

                    Prefetch(
                        "inventory_items",
                        queryset=inventory_qs,
                        to_attr="hub_inventory",
                    )

                ),
                to_attr="active_variants",
            ),

        )[:limit]
    )

    return _enrich_products(products)