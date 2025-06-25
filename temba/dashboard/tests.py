from datetime import timedelta, timezone as tzone

from django.urls import reverse
from django.utils import timezone

from temba.orgs.models import Org
from temba.tests import TembaTest


class DashboardTest(TembaTest):
    def create_activity(self):
        # and some message and call activity
        joe = self.create_contact("Joe", phone="+593979099111")
        self.create_outgoing_msg(joe, "Tea of coffee?")
        self.create_incoming_msg(joe, "Coffee")
        self.create_outgoing_msg(joe, "OK")
        self.create_outgoing_msg(joe, "Wanna hang?", voice=True)
        self.create_incoming_msg(joe, "Sure", voice=True)

    def test_dashboard_home(self):
        dashboard_url = reverse("dashboard.dashboard_home")

        # visit this page without authenticating
        response = self.client.get(dashboard_url, follow=True)

        # nope! cannot visit dashboard.
        self.assertRedirects(response, "/accounts/login/?next=%s" % dashboard_url)

        self.login(self.admin)
        response = self.client.get(dashboard_url, follow=True)

        # yep! it works
        self.assertEqual(response.request["PATH_INFO"], dashboard_url)

    def test_message_history(self):
        url = reverse("dashboard.dashboard_message_history")

        # visit this page without authenticating
        response = self.client.get(url, follow=True)

        # nope!
        self.assertRedirects(response, "/accounts/login/?next=%s" % url)

        self.login(self.admin)
        self.create_activity()
        response = self.client.get(url).json()

        # in, out
        self.assertEqual(2, len(response))

        # incoming messages
        self.assertEqual(1, response[0]["data"][0][1])

        # outgoing messages
        self.assertEqual(2, response[1]["data"][0][1])  # test with since and until parameters
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # test with specific date range
        response = self.client.get(url, {"since": yesterday.isoformat(), "until": tomorrow.isoformat()}).json()

        # should still get the same data since messages are from today
        self.assertEqual(2, len(response))
        self.assertEqual(1, response[0]["data"][0][1])  # incoming
        self.assertEqual(2, response[1]["data"][0][1])  # outgoing

        # test with date range that excludes our messages
        old_date = today - timedelta(days=10)
        response = self.client.get(url, {"since": old_date.isoformat(), "until": yesterday.isoformat()}).json()

        # should get empty data
        self.assertEqual(2, len(response))
        self.assertEqual(0, len(response[0]["data"]))  # no incoming data
        self.assertEqual(0, len(response[1]["data"]))  # no outgoing data

    def test_workspace_stats(self):
        stats_url = reverse("dashboard.dashboard_workspace_stats")

        self.create_activity()

        # create child with no activity
        self.org.features += [Org.FEATURE_CHILD_ORGS]
        self.org.create_new(self.admin, "Test Org", tzone.utc, as_child=True)

        # visit this page without authenticating
        response = self.client.get(stats_url)
        self.assertLoginRedirect(response)

        self.login(self.admin, choose_org=self.org)
        response = self.client.get(stats_url).json()

        self.assertEqual(["Nyaruka"], response["categories"])
        self.assertEqual(2, len(response["series"]))
        self.assertEqual(1, response["series"][0]["data"][0])  # incoming
        self.assertEqual(2, response["series"][1]["data"][0])  # outgoing

        # test with since and until parameters
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # test with specific date range that includes our data
        response = self.client.get(stats_url, {"since": yesterday.isoformat(), "until": tomorrow.isoformat()}).json()

        # should get the same data since messages are from today
        self.assertEqual(["Nyaruka"], response["categories"])
        self.assertEqual(2, len(response["series"]))
        self.assertEqual(1, response["series"][0]["data"][0])  # incoming
        self.assertEqual(2, response["series"][1]["data"][0])  # outgoing

        # test with date range that excludes our messages
        old_date = today - timedelta(days=10)
        response = self.client.get(stats_url, {"since": old_date.isoformat(), "until": yesterday.isoformat()}).json()

        # should get empty data since no activity in that range
        self.assertEqual([], response["categories"])
        self.assertEqual(2, len(response["series"]))
        self.assertEqual([], response["series"][0]["data"])  # no incoming data
        self.assertEqual([], response["series"][1]["data"])  # no outgoing data
