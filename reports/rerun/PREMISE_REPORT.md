# Premise Report -- HALTED (unexpected stuck front)

Generated (UTC): 2026-09-27T19:21:25.215048+00:00

**The permanent tripwire (`pipeline.assert_front_not_past_expiry`) fired on a violation that does NOT match a user-pre-authorized transient graze** (known set: [('NG', '192047__2010-06-28'), ('NG', '192053__2010-12-28')]). This is either a genuinely new stuck-front instance, a different symbol's own already-documented-but-not-yet-authorized graze (e.g. HG's, characterized under the pre-A1 rule and not yet confirmed to recur under A1), or a known graze turning out to be permanent -- either way, per the F11 amendment record, this requires its own check before any further computation. No premise test was computed.

## Detail

- Symbol: CL
- CL: [(Timestamp('2010-06-23 00:00:00'), '182055__2010-06-22'), (Timestamp('2010-06-24 00:00:00'), '182055__2010-06-22'), (Timestamp('2010-06-25 00:00:00'), '182055__2010-06-22'), (Timestamp('2010-06-28 00:00:00'), '182055__2010-06-22'), (Timestamp('2010-06-29 00:00:00'), '182055__2010-06-22')]... (permanent=False)