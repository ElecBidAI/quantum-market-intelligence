-- Splits council_narratives.narrative into narrative_en/narrative_es.
--
-- services/ai-council/src/ai_council/narrator.py now renders both
-- languages from the exact same pipeline run (regime/candidate/decision/
-- opinions/thesis computed once, generate_narrative() called twice) --
-- see that module's docstring for what's translated (prose) vs. not
-- (reason/finding "detail" strings, and the stored regime/decision/
-- final_stance values themselves).
--
-- Safe rename: no production data exists yet, only local demo/test rows.

ALTER TABLE council_narratives RENAME COLUMN narrative TO narrative_en;
ALTER TABLE council_narratives ADD COLUMN narrative_es TEXT NOT NULL DEFAULT '';
ALTER TABLE council_narratives ALTER COLUMN narrative_es DROP DEFAULT;
