# BPMN reference model

`purchase-to-pay-reference.bpmn` is the governed target-state Purchase-to-Pay
model used by the conformance engine. It is authored against BPMN 2.0.2 and can
be opened in BPMN-compatible modeling tools such as Camunda Modeler.

The executable analytics contract is maintained in
`src/process_optimizer/config.py`. CI verifies that the 13 ideal-path activity
names remain aligned with this model.

The model is intentionally human-in-the-loop: duplicate checks may be automated,
while approval, matching exceptions, and payment authorization remain controlled
business decisions.
