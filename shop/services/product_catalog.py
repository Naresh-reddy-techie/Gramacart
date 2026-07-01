from django.db.models import (Q,Avg,Count,Prefetch,)
from inventory.models import Inventory
from admin_dashboard.models import Product,ProductImage,ProductVariant



def _enrich_products(products):
    """
    Adds calculated fields to prefetched products.

    Uses ONLY prefetched data.
    Never queries the database.
    """

    for product in products:

        total_stock = 0
        min_price = None
        default_variant = None

        for variant in getattr(product, "active_variants", []):

            inventories = getattr(
                variant,
                "hub_inventory",
                []
            )

            variant_stock = sum(
                inv.stock
                for inv in inventories
            )

            total_stock += variant_stock

            valid_prices = [

                inv.selling_price

                for inv in inventories

                if inv.selling_price is not None

            ]

            if not valid_prices and getattr(
                variant,
                "price",
                None
            ):
                valid_prices.append(
                    variant.price
                )

            if valid_prices:

                current_price = min(
                    valid_prices
                )

                if (
                    min_price is None
                    or
                    current_price < min_price
                ):

                    min_price = current_price
                    default_variant = variant

        product.total_stock = total_stock

        product.min_price_value = min_price

        product.default_variant_value = default_variant

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

    inventory_qs = Inventory.objects.select_related(
        "shop",
        "variant",
        "variant__product",
    ).filter(
        shop__hub=hub,
        shop__is_active=True,
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

    inventory_qs = Inventory.objects.select_related(
        "shop",
        "variant",
        "variant__product",
    ).filter(
        shop__hub=hub,
        shop__is_active=True,
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