from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.text import slugify

from .models import (
    Address,
    Brand,
    Cart,
    CartItem,
    Category,
    DeliveryPoint,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    Review,
    Seller,
    User,
    Wishlist,
)


class AuthenticationFlowTests(TestCase):
    password = "StrongPass2026!"

    def setUp(self):
        self.user = User.objects.create_user(
            email="aziza@example.com",
            username="aziza",
            password=self.password,
            first_name="Aziza",
            last_name="Karimova",
            phone="+998901234567",
        )

    def test_main_page_is_public(self):
        response = self.client.get(reverse("apps:index"))
        self.assertEqual(response.status_code, 200)

    def test_checkout_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("apps:checkout"))
        expected = f"{reverse('apps:login')}?next={reverse('apps:checkout')}"
        self.assertRedirects(response, expected)

    def test_login_uses_email_and_redirects_to_next(self):
        response = self.client.post(
            reverse("apps:login"),
            {"username": self.user.email.upper(), "password": self.password, "next": reverse("apps:checkout")},
        )
        self.assertRedirects(
            response,
            reverse("apps:checkout"),
            fetch_redirect_response=False,
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("apps:login"))
        self.assertRedirects(response, reverse("apps:index"))

    def test_authenticated_user_is_redirected_away_from_registration(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("apps:signup"))
        self.assertRedirects(response, reverse("apps:index"))

    def test_registration_creates_customer_and_logs_in(self):
        response = self.client.post(reverse("apps:signup"), {
            "first_name": "Dilnoza",
            "last_name": "Rahimova",
            "email": "DILNOZA@example.com",
            "phone": "+998 91 234 56 78",
            "password1": self.password,
            "password2": self.password,
        })
        new_user = User.objects.get(email="dilnoza@example.com")
        self.assertRedirects(response, reverse("apps:index"))
        self.assertTrue(new_user.check_password(self.password))
        self.assertEqual(new_user.role, User.Role.CUSTOMER)
        self.assertEqual(new_user.phone, "+998912345678")
        self.assertEqual(int(self.client.session["_auth_user_id"]), new_user.pk)

    def test_registration_rejects_duplicate_email(self):
        response = self.client.post(reverse("apps:signup"), {
            "first_name": "Aziza",
            "last_name": "Karimova",
            "email": "AZIZA@example.com",
            "phone": "+998 90 765 43 21",
            "password1": self.password,
            "password2": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bu email bilan hisob allaqachon mavjud.")
        self.assertEqual(User.objects.filter(email__iexact="aziza@example.com").count(), 1)

    def test_registration_from_checkout_returns_to_checkout(self):
        response = self.client.post(reverse("apps:signup"), {
            "first_name": "Madina",
            "last_name": "Aliyeva",
            "email": "madina@example.com",
            "phone": "+998 93 111 22 33",
            "password1": self.password,
            "password2": self.password,
            "next": reverse("apps:checkout"),
        })
        self.assertRedirects(
            response,
            reverse("apps:checkout"),
            fetch_redirect_response=False,
        )

    def test_authenticated_user_with_empty_cart_is_redirected_from_checkout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("apps:checkout"))
        self.assertRedirects(response, reverse("apps:cart"))

    def test_logout_accepts_post_and_returns_to_main_page(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("apps:logout"))
        self.assertRedirects(response, reverse("apps:index"))
        self.assertNotIn("_auth_user_id", self.client.session)


class StorefrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user(
            email="customer@example.com",
            username="customer",
            password="StrongPass2026!",
        )
        seller_user = User.objects.create_user(
            email="seller@example.com",
            username="seller",
            password="StrongPass2026!",
            role=User.Role.SELLER,
        )
        cls.seller = Seller.objects.create(user=seller_user, store_name="Tech Store")
        cls.electronics = Category.objects.create(name="Elektronika", slug="elektronika")
        cls.phones = Category.objects.create(
            name="Smartfonlar", slug="smartfonlar", parent=cls.electronics
        )
        audio = Category.objects.create(name="Audio", slug="audio", parent=cls.electronics)
        samsung = Brand.objects.create(name="Samsung", slug="samsung")
        sony = Brand.objects.create(name="Sony", slug="sony")
        cls.discount_product = Product.objects.create(
            seller=cls.seller,
            category=cls.phones,
            brand=samsung,
            name="Samsung Galaxy Test",
            slug="samsung-galaxy-test",
            sku="TEST-SAMSUNG",
            description="5G smartfon",
            price=Decimal("800000"),
            old_price=Decimal("1000000"),
            stock=10,
        )
        cls.best_seller = Product.objects.create(
            seller=cls.seller,
            category=audio,
            brand=sony,
            name="Sony Headphones Test",
            slug="sony-headphones-test",
            sku="TEST-SONY",
            price=Decimal("1200000"),
            stock=10,
        )
        order = Order.objects.create(
            user=cls.customer,
            order_number="ZT-TEST-1",
            status=Order.Status.DELIVERED,
        )
        OrderItem.objects.create(
            order=order,
            product=cls.discount_product,
            seller=cls.seller,
            product_name=cls.discount_product.name,
            price=cls.discount_product.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=order,
            product=cls.best_seller,
            seller=cls.seller,
            product_name=cls.best_seller.name,
            price=cls.best_seller.price,
            quantity=5,
        )
        Review.objects.create(
            user=cls.customer,
            product=cls.discount_product,
            order=order,
            rating=5,
            text="A'lo mahsulot",
        )
        Review.objects.create(
            user=cls.customer,
            product=cls.best_seller,
            order=order,
            rating=3,
            text="Yaxshi",
        )

    def test_homepage_uses_dynamic_catalog_and_product_sections(self):
        response = self.client.get(reverse("apps:index"))

        self.assertContains(response, "Smartfonlar")
        self.assertContains(response, self.discount_product.name)
        self.assertEqual(response.context["best_sellers"][0], self.best_seller)
        self.assertEqual(response.context["popular_brands"][0].name, "Sony")

    def test_search_finds_products_by_name_case_insensitively(self):
        response = self.client.get(reverse("apps:search"), {"q": "galaxy"})

        self.assertContains(response, self.discount_product.name)
        self.assertNotContains(response, self.best_seller.name)
        self.assertEqual(response.context["result_count"], 1)

    def test_search_suggestions_return_matching_product_data(self):
        response = self.client.get(
            reverse("apps:search-suggestions"), {"q": "samsung"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "name": self.discount_product.name,
                    "url": reverse(
                        "apps:product", kwargs={"slug": self.discount_product.slug}
                    ),
                    "image_url": "",
                    "price": f"{self.discount_product.price:.2f}",
                    "category": self.phones.name,
                }
            ],
        )

    def test_search_suggestions_require_two_characters_and_exclude_inactive_products(self):
        self.discount_product.is_active = False
        self.discount_product.save(update_fields=("is_active",))

        short_query = self.client.get(
            reverse("apps:search-suggestions"), {"q": "s"}
        )
        inactive_query = self.client.get(
            reverse("apps:search-suggestions"), {"q": "samsung"}
        )

        self.assertEqual(short_query.json(), {"results": []})
        self.assertEqual(inactive_query.json(), {"results": []})

    def test_header_search_exposes_ajax_suggestions_endpoint(self):
        response = self.client.get(reverse("apps:index"))

        self.assertContains(response, "data-search-form")
        self.assertContains(
            response,
            f'data-suggestions-url="{reverse("apps:search-suggestions")}"',
        )

    def test_search_can_filter_by_category_brand_and_discount(self):
        category_response = self.client.get(reverse("apps:search"), {"category": "audio"})
        brand_response = self.client.get(reverse("apps:search"), {"brand": "samsung"})
        discount_response = self.client.get(reverse("apps:search"), {"discount": "1"})

        self.assertContains(category_response, self.best_seller.name)
        self.assertContains(brand_response, self.discount_product.name)
        self.assertContains(discount_response, self.discount_product.name)
        self.assertNotContains(discount_response, self.best_seller.name)

    def test_catalog_lists_database_categories(self):
        response = self.client.get(reverse("apps:catalog"))

        self.assertContains(response, "Smartfonlar")
        self.assertContains(response, "Audio")

    def test_category_url_uses_slug_and_database_context(self):
        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.phones.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["category"], self.phones)
        self.assertEqual(response.context["parent_category"], self.electronics)
        self.assertEqual(
            [item.slug for item in response.context["breadcrumbs"]],
            ["elektronika", "smartfonlar"],
        )
        self.assertEqual(response.context["product_count"], 1)
        self.assertContains(response, self.discount_product.name)

    def test_parent_category_includes_descendant_products_and_children(self):
        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.electronics.slug})
        )

        self.assertEqual(response.context["product_count"], 2)
        self.assertContains(response, "Smartfonlar")
        self.assertContains(response, "Audio")
        self.assertContains(response, self.discount_product.name)
        self.assertContains(response, self.best_seller.name)

    def test_inactive_and_out_of_stock_products_are_excluded_from_category(self):
        Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Inactive phone",
            slug="inactive-phone",
            sku="INACTIVE-PHONE",
            price=Decimal("100000"),
            stock=5,
            is_active=False,
        )
        Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Out of stock phone",
            slug="out-of-stock-phone",
            sku="OUT-OF-STOCK-PHONE",
            price=Decimal("100000"),
            stock=0,
        )

        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.phones.slug})
        )

        self.assertEqual(response.context["product_count"], 1)
        self.assertNotContains(response, "Inactive phone")
        self.assertNotContains(response, "Out of stock phone")

    def test_product_and_seller_have_precise_dynamic_urls(self):
        product_response = self.client.get(
            reverse("apps:product", kwargs={"slug": self.discount_product.slug})
        )
        seller_response = self.client.get(
            reverse("apps:seller", kwargs={"pk": self.seller.pk})
        )

        self.assertEqual(product_response.status_code, 200)
        self.assertContains(product_response, self.discount_product.name)
        self.assertContains(product_response, self.seller.store_name)
        self.assertEqual(seller_response.status_code, 200)
        self.assertContains(seller_response, self.discount_product.name)

    def test_unknown_or_inactive_detail_objects_return_404(self):
        self.seller.is_active = False
        self.seller.save(update_fields=("is_active",))

        self.assertEqual(self.client.get("/category/unknown/").status_code, 404)
        self.assertEqual(self.client.get("/product/unknown/").status_code, 404)
        self.assertEqual(
            self.client.get(reverse("apps:seller", kwargs={"pk": self.seller.pk})).status_code,
            404,
        )

    def test_legacy_demo_urls_redirect_to_precise_urls(self):
        self.assertRedirects(
            self.client.get(reverse("apps:category-legacy")),
            reverse("apps:category", kwargs={"slug": "audio"}),
        )
        self.assertRedirects(
            self.client.get(reverse("apps:product-legacy")),
            reverse("apps:product", kwargs={"slug": self.best_seller.slug}),
        )
        self.assertRedirects(
            self.client.get(reverse("apps:seller-legacy")),
            reverse("apps:seller", kwargs={"pk": self.seller.pk}),
        )

    def test_category_filters_by_brand_price_discount_and_rating(self):
        response = self.client.get(
            reverse("apps:category", kwargs={"slug": self.electronics.slug}),
            {
                "brand": "samsung",
                "min_price": "700000",
                "max_price": "900000",
                "discount": "1",
                "rating": "4",
            },
        )

        self.assertEqual(response.context["product_count"], 1)
        self.assertContains(response, self.discount_product.name)
        self.assertNotContains(response, self.best_seller.name)
        self.assertEqual(response.context["filter_state"]["brand"], "samsung")
        self.assertEqual(response.context["filter_state"]["rating"], 4)

    def test_availability_filter_can_show_out_of_stock_products(self):
        unavailable = Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Unavailable Galaxy",
            slug="unavailable-galaxy",
            sku="UNAVAILABLE-GALAXY",
            price=Decimal("500000"),
            stock=0,
        )

        default_response = self.client.get(reverse("apps:search"), {"q": "Galaxy"})
        unavailable_response = self.client.get(
            reverse("apps:search"),
            {"q": "Galaxy", "availability": "out_of_stock"},
        )

        self.assertNotContains(default_response, unavailable.name)
        self.assertContains(unavailable_response, unavailable.name)
        self.assertNotContains(unavailable_response, self.discount_product.name)

    def test_sorting_supports_popular_price_rating_and_newest(self):
        url = reverse("apps:category", kwargs={"slug": self.electronics.slug})

        popular = self.client.get(url, {"sort": "popular"})
        cheapest = self.client.get(url, {"sort": "price_asc"})
        expensive = self.client.get(url, {"sort": "price_desc"})
        rating = self.client.get(url, {"sort": "rating"})
        newest = self.client.get(url, {"sort": "newest"})

        self.assertEqual(popular.context["products"][0], self.best_seller)
        self.assertEqual(cheapest.context["products"][0], self.discount_product)
        self.assertEqual(expensive.context["products"][0], self.best_seller)
        self.assertEqual(rating.context["products"][0], self.discount_product)
        self.assertEqual(newest.context["products"][0], self.best_seller)

    def test_category_and_search_pagination_preserve_filter_query(self):
        Product.objects.bulk_create([
            Product(
                seller=self.seller,
                category=self.phones,
                name=f"Page item {index:02d}",
                slug=f"page-item-{index:02d}",
                sku=f"PAGE-ITEM-{index:02d}",
                price=Decimal("750000") + index,
                stock=5,
            )
            for index in range(13)
        ])
        category_url = reverse("apps:category", kwargs={"slug": self.phones.slug})
        category_response = self.client.get(
            category_url,
            {"min_price": "700000", "sort": "price_asc", "page": "2"},
        )
        search_response = self.client.get(
            reverse("apps:search"),
            {"q": "Page item", "availability": "all", "sort": "newest", "page": "2"},
        )

        self.assertEqual(category_response.context["page_obj"].number, 2)
        self.assertIn("min_price=700000", category_response.context["filter_query"])
        self.assertIn("sort=price_asc", category_response.context["filter_query"])
        self.assertNotIn("page=", category_response.context["filter_query"])
        self.assertEqual(search_response.context["page_obj"].number, 2)
        self.assertIn("q=Page+item", search_response.context["filter_query"])
        self.assertIn("availability=all", search_response.context["filter_query"])

    def test_out_of_stock_product_is_accessible_and_marked_unavailable(self):
        product = Product.objects.create(
            seller=self.seller,
            category=self.phones,
            name="Out of stock vision",
            slug="out-of-stock-vision",
            sku="OUT-OF-STOCK-VISION",
            price=Decimal("740000"),
            stock=0,
        )

        response = self.client.get(reverse("apps:product", kwargs={"slug": product.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_out_of_stock"])
        self.assertEqual(response.context["display_stock"], 0)

    def test_seller_slug_route_uses_store_slug_when_available(self):
        slug = slugify(self.seller.store_name)
        response = self.client.get(reverse("apps:seller_slug", kwargs={"pk_or_slug": slug}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["seller"], self.seller)

    def test_wishlist_pages_and_toggle_require_login(self):
        wishlist_url = reverse("apps:wishlist")
        toggle_url = reverse(
            "apps:wishlist-toggle", kwargs={"product_id": self.discount_product.pk}
        )

        self.assertRedirects(
            self.client.get(wishlist_url),
            f"{reverse('apps:login')}?next={wishlist_url}",
        )
        self.assertRedirects(
            self.client.post(toggle_url),
            f"{reverse('apps:login')}?next={toggle_url}",
        )

    def test_wishlist_toggle_adds_then_removes_product(self):
        self.client.force_login(self.customer)
        url = reverse(
            "apps:wishlist-toggle", kwargs={"product_id": self.discount_product.pk}
        )

        added = self.client.post(url)
        self.assertEqual(added.status_code, 200)
        self.assertEqual(
            added.json(),
            {
                "is_wishlisted": True,
                "wishlist_count": 1,
                "message": "Sevimlilarga qo‘shildi",
            },
        )
        self.assertTrue(
            Wishlist.objects.filter(
                user=self.customer, product=self.discount_product
            ).exists()
        )

        removed = self.client.post(url)
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(removed.json()["is_wishlisted"])
        self.assertEqual(removed.json()["wishlist_count"], 0)
        self.assertFalse(Wishlist.objects.filter(user=self.customer).exists())

    def test_wishlist_toggle_only_accepts_post_and_checks_csrf(self):
        url = reverse(
            "apps:wishlist-toggle", kwargs={"product_id": self.discount_product.pk}
        )
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.customer)

        self.assertEqual(csrf_client.get(url).status_code, 405)
        self.assertEqual(csrf_client.post(url).status_code, 403)

        csrf_client.get(reverse("apps:product", kwargs={"slug": self.discount_product.slug}))
        csrf_token = csrf_client.cookies["csrftoken"].value
        response = csrf_client.post(url, HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 200)

    def test_wishlist_page_is_dynamic_and_renders_empty_state(self):
        self.client.force_login(self.customer)
        empty_response = self.client.get(reverse("apps:wishlist"))

        self.assertContains(empty_response, "Sevimlilar ro‘yxati bo‘sh")
        self.assertNotContains(empty_response, self.discount_product.name)

        Wishlist.objects.create(user=self.customer, product=self.discount_product)
        populated_response = self.client.get(reverse("apps:wishlist"))
        self.assertEqual(populated_response.context["product_count"], 1)
        self.assertContains(populated_response, self.discount_product.name)
        self.assertContains(populated_response, "1 ta mahsulot")

    def test_database_wishlist_state_is_rendered_on_cards_detail_and_header(self):
        Wishlist.objects.create(user=self.customer, product=self.discount_product)
        self.client.force_login(self.customer)

        home_response = self.client.get(reverse("apps:index"))
        detail_response = self.client.get(
            reverse("apps:product", kwargs={"slug": self.discount_product.slug})
        )

        self.assertContains(home_response, 'data-wishlist-count>1</b>')
        self.assertContains(
            home_response,
            f'data-wishlist-product="{self.discount_product.pk}"',
        )
        self.assertContains(detail_response, 'aria-pressed="true"')
        self.assertContains(detail_response, "Sevimlilardan olib tashlash")

    def test_compare_is_session_backed_and_renders_dynamic_products(self):
        add_url = reverse("apps:compare-add", kwargs={"product_id": self.discount_product.pk})
        self.assertEqual(self.client.post(add_url).status_code, 200)

        response = self.client.get(reverse("apps:compare"))
        self.assertEqual(response.context["product_count"], 1)
        self.assertContains(response, self.discount_product.name)
        self.assertContains(response, self.discount_product.sku)
        self.assertContains(response, "Brend")

        refreshed_client = Client()
        session = self.client.session
        refreshed_client.cookies["sessionid"] = session.session_key
        refreshed_response = refreshed_client.get(reverse("apps:compare"))
        self.assertContains(refreshed_response, self.discount_product.name)

    def test_compare_rejects_duplicate_different_category_and_more_than_four(self):
        same_category = [
            Product.objects.create(
                seller=self.seller,
                category=self.phones,
                name=f"Compare phone {index}",
                slug=f"compare-phone-{index}",
                sku=f"COMPARE-PHONE-{index}",
                price=Decimal("500000") + index,
                stock=5,
            )
            for index in range(1, 6)
        ]
        add = lambda product: self.client.post(
            reverse("apps:compare-add", kwargs={"product_id": product.pk})
        )

        first = add(self.discount_product)
        duplicate = add(self.discount_product)
        self.assertTrue(first.json()["is_compared"])
        self.assertFalse(duplicate.json()["changed"])
        for product in same_category[:3]:
            self.assertEqual(add(product).status_code, 200)

        limited = add(same_category[3])
        self.assertEqual(limited.status_code, 400)
        self.assertEqual(limited.json()["code"], "limit_reached")
        mismatch = add(self.best_seller)
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(mismatch.json()["code"], "category_mismatch")

    def test_compare_remove_clear_and_empty_state(self):
        add_url = reverse("apps:compare-add", kwargs={"product_id": self.discount_product.pk})
        remove_url = reverse("apps:compare-remove", kwargs={"product_id": self.discount_product.pk})
        clear_url = reverse("apps:compare-clear")

        self.assertEqual(self.client.get(add_url).status_code, 405)
        self.client.post(add_url)
        self.assertEqual(self.client.post(remove_url).json()["compare_count"], 0)
        self.assertFalse(self.client.get(reverse("apps:compare")).context["products"])
        self.client.post(add_url)
        self.assertEqual(self.client.post(clear_url).json()["compare_count"], 0)
        self.assertContains(self.client.get(reverse("apps:compare")), "Taqqoslash ro‘yxati bo‘sh")

    def test_compare_mutations_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        add_url = reverse("apps:compare-add", kwargs={"product_id": self.discount_product.pk})
        self.assertEqual(csrf_client.post(add_url).status_code, 403)

    def test_cart_requires_login_and_is_created_for_authenticated_user(self):
        cart_url = reverse("apps:cart")
        self.assertRedirects(
            self.client.get(cart_url),
            f"{reverse('apps:login')}?next={cart_url}",
        )
        self.client.force_login(self.customer)
        response = self.client.get(cart_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Cart.objects.filter(user=self.customer).exists())
        self.assertContains(response, "Savat bo‘sh")

    def test_guest_cart_add_redirects_to_login_with_original_action(self):
        add_url = reverse("apps:cart-add", kwargs={"product_id": self.discount_product.pk})
        response = self.client.post(add_url)
        self.assertRedirects(
            response,
            f"{reverse('apps:login')}?next={add_url}",
        )

    def test_cart_add_merges_items_and_stores_price_snapshot(self):
        self.client.force_login(self.customer)
        url = reverse("apps:cart-add", kwargs={"product_id": self.discount_product.pk})

        first = self.client.post(url)
        second = self.client.post(url, {"quantity": 2})

        self.assertEqual(first.json()["cart_count"], 1)
        self.assertEqual(second.json()["cart_count"], 3)
        item = CartItem.objects.get(cart__user=self.customer)
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.price, self.discount_product.price)

        self.discount_product.price = Decimal("850000")
        self.discount_product.save(update_fields=("price",))
        response = self.client.get(reverse("apps:cart"))
        self.assertContains(response, "Joriy narx")
        self.assertTrue(response.context["cart_items"][0].price_changed)
        self.assertContains(response, 'data-cart-count>3</b>')

    def test_cart_variant_price_and_stock_limits_are_enforced(self):
        variant = ProductVariant.objects.create(
            product=self.discount_product,
            name="8/256 GB",
            sku="TEST-VARIANT",
            extra_price=Decimal("50000"),
            stock=2,
        )
        self.client.force_login(self.customer)
        url = reverse("apps:cart-add", kwargs={"product_id": self.discount_product.pk})

        added = self.client.post(url, {"variant_id": variant.pk, "quantity": 2})
        blocked = self.client.post(url, {"variant_id": variant.pk})

        self.assertEqual(added.status_code, 200)
        self.assertEqual(added.json()["cart_count"], 2)
        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(blocked.json()["code"], "insufficient_stock")
        item = CartItem.objects.get(cart__user=self.customer)
        self.assertEqual(item.price, variant.final_price)

    def test_cart_update_remove_and_clear(self):
        self.client.force_login(self.customer)
        add_url = reverse("apps:cart-add", kwargs={"product_id": self.discount_product.pk})
        self.client.post(add_url, {"quantity": 2})
        item = CartItem.objects.get(cart__user=self.customer)

        updated = self.client.post(
            reverse("apps:cart-update", kwargs={"item_id": item.pk}),
            {"quantity": 3},
        )
        self.assertEqual(updated.json()["quantity"], 3)
        removed = self.client.post(
            reverse("apps:cart-remove", kwargs={"item_id": item.pk})
        )
        self.assertTrue(removed.json()["removed"])
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

        self.client.post(add_url)
        cleared = self.client.post(reverse("apps:cart-clear"))
        self.assertTrue(cleared.json()["changed"])
        self.assertFalse(CartItem.objects.filter(cart__user=self.customer).exists())

    def add_checkout_item(self):
        self.client.force_login(self.customer)
        self.client.post(
            reverse("apps:cart-add", kwargs={"product_id": self.discount_product.pk})
        )

    def checkout_token(self):
        response = self.client.get(reverse("apps:checkout"))
        return response.context["form"]["checkout_token"].value()

    def checkout_payload(self, payment_type=Order.PaymentType.CASH, **overrides):
        payload = {
            "checkout_token": self.checkout_token(),
            "delivery_type": Order.DeliveryType.ADDRESS,
            "address_mode": "new",
            "new_address_title": "Ish",
            "new_city": "Toshkent",
            "new_street": "Amir Temur ko‘chasi",
            "new_house_number": "108",
            "payment_type": payment_type,
            "phone": "+998 90 123 45 67",
            "notes": "Qo‘ng‘iroq qiling",
        }
        payload.update(overrides)
        return payload

    def test_checkout_requires_a_non_empty_cart_and_uses_server_totals(self):
        self.client.force_login(self.customer)
        self.assertRedirects(
            self.client.get(reverse("apps:checkout")),
            reverse("apps:cart"),
        )

        self.client.post(
            reverse("apps:cart-add", kwargs={"product_id": self.discount_product.pk}),
            {"quantity": 2},
        )
        response = self.client.get(reverse("apps:checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cart_quantity"], 2)
        self.assertEqual(response.context["cart_total"], Decimal("1600000"))
        self.assertEqual(response.context["delivery_fee"], Decimal("25000"))
        self.assertEqual(response.context["grand_total"], Decimal("1625000"))

    def test_checkout_validates_new_address_phone_payment_and_notes(self):
        self.add_checkout_item()
        url = reverse("apps:checkout")
        checkout_token = self.checkout_token()
        invalid = self.client.post(url, {
            "checkout_token": checkout_token,
            "delivery_type": Order.DeliveryType.ADDRESS,
            "address_mode": "new",
            "new_address_title": "",
            "new_city": "",
            "new_street": "",
            "payment_type": "unknown",
            "phone": "90 123",
            "notes": "x" * 1001,
        })

        self.assertFormError(invalid.context["form"], "new_address_title", "Manzil nomini kiriting.")
        self.assertFormError(invalid.context["form"], "new_city", "Shahar yoki hududni kiriting.")
        self.assertFormError(invalid.context["form"], "new_street", "Ko‘chani kiriting.")
        self.assertTrue(invalid.context["form"]["payment_type"].errors)
        self.assertTrue(invalid.context["form"]["phone"].errors)
        self.assertTrue(invalid.context["form"]["notes"].errors)

        valid = self.client.post(url, {
            "checkout_token": checkout_token,
            "delivery_type": Order.DeliveryType.ADDRESS,
            "address_mode": "new",
            "new_address_title": "Ish",
            "new_city": "Toshkent",
            "new_street": "Amir Temur ko‘chasi",
            "new_house_number": "108",
            "payment_type": Order.PaymentType.CASH,
            "phone": "+998 90 123 45 67",
            "notes": "Qo‘ng‘iroq qiling",
        })
        order = Order.objects.get(user=self.customer, checkout_token=checkout_token)
        self.assertRedirects(
            valid,
            reverse("apps:success", kwargs={"order_number": order.order_number}),
        )
        self.assertEqual(order.recipient_phone, "+998901234567")

    def test_checkout_rejects_another_users_address_and_inactive_point(self):
        self.add_checkout_item()
        checkout_token = self.checkout_token()
        other_user = User.objects.create_user(
            email="other@example.com",
            username="other",
            password="StrongPass2026!",
        )
        foreign_address = Address.objects.create(
            user=other_user,
            title="Uy",
            city="Toshkent",
            street="Begona ko‘cha",
            phone="+998901111111",
        )
        inactive_point = DeliveryPoint.objects.create(
            name="Yopiq punkt",
            address="Toshkent, Yashnobod",
            is_active=False,
        )

        address_response = self.client.post(reverse("apps:checkout"), {
            "checkout_token": checkout_token,
            "delivery_type": Order.DeliveryType.ADDRESS,
            "address_mode": "existing",
            "address": foreign_address.pk,
            "payment_type": Order.PaymentType.CARD,
            "phone": "+998901234567",
        })
        point_response = self.client.post(reverse("apps:checkout"), {
            "checkout_token": checkout_token,
            "delivery_type": Order.DeliveryType.PICKUP,
            "delivery_point": inactive_point.pk,
            "payment_type": Order.PaymentType.CARD,
            "phone": "+998901234567",
        })

        self.assertTrue(address_response.context["form"]["address"].errors)
        self.assertTrue(point_response.context["form"]["delivery_point"].errors)

    def test_checkout_creates_order_items_cash_payment_and_uses_current_server_price(self):
        self.add_checkout_item()
        cart_item = CartItem.objects.get(cart__user=self.customer)
        cart_item.quantity = 2
        cart_item.save(update_fields=("quantity",))
        self.discount_product.price = Decimal("850000")
        self.discount_product.save(update_fields=("price",))
        payload = self.checkout_payload(payment_type=Order.PaymentType.CASH)

        response = self.client.post(reverse("apps:checkout"), payload)

        order = Order.objects.get(user=self.customer, checkout_token=payload["checkout_token"])
        self.assertRedirects(
            response,
            reverse("apps:success", kwargs={"order_number": order.order_number}),
        )
        self.assertTrue(order.order_number.startswith("ZT-"))
        self.assertEqual(order.total, Decimal("1725000"))
        self.assertEqual(order.delivery_fee, Decimal("25000"))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.get().price, Decimal("850000"))
        self.assertEqual(order.items.get().sku, self.discount_product.sku)
        self.assertEqual(order.payment.amount, order.total)
        self.assertEqual(order.payment.status, Payment.Status.CASH_ON_DELIVERY)
        self.discount_product.refresh_from_db()
        self.assertEqual(self.discount_product.stock, 8)
        self.assertFalse(CartItem.objects.filter(cart__user=self.customer).exists())

    def test_pickup_card_checkout_decrements_product_and_variant_stock(self):
        variant = ProductVariant.objects.create(
            product=self.discount_product,
            name="12/256 GB",
            sku="CHECKOUT-VARIANT",
            extra_price=Decimal("100000"),
            stock=4,
        )
        point = DeliveryPoint.objects.create(
            name="Checkout punkti",
            address="Toshkent, Chilonzor",
        )
        self.client.force_login(self.customer)
        self.client.post(
            reverse("apps:cart-add", kwargs={"product_id": self.discount_product.pk}),
            {"variant_id": variant.pk, "quantity": 2},
        )
        payload = self.checkout_payload(
            payment_type=Order.PaymentType.CARD,
            delivery_type=Order.DeliveryType.PICKUP,
            delivery_point=point.pk,
            address_mode="",
        )

        self.client.post(reverse("apps:checkout"), payload)

        order = Order.objects.get(checkout_token=payload["checkout_token"])
        variant.refresh_from_db()
        self.discount_product.refresh_from_db()
        self.assertEqual(order.delivery_point, point)
        self.assertIsNone(order.address)
        self.assertEqual(order.delivery_fee, Decimal("0"))
        self.assertEqual(order.total, Decimal("1800000"))
        self.assertEqual(order.items.get().variant_name, variant.name)
        self.assertEqual(order.items.get().sku, variant.sku)
        self.assertEqual(order.payment.provider, "demo_card")
        self.assertEqual(order.payment.status, Payment.Status.DEMO_PENDING)
        self.assertEqual(variant.stock, 2)
        self.assertEqual(self.discount_product.stock, 8)

    def test_checkout_rejects_changed_stock_without_partial_writes(self):
        self.add_checkout_item()
        payload = self.checkout_payload()
        self.discount_product.stock = 0
        self.discount_product.save(update_fields=("stock",))

        response = self.client.post(reverse("apps:checkout"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "faqat 0 dona qoldi")
        self.assertFalse(Order.objects.filter(checkout_token=payload["checkout_token"]).exists())
        self.assertFalse(Payment.objects.filter(order__user=self.customer).exists())
        self.assertTrue(CartItem.objects.filter(cart__user=self.customer).exists())
        self.assertFalse(Address.objects.filter(user=self.customer, title="Ish").exists())

    def test_repeated_checkout_submit_returns_same_order_and_only_reduces_stock_once(self):
        self.add_checkout_item()
        payload = self.checkout_payload(payment_type=Order.PaymentType.INSTALLMENT)

        first = self.client.post(reverse("apps:checkout"), payload)
        second = self.client.post(reverse("apps:checkout"), payload)

        order = Order.objects.get(checkout_token=payload["checkout_token"])
        success_url = reverse("apps:success", kwargs={"order_number": order.order_number})
        self.assertRedirects(first, success_url)
        self.assertRedirects(second, success_url)
        self.assertEqual(Order.objects.filter(checkout_token=payload["checkout_token"]).count(), 1)
        self.assertEqual(order.payment.status, Payment.Status.INSTALLMENT_REVIEW)
        self.discount_product.refresh_from_db()
        self.assertEqual(self.discount_product.stock, 9)

    def test_success_page_shows_created_order_and_blocks_other_users(self):
        self.add_checkout_item()
        payload = self.checkout_payload()
        self.client.post(reverse("apps:checkout"), payload)
        order = Order.objects.get(checkout_token=payload["checkout_token"])
        success_url = reverse("apps:success", kwargs={"order_number": order.order_number})

        response = self.client.get(success_url)
        self.assertContains(response, order.order_number)
        self.assertContains(response, "olganingizda naqd amalga oshiriladi")

        other_user = User.objects.create_user(
            email="success-other@example.com",
            username="success-other",
            password="StrongPass2026!",
        )
        self.client.force_login(other_user)
        self.assertEqual(self.client.get(success_url).status_code, 404)

    def test_pickup_page_reads_active_points_from_database_and_filters_by_area(self):
        visible = DeliveryPoint.objects.create(
            name="Chilonzor punkti",
            address="Toshkent, Chilonzor 3-kvartal",
            working_hours="09:00–21:00",
        )
        hidden = DeliveryPoint.objects.create(
            name="Yunusobod punkti",
            address="Toshkent, Yunusobod",
            is_active=False,
        )

        response = self.client.get(reverse("apps:pickup"), {"q": "Chilonzor"})

        self.assertContains(response, visible.name)
        self.assertContains(response, visible.address)
        self.assertContains(
            response,
            f"{reverse('apps:checkout')}?delivery_point={visible.pk}",
        )
        self.assertNotContains(response, hidden.name)

    def test_pickup_page_exposes_coordinates_for_map_selection(self):
        point = DeliveryPoint.objects.create(
            name="Xaritadagi punkt",
            address="Toshkent, Mirobod tumani",
            latitude=Decimal("41.292438"),
            longitude=Decimal("69.276659"),
        )

        response = self.client.get(reverse("apps:pickup"), {"q": "Mirobod"})

        self.assertContains(response, f'data-pickup-point="{point.pk}"')
        self.assertContains(response, 'data-latitude="41.292438"')
        self.assertContains(response, 'data-longitude="69.276659"')
        self.assertContains(response, f'data-show-pickup="{point.pk}"')
        self.assertContains(response, "leaflet@1.9.4")
        self.assertContains(response, 'data-map-provider="osm"')
        content = response.content.decode()
        self.assertLess(content.index("leaflet.js"), content.index("apps/assets/js/app.js"))

    @override_settings(YANDEX_MAPS_API_KEY="test-yandex-key")
    def test_pickup_page_uses_yandex_when_api_key_is_configured(self):
        DeliveryPoint.objects.create(
            name="Yandex xaritadagi punkt",
            address="Toshkent, Yunusobod",
            latitude=Decimal("41.366721"),
            longitude=Decimal("69.288815"),
        )

        response = self.client.get(reverse("apps:pickup"))

        self.assertContains(response, 'data-map-provider="yandex"')
        self.assertContains(response, "api-maps.yandex.ru/v3/")
        self.assertContains(response, "apikey=test-yandex-key")

    def test_selecting_pickup_prefills_checkout_and_makes_delivery_free(self):
        self.add_checkout_item()
        point = DeliveryPoint.objects.create(
            name="Amir Temur punkti",
            address="Toshkent, Amir Temur 108",
        )

        response = self.client.get(
            reverse("apps:checkout"),
            {"delivery_point": point.pk},
        )

        self.assertEqual(response.context["form"].initial["delivery_type"], Order.DeliveryType.PICKUP)
        self.assertEqual(response.context["form"].initial["delivery_point"], point)
        self.assertEqual(response.context["delivery_fee"], Decimal("0"))
        self.assertContains(response, 'data-delivery-panel="pickup"')
