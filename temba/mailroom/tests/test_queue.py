from unittest.mock import patch

from django_redis import get_redis_connection

from django.utils import timezone

from temba.flows.models import FlowSession, FlowStart
from temba.mailroom.queue import queue_interrupt
from temba.tests import TembaTest, matchers
from temba.utils import json
from temba.utils.uuid import uuid4


class MailroomQueueTest(TembaTest):
    def test_queue_flow_start(self):
        flow = self.create_flow("Test")
        jim = self.create_contact("Jim", phone="+12065551212")
        bobs = self.create_group("Bobs", [self.create_contact("Bob", phone="+12065551313")])

        start = FlowStart.create(
            flow,
            self.admin,
            groups=[bobs],
            contacts=[jim],
            urns=["tel:+1234567890", "twitter:bobby"],
            params={"foo": "bar"},
        )

        start.async_start()

        self.assert_org_queued(self.org)
        self.assert_queued_batch_task(
            self.org,
            {
                "type": "start_flow",
                "task": {
                    "start_id": start.id,
                    "start_type": "M",
                    "org_id": self.org.id,
                    "created_by_id": self.admin.id,
                    "flow_id": flow.id,
                    "contact_ids": [jim.id],
                    "group_ids": [bobs.id],
                    "urns": ["tel:+1234567890", "twitter:bobby"],
                    "query": None,
                    "exclusions": {},
                    "params": {"foo": "bar"},
                },
                "queued_on": matchers.ISODate(),
            },
        )

    def test_queue_contact_import_batch(self):
        imp = self.create_contact_import("media/test_imports/simple.xlsx")
        imp.start()

        self.assert_org_queued(self.org)
        self.assert_queued_batch_task(
            self.org,
            {
                "type": "import_contact_batch",
                "task": {"contact_import_batch_id": imp.batches.get().id},
                "queued_on": matchers.ISODate(),
            },
        )

    @patch("temba.channels.models.Channel.trigger_sync")
    def test_queue_interrupt_channel(self, mock_trigger_sync):
        self.channel.release(self.admin)

        self.assert_org_queued(self.org)
        self.assert_queued_batch_task(
            self.org,
            {
                "type": "interrupt_channel",
                "task": {"channel_id": self.channel.id},
                "queued_on": matchers.ISODate(),
            },
        )

    def test_queue_interrupt_by_contacts(self):
        jim = self.create_contact("Jim", phone="+12065551212")
        bob = self.create_contact("Bob", phone="+12065551313")

        queue_interrupt(self.org, contacts=[jim, bob])

        self.assert_org_queued(self.org)
        self.assert_queued_batch_task(
            self.org,
            {
                "type": "interrupt_sessions",
                "task": {"contact_ids": [jim.id, bob.id]},
                "queued_on": matchers.ISODate(),
            },
        )

    def test_queue_interrupt_by_flow(self):
        flow = self.create_flow("Test")
        flow.archive(self.admin)

        self.assert_org_queued(self.org)
        self.assert_queued_batch_task(
            self.org,
            {"type": "interrupt_sessions", "task": {"flow_ids": [flow.id]}, "queued_on": matchers.ISODate()},
        )

    def test_queue_interrupt_by_session(self):
        contact = self.create_contact("Bob", phone="+1234567890")
        session = FlowSession.objects.create(
            uuid=uuid4(),
            org=self.org,
            contact=contact,
            status=FlowSession.STATUS_WAITING,
            output_url="http://sessions.com/123.json",
            created_on=timezone.now(),
        )

        queue_interrupt(self.org, sessions=[session])

        self.assert_org_queued(self.org)
        self.assert_queued_batch_task(
            self.org,
            {"type": "interrupt_sessions", "task": {"session_ids": [session.id]}, "queued_on": matchers.ISODate()},
        )

    def assert_org_queued(self, org):
        r = get_redis_connection()

        # check we have one org with active tasks
        self.assertEqual(r.zcard("tasks:batch:active"), 1)

        queued_org = json.loads(r.zrange("tasks:batch:active", 0, 1)[0])

        self.assertEqual(queued_org, org.id)

    def assert_queued_batch_task(self, org, expected_task):
        r = get_redis_connection()

        # check we have one task in the org's queue
        self.assertEqual(r.zcard(f"tasks:batch:{org.id}"), 1)

        # load and check that task
        actual_task = json.loads(r.zrange(f"tasks:batch:{org.id}", 0, 1)[0])

        self.assertEqual(actual_task, expected_task)
