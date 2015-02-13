import StringIO
import json
import os
import requests
import tempfile
import zipfile
from mock import patch, MagicMock, mock_open

from django.conf import settings
from django.core.management import call_command

from kalite.testing import KALiteTestCase
from kalite.contentload.management.commands import unpack_assessment_zip as mod


class UnpackAssessmentZipCommandTests(KALiteTestCase):

    def setUp(self):
        _, self.zipfile_path = tempfile.mkstemp()
        with open(self.zipfile_path, "w") as f:
            zf = zipfile.ZipFile(f, "w")
            for dirpath, _, filenames in os.walk(os.path.join(os.path.dirname(__file__), "fixtures")):
                # this toplevel for loop should only do one loop, but
                # it's in a for loop nonetheless since it's more idiomatic
                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    zf.write(full_path, filename)
            zf.close()

    def tearDown(self):
        os.unlink(self.zipfile_path)

    @patch.object(requests, "get", autospec=True)
    def test_command_with_url(self, get_method):
        url = "http://fakeurl.com/test.zip"

        with open(self.zipfile_path) as f:
            zip_raw_data = f.read()
            zf = zipfile.ZipFile(StringIO.StringIO(zip_raw_data))
            get_method.return_value = MagicMock(content=zip_raw_data)

            call_command("unpack_assessment_zip", url)

            get_method.assert_called_once_with(url)

            # verify that the assessment json just extracted is written to the khan data dir
            self.assertEqual(zf.open("assessmentitems.json").read(),
                             open(mod.ASSESSMENT_ITEMS_PATH).read())

            # TODO(aron): write test for verifying that assessment items are combined
            # once the splitting code on the generate_assessment_zips side is written

            # verify that the other items are written to the content directory
            for filename in zf.namelist():
                # already verified above; no need to double-dip
                if "assessmentitems.json" in filename:
                    continue
                else:
                    filename_path = os.path.join(mod.KHAN_CONTENT_PATH, filename)
                    self.assertTrue(os.path.exists(filename_path), "%s wasn't extracted to %s" % (filename, mod.KHAN_CONTENT_PATH))

    def test_command_with_local_path(self):
        pass


class UnpackAssessmentZipUtilityFunctionTests(KALiteTestCase):

    def setUp(self):
        _, self.zipfile_path = tempfile.mkstemp()
        with open(self.zipfile_path, "w") as f:
            zf = zipfile.ZipFile(f, "w")
            for dirpath, _, filenames in os.walk(os.path.join(os.path.dirname(__file__), "fixtures")):
                # this toplevel for loop should only do one loop, but
                # it's in a for loop nonetheless since it's more idiomatic
                for filename in filenames:
                    full_path = os.path.join(dirpath, filename)
                    zf.write(full_path, filename)
            zf.close()

    def tearDown(self):
        os.unlink(self.zipfile_path)

    def test_unpack_zipfile_to_khan_content_extracts_to_content_dir(self):
        zipfile_instance = MagicMock()

        extract_dir = settings.ASSESSMENT_ITEMS_RESOURCES_DIR

        mod.unpack_zipfile_to_khan_content(zipfile_instance)

        zipfile_instance.extractall.assert_called_once_with(extract_dir)

    def test_is_valid_url_returns_false_for_invalid_urls(self):
        invalid_urls = [
            "/something.path",
            "/path/to/somewhere"
            ]

        for url in invalid_urls:
            self.assertFalse(mod.is_valid_url(url))

    def test_extract_assessment_items_to_data_dir(self):
        with open(mod.ASSESSMENT_ITEMS_PATH) as f:
            old_assessment_items = json.load(f)

        with open(self.zipfile_path) as f:
            zf = zipfile.ZipFile(f)
            mod.extract_assessment_items_to_data_dir(zf)
            zf.close()

        # test that it combines the new assessment items with the previous one
        with open(mod.ASSESSMENT_ITEMS_PATH) as f:
            items = json.load(f)

            for old_item in old_assessment_items:
                self.assertTrue(old_item in items)

            # test that there are new items in the assessment items too

        # test that it extract the assessment items version file
        self.assertTrue(os.path.exists(mod.ASSESSMENT_ITEMS_VERSION_PATH), "assessmentitems.json.version wasn't extracted!")

    def test_is_valid_url_returns_true_for_valid_urls(self):
        valid_urls = [
            "http://stackoverflow.com/questions/25259134/how-can-i-check-whether-a-url-is-valid-using-urlparse",
            "http://en.wikipedia.org/wiki/Internationalized_resource_identifier"
        ]

        for url in valid_urls:
            self.assertTrue(mod.is_valid_url(url))
