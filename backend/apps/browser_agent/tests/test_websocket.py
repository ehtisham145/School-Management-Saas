"""WebSocket rules for /ws/browser-agent/<id>/, run through the real ASGI application
(AllowedHostsOriginValidator + AuthMiddlewareStack + URLRouter)."""

import json

import pytest
from asgiref.sync import async_to_sync
from asgiref.testing import ApplicationCommunicator
from channels.db import database_sync_to_async

from apps.browser_agent import services
from apps.browser_agent.models import BrowserTask
from config.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)
GOOD_ORIGIN = b"http://localhost:3000"


class WebsocketCommunicator(ApplicationCommunicator):
    """The small part of channels.testing.WebsocketCommunicator these tests use.

    Not imported from channels: importing anything under `channels.testing` also loads its
    live-server helper, which needs daphne, a server this project doesn't use."""

    def __init__(self, app, path, headers):
        scope = {
            "type": "websocket",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": headers,
            "subprotocols": [],
            "client": ("127.0.0.1", 50000),
            "server": ("localhost", 80),
        }
        super().__init__(app, scope)

    async def connect(self, timeout=2):
        """(True, subprotocol) when accepted, (False, close code) when refused."""
        await self.send_input({"type": "websocket.connect"})
        response = await self.receive_output(timeout)
        if response["type"] == "websocket.close":
            return False, response.get("code", 1000)
        return True, response.get("subprotocol")

    async def receive_json_from(self, timeout=2):
        response = await self.receive_output(timeout)
        assert response["type"] == "websocket.send", response
        return json.loads(response["text"])

    async def disconnect(self, code=1000, timeout=2):
        await self.send_input({"type": "websocket.disconnect", "code": code})
        await self.wait(timeout)


def socket(task, *, teacher=None, origin=GOOD_ORIGIN):
    headers = [(b"origin", origin), (b"host", b"localhost")]
    if teacher is not None:
        headers.append((b"cookie", f"sessionid={teacher.session_key}".encode()))
    return WebsocketCommunicator(application, f"/ws/browser-agent/{task.pk}/", headers=headers)


def run(coroutine_function):
    return async_to_sync(coroutine_function)()


def new_task(teacher):
    return services.create_task(teacher.school, user=teacher.user, goal="Find hours")


def test_the_owner_connects_and_gets_the_current_status(sara):
    task = new_task(sara)

    async def scenario():
        communicator = socket(task, teacher=sara)
        connected, _ = await communicator.connect()
        assert connected
        message = await communicator.receive_json_from()
        assert message == {
            "type": "task.update",
            "task": {"id": task.pk, "status": "queued", "steps_taken": 0, "failure_reason": ""},
        }
        await communicator.disconnect()

    run(scenario)


def test_an_anonymous_socket_is_refused(sara):
    task = new_task(sara)

    async def scenario():
        connected, code = await socket(task).connect()
        assert not connected
        assert code == 4401

    run(scenario)


def test_another_users_task_is_refused(sara, omar):
    task = new_task(sara)

    async def scenario():
        connected, code = await socket(task, teacher=omar).connect()
        assert not connected
        assert code == 4404

    run(scenario)


def test_a_task_id_that_does_not_exist_is_refused(sara):
    task = new_task(sara)
    task.pk = 999_999

    async def scenario():
        connected, code = await socket(task, teacher=sara).connect()
        assert not connected
        assert code == 4404

    run(scenario)


def test_a_socket_from_another_website_is_refused(sara):
    task = new_task(sara)

    async def scenario():
        connected, _ = await socket(task, teacher=sara, origin=b"https://evil.example").connect()
        assert not connected

    run(scenario)


def test_updates_stream_and_the_socket_closes_when_the_task_ends(sara):
    task = new_task(sara)

    async def scenario():
        communicator = socket(task, teacher=sara)
        assert (await communicator.connect())[0]
        await communicator.receive_json_from()  # current status

        await database_sync_to_async(services.record_step)(
            task, number=1, action="goto", domain="example.com", verdict="ok"
        )
        update = await communicator.receive_json_from()
        assert update["step"]["domain"] == "example.com"
        assert "answer" not in update["task"]

        await database_sync_to_async(services.finish_task)(
            task, status=BrowserTask.Status.DONE, answer="9am to 5pm"
        )
        final = await communicator.receive_json_from()
        assert final["task"]["answer"] == "9am to 5pm"
        closed = await communicator.receive_output(timeout=2)
        assert closed == {"type": "websocket.close", "code": 4000}

    run(scenario)


def test_a_finished_task_sends_its_result_and_closes(sara):
    task = new_task(sara)
    services.finish_task(task, status=BrowserTask.Status.DONE, answer="done already")

    async def scenario():
        communicator = socket(task, teacher=sara)
        assert (await communicator.connect())[0]
        message = await communicator.receive_json_from()
        assert message["task"]["answer"] == "done already"
        closed = await communicator.receive_output(timeout=2)
        assert closed["type"] == "websocket.close"

    run(scenario)


def test_an_idle_socket_is_closed(sara, settings):
    settings.BROWSER_AGENT_WS_IDLE_SECONDS = 1
    task = new_task(sara)

    async def scenario():
        communicator = socket(task, teacher=sara)
        assert (await communicator.connect())[0]
        await communicator.receive_json_from()
        closed = await communicator.receive_output(timeout=3)
        assert closed == {"type": "websocket.close", "code": 4408}

    run(scenario)
