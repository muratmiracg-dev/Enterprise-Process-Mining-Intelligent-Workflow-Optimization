# 90-second interview talk track

“I wanted to show that I can go beyond dashboarding and solve an operating
process problem end to end. I modeled Purchase-to-Pay because it combines
workflow, controls, service levels, and capacity decisions.

I first translated the process into an event-data contract and a 13-step BPMN
target. Then I generated 12,000 deterministic synthetic cases with more than
166,000 events. Using Python and PM4Py, I discovered variants and transitions,
measured conformance, and linked bottlenecks and rework to case outcomes.

The baseline showed 62% SLA adherence and 22% rework. I built an explainable
logistic model using only features available at Purchase Order creation, and
validated it on the latest 20% of cases; ROC AUC was 0.822.

Finally, I converted analysis into a decision. A replicated queue simulation
compared approval automation, AP capacity, and a combined scenario. Under the
documented synthetic assumptions, the combined option reduced mean cycle time
by 19.4% and improved SLA by 13.6 points.

I packaged the result as a governed product: FastAPI, PostgreSQL, Power BI,
Docker, observability, CI, 58 tests, bilingual reporting, and explicit
human-in-the-loop limits. The key lesson is that analytics should make the
decision and its uncertainty auditable—not just produce a chart.”
