# FSRS scheduling, version 5

Uses py-fsrs 6.3.2 (FSRS-6), default parameters, target retention 0.90,
maximum 180 days, deterministic intervals. This is not a fitted personal model yet.
Each item has a persistent FSRS card (stability, difficulty, last review) in
memory_states. All timestamps sent to FSRS use UTC.

Feedback mapping: forgot, revealed answers, incorrect spelling before final
submission -> Again; hard without these failures -> Hard; independent clear -> Good.
The hidden familiar shortcut does not imply Easy or manufacture successful reviews.

Every completed answer updates the memory card. Same-day consolidation retains
2/4/8 other-question gaps. Three independent successes graduate to next-day
verification. A delayed independent success uses the FSRS interval. Non-independent
answers return to consolidation. The existing evidence safeguard caps intervals
at seven days until delayed stability criteria are satisfied. Therefore this is
FSRS plus explicit teaching safeguards, not an unmodified FSRS schedule.

Normal answers incrementally update one card. Feedback corrections replay only
that item's history with the latest corrected feedback; duplicate submission
cannot update it twice. Migration replays only legacy-version items; raw history
is preserved. Daily workload limits remain independent from due dates.

History display groups by Asia/Shanghai calendar day and selects the latest
completed attempt per day, showing the latest three learning days. D numbers
are elapsed calendar days from first practice, not review counts. Full attempts
remain in exports. memory_states is included in export and test reset.

No optimizer is currently enabled: per-item adaptation works immediately,
but fitting user-level parameters requires sufficient delayed observations and
out-of-sample validation before replacing defaults.


## Runtime audit (2026-10-31)
Regression coverage includes mixed UTC/+08 due instants, pending multi-answer
incremental updates, duplicate submission, corrected feedback, exact FSRS library
state comparison across 35 deterministic randomized events, long-term due-driven
practice, reconnection, 20-day overdue return, lapse/relearning, test skip exclusion,
and saved answer schedule snapshots. Test databases are isolated.

Version 5 compares timestamps as instants (SQLite julianday/Python aware datetime),
processes every answer after the checkpoint instead of the last answer only,
and excludes test skips from FSRS training. Startup replays legacy queues once.
Default model parameters are still not personalized/fitted. Per-item D/S state
adapts; personal curve averages those states. Curve observations do not optimize
weights. No benchmark claim that this hybrid schedule improves learning outcomes.
