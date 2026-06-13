# QA Questions

Date: 2026-06-13
Data: synthetic seed documents in `data/raw/` (DOC-001 safety_loto, DOC-002 maintenance_press, DOC-003 quality_inspection)

These questions are designed to probe specific system behaviors against the seed data. Run them via `just ui` or the `/answer` endpoint directly.

## Cross-domain traversal

These should pull citations from two or three documents. If citations come back from only the entry domain, the `REQUIRES_SAFETY` and `VALIDATES_WITH` edge traversal is not working.

1. How do I safely replace the bearing on press 4?
   Expected domains: Maintenance (bearing steps) + Safety (LOTO) + QC (housing tolerance, post-repair inspection)

2. What do I do after finishing a bearing replacement before putting the press back in service?
   Expected domains: QC (post-repair checklist) + Maintenance (restoration step 8) + Safety (LOTO restoration)

3. Can I reinstall the drive-end guard before removing my lockout?
   Expected domains: Maintenance (steps 7 and 8) + Safety (restoration procedure order)

## Single-domain precision

These should route cleanly to one domain and cite a specific section, not just the document title.

4. What are the bore diameter tolerances for the bearing housing?
   Entry domain: QualityControl. Expected citation: QC / Bearing Housing Tolerance, H7 fit spec (75.000 mm +0.025 / -0.000).

5. What torque should I use for the bearing housing bolts?
   Entry domain: Maintenance. Expected citation: Maintenance / Torque Specifications, 65 Nm with Loctite 243.

6. What grease should I use for the X200 lubrication points?
   Entry domain: Maintenance. Expected citation: Maintenance / Lubrication Points, NLGI Grade 2.

## Abstain triggers

The system should return an abstain notice, not a fabricated answer.

7. How do I replace the crankshaft on the X200?
   Not covered in any seed document. Expect abstain.

8. What is the rated press force of the X200?
   The 120% overload threshold is mentioned in DOC-003 but the rated force itself is not defined. Borderline case. System should abstain or cite only the overload mention without inventing a value.

9. What is the price of BTC today?
   Completely out of domain. Expect abstain. Known to return "evidence found but insufficient" rather than "below threshold" because noise chunks clear 0.70 similarity.

## Citation quality

These probe whether citations are specific (section level) and whether origin is disclosed correctly. All seed documents are `origin: official` so every citation should show "Official Standard."

10. What happens if a bearing housing measurement is out of tolerance?
    Expected: QC / Bearing Housing Tolerance cited with explicit consequence (housing must be replaced or reconditioned). Origin: Official Standard.

11. When should I replace the drive bearing?
    Expected: Maintenance / Bearing Replacement Procedure cited with all three trigger conditions (5 mm/s RMS vibration, 80 C temperature, visible wear), not just the document title.
