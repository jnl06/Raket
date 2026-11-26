"""Tests for the server-rendered pages: Home, Jobs, Job detail, Post a job."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Profile

from .models import Application, Job

User = get_user_model()
PASSWORD = "S3cure-pass-phrase!"


def make_user(email, role, name):
    user = User.objects.create_user(username=email, email=email, password=PASSWORD)
    Profile.objects.create(user=user, role=role, full_name=name, phone="09171234567")
    return user


def make_job(owner, **overrides):
    data = {
        "title": "House Cleaning",
        "category": "house_cleaning",
        "description": "Clean a 3-bedroom house.",
        "location": "Lucena City",
        "work_date": date.today() + timedelta(days=3),
        "work_schedule": "morning",
        "employment_type": "one_time",
        "duration": "one_day",
        "estimated_payment": 600,
        "pay_period": "day",
        "number_of_workers": 2,
    }
    data.update(overrides)
    return Job.objects.create(posted_by=owner, **data)


class PageTestCase(TestCase):
    def setUp(self):
        self.provider = make_user("reyes@example.com", Profile.Role.PROVIDER, "Reyes Household")
        self.seeker = make_user("ana@example.com", Profile.Role.SEEKER, "Ana Cruz")

    def login(self, user):
        client = Client()
        client.force_login(user)
        return client


class NoPlaceholderDataTests(PageTestCase):
    """The pages must show what is in the database and nothing else."""

    def test_empty_database_shows_no_jobs(self):
        r = self.client.get(reverse("jobs:job_list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.context["jobs"]), [])
        self.assertNotContains(r, "Manual Labor and Loading")
        self.assertNotContains(r, "Household name")
        self.assertContains(r, "No jobs are open right now")

    def test_detail_of_unknown_job_is_404_not_sample_data(self):
        self.assertEqual(self.client.get(reverse("jobs:job_detail", args=[1])).status_code, 404)

    def test_home_hides_popular_searches_without_jobs(self):
        r = self.client.get(reverse("jobs:home"))
        self.assertNotContains(r, "Popular searches")
        self.assertNotContains(r, "Babysitter")

    def test_home_popular_searches_come_from_open_jobs(self):
        make_job(self.provider, category="gardening", title="Lawn care")
        make_job(self.provider, category="gardening", title="Hedge trimming")
        make_job(self.provider, category="laundry", title="Wash")
        r = self.client.get(reverse("jobs:home"))
        self.assertContains(r, "Popular searches")
        labels = [c["label"] for c in r.context["popular_categories"]]
        self.assertEqual(labels, ["Gardening", "Laundry"])
        self.assertContains(r, "?category=gardening")

    def test_detail_shows_only_what_the_poster_entered(self):
        job = make_job(self.provider)  # no experience / industry / how_to_apply / requirements
        r = self.client.get(reverse("jobs:job_detail", args=[job.pk]))
        self.assertContains(r, "Clean a 3-bedroom house.")
        self.assertContains(r, "₱600 a day")
        self.assertNotContains(r, "No Formal Experience")
        self.assertNotContains(r, "At least 18 years old")
        self.assertNotContains(r, "Basic Qualifications")
        self.assertNotContains(r, "How to Apply")
        self.assertNotContains(r, ">Experience<")
        self.assertNotContains(r, ">Industry<")

    def test_detail_shows_optional_sections_when_provided(self):
        job = make_job(
            self.provider,
            requirements="At least 18.\n- Physically fit",
            experience="Some experience",
            industry="Cleaning",
            how_to_apply="Message us.",
            max_payment=900,
            estimated_payment=500,
        )
        r = self.client.get(reverse("jobs:job_detail", args=[job.pk]))
        self.assertContains(r, "At least 18.")
        self.assertContains(r, "Physically fit")
        self.assertContains(r, "Some experience")
        self.assertContains(r, "Message us.")
        self.assertContains(r, "₱500 - 900 a day")
        self.assertContains(r, "2 Roles Open")


class JobListTests(PageTestCase):
    def setUp(self):
        super().setUp()
        make_job(self.provider, title="House Cleaning", employment_type="one_time", duration="one_day", estimated_payment=700)
        make_job(self.provider, title="Garden Work", category="gardening", employment_type="part_time", duration="few_days", estimated_payment=650)
        make_job(self.provider, title="Cook", category="cook_kitchen_helper", employment_type="full_time", duration="ongoing", estimated_payment=900)
        make_job(self.provider, title="Closed one", status="closed")
        past = make_job(self.provider, title="Past one")
        Job.objects.filter(pk=past.pk).update(work_date=date.today() - timedelta(days=1))

    def titles(self, **params):
        r = self.client.get(reverse("jobs:job_list"), params)
        self.assertEqual(r.status_code, 200)
        return [j.title for j in r.context["jobs"]]

    def test_only_open_upcoming_jobs_are_listed(self):
        self.assertCountEqual(self.titles(), ["House Cleaning", "Garden Work", "Cook"])

    def test_filters(self):
        self.assertEqual(self.titles(employment_type="part_time"), ["Garden Work"])
        self.assertEqual(self.titles(duration="ongoing"), ["Cook"])
        self.assertEqual(self.titles(category="gardening"), ["Garden Work"])
        self.assertEqual(self.titles(q="garden"), ["Garden Work"])

    def test_junk_filter_values_are_ignored_not_errors(self):
        self.assertEqual(len(self.titles(employment_type="nope", duration="all", category="zzz", sort="bogus")), 3)

    def test_sort_by_pay(self):
        self.assertEqual(self.titles(sort="pay_high")[0], "Cook")
        self.assertEqual(self.titles(sort="pay_low")[0], "Garden Work")

    def test_rate_uses_the_pay_period_of_each_job(self):
        make_job(self.provider, title="Tutor", pay_period="hour", estimated_payment=150, max_payment=250)
        r = self.client.get(reverse("jobs:job_list"), {"q": "tutor"})
        self.assertContains(r, "₱150 - 250 / Hour")

    def test_same_filters_as_the_api(self):
        api = self.client.get(reverse("api:jobs"), {"employment_type": "part_time", "category": "gardening"}).json()
        page = self.titles(employment_type="part_time", category="gardening")
        self.assertEqual([j["title"] for j in api["results"]], page)

    def test_pagination_keeps_filters(self):
        for i in range(12):
            make_job(self.provider, title=f"Tutor {i}", category="other")
        r = self.client.get(reverse("jobs:job_list"), {"category": "other"})
        self.assertEqual(r.context["page"].paginator.num_pages, 2)
        self.assertEqual(len(r.context["jobs"]), 10)
        self.assertContains(r, "category=other&amp;page=2")
        r = self.client.get(reverse("jobs:job_list"), {"category": "other", "page": 2})
        self.assertEqual(len(r.context["jobs"]), 2)
        self.assertContains(r, "You're all caught up")
        # out-of-range / junk page numbers fall back instead of erroring
        self.assertEqual(self.client.get(reverse("jobs:job_list"), {"page": 99}).status_code, 200)
        self.assertEqual(self.client.get(reverse("jobs:job_list"), {"page": "x"}).status_code, 200)

    def test_empty_search_offers_to_clear_filters(self):
        r = self.client.get(reverse("jobs:job_list"), {"q": "zzzz"})
        self.assertContains(r, "No jobs match your search.")


class JobDetailApplyStateTests(PageTestCase):
    def setUp(self):
        super().setUp()
        self.job = make_job(self.provider)
        self.url = reverse("jobs:job_detail", args=[self.job.pk])

    def state(self, client):
        return client.get(self.url).context["apply_state"]

    def test_states(self):
        self.assertEqual(self.state(self.client), "anonymous")
        self.assertEqual(self.state(self.login(self.seeker)), "can_apply")
        self.assertEqual(self.state(self.login(self.provider)), "owner")
        other = make_user("other@example.com", Profile.Role.PROVIDER, "Other")
        self.assertEqual(self.state(self.login(other)), "provider")

    def test_applied_state_and_hired_counts_reduce_open_roles(self):
        Application.objects.create(job=self.job, applicant=self.seeker, status="hired")
        c = self.login(self.seeker)
        r = c.get(self.url)
        self.assertEqual(r.context["apply_state"], "applied")
        self.assertEqual(r.context["roles_open"], 1)
        self.assertContains(r, "Hired")
        self.assertNotContains(r, "Withdraw application")

    def test_closed_job_hidden_from_public_but_not_from_applicants_or_owner(self):
        Application.objects.create(job=self.job, applicant=self.seeker)
        self.job.status = "closed"
        self.job.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.login(self.seeker).get(self.url).status_code, 200)
        self.assertEqual(self.login(self.provider).get(self.url).status_code, 200)

    def test_past_job_is_not_open_for_applying(self):
        Job.objects.filter(pk=self.job.pk).update(work_date=date.today() - timedelta(days=1))
        self.assertEqual(self.state(self.login(self.seeker)), "closed")

    def test_anonymous_sign_in_link_returns_here(self):
        r = self.client.get(self.url)
        self.assertContains(r, f"{reverse('accounts:signin')}?next={self.url}")


class PostJobPageTests(PageTestCase):
    def payload(self, **overrides):
        data = {
            "title": "Babysitter",
            "category": "babysitter",
            "description": "Watch two kids.",
            "location": "Lucena City",
            "work_date": (date.today() + timedelta(days=5)).isoformat(),
            "work_schedule": "afternoon",
            "employment_type": "part_time",
            "duration": "few_days",
            "estimated_payment": "800",
            "max_payment": "",
            "pay_period": "day",
            "number_of_workers": "1",
            "requirements": "",
            "experience": "",
            "industry": "",
            "how_to_apply": "",
            "confirm": "on",
        }
        data.update(overrides)
        return data

    def test_requires_sign_in(self):
        r = self.client.get(reverse("jobs:post_job"))
        self.assertRedirects(r, f"{reverse('accounts:signin')}?next={reverse('jobs:post_job')}")

    def test_seekers_are_turned_away(self):
        r = self.login(self.seeker).post(reverse("jobs:post_job"), self.payload())
        self.assertRedirects(r, reverse("jobs:home"))
        self.assertEqual(Job.objects.count(), 0)

    def test_form_renders_empty_with_no_preselected_values(self):
        r = self.login(self.provider).get(reverse("jobs:post_job"))
        self.assertEqual(r.status_code, 200)
        form = r.context["form"]
        for name in ("employment_type", "duration", "pay_period", "number_of_workers", "category"):
            self.assertIn(form[name].value(), (None, ""), name)
        self.assertContains(r, "Select employment type")

    def test_provider_can_post_and_lands_on_the_new_job(self):
        r = self.login(self.provider).post(reverse("jobs:post_job"), self.payload())
        job = Job.objects.get()
        self.assertRedirects(r, reverse("jobs:job_detail", args=[job.pk]))
        self.assertEqual(job.posted_by, self.provider)
        self.assertEqual(job.status, "active")
        self.assertEqual((job.experience, job.industry, job.how_to_apply), ("", "", ""))
        self.assertIsNone(job.max_payment)

    def test_every_required_field_is_enforced(self):
        required = ["title", "category", "description", "location", "work_date", "work_schedule",
                    "employment_type", "duration", "estimated_payment", "pay_period", "number_of_workers", "confirm"]
        r = self.login(self.provider).post(reverse("jobs:post_job"), {})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sorted(r.context["form"].errors), sorted(required))
        self.assertEqual(Job.objects.count(), 0)

    def test_rules(self):
        c = self.login(self.provider)
        past = (date.today() - timedelta(days=1)).isoformat()
        r = c.post(reverse("jobs:post_job"), self.payload(work_date=past, estimated_payment="0", number_of_workers="0"))
        errors = r.context["form"].errors
        for name in ("work_date", "estimated_payment", "number_of_workers"):
            self.assertIn(name, errors)
        r = c.post(reverse("jobs:post_job"), self.payload(estimated_payment="500", max_payment="100"))
        self.assertIn("max_payment", r.context["form"].errors)
        self.assertEqual(Job.objects.count(), 0)


class AuthPageTests(PageTestCase):
    def test_pages_render(self):
        for name in ("signin", "signup", "forgot_password", "reset_password"):
            self.assertEqual(self.client.get(reverse(f"accounts:{name}")).status_code, 200, name)

    def test_signed_in_users_skip_the_auth_pages(self):
        c = self.login(self.seeker)
        self.assertRedirects(c.get(reverse("accounts:signin")), reverse("jobs:home"))
        self.assertRedirects(c.get(reverse("accounts:signup")), reverse("jobs:home"))

    def test_next_must_stay_on_this_site(self):
        r = self.client.get(reverse("accounts:signin"), {"next": "https://evil.example/steal"})
        self.assertEqual(r.context["next"], "")
        r = self.client.get(reverse("accounts:signin"), {"next": "/jobs/3/"})
        self.assertEqual(r.context["next"], "/jobs/3/")

    def test_navbar_reflects_session(self):
        r = self.client.get(reverse("jobs:home"))
        self.assertContains(r, "Sign in")
        r = self.login(self.seeker).get(reverse("jobs:home"))
        self.assertContains(r, "Ana Cruz")
        self.assertContains(r, "Sign out")
        self.assertNotContains(r, ">Sign in<")

    def test_api_is_mounted(self):
        self.assertEqual(self.client.get("/api/auth/csrf/").status_code, 200)
        self.assertEqual(self.client.get("/api/jobs/").status_code, 200)


class ModelTests(PageTestCase):
    def test_counts_and_open_roles(self):
        job = make_job(self.provider, number_of_workers=2)
        other = make_user("b@example.com", Profile.Role.SEEKER, "B")
        Application.objects.create(job=job, applicant=self.seeker, status="hired")
        Application.objects.create(job=job, applicant=other)
        annotated = Job.objects.with_counts().get(pk=job.pk)
        self.assertEqual((annotated.applicant_count, annotated.hired_count), (2, 1))

    def test_payment_text(self):
        j = make_job(self.provider, estimated_payment=1250.5, max_payment=2000, pay_period="job")
        self.assertEqual(j.payment_phrase, "₱1,250.50 - 2,000 for the whole job")


class ManagePagesTests(PageTestCase):
    """Applied jobs, Manage posted jobs and Manage applicants."""

    def setUp(self):
        super().setUp()
        self.job = make_job(self.provider, title="Garden help")
        self.other = make_user("other@example.com", Profile.Role.PROVIDER, "Other Household")
        self.app = Application.objects.create(
            job=self.job, applicant=self.seeker, cover_note="Available all week."
        )

    def test_pages_send_visitors_to_sign_in(self):
        for name in ("jobs:my_applications", "jobs:my_jobs", "jobs:manage_applicants"):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn(reverse("accounts:signin"), r["Location"])

    def test_pages_reject_the_wrong_role(self):
        r = self.login(self.seeker).get(reverse("jobs:my_jobs"))
        self.assertRedirects(r, reverse("jobs:home"))
        r = self.login(self.provider).get(reverse("jobs:my_applications"))
        self.assertRedirects(r, reverse("jobs:home"))

    def test_applied_jobs_lists_my_applications_with_filters(self):
        c = self.login(self.seeker)
        r = c.get(reverse("jobs:my_applications"))
        self.assertContains(r, "Garden help")
        self.assertContains(r, "Available all week.")
        r = c.get(reverse("jobs:my_applications"), {"status": "hired"})
        self.assertNotContains(r, "Garden help")
        self.assertContains(r, "No applications with this status.")

    def test_posted_jobs_shows_only_my_jobs_with_counts(self):
        make_job(self.other, title="Not mine")
        r = self.login(self.provider).get(reverse("jobs:my_jobs"))
        self.assertContains(r, "Garden help")
        self.assertNotContains(r, "Not mine")
        self.assertContains(r, "1 applicant")

    def test_applicants_hide_contact_until_hired(self):
        c = self.login(self.provider)
        r = c.get(reverse("jobs:manage_applicants"))
        self.assertContains(r, "Ana Cruz")
        self.assertContains(r, "Contact details show after you hire.")
        self.assertNotContains(r, "09171234567")
        self.app.status = Application.Status.HIRED
        self.app.save()
        r = c.get(reverse("jobs:manage_applicants"))
        self.assertContains(r, "09171234567")

    def test_applicants_of_other_households_stay_private(self):
        c = self.login(self.other)
        r = c.get(reverse("jobs:manage_applicants"))
        self.assertNotContains(r, "Ana Cruz")
        r = c.get(reverse("jobs:manage_applicants"), {"job": self.job.pk})
        self.assertNotContains(r, "Ana Cruz")

    def test_navbar_links_to_manage_pages(self):
        r = self.client.get(reverse("jobs:home"))
        for name in ("jobs:my_applications", "jobs:my_jobs", "jobs:manage_applicants"):
            self.assertContains(r, f'href="{reverse(name)}"')
