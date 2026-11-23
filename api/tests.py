import json
import shutil
import tempfile
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from jobs.models import Application, Job

User = get_user_model()
PASSWORD = "S3cure-pass-phrase!"
TMP_MEDIA = tempfile.mkdtemp()


def make_user(email, role, name=None, phone="09171234567"):
    user = User.objects.create_user(username=email, email=email, password=PASSWORD)
    Profile.objects.create(user=user, role=role, full_name=name or email.split("@")[0], phone=phone)
    return user


def job_payload(**overrides):
    payload = {
        "title": "Manual Labor and Loading",
        "category": "other",
        "description": "Help load and unload trucks.",
        "location": "Lucena City",
        "work_date": (date.today() + timedelta(days=3)).isoformat(),
        "work_schedule": "whole_day",
        "estimated_payment": 500,
        "max_payment": 900,
        "pay_period": "day",
        "number_of_workers": 2,
        "requirements": "At least 18 years old.\nPhysically fit.",
        "employment_type": "part_time",
        "duration": "one_two_weeks",
        "industry": "Logistics, Warehouse",
        "confirm": True,
    }
    payload.update(overrides)
    return payload


class ApiTestCase(TestCase):
    def setUp(self):
        self.provider = make_user("reyes@example.com", Profile.Role.PROVIDER, "Reyes")
        self.seeker = make_user("ana@example.com", Profile.Role.SEEKER, "Ana Cruz")
        self.seeker2 = make_user("ben@example.com", Profile.Role.SEEKER, "Ben Lim")

    def client_for(self, user=None):
        client = Client()
        if user:
            client.force_login(user)
        return client

    def post(self, client, name, data=None, **kwargs):
        return client.post(
            reverse(f"api:{name}", kwargs=kwargs),
            json.dumps(data or {}),
            content_type="application/json",
        )

    def patch(self, client, name, data, **kwargs):
        return client.patch(
            reverse(f"api:{name}", kwargs=kwargs), json.dumps(data), content_type="application/json"
        )

    def get(self, client, name, params=None, **kwargs):
        return client.get(reverse(f"api:{name}", kwargs=kwargs), params or {})

    def make_job(self, owner=None, **overrides):
        data = job_payload(**overrides)
        data.pop("confirm")
        return Job.objects.create(posted_by=owner or self.provider, **data)


