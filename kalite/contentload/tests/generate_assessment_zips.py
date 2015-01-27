import json
import os
import requests
import zipfile
from mock import patch, MagicMock

from django.core.management import call_command

from kalite.testing import KALiteTestCase
from kalite.contentload.management.commands import generate_assessment_zips as mod

TEST_FIXTURES_DIR = os.path.join(os.path.dirname(__file__),
                                        "fixtures")


class GenerateAssessmentItemsCommandTests(KALiteTestCase):

    @patch.object(requests, 'get')
    def test_command(self, get_method):
        with open(os.path.join(TEST_FIXTURES_DIR, "assessment_items_sample.json")) as f:
            assessment_items_content = f.read()

        get_method.return_value = MagicMock(content=assessment_items_content)

        call_command("generate_assessment_zips")

        self.assertEqual(get_method.call_count, 2, "requests.get not called the correct # of times!")

        with zipfile.ZipFile(mod.ZIP_FILE_PATH) as zf:
            self.assertIn("assessment_items.json", zf.namelist())  # make sure assessment items is written

            for filename in zf.namelist():
                if ".gif" in filename:
                    continue
                elif ".jpg" in filename:
                    continue
                elif ".png" in filename:
                    continue
                elif "assessment_items.json" in filename:
                    continue
                else:
                    self.assertTrue(False, "Invalid file %s got in the assessment zip!" % filename)


class UtilityFunctionTests(KALiteTestCase):

    def setUp(self):

        with open(os.path.join(TEST_FIXTURES_DIR, "assessment_items_sample.json")) as f:
            self.assessment_sample = json.load(f)
        self.imgurl = "https://ka-perseus-graphie.s3.amazonaws.com/8ea5af1fa5a5e8b8e727c3211083111897d23f5d.png"

    @patch.object(zipfile, "ZipFile", autospec=True)
    def test_write_assessment_json_to_zip(self, zipfile_class):
        with zipfile.ZipFile(mod.ZIP_FILE_PATH) as zf:
            mod.write_assessment_to_zip(zf, self.assessment_sample)

            self.assertEqual(zf.writestr.call_args[0][0]  # call_args[0] are the positional arguments
                             , "assessment_items.json")

    def test_gets_images_urls_inside_item_data(self):

        result = list(mod.all_image_urls(self.assessment_sample))
        self.assertIn(
            self.imgurl,
            result,
            "%s not found!" % self.imgurl
        )

    def test_localhosted_image_urls_replaces_with_local_urls(self):
        new_assessment_items = mod.localhosted_image_urls(self.assessment_sample)

        all_images = list(mod.all_image_urls(new_assessment_items))
        self.assertNotIn(self.imgurl, all_images)

    @patch.object(requests, "get")
    def test_download_url_to_zip_writes_to_zipfile(self, get_method):
        expected_return_value = "none"

        zipobj = MagicMock()

        get_method.return_value = MagicMock(content=expected_return_value)

        mod.download_url_to_zip(zipobj, "http://test.com")

        zipobj.writestr.assert_called_once_with("test.com", expected_return_value)

    @patch.object(zipfile, "ZipFile", autospec=True)
    @patch.object(mod, "download_url_to_zip")
    def test_download_url_downloads_all_urls(self, download_method, zipfile_class):
        download_method.return_value = 1

        urls = ["http://test1.com", "http://test2.com"]
        with zipfile.ZipFile(mod.ZIP_FILE_PATH) as zf:
            mod.download_urls(zf, urls)

        self.assertEqual(download_method.call_count, len(urls))
