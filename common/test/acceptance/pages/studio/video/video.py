"""
CMS Video
"""

import os
import requests
from bok_choy.promise import EmptyPromise, Promise
from bok_choy.javascript import wait_for_js, js_defined
from ....tests.helpers import YouTubeStubConfig
from ...lms.video.video import VideoPage
from selenium.webdriver.common.keys import Keys


CLASS_SELECTORS = {
    'video_container': 'div.video',
    'video_init': '.is-initialized',
    'video_xmodule': '.xmodule_VideoModule',
    'video_spinner': '.video-wrapper .spinner',
    'video_controls': 'section.video-controls',
    'attach_asset': '.upload-dialog > input[type="file"]',
    'upload_dialog': '.wrapper-modal-window-assetupload',
    'xblock': '.add-xblock-component',
    'slider_range': '.slider-range',
}

BUTTON_SELECTORS = {
    'create_video': "a[data-category='video']",
    'handout_download': '.video-handout.video-download-button a',
    'handout_download_editor': '.wrapper-comp-setting.file-uploader .download-action',
    'upload_asset': '.upload-action',
    'asset_submit': '.action-upload',
    'handout_clear': '.wrapper-comp-setting.file-uploader .setting-clear',
}

DISPLAY_NAME = "Component Display Name"

DEFAULT_SETTINGS = [
    # basic
    [DISPLAY_NAME, 'Video', False],
    ['Default Video URL', 'http://youtu.be/OEoXaMPEzfM, , ', False],

    # advanced
    [DISPLAY_NAME, 'Video', False],
    ['Default Timed Transcript', '', False],
    ['Download Transcript Allowed', 'False', False],
    ['Downloadable Transcript URL', '', False],
    ['Show Transcript', 'True', False],
    ['Transcript Languages', '', False],
    ['Upload Handout', '', False],
    ['Video Download Allowed', 'False', False],
    ['Video File URLs', '', False],
    ['Video Start Time', '00:00:00', False],
    ['Video Stop Time', '00:00:00', False],
    ['YouTube ID', 'OEoXaMPEzfM', False],
    ['YouTube ID for .75x speed', '', False],
    ['YouTube ID for 1.25x speed', '', False],
    ['YouTube ID for 1.5x speed', '', False]
]


@js_defined('window.Video', 'window.RequireJS.require', 'window.jQuery', 'window.XModule', 'window.XBlock',
            'window.MathJax.isReady')
