import unittest
import numpy as np
import cv2

from core.service.template_matcher import TemplateMatcher


class TestTemplateMatcher(unittest.TestCase):
    def test_match(self):
        img = cv2.imread("../data/test/template_matching/template_matching_test.png")
        template = cv2.imread("../data/test/template_matching/template.png")
        matcher = TemplateMatcher()
        res = matcher.find_match(img, template)
        print(res)
        self.assertEqual(res, (0.0, (0, 0)))

    def test_match_all(self):
        img = cv2.imread("../data/test/template_matching/template_matching_test.png")
        template = cv2.imread("../data/test/template_matching/template.png")
        matcher = TemplateMatcher()
        res = matcher.find_match_all(img, template)
        print(res)
        self.assertEqual(res, (0.0, (0, 0)))

    def test_match_all_by_roi(self):
        img = cv2.imread("../data/test/template_matching/template_matching_test.png")
        template = cv2.imread("../data/test/template_matching/template.png")
        roi = [0, 0, 100, 100]

        matcher = TemplateMatcher()
        res = matcher.find_match_all(img, template, roi=roi)
        print(res)
        self.assertEqual(res, (0.0, (0, 0)))
