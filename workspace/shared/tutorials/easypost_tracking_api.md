# EasyPost Tracking API — Agent Tutorial (READ FIRST before any EasyPost diagnosis)

## MANDATORY SOURCE OF TRUTH
Whenever EasyPost is involved, the agent MUST consult the OFFICIAL EasyPost API docs and derive
field names / status values from them — never from intuition, memory, or a prior buggy assumption:
  ->  https://docs.easypost.com/docs/tracking
Key doc pages:
  - Tracker object:   https://docs.easypost.com/docs/tracking/tracker
  - Tracking statuses: https://docs.easypost.com/docs/tracking#trackingdetail-status
  - Shipment object:  https://docs.easypost.com/docs/shipments/shipment-object
If anything below disagrees with the live docs, the DOCS win — update this file from them.

## AUTH (read-only in this integration)
- Base: `https://api.easypost.com/v2`
- Auth: HTTP Basic — the API key is the USERNAME, password is EMPTY.
  Header: `Authorization: Basic base64("<EASYPOST_API_KEY>:")` (note the trailing colon).
- Key source: `EASYPOST_API_KEY` in `workspace/shared/oth/.cred`. NEVER print or log the key value.
- Test vs production: EasyPost has separate test (`EZTK...`) and production (`EZAK...`) keys.
  Trackers created with a test key only ever return simulated events — confirm which key is in use
  before concluding a shipment "isn't moving".

## AUTHORITATIVE TRACKER STATUS ENUM (from the docs — `tracker.status`)
["unknown", "pre_transit", "in_transit", "out_for_delivery", "delivered",
 "available_for_pickup", "return_to_sender", "failure", "cancelled", "error"]
Unlike Veeqo (whose order status STOPS at "shipped"), EasyPost DOES model the full post-shipping
lifecycle — `out_for_delivery` and `delivered` are real tracker statuses here. That is exactly why
EasyPost complements Veeqo: use Veeqo for order/fulfillment state, EasyPost for live carrier progress.

## Endpoints (GET only in this integration — whitelist: trackers, shipments, addresses, parcels, users)
- GET /v2/trackers                 -> list trackers (paginated; supports `tracking_code`, `carrier` filters)
- GET /v2/trackers/{tracker_id}    -> one tracker + `tracking_details[]` (the carrier scan history)
- GET /v2/shipments                -> list shipments
- GET /v2/shipments/{shipment_id}  -> one shipment (+ its `tracker`)
- GET /v2/users                    -> the authenticated account (sanity/whoami check)
Any non-GET method or any other endpoint raises PermissionError before a request is built — this
integration cannot create labels, buy postage, or mutate anything.

## TRUE signals for live delivery state (ANY present => treat accordingly)
- `tracker.status`                          -> the summarized current state (enum above) <-- primary
- `tracker.tracking_details[]`              -> ordered scan events, each with `.status`, `.message`,
                                               `.datetime`, `.tracking_location`               <-- detail
- `tracker.est_delivery_date`               -> carrier ETA (may be null early)
- `tracker.carrier` + `tracker.tracking_code` -> which carrier + the tracking number
- `tracker.public_url`                       -> human-readable tracking page

## Fields that are OFTEN NULL and MUST NOT be used ALONE to decide state
- `tracker.est_delivery_date`   (null until the carrier commits an ETA)
- `tracker.signed_by`           (only set on delivery for signature-required services)
- `tracking_details` may be EMPTY right after creation (`pre_transit` / `unknown`) — do NOT conclude
  "lost" from an empty history; poll again or check the carrier directly.

## GOLDEN RULE (why this file exists)
Never guess EasyPost field names or invent statuses. Read the live tracker JSON fully, take state
from `tracker.status` corroborated by the latest `tracking_details[]` event, and if a field is null
do NOT conclude — check the alternate signals above. When EasyPost disagrees with Veeqo, EasyPost is
the authority for POST-SHIPPING carrier progress (out_for_delivery / delivered); Veeqo is the
authority for pre-shipping ORDER/fulfillment state.
