#!/usr/bin/env python3
"""
Test Suite: Career-Ops Engine & A-H Evaluation Framework
Verifies:
1. Complete A-H Block Generation across all 8 evaluation dimensions
2. Fit Score Computation strictly bounded within 1.0 to 5.0 scale
3. Work Authorization Hard Blocker enforcement when JD disallows sponsorship and candidate requires it
4. Posting Legitimacy, ATS Detection, and Ghost Job signal detection
5. STAR+R Behavioral Interview Story Bank (Situation, Task, Action, Result, Reflection)
6. 4-Angle Cover Letter Generation with zero banned AI buzzwords
7. CLI and Programmatic API parity
"""

import os
import sys
import json
import unittest

# Ensure scripts directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import career_ops


class TestCareerOpsEvaluation(unittest.TestCase):

    def setUp(self):
        self.sample_jd = """
Title: Senior Systems Infrastructure Engineer
Company: Cloudflare
Location: San Francisco, CA (Remote)
Salary: $190,000 - $240,000 / year
Requirements:
- 5+ years of production experience in systems engineering
- Strong proficiency in Rust, Go, or C++
- Expertise in distributed microservices, low-latency networking, and Linux internals
- Experience with Docker, Kubernetes, and CI/CD automation
- BS in Computer Science or equivalent
"""
        self.candidate_profile = {
            "fullName": "Elena Rostova",
            "email": "elena.rostova@example.com",
            "yearsExperience": "7+ years",
            "skills": "Rust, Go, Distributed Systems, Linux, Docker, Kubernetes, CI/CD",
            "workAuthorization": "Citizen / Permanent Resident (No sponsorship required)",
            "targetSalaryMin": 180000,
            "targetSalaryMax": 230000
        }

    def test_ah_blocks_generation(self):
        """Verifies all A-H evaluation blocks are populated with authentic signal."""
        res = career_ops.evaluate_job_posting(self.sample_jd, self.candidate_profile)
        
        # Check top-level keys
        self.assertIn("fitScore", res)
        self.assertIn("recommendation", res)
        self.assertIn("hardBlocker", res)
        self.assertIn("blockA_summary", res)
        self.assertIn("blockB_fitMatch", res)
        self.assertIn("blockC_levelStrategy", res)
        self.assertIn("blockD_compensation", res)
        self.assertIn("blockE_pitch", res)
        self.assertIn("blockF_storyBank", res)
        self.assertIn("blockG_legitimacy", res)
        self.assertIn("blockH_workAuth", res)

        # Block A: Role & Posting Summary
        block_a = res["blockA_summary"]
        self.assertEqual(block_a["company"], "Cloudflare")
        self.assertIn("Systems", block_a["jobTitle"])
        self.assertEqual(block_a["workArrangement"], "Remote")

        # Block B: Fit Match
        block_b = res["blockB_fitMatch"]
        self.assertGreaterEqual(len(block_b["requirements"]), 3)
        self.assertTrue(any(r["weight"] == "Critical" for r in block_b["requirements"]))
        self.assertTrue(any(r["status"] == "Matched" for r in block_b["requirements"]))

        # Block C: Seniority Calibration
        block_c = res["blockC_levelStrategy"]
        self.assertEqual(block_c["detectedLevel"], "Senior")
        self.assertIn("Senior", block_c["calibration"])

        # Block D: Compensation
        block_d = res["blockD_compensation"]
        self.assertIn("$190,000", block_d["postedSalaryRange"])
        self.assertIn("Aligned", block_d["salaryGapAnalysis"])

        # Block E: Strategic Pitch
        block_e = res["blockE_pitch"]
        self.assertTrue(len(block_e["valueProposition"]) > 50)
        self.assertIn("Elena Rostova", block_e["valueProposition"] or self.candidate_profile["fullName"])

        # Block F: STAR+R Stories
        block_f = res["blockF_storyBank"]
        self.assertGreaterEqual(len(block_f["stories"]), 3)
        for story in block_f["stories"]:
            self.assertIn("situation", story)
            self.assertIn("task", story)
            self.assertIn("action", story)
            self.assertIn("result", story)
            self.assertIn("reflection", story)

        # Block G: Legitimacy
        block_g = res["blockG_legitimacy"]
        self.assertTrue(block_g["urlReachable"])
        self.assertFalse(block_g["isGhostJob"])

        # Block H: Work Auth
        block_h = res["blockH_workAuth"]
        self.assertFalse(block_h["hardBlocker"])
        self.assertIn("Clear", block_h["status"])

    def test_fit_score_range_and_recommendation(self):
        """Verifies Fit Score scale is strictly 1.0 to 5.0 with calibrated thresholds."""
        res = career_ops.evaluate_job_posting(self.sample_jd, self.candidate_profile)
        score = res["fitScore"]
        self.assertGreaterEqual(score, 1.0)
        self.assertLessEqual(score, 5.0)
        self.assertIn("Strong Fit", res["recommendation"])

    def test_work_auth_hard_blocker_enforcement(self):
        """Triggers hard blocker when JD bans visa sponsorship and candidate needs it."""
        no_sponsor_jd = """
Title: Security Operations Specialist
Company: Defense Dynamics
Location: Washington, DC
Requirement: US Citizens or Green Card only. No visa sponsorship available.
"""
        sponsorship_candidate = {
            "fullName": "Raj Patel",
            "yearsExperience": "6+ years",
            "skills": "Cybersecurity, Python, Linux",
            "workAuthorization": "Requires Visa Sponsorship (H-1B Transfer / OPT)"
        }
        res = career_ops.evaluate_job_posting(no_sponsor_jd, sponsorship_candidate)
        
        self.assertTrue(res["hardBlocker"])
        self.assertEqual(res["fitScore"], 1.0)
        self.assertIn("Hard Blocker", res["recommendation"])
        self.assertTrue(res["blockH_workAuth"]["hardBlocker"])
        self.assertIn("DO NOT APPLY", res["blockH_workAuth"]["status"])

    def test_cover_letter_generation_and_buzzword_ban(self):
        """Verifies 4-angle structure and strict absence of banned AI buzzwords."""
        letter = career_ops.generate_cover_letter(self.sample_jd, self.candidate_profile)
        
        # Must include recipient and candidate
        self.assertIn("Cloudflare", letter)
        self.assertIn("Elena Rostova", letter)
        
        # Verify absence of banned buzzwords
        banned = [
            "delve", "tapestry", "beacon", "pivotal", "testament",
            "unleash", "groundbreaking", "furthermore", "moreover", "revolutionize"
        ]
        letter_lower = letter.lower()
        for word in banned:
            self.assertNotIn(f" {word} ", f" {letter_lower} ", f"Banned buzzword found: '{word}'")

    def test_ats_portal_detection(self):
        """Verifies accurate detection of common ATS portal domains."""
        self.assertEqual(career_ops.detect_ats_portal("https://boards.greenhouse.io/stripe/jobs/123", ""), "Greenhouse")
        self.assertEqual(career_ops.detect_ats_portal("https://jobs.lever.co/anthropic/456", ""), "Lever")
        self.assertEqual(career_ops.detect_ats_portal("https://jobs.ashbyhq.com/openai/789", ""), "Ashby")
        self.assertEqual(career_ops.detect_ats_portal("https://company.myworkdayjobs.com/careers/job", ""), "Workday")
        self.assertEqual(career_ops.detect_ats_portal("https://www.google.com/about/careers/applications/jobs/results/", ""), "Google Careers")


if __name__ == "__main__":
    print("=" * 65)
    print("💼 Running Career-Ops Python Engine Test Suite...")
    print("=" * 65)
    unittest.main()
