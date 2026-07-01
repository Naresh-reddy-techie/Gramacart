from io import BytesIO

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
)
from inventory.models import Inventory
from admin_dashboard.models import CompanyInfo
from collections import OrderedDict

class CatalogueGenerator:
    """
    Generates a product catalogue for a Delivery Hub.

    Flow:
        DeliveryHub
            ↓
        Shops
            ↓
        Inventory
            ↓
        Product Variant
            ↓
        Product
            ↓
        Category
    """

    def __init__(self, hub):
        self.hub = hub
        self.company = CompanyInfo.objects.first()

    def generate(self):

        buffer = BytesIO()

        doc = SimpleDocTemplate(buffer)

        styles = getSampleStyleSheet()

        story = []

        # Always load catalogue data first
        categories = self.group_inventory_by_category()

        # --------------------------------------------------
        # COMPANY
        # --------------------------------------------------

        if self.company:

            story.append(
                Paragraph(
                    self.company.name,
                    styles["Heading1"]
                )
            )

            story.append(
                Paragraph(
                    f"Categories : {len(categories)}",
                    styles["Heading2"]
                )
            )

            if self.company.tagline:
                story.append(
                    Paragraph(
                        self.company.tagline,
                        styles["Normal"]
                    )
                )

            if self.company.phone:
                story.append(
                    Paragraph(
                        f"Phone : {self.company.phone}",
                        styles["Normal"]
                    )
                )
    
    def get_inventory(self):

        return (
            Inventory.objects
            .filter(
                shop__hub=self.hub,
                shop__is_active=True,
                stock__gt=0,
                variant__is_active=True,
                variant__product__is_active=True,
            )
            .select_related(
                "shop",
                "variant",
                "variant__product",
                "variant__product__category",
            )
            .prefetch_related(
                "variant__product__product_images",
            )
            .order_by(
                "variant__product__category__name",
                "variant__product__name",
            )
        )
    
    def group_inventory_by_category(self):

        grouped = OrderedDict()

        for item in self.get_inventory():

            category = item.variant.product.category

            if category.id not in grouped:

                grouped[category.id] = {
                    "category": category,
                    "products": []
                }

            grouped[category.id]["products"].append(item)

        return grouped