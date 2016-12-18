from django.urls import reverse

from misago.acl.testutils import override_acl

from .. import testutils
from ..models import ThreadParticipant
from .test_privatethreads import PrivateThreadsTestCase


class PrivateThreadsApiListTests(PrivateThreadsTestCase):
    def setUp(self):
        super(PrivateThreadsApiListTests, self).setUp()

        self.api_link = reverse('misago:api:private-thread-list')

    def test_unauthenticated(self):
        """api requires user to sign in and be able to access it"""
        self.logout_user()

        response = self.client.get(self.api_link)
        self.assertContains(response, "sign in to use private threads", status_code=403)

    def test_no_permission(self):
        """api requires user to have permission to be able to access it"""
        override_acl(self.user, {
            'can_use_private_threads': 0
        })

        response = self.client.get(self.api_link)
        self.assertContains(response, "can't use private threads", status_code=403)

    def test_empty_list(self):
        """api has no showstoppers on returning empty list"""
        response = self.client.get(self.api_link)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertEqual(response_json['count'], 0)

    def test_thread_visibility(self):
        """only participated threads are returned by private threads api"""
        visible = testutils.post_thread(category=self.category, poster=self.user)
        hidden = testutils.post_thread(category=self.category, poster=self.user)
        reported = testutils.post_thread(category=self.category, poster=self.user)

        ThreadParticipant.objects.add_participants(visible, [self.user])

        reported.has_reported_posts = True
        reported.save()

        response = self.client.get(self.api_link)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertEqual(response_json['count'], 1)
        self.assertEqual(response_json['results'][0]['id'], visible.id)

        # threads with reported posts will also show to moderators
        override_acl(self.user, {
            'can_moderate_private_threads': 1
        })

        response = self.client.get(self.api_link)
        self.assertEqual(response.status_code, 200)

        response_json = response.json()
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(response_json['results'][0]['id'], reported.id)
        self.assertEqual(response_json['results'][1]['id'], visible.id)


class PrivateThreadsApiGetTests(PrivateThreadsTestCase):
    def setUp(self):
        super(PrivateThreadsApiGetTests, self).setUp()

        self.thread = testutils.post_thread(self.category, poster=self.user)
        self.api_url = self.thread.get_api_url()

    def test_anonymous(self):
        """anonymous user can't see private thread"""
        self.logout_user()

        response = self.client.get(self.api_url)
        self.assertContains(response, "sign in to use private threads", status_code=403)

    def test_no_permission(self):
        """user needs to have permission to see private thread"""
        override_acl(self.user, {
            'can_use_private_threads': 0
        })

        response = self.client.get(self.api_url)
        self.assertContains(response, "t use private threads", status_code=403)

    def test_no_participant(self):
        """user cant see thread he isn't part of"""
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 404)

    def test_mod_not_reported(self):
        """moderator can't see private thread that has no reports"""
        override_acl(self.user, {
            'can_moderate_private_threads': 1
        })

        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 404)

    def test_reported_not_mod(self):
        """non-mod can't see private thread that has reported posts"""
        self.thread.has_reported_posts = True
        self.thread.save()

        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 404)

    def test_can_see_owner(self):
        """user can see thread he is owner of"""
        ThreadParticipant.objects.set_owner(self.thread, self.user)

        response = self.client.get(self.api_url)
        self.assertContains(response, self.thread.title)

    def test_can_see_participant(self):
        """user can see thread he is participant of"""
        ThreadParticipant.objects.add_participants(self.thread, [self.user])

        response = self.client.get(self.api_url)
        self.assertContains(response, self.thread.title)

    def test_mod_can_see_reported(self):
        """moderator can see private thread that has reports"""
        override_acl(self.user, {
            'can_moderate_private_threads': 1
        })

        self.thread.has_reported_posts = True
        self.thread.save()

        response = self.client.get(self.api_url)
        self.assertContains(response, self.thread.title)