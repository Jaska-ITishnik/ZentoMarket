from django.db import transaction
from django.utils import timezone

from .models import Chat, ChatMessage, Product, Seller, User


class ChatValidationError(Exception):
    def __init__(self, message, code="invalid_chat"):
        self.message = message
        self.code = code
        super().__init__(message)


def user_can_access_chat(user, chat):
    if not user.is_authenticated or chat.seller_id is None:
        return False
    return user.pk in {chat.user_id, chat.seller.user_id}


def start_chat(customer, seller_id, product_id=None):
    if not customer.is_authenticated or customer.role != User.Role.CUSTOMER:
        raise ChatValidationError(
            "Suhbatni faqat xaridor boshlashi mumkin.",
            "customer_only",
        )

    seller = Seller.objects.filter(pk=seller_id, is_active=True).select_related("user").first()
    if seller is None:
        raise ChatValidationError("Do‘kon topilmadi.", "seller_not_found")
    if seller.user_id == customer.pk:
        raise ChatValidationError("O‘z do‘koningiz bilan suhbat ochib bo‘lmaydi.", "own_store")

    product = None
    if product_id:
        product = Product.objects.filter(
            pk=product_id,
            seller=seller,
            is_active=True,
        ).first()
        if product is None:
            raise ChatValidationError("Mahsulot bu do‘konga tegishli emas.", "invalid_product")

    chat, created = Chat.objects.get_or_create(
        user=customer,
        seller=seller,
        defaults={
            "product": product,
            "subject": product.name if product else seller.store_name,
        },
    )
    if not created and product and chat.product_id is None:
        chat.product = product
        chat.subject = product.name
        chat.save(update_fields=["product", "subject", "updated_at"])
    return chat, created


@transaction.atomic
def send_chat_message(chat_id, sender, text):
    text = (text or "").strip()
    if not text:
        raise ChatValidationError("Xabar matnini kiriting.", "empty_message")
    if len(text) > 2000:
        raise ChatValidationError("Xabar 2000 belgidan oshmasligi kerak.", "message_too_long")

    chat = (
        Chat.objects.select_for_update()
        .select_related("seller__user", "user")
        .filter(pk=chat_id, seller__isnull=False)
        .first()
    )
    if chat is None or not user_can_access_chat(sender, chat):
        raise ChatValidationError("Bu suhbatga kirish huquqi yo‘q.", "forbidden")

    is_customer = sender.pk == chat.user_id
    if not is_customer and not chat.messages.filter(sender_id=chat.user_id).exists():
        raise ChatValidationError(
            "Do‘kon egasi xaridorning birinchi xabaridan keyin javob bera oladi.",
            "customer_must_write_first",
        )

    message = ChatMessage.objects.create(chat=chat, sender=sender, text=text)
    Chat.objects.filter(pk=chat.pk).update(updated_at=timezone.now())
    return message


def mark_chat_read(chat, reader):
    if not user_can_access_chat(reader, chat):
        return 0
    return chat.messages.exclude(sender=reader).filter(is_read=False).update(is_read=True)
