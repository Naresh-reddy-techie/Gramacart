from django.urls import path
from . import views

urlpatterns = [

    path(
        "shop-settlements/",
        views.shop_settlement_list,
        name="settlement_list"
    ),

    path(
        "shop-wallets/",
        views.shop_wallet_list,
        name="shop_wallet_list"
    ),
    path(
        "shop-wallets/<int:wallet_id>/",
        views.shop_wallet_detail,
        name="shop_wallet_detail"
    ),
    path(
        "shop-wallets/<int:wallet_id>/pay/",
        views.shop_wallet_pay,
        name="shop_wallet_pay"
    ),

]