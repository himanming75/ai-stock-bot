# Final Validation Qualification

Adds a final decision layer on top of existing Validation History and 10-Day Report.

Decision rules:

PASS:
- validation days target met;
- resolved outcomes target met;
- AI model health is GREEN;
- research comparison is ready;
- Paper qualification passed;
- no hard safety/data-integrity failure.

CONTINUE:
- no hard failure;
- one or more readiness gates are still incomplete.

FAIL:
Reserved only for actual hard safety/data-integrity violations such as:
- synthetic validation days;
- interpolated history;
- fabricated future outcomes;
- Validation Lab submitting Paper/Live orders;
- automatic model/strategy/threshold promotion enabled.

PASS never promotes automatically. It only allows manual promotion review.

The "Write Final Qualification Report" action writes the current factual decision
to runtime/validation_final_qualification as JSON.
