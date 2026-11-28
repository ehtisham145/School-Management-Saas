"""Live updates for one browser task: /ws/browser-agent/<task_id>/.

- Only a signed-in user (session cookie, AuthMiddlewareStack) may connect, and only to a
  task they created in their active workspace. Anything else is closed before accept, so
  guessing task ids shows nothing.
- The Origin header must match ALLOWED_HOSTS (AllowedHostsOriginValidator in asgi.py).
- The socket closes when the task ends, after BROWSER_AGENT_WS_IDLE_SECONDS without
  traffic, and at the latest a minute after the task's hard time limit.
- Phase 2 adds the login hand-off (screencast frames and the teacher's input) here; for
  now the client may only send {"type": "ping"}."""

import asyncio
import contextlib

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from apps.browser_agent import realtime, selectors
from apps.browser_agent.models import BrowserTask
from apps.tenancy.selectors import get_switchable_membership

CLOSE_UNAUTHORISED = 4401
CLOSE_NOT_FOUND = 4404
CLOSE_IDLE = 4408
CLOSE_FINISHED = 4000


@database_sync_to_async
def _owned_task(scope, task_id):
    """The task if the connecting user created it in their active, usable membership."""
    user = scope.get("user")
    session = scope.get("session")
    if user is None or not user.is_authenticated or session is None:
        return None
    membership = get_switchable_membership(user, session.get("active_membership_id"))
    if membership is None:
        return None
    return selectors.get_task(membership.school, task_id, user=user)


class BrowserTaskConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHORISED)
            return
        try:
            task_id = int(self.scope["url_route"]["kwargs"]["task_id"])
        except (KeyError, TypeError, ValueError):
            await self.close(code=CLOSE_NOT_FOUND)
            return
        task = await _owned_task(self.scope, task_id)
        if task is None:
            await self.close(code=CLOSE_NOT_FOUND)
            return

        self.group = realtime.group_name(task.pk)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "task.update", "task": realtime.task_payload(task)})
        if task.status in BrowserTask.FINISHED:
            await self.close(code=CLOSE_FINISHED)
            return

        self._activity = asyncio.Event()
        self._watchdog = asyncio.ensure_future(self._watch())

    async def disconnect(self, code):
        watchdog = getattr(self, "_watchdog", None)
        if watchdog is not None:
            watchdog.cancel()
        group = getattr(self, "group", None)
        if group is not None:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if isinstance(content, dict) and content.get("type") == "ping":
            self._touch()
            await self.send_json({"type": "pong"})

    async def task_update(self, event):
        self._touch()
        message = {"type": "task.update", "task": event["task"]}
        if "step" in event:
            message["step"] = event["step"]
        await self.send_json(message)
        if event["task"].get("status") in BrowserTask.FINISHED:
            await self.close(code=CLOSE_FINISHED)

    def _touch(self):
        activity = getattr(self, "_activity", None)
        if activity is not None:
            activity.set()

    async def _watch(self):
        loop = asyncio.get_running_loop()
        idle = settings.BROWSER_AGENT_WS_IDLE_SECONDS
        deadline = loop.time() + settings.BROWSER_AGENT_HARD_TIME_LIMIT + 60
        while True:
            self._activity.clear()
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                await asyncio.wait_for(self._activity.wait(), timeout=min(idle, remaining))
            except TimeoutError:
                break
        with contextlib.suppress(Exception):
            await self.close(code=CLOSE_IDLE)
