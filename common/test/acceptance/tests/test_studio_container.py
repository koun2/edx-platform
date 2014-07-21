"""
Acceptance tests for Studio related to the container page.
The container page is used both for display units, and for
displaying containers within units.
"""

from ..pages.studio.auto_auth import AutoAuthPage
from ..pages.studio.overview import CourseOutlinePage
from ..fixtures.course import CourseFixture, XBlockFixtureDesc

from .helpers import UniqueCourseTest
from ..pages.studio.component_editor import ComponentEditorView
from ..pages.studio.utils import add_discussion
from ..pages.lms.courseware import CoursewarePage
from ..pages.lms.staff_view import StaffPage

from unittest import skip
import datetime
from bok_choy.promise import Promise


class ContainerBase(UniqueCourseTest):
    """
    Base class for tests that do operations on the container page.
    """
    __test__ = False

    def setUp(self):
        """
        Create a unique identifier for the course used in this test.
        """
        # Ensure that the superclass sets up
        super(ContainerBase, self).setUp()

        self.outline = CourseOutlinePage(
            self.browser,
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run']
        )

        self.setup_fixtures()

        self.auth_page = AutoAuthPage(
            self.browser,
            staff=False,
            username=self.user.get('username'),
            email=self.user.get('email'),
            password=self.user.get('password')
        )

        self.auth_page.visit()

    def setup_fixtures(self):
        pass

    def go_to_nested_container_page(self):
        """
        Go to the nested container page.
        """
        unit = self.go_to_unit_page()
        # The 0th entry is the unit page itself.
        container = unit.xblocks[1].go_to_container()
        return container

    def go_to_unit_page(self, section_name='Test Section', subsection_name='Test Subsection', unit_name='Test Unit'):
        """
        Go to the test unit page.

        If make_draft is true, the unit page will be put into draft mode.
        """
        self.outline.visit()
        subsection = self.outline.section(section_name).subsection(subsection_name)
        return subsection.toggle_expand().unit(unit_name).go_to()

    def verify_ordering(self, container, expected_orderings):
        """
        Verifies the expected ordering of xblocks on the page.
        """
        xblocks = container.xblocks
        blocks_checked = set()
        for expected_ordering in expected_orderings:
            for xblock in xblocks:
                parent = expected_ordering.keys()[0]
                if xblock.name == parent:
                    blocks_checked.add(parent)
                    children = xblock.children
                    expected_length = len(expected_ordering.get(parent))
                    self.assertEqual(
                        expected_length, len(children),
                        "Number of children incorrect for group {0}. Expected {1} but got {2}.".format(parent, expected_length, len(children)))
                    for idx, expected in enumerate(expected_ordering.get(parent)):
                        self.assertEqual(expected, children[idx].name)
                        blocks_checked.add(expected)
                    break
        self.assertEqual(len(blocks_checked), len(xblocks))

    def verify_groups(self, container, active_groups, inactive_groups):
        """
        Check that the groups appear and are correctly categorized as to active and inactive.

        Also checks that the "add missing groups" button/link is not present unless a value of False is passed
        for verify_missing_groups_not_present.
        """
        def wait_for_xblocks_to_render():
            # First xblock is the container for the page, subtract 1.
            return (len(active_groups) + len(inactive_groups) == len(container.xblocks) - 1, len(active_groups))

        Promise(wait_for_xblocks_to_render, "Number of xblocks on the page are incorrect").fulfill()

        def check_xblock_names(expected_groups, actual_blocks):
            self.assertEqual(len(expected_groups), len(actual_blocks))
            for idx, expected in enumerate(expected_groups):
                self.assertEqual(expected, actual_blocks[idx].name)

        check_xblock_names(active_groups, container.active_xblocks)
        check_xblock_names(inactive_groups, container.inactive_xblocks)

        # Verify inactive xblocks appear after active xblocks
        check_xblock_names(active_groups + inactive_groups, container.xblocks[1:])

    def do_action_and_verify(self, action, expected_ordering):
        """
        Perform the supplied action and then verify the resulting ordering.
        """
        container = self.go_to_nested_container_page()
        action(container)

        self.verify_ordering(container, expected_ordering)

        # Reload the page to see that the change was persisted.
        container = self.go_to_nested_container_page()
        self.verify_ordering(container, expected_ordering)


