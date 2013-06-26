"""
This file contains tasks that are designed to perform background operations on the
running state of a course.

At present, these tasks all operate on StudentModule objects in one way or another,
so they share a visitor architecture.  Each task defines an "update function" that
takes a module_descriptor, a particular StudentModule object, and xmodule_instance_args.

A task may optionally specify a "filter function" that takes a query for StudentModule
objects, and adds additional filter clauses.

A task also passes through "xmodule_instance_args", that are used to provide
information to our code that instantiates xmodule instances.

The task definition then calls the traversal function, passing in the three arguments
above, along with the id value for an InstructorTask object.  The InstructorTask
object contains a 'task_input' row which is a JSON-encoded dict containing
a problem URL and optionally a student.  These are used to set up the initial value
of the query for traversing StudentModule objects.

"""
from django.utils.translation import ugettext_noop
from celery import task
from functools import partial

from instructor_task.tasks_helper import (
    run_main_task,
    BaseInstructorTask,
    delete_problem_module_state,
    perform_enrolled_student_update,
    _perform_module_state_update, # Evil, temporary
    rescore_problem_module_state,
    reset_attempts_module_state,
    update_offline_grade,
    update_problem_module_state
)
from bulk_email.tasks import perform_delegate_email_batches


@task(base=BaseInstructorTask)  # pylint: disable=E1102
def rescore_problem(entry_id, xmodule_instance_args):
    """Rescores a problem in a course, for all students or one specific student.

    `entry_id` is the id value of the InstructorTask entry that corresponds to this task.
    The entry contains the `course_id` that identifies the course, as well as the
    `task_input`, which contains task-specific input.

    The task_input should be a dict with the following entries:

      'problem_url': the full URL to the problem to be rescored.  (required)

      'student': the identifier (username or email) of a particular user whose
          problem submission should be rescored.  If not specified, all problem
          submissions for the problem will be rescored.

    `xmodule_instance_args` provides information needed by _get_module_instance_for_task()
    to instantiate an xmodule instance.
    """
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('rescored')
    update_fcn = partial(rescore_problem_module_state, xmodule_instance_args)

    def filter_fcn(modules_to_update):
        """Filter that matches problems which are marked as being done"""
        return modules_to_update.filter(state__contains='"done": true')

    visit_fcn = partial(_perform_module_state_update, update_fcn, filter_fcn)
    return run_main_task(entry_id, visit_fcn, action_name)


@task(base=BaseInstructorTask)  # pylint: disable=E1102
def reset_problem_attempts(entry_id, xmodule_instance_args):
    """Resets problem attempts to zero for a particular problem for all students in a course.

    `entry_id` is the id value of the InstructorTask entry that corresponds to this task.
    The entry contains the `course_id` that identifies the course, as well as the
    `task_input`, which contains task-specific input.

    The task_input should be a dict with the following entries:

      'problem_url': the full URL to the problem to be rescored.  (required)

    `xmodule_instance_args` provides information needed by _get_module_instance_for_task()
    to instantiate an xmodule instance.
    """
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('reset')
    update_fcn = partial(reset_attempts_module_state, xmodule_instance_args)
    visit_fcn = partial(perform_module_state_update, update_fcn, None)
    return run_main_task(entry_id, visit_fcn, action_name)


@task(base=BaseInstructorTask)  # pylint: disable=E1102
def delete_problem_state(entry_id, xmodule_instance_args):
    """Deletes problem state entirely for all students on a particular problem in a course.

    `entry_id` is the id value of the InstructorTask entry that corresponds to this task.
    The entry contains the `course_id` that identifies the course, as well as the
    `task_input`, which contains task-specific input.

    The task_input should be a dict with the following entries:

      'problem_url': the full URL to the problem to be rescored.  (required)

    `xmodule_instance_args` provides information needed by _get_module_instance_for_task()
    to instantiate an xmodule instance.
    """
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('deleted')
    update_fcn = partial(delete_problem_module_state, xmodule_instance_args)
    visit_fcn = partial(perform_module_state_update, update_fcn, None)
    return run_main_task(entry_id, visit_fcn, action_name)


@task(base=BaseInstructorTask)  # pylint: disable=E1102
def send_bulk_course_email(entry_id, _xmodule_instance_args):
    """Sends emails to recipients enrolled in a course.

    action_name = 'deleted'
    update_fcn = partial(delete_problem_module_state, xmodule_instance_args)
    visit_fcn = perform_module_state_update
    return run_update_task(entry_id, visit_fcn, update_fcn, action_name, filter_fcn=None)

    The task_input should be a dict with the following entries:

      'email_id': the full URL to the problem to be rescored.  (required)

    `_xmodule_instance_args` provides information needed by _get_module_instance_for_task()
    to instantiate an xmodule instance.  This is unused here.
    """
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('emailed')
    visit_fcn = perform_delegate_email_batches
    return run_main_task(entry_id, visit_fcn, action_name)


@task(base=BaseInstructorTask)  # pylint: disable=E1102
def update_offline_grades(entry_id, xmodule_instance_args):
    """Updates grades stored offline for all students in a course.

    `entry_id` is the id value of the InstructorTask entry that corresponds to this task.
    The entry contains the `course_id` that identifies the course, as well as the
    `task_input`, which contains task-specific input.

    The task_input should be a dict with no entries.

    `xmodule_instance_args` provides information needed by _get_module_instance_for_task()
    to instantiate an xmodule instance.
    """
    action_name = 'graded'
    update_fcn = partial(update_offline_grade, xmodule_instance_args)
    visit_fcn = perform_enrolled_student_update
    return run_update_task(entry_id, visit_fcn, update_fcn, action_name, filter_fcn=None)
