# Purchase-to-Pay process model

## Ideal path

1. Purchase Request Created
2. Manager Approval
3. Procurement Review
4. Purchase Order Created
5. Purchase Order Sent
6. Supplier Confirmation
7. Goods Received
8. Invoice Received
9. Invoice Duplicate Check
10. Invoice Matched
11. Payment Authorized
12. Payment Executed
13. Case Closed

## Designed controls

| Control point | Purpose | Automation position |
|---|---|---|
| Manager approval | Budget and authority | Low-risk routing may automate assignment, not accountability |
| Duplicate check | Prevent duplicate payment | Automated detection, human exception review |
| Three-way match | PO/goods/invoice consistency | Rules can flag; AP resolves |
| Payment authorization | Segregation of duties | Human authorization retained |
| Case closure | Complete audit trail | Automated after payment confirmation |

## Exception taxonomy

- **Missing:** an expected activity is absent.
- **Unexpected:** an activity is outside the target path.
- **Repeated:** an activity occurs more often than designed.
- **Reordered:** represented through edit distance and trace inspection.

The BPMN source is `bpmn/purchase-to-pay-reference.bpmn`. Activity names in the
Python ideal-path contract are kept literal so conformance results remain
auditable.