class NestedVerticalTest(ContainerBase):
    __test__ = False

    """
    Sets up a course structure with nested verticals.
    """
    def setup_fixtures(self):
        self.container_title = ""
        self.group_a = "Group A"
        self.group_b = "Group B"
        self.group_empty = "Group Empty"
        self.group_a_item_1 = "Group A Item 1"
        self.group_a_item_2 = "Group A Item 2"
        self.group_b_item_1 = "Group B Item 1"
        self.group_b_item_2 = "Group B Item 2"

        self.group_a_handle = 0
        self.group_a_item_1_handle = 1
        self.group_a_item_2_handle = 2
        self.group_empty_handle = 3
        self.group_b_handle = 4
        self.group_b_item_1_handle = 5
        self.group_b_item_2_handle = 6

        self.group_a_item_1_action_index = 0
        self.group_a_item_2_action_index = 1

        self.duplicate_label = "Duplicate of '{0}'"
        self.discussion_label = "Discussion"

        course_fix = CourseFixture(
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run'],
            self.course_info['display_name']
        )

        course_fix.add_children(
            XBlockFixtureDesc('chapter', 'Test Section').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection').add_children(
                    XBlockFixtureDesc('vertical', 'Test Unit').add_children(
                        XBlockFixtureDesc('vertical', 'Test Container').add_children(
                            XBlockFixtureDesc('vertical', 'Group A').add_children(
                                XBlockFixtureDesc('html', self.group_a_item_1),
                                XBlockFixtureDesc('html', self.group_a_item_2)
                            ),
                            XBlockFixtureDesc('vertical', 'Group Empty'),
                            XBlockFixtureDesc('vertical', 'Group B').add_children(
                                XBlockFixtureDesc('html', self.group_b_item_1),
                                XBlockFixtureDesc('html', self.group_b_item_2)
                            )
                        )
                    )
                )
            )
        ).install()

        self.user = course_fix.user


