from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.integrations.email.adapter import preview_messages
from apps.integrations.email.branded import html_for_preview


class Command(BaseCommand):
    help = "Dev only: writes every email, with sample data, to local HTML and text files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default=str(Path(settings.BASE_DIR) / ".email-previews"),
            help="Folder to write to.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("preview_emails only runs with DEBUG on.")

        out = Path(options["out"])
        out.mkdir(parents=True, exist_ok=True)
        for name, message in preview_messages().items():
            (out / f"{name}.html").write_text(html_for_preview(message), encoding="utf8")
            (out / f"{name}.txt").write_text(
                f"Subject: {message.subject}\n\n{message.body}\n", encoding="utf8"
            )
            self.stdout.write(f"{out / name}.html")
