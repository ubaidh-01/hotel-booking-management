import pandas as pd
from django.core.management.base import BaseCommand

from properties.models import Property


class Command(BaseCommand):
    help = "Import property data from an Excel file."

    def add_arguments(self, parser):
        parser.add_argument(
            "excel_path",
            type=str,
            help="Path to the Excel file containing property data",
        )

    def handle(self, *args, **options):
        excel_path = options["excel_path"]

        try:
            df = pd.read_excel(excel_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading Excel: {e}"))
            return

        # Ensure enough columns exist
        required_columns = [0, 3, 5, 6]  # A, D, F, G
        if any(col >= len(df.columns) for col in required_columns):
            self.stderr.write(self.style.ERROR("Excel file missing required columns."))
            return

        created_count = 0
        updated_count = 0

        for _, row in df.iterrows():
            name = row.iloc[0]
            total_rooms = row.iloc[3]
            address = row.iloc[5]
            address_chinese = row.iloc[6]

            if pd.isna(name):
                continue  # Skip empty rows

            obj, created = Property.objects.update_or_create(
                name=name,
                defaults={
                    "total_rooms": int(total_rooms) if not pd.isna(total_rooms) else 0,
                    "address": address if not pd.isna(address) else "",
                    "address_chinese": address_chinese if not pd.isna(address_chinese) else "",
                    "property_type": "apartment",  # Change if needed
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Import completed: {created_count} created, {updated_count} updated."
        ))
