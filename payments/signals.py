from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from notifications.tasks import generate_payment_receipts


@receiver(post_save, sender=Payment)
def generate_receipt_on_payment_completion(sender, instance, created, **kwargs):
    """Generate receipt when payment is marked as completed"""
    if instance.status == 'completed' and not instance.receipt_generated:
        # Use Celery task for background processing
        generate_payment_receipts.delay()