class DragAndDropTest(NestedVerticalTest):
    """
    Tests of reordering within the container page.
    """
    __test__ = True

    def drag_and_verify(self, source, target, expected_ordering):
        self.do_action_and_verify(
            lambda (container): container.drag(source, target),
            expected_ordering
        )

    @skip("Sporadically drags outside of the Group.")
    def test_reorder_in_group(self):
        """
        Drag Group A Item 2 before Group A Item 1.
        """
        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_a_item_2, self.group_a_item_1]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]
        self.drag_and_verify(self.group_a_item_2_handle, self.group_a_item_1_handle, expected_ordering)

    def test_drag_to_top(self):
        """
        Drag Group A Item 1 to top level (outside of Group A).
        """
        expected_ordering = [{self.container_title: [self.group_a_item_1, self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]
        self.drag_and_verify(self.group_a_item_1_handle, self.group_a_handle, expected_ordering)

    def test_drag_into_different_group(self):
        """
        Drag Group B Item 1 into Group A (first element).
        """
        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_b_item_1, self.group_a_item_1, self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_2]},
                             {self.group_empty: []}]
        self.drag_and_verify(self.group_b_item_1_handle, self.group_a_item_1_handle, expected_ordering)

    def test_drag_group_into_group(self):
        """
        Drag Group B into Group A (first element).
        """
        expected_ordering = [{self.container_title: [self.group_a, self.group_empty]},
                             {self.group_a: [self.group_b, self.group_a_item_1, self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]
        self.drag_and_verify(self.group_b_handle, self.group_a_item_1_handle, expected_ordering)

    def test_drag_after_addition(self):
        """
        Add some components and then verify that drag and drop still works.
        """
        group_a_menu = 0

        def add_new_components_and_rearrange(container):
            # Add a video component to Group 1
            add_discussion(container, group_a_menu)
            # Duplicate the first item in Group A
            container.duplicate(self.group_a_item_1_action_index)

            first_handle = self.group_a_item_1_handle
            # Drag newly added video component to top.
            container.drag(first_handle + 3, first_handle)
            # Drag duplicated component to top.
            container.drag(first_handle + 2, first_handle)

        duplicate_label = self.duplicate_label.format(self.group_a_item_1)

        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [duplicate_label, self.discussion_label, self.group_a_item_1, self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]

        self.do_action_and_verify(add_new_components_and_rearrange, expected_ordering)


class AddComponentTest(NestedVerticalTest):
    """
    Tests of adding a component to the container page.
    """
    __test__ = True

    def add_and_verify(self, menu_index, expected_ordering):
        self.do_action_and_verify(
            lambda (container): add_discussion(container, menu_index),
            expected_ordering
        )

    def test_add_component_in_group(self):
        group_b_menu = 2

        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_a_item_1, self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2, self.discussion_label]},
                             {self.group_empty: []}]
        self.add_and_verify(group_b_menu, expected_ordering)

    def test_add_component_in_empty_group(self):
        group_empty_menu = 1

        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_a_item_1, self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: [self.discussion_label]}]
        self.add_and_verify(group_empty_menu, expected_ordering)

    def test_add_component_in_container(self):
        container_menu = 3

        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b, self.discussion_label]},
                             {self.group_a: [self.group_a_item_1, self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]
        self.add_and_verify(container_menu, expected_ordering)


class DuplicateComponentTest(NestedVerticalTest):
    """
    Tests of duplicating a component on the container page.
    """
    __test__ = True

    def duplicate_and_verify(self, source_index, expected_ordering):
        self.do_action_and_verify(
            lambda (container): container.duplicate(source_index),
            expected_ordering
        )

    def test_duplicate_first_in_group(self):
        duplicate_label = self.duplicate_label.format(self.group_a_item_1)
        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_a_item_1, duplicate_label, self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]
        self.duplicate_and_verify(self.group_a_item_1_action_index, expected_ordering)

    def test_duplicate_second_in_group(self):
        duplicate_label = self.duplicate_label.format(self.group_a_item_2)
        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_a_item_1, self.group_a_item_2, duplicate_label]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]
        self.duplicate_and_verify(self.group_a_item_2_action_index, expected_ordering)

    def test_duplicate_the_duplicate(self):
        first_duplicate_label = self.duplicate_label.format(self.group_a_item_1)
        second_duplicate_label = self.duplicate_label.format(first_duplicate_label)

        expected_ordering = [
            {self.container_title: [self.group_a, self.group_empty, self.group_b]},
            {self.group_a: [self.group_a_item_1, first_duplicate_label, second_duplicate_label, self.group_a_item_2]},
            {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
            {self.group_empty: []}
        ]

        def duplicate_twice(container):
            container.duplicate(self.group_a_item_1_action_index)
            container.duplicate(self.group_a_item_1_action_index + 1)

        self.do_action_and_verify(duplicate_twice, expected_ordering)


class DeleteComponentTest(NestedVerticalTest):
    """
    Tests of deleting a component from the container page.
    """
    __test__ = True

    def delete_and_verify(self, source_index, expected_ordering):
        self.do_action_and_verify(
            lambda (container): container.delete(source_index),
            expected_ordering
        )

    def test_delete_first_in_group(self):
        expected_ordering = [{self.container_title: [self.group_a, self.group_empty, self.group_b]},
                             {self.group_a: [self.group_a_item_2]},
                             {self.group_b: [self.group_b_item_1, self.group_b_item_2]},
                             {self.group_empty: []}]

        # Group A itself has a delete icon now, so item_1 is index 1 instead of 0.
        group_a_item_1_delete_index = 1
        self.delete_and_verify(group_a_item_1_delete_index, expected_ordering)


class EditContainerTest(NestedVerticalTest):
    """
    Tests of editing a container.
    """
    __test__ = True

    def modify_display_name_and_verify(self, component):
        """
        Helper method for changing a display name.
        """
        modified_name = 'modified'
        self.assertNotEqual(component.name, modified_name)
        component.edit()
        component_editor = ComponentEditorView(self.browser, component.locator)
        component_editor.set_field_value_and_save('Display Name', modified_name)
        self.assertEqual(component.name, modified_name)

    def test_edit_container_on_unit_page(self):
        """
        Test the "edit" button on a container appearing on the unit page.
        """
        unit = self.go_to_unit_page()
        component = unit.xblocks[1]
        self.modify_display_name_and_verify(component)

    def test_edit_container_on_container_page(self):
        """
        Test the "edit" button on a container appearing on the container page.
        """
        container = self.go_to_nested_container_page()
        self.modify_display_name_and_verify(container)


class UnitPublishingTest(ContainerBase):
    """
    Tests of the publishing control and related widgets on the Unit page.
    """
    __test__ = True

    PUBLISHED_STATUS = "Publishing Status\nPublished"
    DRAFT_STATUS = "Publishing Status\nDraft (Unpublished changes)"
    LOCKED_STATUS = "Publishing Status\nUnpublished (Staff only)"
    RELEASE_TITLE_RELEASED = "RELEASED:"

    def setup_fixtures(self):
        """
        Sets up a course structure with a unit and a single HTML child.
        """
        self.html_content = '<p><strong>Body of HTML Unit.</strong></p>'
        self.courseware = CoursewarePage(self.browser, self.course_id)

        course_fix = CourseFixture(
            self.course_info['org'],
            self.course_info['number'],
            self.course_info['run'],
            self.course_info['display_name']
        )
        past_start_date = datetime.datetime(1974, 6, 22)
        self.past_start_date_text = "Jun 22, 1974 at 00:00 UTC"

        course_fix.add_children(
            XBlockFixtureDesc('chapter', 'Test Section').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection').add_children(
                    XBlockFixtureDesc('vertical', 'Test Unit').add_children(
                        XBlockFixtureDesc('html', 'Test html', data=self.html_content)
                    )
                )
            ),
            XBlockFixtureDesc('chapter', 'Unlocked Section', metadata={'start': past_start_date.isoformat()}).add_children(
                XBlockFixtureDesc('sequential', 'Unlocked Subsection').add_children(
                    XBlockFixtureDesc('vertical', 'Unlocked Unit').add_children(
                        XBlockFixtureDesc('problem', '<problem></problem>', data=self.html_content)
                    )
                )
            ),
            XBlockFixtureDesc('chapter', 'Section With Locked Unit').add_children(
                XBlockFixtureDesc('sequential', 'Subsection With Locked Unit', metadata={'start': past_start_date.isoformat()}).add_children(
                    XBlockFixtureDesc('vertical', 'Locked Unit', metadata={'visible_to_staff_only': True}).add_children(
                        XBlockFixtureDesc('discussion', '', data=self.html_content)
                    )
                )
            )
        ).install()

        self.user = course_fix.user

    def test_publishing(self):
        """
        Scenario: The publish title changes based on whether or not draft content exists
            Given I have a published unit with no unpublished changes
            When I go to the unit page in Studio
            Then the title in the Publish information box is "Published"
            And the Publish button is disabled
            And when I add a component to the unit
            Then the title in the Publish information box is "Draft (Unpublished changes)"
            And the Publish button is enabled
            And when I click the Publish button
            Then the title in the Publish information box is "Published"
        """
        unit = self.go_to_unit_page()
        self._verify_publish_title(unit, self.PUBLISHED_STATUS)
        # Start date set in course fixture to 1970.
        self._verify_release_date_info(
            unit, self.RELEASE_TITLE_RELEASED, 'Jan 01, 1970 at 00:00 UTC with Section "Test Section"'
        )
        # Should not be able to click on Publish action -- but I don't know how to test that it is not clickable.
        # TODO: continue discussion with Muhammad and Jay about this.

        # Add a component to the page so it will have unpublished changes.
        add_discussion(unit)
        self._verify_publish_title(unit, self.DRAFT_STATUS)
        unit.publish_action.click()
        unit.wait_for_ajax()
        self._verify_publish_title(unit, self.PUBLISHED_STATUS)

    def test_discard_changes(self):
        """
        Scenario: The publish title changes after "Discard Changes" is clicked
            Given I have a published unit with no unpublished changes
            When I go to the unit page in Studio
            Then the Discard Changes button is disabled
            And I add a component to the unit
            Then the title in the Publish information box is "Draft (Unpublished changes)"
            And the Discard Changes button is enabled
            And when I click the Discard Changes button
            Then the title in the Publish information box is "Published"
        """
        unit = self.go_to_unit_page()
        add_discussion(unit)
        self._verify_publish_title(unit, self.DRAFT_STATUS)
        unit.discard_changes()
        self._verify_publish_title(unit, self.PUBLISHED_STATUS)

    def test_view_live_no_changes(self):
        """
        Scenario: "View Live" shows published content in LMS
            Given I have a published unit with no unpublished changes
            When I go to the unit page in Studio
            Then the View Live button is enabled
            And when I click on the View Live button
            Then I see the published content in LMS
        """
        unit = self.go_to_unit_page()
        unit.view_published_version()
        self._verify_components_visible(['html'])

    def test_view_live_changes(self):
        """
        Scenario: "View Live" does not show draft content in LMS
            Given I have a published unit with no unpublished changes
            When I go to the unit page in Studio
            And when I add a component to the unit
            And when I click on the View Live button
            Then I see the published content in LMS
            And I do not see the unpublished component
        """
        unit = self.go_to_unit_page()
        add_discussion(unit)
        unit.view_published_version()
        self._verify_components_visible(['html'])
        self.assertEqual(self.html_content, self.courseware.xblock_component_html_content(0))

    def test_view_live_after_publish(self):
        """
        Scenario: "View Live" shows newly published content
            Given I have a published unit with no unpublished changes
            When I go to the unit page in Studio
            And when I add a component to the unit
            And when I click the Publish button
            And when I click on the View Live button
            Then I see the newly published component
        """
        unit = self.go_to_unit_page()
        add_discussion(unit)
        unit.publish_action.click()
        unit.view_published_version()
        self._verify_components_visible(['html', 'discussion'])

    def test_initially_unlocked_visible_to_students(self):
        """
        Scenario: An unlocked unit with release date in the past is visible to students
            Given I have a published unlocked unit with release date in the past
            When I go to the unit page in Studio
            Then the unit has a warning that it is visible to students
            And it is marked as "RELEASED" with release date in the past visible
            And when I click on the View Live Button
            And when I view the course as a student
            Then I see the content in the unit
        """
        unit = self.go_to_unit_page("Unlocked Section", "Unlocked Subsection", "Unlocked Unit")
        self._verify_publish_title(unit, self.PUBLISHED_STATUS)
        self.assertTrue(unit.currently_visible_to_students)
        self._verify_release_date_info(
            unit, self.RELEASE_TITLE_RELEASED, self.past_start_date_text + ' with Section "Unlocked Section"'
        )
        unit.view_published_version()
        self._verify_student_view_visible(['problem'])

    def test_locked_visible_to_staff_only(self):
        """
        Scenario: After locking a unit with release date in the past, it is only visible to staff
            Given I have a published unlocked unit with release date in the past
            When I go to the unit page in Studio
            And when I select "Hide from students"
            Then the unit does not have a warning that it is visible to students
            And when I click on the View Live Button
            Then I see the content in the unit when logged in as staff
            And when I view the course as a student
            Then I do not see any content in the unit
        """
        unit = self.go_to_unit_page("Unlocked Section", "Unlocked Subsection", "Unlocked Unit")
        checked = unit.toggle_staff_lock()
        self.assertTrue(checked)
        self.assertFalse(unit.currently_visible_to_students)
        self._verify_publish_title(unit, self.LOCKED_STATUS)
        unit.view_published_version()
        # Will initially be in staff view, locked component should be visible.
        self._verify_components_visible(['problem'])
        # Switch to student view and verify not visible
        self._verify_student_view_locked()

    def test_initially_locked_not_visible_to_students(self):
        """
        Scenario: A locked unit with release date in the past is not visible to students
            Given I have a published locked unit with release date in the past
            When I go to the unit page in Studio
            Then the unit does not have a warning that it is visible to students
            And it is marked as "RELEASED" with release date in the past visible
            And when I click on the View Live Button
            And when I view the course as a student
            Then I do not see any content in the unit
        """
        unit = self.go_to_unit_page("Section With Locked Unit", "Subsection With Locked Unit", "Locked Unit")
        self._verify_publish_title(unit, self.LOCKED_STATUS)
        self.assertFalse(unit.currently_visible_to_students)
        self._verify_release_date_info(
            unit, self.RELEASE_TITLE_RELEASED,
            self.past_start_date_text + ' with Subsection "Subsection With Locked Unit"'
        )
        unit.view_published_version()
        self._verify_student_view_locked()

    def test_unlocked_visible_to_all(self):
        """
        Scenario: After unlocking a unit with release date in the past, it is visible to both students and staff
            Given I have a published unlocked unit with release date in the past
            When I go to the unit page in Studio
            And when I deselect "Hide from students"
            Then the unit does have a warning that it is visible to students
            And when I click on the View Live Button
            Then I see the content in the unit when logged in as staff
            And when I view the course as a student
            Then I see the content in the unit
        """
        unit = self.go_to_unit_page("Section With Locked Unit", "Subsection With Locked Unit", "Locked Unit")
        checked = unit.toggle_staff_lock()
        self.assertFalse(checked)
        self._verify_publish_title(unit, self.PUBLISHED_STATUS)
        self.assertTrue(unit.currently_visible_to_students)
        unit.view_published_version()
        # Will initially be in staff view, components always visible.
        self._verify_components_visible(['discussion'])
        # Switch to student view and verify visible.
        self._verify_student_view_visible(['discussion'])

    def _verify_student_view_locked(self):
        """
        Verifies no component is visible when viewing as a student.
        """
        StaffPage(self.browser).toggle_staff_view()
        self.assertEqual(0, self.courseware.num_xblock_components)

    def _verify_student_view_visible(self, expected_components):
        """
        Verifies expected components are visible when viewing as a student.
        """
        StaffPage(self.browser).toggle_staff_view()
        self._verify_components_visible(expected_components)

    def _verify_components_visible(self, expected_components):
        """
        Verifies the expected components are visible (and there are no extras).
        """
        self.assertEqual(len(expected_components), self.courseware.num_xblock_components)
        for index, component in enumerate(expected_components):
            self.assertEqual(component, self.courseware.xblock_component_type(index))

    def _verify_release_date_info(self, unit, expected_title, expected_date):
        """
        Verifies how the release date is displayed in the publishing sidebar.
        """
        self.assertEqual(expected_title, unit.release_title)
        self.assertEqual(expected_date, unit.release_date)

    def _verify_publish_title(self, unit, expected_title):
        """
        Waits for the publish title to change to the expected value.
        """
        def wait_for_title_change():
            return (unit.publish_title == expected_title, unit.publish_title)

        Promise(wait_for_title_change, "Publish title incorrect. Found '" + unit.publish_title + "'").fulfill()

    # TODO: need to work with Jay/Christine to get testing of "Preview" working.
    # def test_preview(self):
    #     unit = self.go_to_unit_page()
    #     add_discussion(unit)
    #     unit.preview()
    #     self.assertEqual(2, self.courseware.num_xblock_components)
    #     self.assertEqual('html', self.courseware.xblock_component_type(0))
    #     self.assertEqual('discussion', self.courseware.xblock_component_type(1))
