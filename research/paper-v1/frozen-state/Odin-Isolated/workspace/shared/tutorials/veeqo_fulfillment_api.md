# Veeqo Fulfillment API — Agent Tutorial (READ FIRST before any Veeqo diagnosis)

## MANDATORY SOURCE OF TRUTH
Whenever Veeqo is involved, the agent MUST consult the OFFICIAL Veeqo API catalog and derive
field names / status values from it — never from intuition, memory, or a prior buggy assumption:
  ->  https://developers.veeqo.com/api/
Key catalog pages:
  - Order statuses:   https://developers.veeqo.com/resources/order_statuses
  - Order detail:     https://developers.veeqo.com/api/operations/view-an-order-detail/
  - Tracking events:  https://developers.veeqo.com/api/operations/view-tracking-events/
If anything below disagrees with the live catalog, the CATALOG wins — update this file from it.

## GOLDEN RULE (why this file exists)
Never guess Veeqo field names from intuition/logic. A real incident: agents + production code decided "shipped"
from `shipped_at` / status enums — Veeqo leaves those NULL for the manual "mark as shipped" flow, so a genuinely
SHIPPED order looked un-shipped and froze at PAID. ALWAYS determine state from the TRUE signals below, read the
live JSON fully, and if a field is null do NOT conclude — check the alternate signals.

## AUTHORITATIVE ORDER STATUS ENUM (from the catalog — order-level `order.status`)
["awaiting_payment", "awaiting_stock", "awaiting_fulfillment", "shipped", "on_hold", "cancelled", "refunded"]
CRITICAL CONSEQUENCE: the order-level status STOPS AT "shipped". Veeqo has NO order status for
"out_for_delivery" or "delivered". Those post-shipping states DO NOT exist on order.status — do not look for them there.
Also: "Payment Required" in the Veeqo portal == order.status == "awaiting_payment". For orders paid on OUR
website and merely pushed to Veeqo for fulfilment, Veeqo's ledger is never told "paid", so it sits at
awaiting_payment / "Payment Required" FOREVER even after the item ships. That label is cosmetic; it is NOT money owed
and NOT our real order state.

## Endpoints (header: x-api-key: <veeqoApiKey from RUNTIME_OPERATIONAL_SETTINGS>)
- GET https://api.veeqo.com/orders/{veeqo_order_id}  -> order + allocations[] (+ allocation.shipment, tracking_number)
- GET https://api.veeqo.com/shipping/tracking_events/{shipment_id}  -> post-shipping carrier progress (SEE BELOW)
- Shipments may also be listed per order; a 404 there just means no separate shipment record (use the allocation).

## SHIPPED / DISPATCHED — TRUE signals (ANY present => treat as shipped/dispatched)
- allocations[].dispatch_date                     (ISO timestamp; set when dispatched)  <-- primary
- allocations[].shipment.shipped_by_id            (user id who marked it shipped)       <-- primary
- allocations[].shipment.tracking_number.tracking_number (+ .status == 'created')       (label made)
- allocations[].shipment.id / package number      (a shipment/package exists)

## Fields that are OFTEN NULL and MUST NOT be used ALONE to decide shipped
- order.status  (can remain 'awaiting_payment' even after the item ships)
- allocations[].status, allocations[].shipment.status, shipped_at   (null in the manual-ship flow)

## POST-SHIPPING states (out_for_delivery / delivered) — the ONLY correct source
These are NOT order statuses. They come from carrier tracking, exposed by:
  GET https://api.veeqo.com/shipping/tracking_events/{shipment_id}
  -> array of events; each event has: timestamp, description, detail, location, status
  -> event.status enum: ["awaiting_collection", "in_transit", "out_for_delivery", "delivered"]
IMPORTANT CONDITION (from the catalog): "Tracking events will be available if the label was PURCHASED in Veeqo."
  * Label bought inside Veeqo  -> tracking_events returns the real progression -> use event.status.
  * Label NOT bought in Veeqo (manual mark-as-shipped, Amazon FBA, externally-entered tracking number)
    -> tracking_events is EMPTY or 404. Do NOT conclude "no delivery info". FALL BACK to the CARRIER
       (e.g. USPS) using the tracking_number to obtain out_for_delivery / delivered.
Never assume the endpoint is empty without calling it live for the specific shipment_id (golden rule).

## RESPONSIBILITY MAP (who owns each stage)
- Veeqo owns:   the SHIPPED/dispatched fact (true signals) + the tracking number + (if label bought in Veeqo) tracking_events.
- Carrier owns: physical transit truth -> out_for_delivery, delivered (via Veeqo tracking_events OR the carrier API).
- OUR website owns: DEFINING the lifecycle stages and mapping each from the correct signal, persisting them, and
  showing the SAME status on the my-order card, admin-orders page and customer card. Stages after delivered
  (e.g. "reviewed") are purely our own app lifecycle. "Veeqo doesn't define it" is NOT a reason to leave a gap.

## Correct mapping to OUR order status
ORDERED -> SHIPPED once a dispatched shipment exists (dispatch_date OR shipped_by_id OR tracking label).
Persist: veeqoShipmentId (allocation.shipment.id), tracking_number, carrier, and set our shipped_at = dispatch_date.
SHIPPED -> OUT_FOR_DELIVERY -> DELIVERED driven by tracking_events[].status (or carrier fallback), newest event wins.
DELIVERED -> (app-owned) REVIEWED / post-delivery states handled entirely by our app.

## If the API response shape changes in the future
Update THIS tutorial from the LIVE response + the catalog first; agents must re-read it. Do NOT hardcode or intuit field names.

## PERSISTENCE SHAPE RULE (read before writing ANY Veeqo field to the DB)
Veeqo returns several fields as OBJECTS, not scalars. Before persisting ANY Veeqo-derived value to a
Prisma column, the value's shape MUST match the column's scalar type — otherwise Prisma throws at runtime
and the surrounding syncOrder() aborts BEFORE it commits the order status (symptom: a genuinely shipped
order stays frozen at its previous status).
Known OBJECT-shaped Veeqo fields (extract the scalar before persisting):
- tracking_number  -> the string is at  tracking_number.tracking_number  (NOT the object itself)
- carrier          -> use carrier.name / carrier.slug
- allocation, shipment -> containers; pull the scalar you need (id, dispatch_date, shipped_by_id)
AUDIT DUTY: when diagnosing, trace the ENTIRE shipped-order execution path (syncOrder and EVERY helper it
calls that writes to the DB, including simulator bookkeeping like recordRealStatus). For each external field
written to a column, cross-check its shape against prisma/schema.prisma. Flag every String? column that
receives an object. Never assume a Veeqo field is a scalar just because its name reads like one.