class VideoComponentPage(VideoPage):
    """
    CMS Video Component Page
    """

    url = None

    @wait_for_js
    def is_browser_on_page(self):
        return self.q(css='div{0}'.format(CLASS_SELECTORS['video_xmodule'])).present or self.q(
            css='div{0}'.format(CLASS_SELECTORS['xblock'])).present

    def get_element_selector(self, video_display_name, class_name, vertical=True):
        return super(VideoComponentPage, self).get_element_selector(None, class_name, vertical=False)

    def _wait_for(self, check_func, desc, result=False, timeout=200):
        """
        Calls the method provided as an argument until the Promise satisfied or BrokenPromise

        Arguments:
            check_func (callable): Promise function to be fulfilled.
            desc (str): Description of the Promise, used in log messages.
            result (bool): Indicates whether we need result from Promise or not
            timeout (float): Maximum number of seconds to wait for the Promise to be satisfied before timing out.

        """
        if result:
            return Promise(check_func, desc, timeout=timeout).fulfill()
        else:
            return EmptyPromise(check_func, desc, timeout=timeout).fulfill()

    def wait_for_video_component_render(self):
        """
        Wait until video component rendered completely
        """
        if not YouTubeStubConfig.get_configuration().get('youtube_api_blocked'):
            self._wait_for(lambda: self.q(css=CLASS_SELECTORS['video_init']).present, 'Video Player Initialized')
            self._wait_for(lambda: not self.q(css=CLASS_SELECTORS['video_spinner']).visible,
                           'Video Buffering Completed')
            self._wait_for(lambda: self.q(css=CLASS_SELECTORS['video_controls']).visible, 'Player Controls are Visible')

    def click_button(self, button_name, index=0):
        """
        Click on a button as specified by `button_name`

        Arguments:
            button_name (str): button name
            index (int): query index

        """
        self.q(css=BUTTON_SELECTORS[button_name]).nth(index).click()
        self.wait_for_ajax()

    @staticmethod
    def file_path(filename):
        """
        Construct file path to be uploaded to assets.

        Arguments:
            filename (str): asset filename

        """
        return os.sep.join(__file__.split(os.sep)[:-5]) + '/data/uploads/' + filename

    def upload_handout(self, handout_filename):
        """
        Upload a handout file to assets

        Arguments:
            handout_filename (str): handout file name

        """
        self.upload_asset(handout_filename)

    def upload_asset(self, asset_filename, index=0):
        """
        Upload a asset file to assets

        Arguments:
            asset_filename (str): asset file name
            index (int): query index

        """
        asset_file_path = self.file_path(asset_filename)

        self.click_button('upload_asset', index)

        self.q(css=CLASS_SELECTORS['attach_asset']).results[0].send_keys(asset_file_path)

        self.click_button('asset_submit')

        # confirm upload completion
        self._wait_for(lambda: not self.q(css=CLASS_SELECTORS['upload_dialog']).present, 'Upload Completed')

    def clear_handout(self):
        """
        Clear handout from settings
        """
        self.click_button('handout_clear')

    def _get_handout(self, url):
        """
        Download handout at `url`
        """
        kwargs = dict()

        session_id = [{i['name']: i['value']} for i in self.browser.get_cookies() if i['name'] == u'sessionid']
        if session_id:
            kwargs.update({
                'cookies': session_id[0]
            })

        response = requests.get(url, **kwargs)
        return response.status_code < 400, response.headers

    def download_handout(self, mime_type, is_editor=False):
        """
        Download handout with mime type specified by `mime_type`

        Arguments:
            mime_type (str): mime type of handout file

        Returns:
            tuple: Handout download result.

        """
        selector = BUTTON_SELECTORS['handout_download_editor'] if is_editor else BUTTON_SELECTORS['handout_download']

        handout_url = self.q(css=selector).attrs('href')[0]
        result, headers = self._get_handout(handout_url)

        return result, headers['content-type'] == mime_type

    @property
    def is_handout_button_visible(self):
        """
        Check if handout download button is visible
        """
        # TODO! Remove .present below after bok-choy is updated to latest commit, Only .visible is enough
        return self.q(css=BUTTON_SELECTORS['handout_download']).present and self.q(
            css=BUTTON_SELECTORS['handout_download']).visible

    def create_video(self):
        """
        Create a Video Component by clicking on Video button and wait rendering completion.
        """
        component_selector = '.component'

        # Create video
        self.click_button('create_video')
        self.wait_for_video_component_render()

        # Get current xblock components count
        # New xblock components count should be equals to 2
        # Why 2? One video component is created by default for each test. Please see
        # test_studio_video_module.py:CMSVideoTest._create_course_unit
        # And we are creating second video component here.
        xblock_components_after = len(self.q(css=component_selector).results)

        # Also ensure that newly created xblock component type is video
        xblock_component_type_selector = 'li.component .xblock'
        new_xblock_component_types = self.q(css=xblock_component_type_selector).attrs('data-block-type')

        return xblock_components_after == 2 and new_xblock_component_types[1] == 'video'

    def focus_caption_line(self, line_number):
        """
        Focus a caption line as specified by `line_number`

        Arguments:
            line_number (int): caption line number

        """
        caption_line_selector = ".subtitles > li[data-index='{index}']".format(index=line_number - 1)
        self.q(css=caption_line_selector).results[0].send_keys(Keys.ENTER)

    def is_caption_line_focused(self, line_number):
        """
        Check if a caption line focused

        Arguments:
            line_number (int): caption line number

        """
        caption_line_selector = ".subtitles > li[data-index='{index}']".format(index=line_number - 1)
        attributes = self.q(css=caption_line_selector).attrs('class')

        return 'focused' in attributes

    def set_settings_field_value(self, field, value):
        """
        In Advanced Tab set `field` with `value`

        Arguments:
            field (str): field name
            value (str): field value

        """
        query = '.wrapper-comp-setting > label:nth-child(1)'
        field_id = ''

        for index, _ in enumerate(self.q(css=query)):
            if field in self.q(css=query).nth(index).text[0]:
                field_id = self.q(css=query).nth(index).attrs('for')[0]
                break

        self.q(css='#{}'.format(field_id)).fill(value)

    @property
    def is_slider_range_visible(self):
        """
        Check if slider range visible.

        Returns:
            bool: slider range is visible of not

        """
        return self.q(css=CLASS_SELECTORS['slider_range']).visible

    def verify_settings(self):
        """
        Verify that video component has correct default settings.
        """
        query = '.wrapper-comp-setting'

        settings = self.q(css=query).results

        if len(DEFAULT_SETTINGS) != len(settings):
            return False

        for counter, setting in enumerate(settings):
            is_verified = self._verify_setting_entry(setting,
                                                     DEFAULT_SETTINGS[counter][0],
                                                     DEFAULT_SETTINGS[counter][1],
                                                     DEFAULT_SETTINGS[counter][2])
            if is_verified is False:
                return is_verified

        return True


    @staticmethod
    def _verify_setting_entry(setting, field_name, field_value, explicitly_set):
        """
        Verify a `setting` entry.

        Arguments:
            setting (WebElement): Selenium WebElement
            field_name (str): Name of field
            field_value (str): Value of field

        Returns:
            bool: Is `setting` has correct value

        """
        if field_name != setting.find_element_by_class_name('setting-label').get_attribute('innerHTML'):
            return False

        # Get class attribute values
        classes = setting.get_attribute('class').split()
        list_type_classes = ['metadata-list-enum', 'metadata-dict', 'metadata-video-translations']
        is_list_type = any(list_type in classes for list_type in list_type_classes)

        if is_list_type:
            current_value = ', '.join(
                ele.get_attribute('value') for ele in setting.find_elements_by_class_name('list-settings-item'))
        elif 'metadata-videolist-enum' in setting.get_attribute('class'):
            current_value = ', '.join(item.find_element_by_tag_name('input').get_attribute('value') for item in
                                      setting.find_elements_by_class_name('videolist-settings-item'))
        else:
            current_value = setting.find_element_by_class_name('setting-input').get_attribute('value')

        if field_value != current_value:
            return False

        # Clear button should be visible(active class is present) for
        # every setting that don't have 'metadata-videolist-enum' class
        if 'metadata-videolist-enum' not in setting.get_attribute('class'):
            setting_clear_button = setting.find_elements_by_class_name('setting-clear')[0]
            if 'active' not in setting_clear_button.get_attribute('class'):
                return False

        return True

    def set_field_value(self, field_name, field_value, field_type='input'):
        """
        Set settings input `field` with `value`

        Arguments:
            field_name (str): Name of field
            field_value (str): Name of value
            field_type (str): `input`, `select` etc(more to be added later)

        """
        query = '.wrapper-comp-setting > label:nth-child(1)'
        field_id = ''

        if field_type == 'input':
            for index, setting in enumerate(self.q(css=query)):
                if field_name in self.q(css=query).nth(index).text[0]:
                    field_id = self.q(css=query).nth(index).attrs('for')[0]
                    break

            self.q(css='#{}'.format(field_id)).fill(field_value)
        elif field_type == 'select':
            self.q(css='select[name="{0}"] option[value="{1}"]'.format(field_name, field_value)).first.click()

    def verify_field_value(self, field_name, field_value):
        """
        Get settings value of `field_name`

        Arguments:
            field_name (str): Name of field
            field_value (str): Name of value

        Returns:
            bool: If `field_name` has `field_value`

        """
        _, setting = self._get_setting_entry(field_name)
        return self._verify_setting_entry(setting, field_name, field_value, True)

    def _get_setting_entry(self, field_name):
        """
        Get setting entry of `field_name`

        Arguments:
            field_name (str): Name of field

        Returns:
            setting (WebElement): Selenium WebElement

        """
        for index, setting in enumerate(self.q(css='.wrapper-comp-setting').results):
            if setting.find_element_by_class_name('setting-label').get_attribute('innerHTML') == field_name:
                return index, setting

    def upload_translation(self, transcript_name, language_code):
        """
        Upload a translation file.

        Arguments:
            transcript_name (str):
            language_code (str):

        """
        # Click on `Transcript Languages` Add button
        add_selector = '.wrapper-translations-settings > a'
        self.q(css=add_selector).first.click()

        # Get count of translations already added
        translations_items = '.wrapper-translations-settings .list-settings-item'
        translations_count = len(self.q(css=translations_items).results)

        # Select `language_code` for correct drop down
        language_selector = translations_items + ' select option[value="{}"]'.format(language_code)
        self.q(css=language_selector).nth(translations_count - 1).click()

        self.upload_asset(transcript_name, translations_count - 1)

    def translations(self):
        """
        Extract translations

        Returns:
            list: list translation language codes

        """
        translations_selector = '.metadata-video-translations .remove-setting'
        return self.q(css=translations_selector).attrs('data-lang')