class AuthTests(ApiTestCase):
    def register_payload(self, **overrides):
        data = {
            "role": "job_seeker",
            "full_name": "Maria Santos",
            "email": "Maria@Example.com",
            "phone": "+63 917 123 4567",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "agree_terms": True,
        }
        data.update(overrides)
        return data

    def test_register_creates_user_profile_and_signs_in(self):
        c = Client()
        r = self.post(c, "register", self.register_payload())
        self.assertEqual(r.status_code, 201, r.content)
        user = User.objects.get(email="maria@example.com")
        self.assertEqual(user.profile.role, "job_seeker")
        self.assertEqual(self.get(c, "me").json()["user"]["full_name"], "Maria Santos")

    def test_register_validation(self):
        c = Client()
        r = self.post(
            c,
            "register",
            self.register_payload(
                email="nope", password="123", confirm_password="x", agree_terms=False, role="admin", phone=""
            ),
        )
        self.assertEqual(r.status_code, 400)
        fields = r.json()["error"]["fields"]
        for f in ("email", "password", "confirm_password", "agree_terms", "role", "phone"):
            self.assertIn(f, fields)

    def test_register_duplicate_email_case_insensitive(self):
        c = Client()
        self.assertEqual(self.post(c, "register", self.register_payload()).status_code, 201)
        r = self.post(Client(), "register", self.register_payload(email="MARIA@example.com"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.json()["error"]["fields"])

    def test_login_logout(self):
        c = Client()
        bad = self.post(c, "login", {"email": "ana@example.com", "password": "wrong"})
        self.assertEqual(bad.status_code, 401)
        ok = self.post(c, "login", {"email": "ANA@example.com", "password": PASSWORD, "remember_me": True})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.get(c, "me").status_code, 200)
        self.post(c, "logout")
        self.assertEqual(self.get(c, "me").status_code, 401)

    def test_login_without_remember_me_expires_at_browser_close(self):
        c = Client()
        self.post(c, "login", {"email": "ana@example.com", "password": PASSWORD})
        self.assertTrue(c.session.get_expire_at_browser_close())

    def test_login_works_for_plain_username_accounts(self):
        User.objects.create_superuser("admin", "", PASSWORD)
        r = self.post(Client(), "login", {"email": "admin", "password": PASSWORD})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user"]["role"], "job_provider")  # profile created lazily

    def test_method_not_allowed_and_json_errors(self):
        r = self.get(Client(), "login")
        self.assertEqual(r.status_code, 405)
        r = Client().post(reverse("api:login"), "{bad", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"]["code"], "invalid_json")

    def test_password_reset_flow(self):
        c = Client()
        self.post(c, "password_reset", {"email": "nobody@example.com"})
        self.assertEqual(len(mail.outbox), 0)  # same 200 response, no email
        self.assertEqual(self.post(c, "password_reset", {"email": "ana@example.com"}).status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        uid = body.split("uid=")[1].split("&")[0]
        token = body.split("token=")[1].split()[0]
        bad = self.post(c, "password_reset_confirm", {"uid": uid, "token": "bad", "new_password": "N3w-pass-phrase!"})
        self.assertEqual(bad.status_code, 400)
        weak = self.post(c, "password_reset_confirm", {"uid": uid, "token": token, "new_password": "123"})
        self.assertEqual(weak.status_code, 400)
        ok = self.post(c, "password_reset_confirm", {"uid": uid, "token": token, "new_password": "N3w-pass-phrase!"})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(User.objects.get(email="ana@example.com").check_password("N3w-pass-phrase!"))

    @override_settings(MEDIA_ROOT=TMP_MEDIA)
    def test_profile_update_and_resume_upload(self):
        c = self.client_for(self.seeker)
        r = self.patch(c, "me", {"phone": "09170000000", "skills": ["Cleaning", "Cooking"], "availability": ["part_time"]})
        self.assertEqual(r.status_code, 200, r.content)
        user = r.json()["user"]
        self.assertEqual(user["skills"], ["Cleaning", "Cooking"])
        self.assertEqual(user["availability"][0]["label"], "Part-time")

        bad = c.post(reverse("api:me"), {"resume": SimpleUploadedFile("cv.exe", b"x")})
        self.assertEqual(bad.status_code, 400)
        good = c.post(reverse("api:me"), {"resume": SimpleUploadedFile("cv.pdf", b"%PDF-1.4 hi")})
        self.assertEqual(good.status_code, 200, good.content)
        self.assertTrue(good.json()["user"]["has_resume"])
        self.assertEqual(b"".join(self.get(c, "my_resume").streaming_content), b"%PDF-1.4 hi")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)


class JobTests(ApiTestCase):
    def test_only_providers_can_post(self):
        r = self.post(Client(), "jobs", job_payload())
        self.assertEqual(r.status_code, 401)
        r = self.post(self.client_for(self.seeker), "jobs", job_payload())
        self.assertEqual(r.status_code, 403)

    def test_create_and_detail(self):
        c = self.client_for(self.provider)
        r = self.post(c, "jobs", job_payload())
        self.assertEqual(r.status_code, 201, r.content)
        job = r.json()["job"]
        self.assertTrue(job["is_owner"])
        self.assertEqual(job["roles_open"], 2)
        self.assertEqual(job["payment"], {"currency": "PHP", "amount": 500, "max_amount": 900, "period": "day"})
        self.assertEqual(job["qualifications"], ["At least 18 years old.", "Physically fit."])
        self.assertEqual(job["household"], "Reyes")

        public = self.get(Client(), "job_detail", job_id=job["id"]).json()["job"]
        self.assertFalse(public["is_owner"])
        self.assertNotIn("applicant_count", public)

    def test_create_validation(self):
        c = self.client_for(self.provider)
        r = self.post(
            c,
            "jobs",
            job_payload(
                work_date=(date.today() - timedelta(days=1)).isoformat(),
                estimated_payment=0,
                number_of_workers=0,
                max_payment=10,
                category="nope",
                confirm=False,
            ),
        )
        self.assertEqual(r.status_code, 400)
        r = self.post(c, "jobs", job_payload(work_date=(date.today() - timedelta(days=1)).isoformat(), estimated_payment=-5, max_payment=None))
        fields = r.json()["error"]["fields"]
        self.assertIn("work_date", fields)
        self.assertIn("estimated_payment", fields)
        r = self.post(c, "jobs", job_payload(max_payment=100))
        self.assertIn("max_payment", r.json()["error"]["fields"])

    def test_nothing_is_filled_in_for_the_poster(self):
        """No field default: leaving out a content field is a validation error, not a guess."""
        c = self.client_for(self.provider)
        payload = job_payload()
        for field in ("employment_type", "duration", "pay_period", "number_of_workers"):
            payload.pop(field, None)
        r = self.post(c, "jobs", payload)
        self.assertEqual(r.status_code, 400)
        fields = r.json()["error"]["fields"]
        for field in ("employment_type", "duration", "pay_period", "number_of_workers"):
            self.assertIn(field, fields)
        self.assertEqual(Job.objects.count(), 0)

    def test_optional_fields_stay_empty_when_omitted(self):
        c = self.client_for(self.provider)
        payload = job_payload(max_payment=None)
        for field in ("experience", "industry", "requirements"):
            payload.pop(field, None)
        r = self.post(c, "jobs", payload)
        self.assertEqual(r.status_code, 201, r.content)
        job = r.json()["job"]
        self.assertEqual((job["experience"], job["industry"], job["how_to_apply"]), ("", "", ""))
        self.assertEqual(job["qualifications"], [])
        self.assertIsNone(job["payment"]["max_amount"])

    def test_job_model_has_no_content_defaults(self):
        for name in ("employment_type", "duration", "pay_period", "number_of_workers", "experience", "industry", "how_to_apply"):
            self.assertFalse(Job._meta.get_field(name).has_default(), name)

    def test_browse_filters_search_and_sort(self):
        self.make_job(title="House Cleaning", category="house_cleaning", industry="", employment_type="one_time", duration="one_day", estimated_payment=700)
        self.make_job(title="Garden Maintenance", category="gardening", industry="", employment_type="part_time", duration="few_days", estimated_payment=650, location="Tayabas City")
        self.make_job(title="Cook", category="cook_kitchen_helper", industry="", employment_type="full_time", duration="ongoing", estimated_payment=900, description="Helps with house chores too")
        closed = self.make_job(title="Old job")
        closed.status = Job.Status.CLOSED
        closed.save()
        past = self.make_job(title="Past job")
        Job.objects.filter(pk=past.pk).update(work_date=date.today() - timedelta(days=1))

        c = Client()
        r = self.get(c, "jobs").json()
        self.assertEqual(r["pagination"]["count"], 3)  # closed + past excluded

        titles = lambda params: [j["title"] for j in self.get(c, "jobs", params).json()["results"]]
        self.assertEqual(titles({"employment_type": "part_time"}), ["Garden Maintenance"])
        self.assertEqual(titles({"employment_type": "all", "duration": "all"}).__len__(), 3)
        self.assertEqual(titles({"duration": "ongoing"}), ["Cook"])
        self.assertEqual(titles({"category": "gardening"}), ["Garden Maintenance"])
        self.assertEqual(titles({"location": "tayabas"}), ["Garden Maintenance"])
        # relevance: title match ranks above description match
        self.assertEqual(titles({"q": "house"}), ["House Cleaning", "Cook"])
        self.assertEqual(titles({"sort": "pay_high"})[0], "Cook")
        self.assertEqual(titles({"sort": "pay_low"})[0], "Garden Maintenance")

        self.assertEqual(self.get(c, "jobs", {"sort": "bogus"}).status_code, 400)
        self.assertEqual(self.get(c, "jobs", {"employment_type": "bogus"}).status_code, 400)

    def test_pagination(self):
        for i in range(12):
            self.make_job(title=f"Job {i}")
        r = self.get(Client(), "jobs", {"page_size": 5, "page": 3}).json()
        self.assertEqual(r["pagination"]["shown"], 2)
        self.assertEqual(r["pagination"]["num_pages"], 3)
        self.assertFalse(r["pagination"]["has_next"])
        # out-of-range page clamps to last page
        r = self.get(Client(), "jobs", {"page_size": 5, "page": 99}).json()
        self.assertEqual(r["pagination"]["page"], 3)
        self.assertEqual(self.get(Client(), "jobs", {"page": "x"}).status_code, 400)

    def test_categories_sorted_by_popularity(self):
        self.make_job(category="babysitter")
        self.make_job(category="babysitter")
        self.make_job(category="gardening")
        r = self.get(Client(), "categories").json()
        self.assertEqual([c["value"] for c in r["results"][:2]], ["babysitter", "gardening"])
        self.assertEqual(r["results"][0]["job_count"], 2)

    def test_edit_close_repost_permissions(self):
        job = self.make_job()
        other = make_user("other@example.com", Profile.Role.PROVIDER)
        self.assertEqual(self.patch(self.client_for(other), "job_detail", {"title": "x"}, job_id=job.pk).status_code, 403)
        self.assertEqual(self.patch(self.client_for(self.seeker), "job_detail", {"title": "x"}, job_id=job.pk).status_code, 403)
        self.assertEqual(self.post(self.client_for(other), "job_close", job_id=job.pk).status_code, 403)

        c = self.client_for(self.provider)
        r = self.patch(c, "job_detail", {"title": "Renamed", "estimated_payment": 750}, job_id=job.pk)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["job"]["title"], "Renamed")
        self.assertEqual(r.json()["job"]["location"], "Lucena City")  # untouched fields preserved

        r = self.post(c, "job_close", job_id=job.pk)
        self.assertEqual(r.json()["job"]["status"], "closed")
        # closed jobs vanish from public browse and public detail
        self.assertEqual(self.get(Client(), "jobs").json()["pagination"]["count"], 0)
        self.assertEqual(self.get(Client(), "job_detail", job_id=job.pk).status_code, 404)

        r = self.post(c, "job_repost", job_id=job.pk)
        self.assertEqual(r.status_code, 201, r.content)
        new = r.json()["job"]
        self.assertNotEqual(new["id"], job.pk)
        self.assertEqual(new["status"], "active")
        self.assertEqual(new["title"], "Renamed")

    def test_repost_with_past_date_requires_new_date(self):
        job = self.make_job(status="closed")
        Job.objects.filter(pk=job.pk).update(work_date=date.today() - timedelta(days=5))
        c = self.client_for(self.provider)
        self.assertEqual(self.post(c, "job_repost", job_id=job.pk).status_code, 400)
        new_date = (date.today() + timedelta(days=7)).isoformat()
        r = self.post(c, "job_repost", {"work_date": new_date}, job_id=job.pk)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["job"]["work_date"], new_date)

    def test_editing_job_with_past_work_date_does_not_require_new_date(self):
        job = self.make_job()
        Job.objects.filter(pk=job.pk).update(work_date=date.today() - timedelta(days=2))
        r = self.patch(self.client_for(self.provider), "job_detail", {"title": "Still editable"}, job_id=job.pk)
        self.assertEqual(r.status_code, 200, r.content)

    def test_my_jobs_stats_filter_sort(self):
        a = self.make_job(title="A")
        b = self.make_job(title="B", location="Tayabas City")
        c_ = self.make_job(title="C", status="closed")
        other = make_user("other@example.com", Profile.Role.PROVIDER)
        self.make_job(owner=other, title="Not mine")
        for u in (self.seeker, self.seeker2):
            Application.objects.create(job=b, applicant=u)
        Application.objects.create(job=a, applicant=self.seeker)

        c = self.client_for(self.provider)
        r = self.get(c, "my_jobs").json()
        self.assertEqual(r["stats"], {"total_jobs": 3, "active_jobs": 2, "closed_jobs": 1, "total_applicants": 3})
        self.assertEqual(len(r["results"]), 3)

        r = self.get(c, "my_jobs", {"status": "active", "sort": "applicants"}).json()
        self.assertEqual([j["title"] for j in r["results"]], ["B", "A"])
        self.assertEqual(r["results"][0]["applicant_count"], 2)
        self.assertEqual(r["stats"]["total_jobs"], 3)  # stats ignore filters
        r = self.get(c, "my_jobs", {"q": "tayabas"}).json()
        self.assertEqual([j["title"] for j in r["results"]], ["B"])
        self.assertEqual(self.get(self.client_for(self.seeker), "my_jobs").status_code, 403)


class ApplicationFlowTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.job = self.make_job(number_of_workers=1)

    def test_apply_rules(self):
        c = self.client_for(self.seeker)
        self.assertEqual(self.post(Client(), "job_apply", job_id=self.job.pk).status_code, 401)
        self.assertEqual(self.post(self.client_for(self.provider), "job_apply", job_id=self.job.pk).status_code, 403)

        r = self.post(c, "job_apply", {"cover_note": "I'm available."}, job_id=self.job.pk)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["application"]["status"]["value"], "submitted")
        self.assertEqual(r.json()["application"]["job"]["household"], "Reyes")
        self.assertEqual(self.post(c, "job_apply", job_id=self.job.pk).status_code, 409)

        detail = self.get(c, "job_detail", job_id=self.job.pk).json()["job"]
        self.assertEqual(detail["my_application"]["status"], "submitted")

        self.job.status = "closed"
        self.job.save()
        self.assertEqual(self.post(self.client_for(self.seeker2), "job_apply", job_id=self.job.pk).status_code, 409)
        # an applicant can still open the closed job they applied to
        self.assertEqual(self.get(c, "job_detail", job_id=self.job.pk).status_code, 200)

    def test_cannot_apply_after_the_work_date_has_passed(self):
        Job.objects.filter(pk=self.job.pk).update(work_date=date.today() - timedelta(days=1))
        r = self.post(self.client_for(self.seeker), "job_apply", job_id=self.job.pk)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["error"]["code"], "job_closed")

    def test_my_applications_counts_filter_search(self):
        j2 = self.make_job(title="House Cleaning", location="Tayabas City")
        j3 = self.make_job(title="Home Painting")
        Application.objects.create(job=self.job, applicant=self.seeker)
        Application.objects.create(job=j2, applicant=self.seeker, status="under_review")
        Application.objects.create(job=j3, applicant=self.seeker, status="hired")
        Application.objects.create(job=j3, applicant=self.seeker2)

        c = self.client_for(self.seeker)
        r = self.get(c, "my_applications").json()
        self.assertEqual(r["counts"], {"total": 3, "submitted": 1, "under_review": 1, "hired": 1, "rejected": 0})
        r = self.get(c, "my_applications", {"status": "under_review"}).json()
        self.assertEqual([a["job"]["title"] for a in r["results"]], ["House Cleaning"])
        r = self.get(c, "my_applications", {"q": "reyes"}).json()
        self.assertEqual(len(r["results"]), 3)  # household name search
        self.assertEqual(self.get(self.client_for(self.provider), "my_applications").status_code, 403)

    def test_applicants_list_visibility_and_pagination(self):
        for i in range(10):
            u = make_user(f"w{i}@example.com", Profile.Role.SEEKER, f"Worker {i}")
            Application.objects.create(job=self.job, applicant=u)
        other = make_user("other@example.com", Profile.Role.PROVIDER)

        r = self.get(self.client_for(self.provider), "job_applicants", job_id=self.job.pk).json()
        self.assertEqual(r["pagination"]["shown"], 9)
        self.assertEqual(r["pagination"]["count"], 10)
        self.assertEqual(r["job"]["applicant_count"], 10)
        self.assertEqual(r["counts"]["submitted"], 10)
        self.assertIsNone(r["results"][0]["applicant"]["email"])  # contact hidden until hired

        self.assertEqual(self.get(self.client_for(other), "job_applicants", job_id=self.job.pk).status_code, 403)
        self.assertEqual(self.get(self.client_for(self.seeker), "job_applicants", job_id=self.job.pk).status_code, 403)

    def test_hire_reveals_contact_and_closes_job_when_filled(self):
        a1 = Application.objects.create(job=self.job, applicant=self.seeker)
        a2 = Application.objects.create(job=self.job, applicant=self.seeker2)
        c = self.client_for(self.provider)

        r = self.patch(c, "application_detail", {"status": "hired"}, application_id=a1.pk)
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body["application"]["status"]["value"], "hired")
        self.assertEqual(body["application"]["applicant"]["email"], "ana@example.com")
        self.assertEqual(body["job_status"], "closed")  # 1 of 1 roles filled

        # idempotent
        self.assertEqual(self.patch(c, "application_detail", {"status": "hired"}, application_id=a1.pk).status_code, 200)
        # roles filled -> second hire blocked
        r = self.patch(c, "application_detail", {"status": "hired"}, application_id=a2.pk)
        self.assertEqual(r.status_code, 409)
        # hired can't be rejected
        self.assertEqual(self.patch(c, "application_detail", {"status": "rejected"}, application_id=a1.pk).status_code, 409)
        # the other applicant can still be rejected
        self.assertEqual(self.patch(c, "application_detail", {"status": "rejected"}, application_id=a2.pk).status_code, 200)

    def test_multi_role_job_stays_open_until_filled(self):
        job = self.make_job(number_of_workers=2)
        a1 = Application.objects.create(job=job, applicant=self.seeker)
        a2 = Application.objects.create(job=job, applicant=self.seeker2)
        c = self.client_for(self.provider)
        r = self.patch(c, "application_detail", {"status": "hired"}, application_id=a1.pk).json()
        self.assertEqual(r["job_status"], "active")
        self.assertEqual(self.get(Client(), "job_detail", job_id=job.pk).json()["job"]["roles_open"], 1)
        r = self.patch(c, "application_detail", {"status": "hired"}, application_id=a2.pk).json()
        self.assertEqual(r["job_status"], "closed")

    def test_cannot_lower_workers_below_hired(self):
        job = self.make_job(number_of_workers=2)
        a = Application.objects.create(job=job, applicant=self.seeker, status="hired")
        Application.objects.create(job=job, applicant=self.seeker2, status="hired")
        r = self.patch(self.client_for(self.provider), "job_detail", {"number_of_workers": 1}, job_id=job.pk)
        self.assertEqual(r.status_code, 400)

    def test_decision_permissions_and_validation(self):
        app = Application.objects.create(job=self.job, applicant=self.seeker)
        other = make_user("other@example.com", Profile.Role.PROVIDER)
        self.assertEqual(self.patch(self.client_for(other), "application_detail", {"status": "hired"}, application_id=app.pk).status_code, 403)
        self.assertEqual(self.patch(self.client_for(self.seeker), "application_detail", {"status": "hired"}, application_id=app.pk).status_code, 403)
        self.assertEqual(self.patch(self.client_for(self.provider), "application_detail", {"status": "submitted"}, application_id=app.pk).status_code, 400)
        self.assertEqual(self.patch(self.client_for(self.provider), "application_detail", {"status": "hired"}, application_id=9999).status_code, 404)

    def test_withdraw(self):
        app = Application.objects.create(job=self.job, applicant=self.seeker)
        other_app = Application.objects.create(job=self.job, applicant=self.seeker2)
        c = self.client_for(self.seeker)
        self.assertEqual(c.delete(reverse("api:application_detail", kwargs={"application_id": other_app.pk})).status_code, 404)
        self.assertEqual(c.delete(reverse("api:application_detail", kwargs={"application_id": app.pk})).status_code, 200)
        self.assertFalse(Application.objects.filter(pk=app.pk).exists())
        hired = Application.objects.create(job=self.job, applicant=self.seeker, status="hired")
        self.assertEqual(c.delete(reverse("api:application_detail", kwargs={"application_id": hired.pk})).status_code, 409)

    @override_settings(MEDIA_ROOT=TMP_MEDIA)
    def test_resume_access_and_auto_under_review(self):
        app = Application.objects.create(job=self.job, applicant=self.seeker)
        owner = self.client_for(self.provider)

        r = self.get(owner, "application_resume", application_id=app.pk)
        self.assertEqual(r.status_code, 404)  # no resume uploaded yet
        self.assertEqual(r.json()["error"]["code"], "no_resume")

        self.client_for(self.seeker).post(reverse("api:me"), {"resume": SimpleUploadedFile("cv.pdf", b"%PDF-resume")})
        self.assertEqual(self.get(self.client_for(self.seeker2), "application_resume", application_id=app.pk).status_code, 403)
        self.assertEqual(self.get(Client(), "application_resume", application_id=app.pk).status_code, 401)

        # applicant viewing own resume does not change status
        self.get(self.client_for(self.seeker), "application_resume", application_id=app.pk)
        app.refresh_from_db()
        self.assertEqual(app.status, "submitted")

        r = self.get(owner, "application_resume", application_id=app.pk)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"%PDF-resume")
        app.refresh_from_db()
        self.assertEqual(app.status, "under_review")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)
