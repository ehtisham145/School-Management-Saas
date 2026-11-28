"""Phase 0 prototype: run one browser agent task from the terminal.

    python manage.py run_browser_task --workspace 12 "Find the hours" --url https://example.com

Needs BROWSER_AGENT_ENABLED=True, OPENAI_API_KEY and `playwright install chromium`."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.browser_agent import services
from apps.browser_agent.agent import playwright_opener, run_task
from apps.tenancy.selectors import get_individual_teacher_membership


class Command(BaseCommand):
    help = "Run one browser agent task for an individual teacher's workspace (prototype)."

    def add_arguments(self, parser):
        parser.add_argument("goal", help="What the agent should do.")
        parser.add_argument(
            "--workspace", type=int, required=True, help="School id of the workspace."
        )
        parser.add_argument("--url", default="", help="Optional start page.")
        parser.add_argument("--headed", action="store_true", help="Show the browser window.")

    def handle(self, *args, goal, workspace, url, headed, **options):
        if not settings.BROWSER_AGENT_ENABLED:
            raise CommandError("Set BROWSER_AGENT_ENABLED=True in .env first.")
        membership = get_individual_teacher_membership(workspace)
        if membership is None:
            raise CommandError("No active individual teacher workspace with that id.")

        try:
            task = services.create_task(
                membership.school, user=membership.user, goal=goal, start_url=url
            )
        except services.TaskInputError as error:
            raise CommandError(error.code) from error

        self.stdout.write(f"Task {task.pk} started.")
        task = run_task(
            task,
            open_browser=playwright_opener(headless=not headed),
            on_step=self._print_step,
        )

        self.stdout.write("")
        self.stdout.write(f"Status: {task.status} {task.failure_reason}".rstrip())
        self.stdout.write(
            f"Steps: {task.steps_taken}  Tokens: {task.input_tokens} in / "
            f"{task.output_tokens} out  Cost: ${task.cost_usd:.4f}"
        )
        if task.answer:
            self.stdout.write("Answer:")
            self.stdout.write(task.answer)

    def _print_step(self, step):
        note = f" ({step.note})" if step.note else ""
        self.stdout.write(
            f"  {step.number:>2}. {step.action:<8} {step.verdict:<8} {step.domain}{note}"
            f"  [{step.duration_ms} ms]"
        )
