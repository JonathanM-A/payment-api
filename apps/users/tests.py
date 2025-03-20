from django.test import TestCase
from .models import User
import uuid


class CustomerTestClass(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            name="Peter Griffin", email="birdistheword@quahog.com"
        )

    def test_name_label(self):
        user = self.user
        field_label = user._meta.get_field("name").verbose_name
        self.assertEqual(field_label, "name")

    def test_email_label(self):
        user = self.user
        field_label = user._meta.get_field("email").verbose_name
        self.assertEqual(field_label, "email")

    def test_name_max_length(self):
        user = self.user
        max_length = user._meta.get_field("name").max_length
        self.assertEqual(max_length, 100)

    def test_email_unique(self):
        user = self.user
        unique = user._meta.get_field("email").unique
        self.assertTrue(unique)

    def test_object_name_is_name(self):
        user = self.user
        expected_object_name = user.name
        self.assertEqual(str(user), expected_object_name)

    def test_create_user_with_name_and_email(self):
        user = User.objects.create(name="Jane Doe", email="jane@example.com")
        self.assertEqual(user.name, "Jane Doe")
        self.assertEqual(user.email, "jane@example.com")

    def test_email_uniqueness_constraint(self):
        # Try to create another user with the same email
        with self.assertRaises(Exception):
            User.objects.create(name="Another Peter", email="birdistheword@quahog.com")

    def test_id_is_uuid(self):
        user = self.user
        self.assertIsInstance(user.id, uuid.UUID)
