from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_save
from django.conf import settings
from datetime import date, datetime, timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

CAMPUSES = (
    (1, u'PO'), (2, u'SC'), (3, u'CMC'), (4, u'HM'), (5, u'PZ'), (6, u'CGU'), (7, u'CU'), (8, u'KS'), (-1, u'?'))
CAMPUSES_FULL_NAMES = {1: 'Pomona', 2: 'Scripps', 3: 'Claremont-McKenna', 4: 'Harvey Mudd', 5: 'Pitzer'}
CAMPUSES_LOOKUP = dict([(a[1], a[0]) for a in CAMPUSES])

# Some campuses are represented more than one way so we make aliases
CAMPUSES_LOOKUP['CM'] = CAMPUSES_LOOKUP['CMC']
CAMPUSES_LOOKUP['CUC'] = CAMPUSES_LOOKUP['CU']
CAMPUSES_LOOKUP['CG'] = CAMPUSES_LOOKUP['CGU']

SESSIONS = ((u'SP', u'Spring'), (u'FA', u'Fall'))
SUBSESSIONS = ((u'P1', u'1'), (u'P2', u'2'))

POSSIBLE_GRADES = (
    (1, u'A'), (2, u'A-'), (3, u'B+'), (4, u'B'), (5, u'B-'), (6, u'C+'), (7, u'C'),
    (8, u'C-'), (9, u'D+'), (10, u'D'), (11, u'D-'), (12, u'F'))

# TODO: Make this robust for different semesters
# (see the academic calendar at http://catalog.pomona.edu/content.php?catoid=21&navoid=4445)
START_DATE = date(2016, 8, 30)
END_DATE = date(2016, 12, 7)


class Term(models.Model):
    key = models.CharField(max_length=20, unique=True)
    year = models.PositiveSmallIntegerField()
    session = models.CharField(max_length=2, choices=SESSIONS)

    def is_current_term(self):
        current_term = Term.objects.all()[0]
        return self == current_term

    def __unicode__(self):
        return u'%s %s' % (self.session, self.year)

    class Meta:
        ordering = ['-year', 'session']


class Instructor(models.Model):
    name = models.CharField(max_length=100)
    rating = models.FloatField(blank = True, null = True)
    useful_rating = models.FloatField(blank=True, null=True)
    engagement_rating = models.FloatField(blank=True, null=True)
    difficulty_rating = models.FloatField(blank=True, null=True)
    competency_rating = models.FloatField(blank=True, null=True)
    lecturing_rating = models.FloatField(blank=True, null=True)
    enthusiasm_rating = models.FloatField(blank=True, null=True)
    approachable_rating = models.FloatField(blank=True, null=True)

    def __unicode__(self):
        return self.name

    def slug(self):
        return slugify(self.name)

    def get_miscellaneous_ratings(self):
        return [self.useful_rating or 0, self.engagement_rating or 0, self.difficulty_rating or 0, self.competency_rating or 0, self.lecturing_rating or 0, self.enthusiasm_rating or 0, self.approachable_rating or 0]


class Department(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)

    def course_count(self):
        return len(self.primary_course_set.all())

    def non_breaking_name(self):
        return self.name.replace(' ', '&nbsp;')

    def __unicode__(self):
        return u'[%s] %s' % (self.code, self.name)


