from django.core.management.base import BaseCommand

from assets.models import Asset


class Command(BaseCommand):
    help = "Runs maintenance checks and fixes across asset data."

    def handle(self, *args, **options):
        self.fix_current_history()

    def fix_current_history(self):
        """
        Ensure each asset's current_history points at its most recent history entry.
        """
        fixed = 0
        for asset in Asset.objects.select_related("current_history"):
            latest = asset.histories.order_by("-when").first()
            if asset.current_history_id != (latest.id if latest else None):
                self.stdout.write(
                    f"  {asset}: current_history {asset.current_history} -> {latest}"
                )
                asset.current_history = latest
                asset.save(update_fields=["current_history"])
                fixed += 1
        self.stdout.write(
            self.style.SUCCESS(f"current_history: fixed {fixed} asset(s)")
        )
