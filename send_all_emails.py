import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wing_kon_property.settings')
django.setup()

from notifications.tasks import (
    send_rent_reminders,
    send_contract_reminders,
    send_birthday_wishes,
    process_late_fees,
    detect_rent_increases,
    create_late_fee_payments,
    send_move_out_reminders,
    send_final_move_out_warnings,
    allocate_utility_bills,
    send_utility_payment_reminders,
    check_maintenance_overdue,
    send_maintenance_updates_to_tenants,
    escalate_high_priority_tickets,
    generate_payment_receipts,
    process_pending_receipts,
    send_test_email
)


def send_all_emails():
    """Send all emails from all Celery tasks"""
    print("🚀 Sending ALL emails from all tasks...\n")

    # List of all email tasks
    email_tasks = [
        ("Test Email", send_test_email),
        ("Rent Reminders", send_rent_reminders),
        ("Contract Reminders", send_contract_reminders),
        ("Birthday Wishes", send_birthday_wishes),
        ("Late Fee Processing", process_late_fees),
        ("Rent Increase Detection", detect_rent_increases),
        ("Late Fee Payment Creation", create_late_fee_payments),
        ("Move Out Reminders", send_move_out_reminders),
        ("Final Move Out Warnings", send_final_move_out_warnings),
        ("Utility Bill Allocation", allocate_utility_bills),
        ("Utility Payment Reminders", send_utility_payment_reminders),
        ("Maintenance Overdue Check", check_maintenance_overdue),
        ("Maintenance Updates", send_maintenance_updates_to_tenants),
        ("Maintenance Escalation", escalate_high_priority_tickets),
        ("Payment Receipt Generation", generate_payment_receipts),
        ("Pending Receipt Processing", process_pending_receipts),
    ]

    results = []

    for task_name, task_function in email_tasks:
        print(f"📧 Sending: {task_name}")
        try:
            result = task_function.delay()
            results.append((task_name, result))
            print(f"   ✅ Queued successfully: {result.id}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            results.append((task_name, None))

    print(f"\n🎉 Completed! Queued {len([r for r in results if r[1] is not None])} email tasks.")
    print("📬 Check your email inbox and Celery worker logs for results.")

    return results


if __name__ == "__main__":
    send_all_emails()