class RequirementArea(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    campus = models.SmallIntegerField(choices=CAMPUSES)

    def course_count(self):
        return len(self.course_set.all())

    def non_breaking_name(self):
        return self.name.replace(' ', '&nbsp;')

    def __unicode__(self):
        return u'[%s] %s' % (self.code, self.name)

    @models.permalink
    def get_absolute_url(self):
        return ('requirement_area_detail', (), {'slug': self.code, })


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    code_slug = models.CharField(max_length=20, unique=True, db_index=True)

    number = models.IntegerField(default=0)
    name = models.CharField(max_length=256)
    rating = models.FloatField(blank=True, null=True)
    useful_rating = models.FloatField(blank=True, null=True)
    engagement_rating = models.FloatField(blank=True, null=True)
    difficulty_rating = models.FloatField(blank=True, null=True)
    competency_rating = models.FloatField(blank=True, null=True)
    lecturing_rating = models.FloatField(blank=True, null=True)
    enthusiasm_rating = models.FloatField(blank=True, null=True)
    approachable_rating = models.FloatField(blank=True, null=True)

    primary_department = models.ForeignKey(Department, related_name='primary_course_set', null=True)
    departments = models.ManyToManyField(Department, related_name='course_set')
    requirement_areas = models.ManyToManyField(RequirementArea, related_name='course_set')

    def __unicode__(self):
        return u'[%s] %s' % (self.code, self.name)

    class Meta:
        ordering = ('code',)

    @models.permalink
    def get_absolute_url(self):
        return ('course_detail', (),
                {'course_code': self.code_slug})

    def get_miscellaneous_ratings(self):
        return [self.useful_rating or 0, self.engagement_rating or 0, self.difficulty_rating or 0, self.competency_rating or 0, self.lecturing_rating or 0, self.enthusiasm_rating or 0, self.approachable_rating or 0]

    # TODO: Merge instructors who taught this class previously
    def get_instructors_from_all_sections(self):
        instructors = []
        for section in self.sections.all():
            instructors += section.instructors.all()
        return instructors

    def get_most_recent_section(self):
        return self.sections.all().order_by('term')[0]

class Section(models.Model):
    term = models.ForeignKey(Term, related_name='sections')
    course = models.ForeignKey(Course, related_name='sections')

    code = models.CharField(max_length=20)
    code_slug = models.CharField(max_length=20)

    instructors = models.ManyToManyField(Instructor, related_name='sections')

    grading_style = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    credit = models.FloatField(default=1.00)
    requisites = models.BooleanField(default=False)
    fee = models.BooleanField(default=False)

    perms = models.IntegerField(null=True)
    spots = models.IntegerField(null=True)
    filled = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.code
        # return u'[%s] %s (%s)' % (
        #     self.code, self.course.name, ', '.join(self.instructors.all().values_list('name', flatten=True)))

    def get_campuses(self):
        campuses = []
        for mtg in self.meeting_set.all():
            campuses.append(mtg.get_campus())
        return campuses

    def get_campus(self):
        campii = self.get_campuses()
        if len(campii) > 0:
            return self.get_campuses()[0]
        else:
            return 'UU'

    def json(self):
        event_list = []
        for mtg in self.meeting_set.all():
            for begin, end in mtg.to_datetime_ranges():
                event_list.append({
                    'id': '%s-%s-%s' % (self.code, mtg.id, begin.strftime('%w')),
                    'start': begin,
                    'end': end,
                    'title': self.code,
                })

        return {'events': event_list, 'info': {'course_code': self.code, 'course_code_slug': self.code_slug,
                                               'detail_url': self.get_url_to_section_page(),
                                               'campus_code': self.get_campus(), }}

    def get_average_rating(self):
        reviews = CourseReview.objects.filter(course=self.course, instructor__in=self.instructors.all())
        return reviews.aggregate(Avg("overall_rating"))["overall_rating__avg"]

    def get_miscellaneous_ratings(self):
        reviews = CourseReview.objects.filter(course=self.course, instructor__in=self.instructors.all())
        useful_rating = reviews.aggregate(Avg("useful_rating"))["useful_rating__avg"]
        engagement_rating = reviews.aggregate(Avg("engagement_rating"))["engagement_rating__avg"]
        difficulty_rating = reviews.aggregate(Avg("difficulty_rating"))["difficulty_rating__avg"]
        competency_rating = reviews.aggregate(Avg("competency_rating"))["competency_rating__avg"]
        lecturing_rating = reviews.aggregate(Avg("lecturing_rating"))["lecturing_rating__avg"]
        enthusiasm_rating = reviews.aggregate(Avg("enthusiasm_rating"))["enthusiasm_rating__avg"]
        approachable_rating = reviews.aggregate(Avg("approachable_rating"))["approachable_rating__avg"]
        return [useful_rating, engagement_rating, difficulty_rating, competency_rating, lecturing_rating, enthusiasm_rating, approachable_rating]

    @models.permalink
    def get_absolute_url(self):
        if not self.course.primary_department: print self.course
        return ('section_detail', (),
                {'course_code': self.code_slug, 'instructor': self.instructors.all()[0].slug() })

    def get_url_to_section_page(self):
        # It doesn't really matter which instructor we choose here, since from the section page the user will be able
        # to find information about the other instructors that teach this class too (if there are multiple)
        # But never return the "staff" instructor if possible!
        staff_instructor_object = Instructor.objects.get(name='Staff')
        possible_instructors = self.instructors.all()
        instructor = possible_instructors[0] if possible_instructors else staff_instructor_object

        if instructor == staff_instructor_object and len(possible_instructors) > 1:
            instructor = possible_instructors[1]

        return '/courses/browse/instructor/{0}/course/{1}/'.format(instructor.id, self.course.code_slug)

    class Meta:
        ordering = ('code',)


class Meeting(models.Model):
    section = models.ForeignKey(Section)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    begin = models.TimeField()
    end = models.TimeField()
    campus = models.SmallIntegerField(choices=CAMPUSES)
    location = models.CharField(max_length=100)

    def gen_days(self):
        s = []
        if self.monday: s.append('M')
        if self.tuesday: s.append('T')
        if self.wednesday: s.append('W')
        if self.thursday: s.append('R')
        if self.friday: s.append('F')
        return s

    def to_datetime_ranges(self, base_date=None):
        ranges = []
        combine_dates = []

        # Historical note: the frontend calendar supports navigating week
        # by week, but we've turned it into a stripped down week calendar.
        #
        # Under the hood, it still wants a timestamp for events, though it
        # doesn't matter what as long as the day of the week works correctly.
        frontend_calendar_start = date(2012, 9, 3)

        # Note: the version of JQuery-WeekCalendar we have gets off by two on
        # computing day-of-week starting in 2013. Rather than fix this, since
        # we don't use the rest of its features, we froze it in the past.

        if not base_date:
            base_date = frontend_calendar_start

        if self.monday:
            combine_dates.append(base_date + timedelta(
                days=(7 + 0 - base_date.weekday()) % 7 # get correct weekday
                # offset depending on
                # start date weekday
            ))
        if self.tuesday:
            combine_dates.append(base_date + timedelta(
                days=(7 + 1 - base_date.weekday()) % 7
            ))
        if self.wednesday:
            combine_dates.append(base_date + timedelta(
                days=(7 + 2 - base_date.weekday()) % 7
            ))
        if self.thursday:
            combine_dates.append(base_date + timedelta(
                days=(7 + 3 - base_date.weekday()) % 7
            ))
        if self.friday:
            combine_dates.append(base_date + + timedelta(
                days=(7 + 4 - base_date.weekday()) % 7
            ))

        for basedate in combine_dates:
            begin = datetime.combine(basedate, self.begin)
            end = datetime.combine(basedate, self.end)
            if end > begin: # Sanity check for malformed meetings in CX
                ranges.append((begin, end))

        return ranges

    def get_campus(self):
        return CAMPUSES[self.campus - 1][1] # CAMPUSES is now 1-based

    def __unicode__(self):
        return u'[%s] Meeting every %s, %s-%s' % (
            self.section.code, ''.join(self.gen_days()), self.begin.strftime('%I:%M %p'), self.end.strftime('%I:%M %p'))


class Schedule(models.Model):
    sections = models.ManyToManyField(Section)
    create_ts = models.DateTimeField(default=datetime.now)

    def json(self):
        all_sections = []
        for section in self.sections.all():
            all_sections.append(section.json())
        return all_sections

    def json_encoded(self):
        return json.dumps(self.json(), cls=DjangoJSONEncoder)

    @models.permalink
    def get_absolute_url(self):
        return ('aspc.courses.views.view_schedule', (self.id,))

    def outside_url(self):
        return u''.join([settings.OUTSIDE_URL_BASE, self.get_absolute_url()])

    def __unicode__(self):
        return u'Schedule %i' % (self.id,)

class RefreshHistory(models.Model):
    FULL = 0
    REGISTRATION = 1

    run_date = models.DateTimeField(default=datetime.now)
    last_refresh_date = models.DateTimeField()
    term = models.ForeignKey(Term, related_name='term')
    type = models.IntegerField(choices=(
        (FULL, 'Full'),
        (REGISTRATION, 'Registration'),
        ))

    def __unicode__(self):
        return u"{0} refresh at {1}".format(self.get_type_display(), self.last_refresh_date.isoformat())

        class Meta:
            verbose_name_plural = 'refresh histories'

class CourseReview(models.Model):
    author = models.ForeignKey(User)
    course = models.ForeignKey(Course)
    instructor = models.ForeignKey(Instructor)
    created_date = models.DateTimeField(default=datetime.now)
    comments = models.TextField(blank=True, null=True)

    overall_rating = models.FloatField(blank=True, null=True)
    grade = models.PositiveSmallIntegerField(blank=True, null=True, choices=POSSIBLE_GRADES)
    useful_rating = models.FloatField(blank=True, null=True)
    engagement_rating = models.FloatField(blank=True, null=True)
    difficulty_rating = models.FloatField(blank=True, null=True)
    competency_rating = models.FloatField(blank=True, null=True)
    lecturing_rating = models.FloatField(blank=True, null=True)
    enthusiasm_rating = models.FloatField(blank=True, null=True)
    approachable_rating = models.FloatField(blank=True, null=True)
    work_per_week = models.PositiveSmallIntegerField(blank=True, null=True)

    class Meta:
      unique_together = ('author', 'course', 'instructor')

    def __unicode__(self):
        return u"Review of {0} taught by {1}: {2}".format(unicode(self.course.code_slug), unicode(self.instructor.name), unicode(str(self.overall_rating)))

    def get_url_to_section_page(self):
        return '/courses/browse/instructor/{0}/course/{1}/'.format(self.instructor.id, self.course.code_slug)

    def update_course_and_instructor_rating(self):
        instructor_related_reviews = CourseReview.objects.filter(instructor = self.instructor)
        self.instructor.rating = instructor_related_reviews.aggregate(Avg("overall_rating"))["overall_rating__avg"]
        self.instructor.useful_rating = instructor_related_reviews.aggregate(Avg("useful_rating"))["useful_rating__avg"]
        self.instructor.engagement_rating = instructor_related_reviews.aggregate(Avg("engagement_rating"))["engagement_rating__avg"]
        self.instructor.difficulty_rating = instructor_related_reviews.aggregate(Avg("difficulty_rating"))["difficulty_rating__avg"]
        self.instructor.competency_rating = instructor_related_reviews.aggregate(Avg("competency_rating"))["competency_rating__avg"]
        self.instructor.lecturing_rating = instructor_related_reviews.aggregate(Avg("lecturing_rating"))["lecturing_rating__avg"]
        self.instructor.enthusiasm_rating = instructor_related_reviews.aggregate(Avg("enthusiasm_rating"))["enthusiasm_rating__avg"]
        self.instructor.approachable_rating = instructor_related_reviews.aggregate(Avg("approachable_rating"))["approachable_rating__avg"]
        self.instructor.save()

        course_related_reviews = CourseReview.objects.filter(course = self.course)
        self.course.rating = course_related_reviews.aggregate(Avg("overall_rating"))["overall_rating__avg"]
        self.course.useful_rating = course_related_reviews.aggregate(Avg("useful_rating"))["useful_rating__avg"]
        self.course.engagement_rating = course_related_reviews.aggregate(Avg("engagement_rating"))["engagement_rating__avg"]
        self.course.difficulty_rating = course_related_reviews.aggregate(Avg("difficulty_rating"))["difficulty_rating__avg"]
        self.course.competency_rating = course_related_reviews.aggregate(Avg("competency_rating"))["competency_rating__avg"]
        self.course.lecturing_rating = course_related_reviews.aggregate(Avg("lecturing_rating"))["lecturing_rating__avg"]
        self.course.enthusiasm_rating = course_related_reviews.aggregate(Avg("enthusiasm_rating"))["enthusiasm_rating__avg"]
        self.course.approachable_rating = course_related_reviews.aggregate(Avg("approachable_rating"))["approachable_rating__avg"]
        self.course.save()

    # update the instructor/course average on save/create
    def create(self, *args, **kwargs):
        super(CourseReview, self).create(*args, **kwargs)
        self.update_course_and_instructor_rating()

    def save(self, *args, **kwargs):
        super(CourseReview, self).save(*args, **kwargs)
        self.update_course_and_instructor_rating()

    def delete(self, *args, **kwargs):
        super(CourseReview, self).delete(*args, **kwargs)
        self.update_course_and_instructor_rating()
