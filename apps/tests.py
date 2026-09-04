from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Brand, Category, Order, OrderItem, Product, Seller, User


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
        self.assertRedirects(response, reverse("apps:checkout"))
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
        self.assertRedirects(response, reverse("apps:checkout"))

    def test_authenticated_user_can_open_checkout(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("apps:checkout"))
        self.assertEqual(response.status_code, 200)

    def test_logout_accepts_post_and_returns_to_main_page(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("apps:logout"))
        self.assertRedirects(response, reverse("apps:index"))
        self.assertNotIn("_auth_user_id", self.client.session)


class StorefrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        customer = User.objects.create_user(
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
        seller = Seller.objects.create(user=seller_user, store_name="Tech Store")
        phones = Category.objects.create(name="Smartfonlar", slug="smartfonlar")
        audio = Category.objects.create(name="Audio", slug="audio")
        samsung = Brand.objects.create(name="Samsung", slug="samsung")
        sony = Brand.objects.create(name="Sony", slug="sony")
        cls.discount_product = Product.objects.create(
            seller=seller,
            category=phones,
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
            seller=seller,
            category=audio,
            brand=sony,
            name="Sony Headphones Test",
            slug="sony-headphones-test",
            sku="TEST-SONY",
            price=Decimal("1200000"),
            stock=10,
        )
        order = Order.objects.create(
            user=customer,
            order_number="ZT-TEST-1",
            status=Order.Status.DELIVERED,
        )
        OrderItem.objects.create(
            order=order,
            product=cls.discount_product,
            seller=seller,
            product_name=cls.discount_product.name,
            price=cls.discount_product.price,
            quantity=1,
        )
        OrderItem.objects.create(
            order=order,
            product=cls.best_seller,
            seller=seller,
            product_name=cls.best_seller.name,
            price=cls.best_seller.price,
            quantity=5,
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
