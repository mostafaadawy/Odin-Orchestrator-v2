# HANDOFF — Veeqo / Fulfillment Order-Lifecycle Fix (Redberry Organics)

Read fully before acting. Facts below are verified against the LIVE production system + Veeqo's official API catalog — do not re-derive them.

## 0. USER + STYLE
- Owner: Mostafa. HAS A VISUAL IMPAIRMENT → answers must be SHORT, precise, literal. No guessing; if unknown, verify.
- Standards: never say "done" before strong testing; work until yes; NO fake checkmarks; no gaps/caveats — solve correctly; respect middleware/audit/DB/scopes; smarter not script-like.
- Read-only diagnosis runs via the Odin bridge using the DELTA-SCOPED Veeqo key (not the default env key). No DB rebase. Deploy uses ODIN_MIG_OVERRIDE=none.

## 1. TASK
Veeqo status inconsistent between portal and website (My-Orders card, admin-orders page, customer card). "Shipped" already fixed. NOW make FUTURE states work: out_for_delivery, delivered, and post-delivery (reviewed) — without breaking the switchable fulfilment-provider interface (3PL <-> Veeqo).
Reference order #P-1959471694: Ahmed Elhenawy, ROR-1RS-1500, $22.95, shipped Jul 21 2026, USPS tracking 9361289736066469804724, Veeqo shipment 1400784804, ships from Amazon FBA (manual mark-as-shipped).

## 2. VERIFIED FACTS
CATALOG (always use https://developers.veeqo.com/api/):
- order.status enum = awaiting_payment, awaiting_stock, awaiting_fulfillment, shipped, on_hold, cancelled, refunded. STOPS at shipped — no out_for_delivery/delivered at order level.
- "Payment Required" = order.status awaiting_payment = cosmetic (paid on our site via Stripe, only pushed to Veeqo). Not money owed, not our real state.
- Post-shipping states ONLY from GET /shipping/tracking_events/{shipment_id}; event.status enum = awaiting_collection, in_transit, out_for_delivery, delivered. Available ONLY if the label was purchased in Veeqo.
- Manual-ship trap: order.status/allocation.status/shipment.status/shipped_at are null/stale even when shipped. TRUE shipped signals: allocation.dispatch_date, shipment.shipped_by_id, shipment.tracking_number(+.status=='created'). tracking_number and carrier are OBJECTS (extract tracking_number.tracking_number, carrier.name).

LIVE data #P-1959471694:
- Our DB Order id=6: status=SHIPPED, lifecyclePhase=SHIPPED, veeqoShipmentId=1400784804, trackingNumber=9361289736066469804724, trackingCarrier=USPS, deliveredAt=NULL, outForDeliveryAt=NULL, poller alive (hourly).
- Live Veeqo: order.status=awaiting_payment, dispatch_date=2026-07-21T14:00:19Z, shipment.id=1400784804, shipped_by_id=363013, tracking_number.tracking_number=9361...804724 (status=created), carrier=USPS.
- GET /shipping/tracking_events/1400784804 => HTTP 200, body [] EMPTY (label not bought in Veeqo). USPS itself shows delivered ~Jul 23.

ROOT CAUSE: post-shipping lifecycle derives ONLY from Veeqo tracking_events; empty for FBA/manual/external labels => order frozen at SHIPPED forever. NO carrier-direct fallback. DB already has outForDeliveryAt/deliveredAt columns => no schema change.

## 3. CODE MAP (VM /home/mostafa/bendcore, NestJS+Prisma)
- src/veeqo/veeqo-order-sync.service.ts: pickLatestTrackingEvent L57 (null on empty); getLatestVeeqoTrackingEvent L88 (calls veeqoService.listTrackingEvents; null on empty/404); normalizeInternalStatus L134; resolveLifecycleState L171-320 (OFD/DELIVERED only from tracking_event_status/combined text; shipped signals->SHIPPED; NO carrier fallback); getOrderTracking L355-640; syncActiveOrdersCron L771 (@Cron */5s); syncOrder L816.
- src/veeqo/veeqo.service.ts (listTrackingEvents,getOrder,listShipments,USPS rates). src/veeqo/veeqo-simulator.service.ts (sim OFD/delivered).
- src/fulfillment/fulfillment-provider.interface.ts (245 lines, the switchable contract — do NOT break). providers/veeqo-fulfillment.provider.ts, threepl-fulfillment.provider.ts.
- src/orders/orders.service.ts (DTO ~L288-306 exposes deliveredAt,outForDeliveryAt,shippingStatusNextCheckAt,trackingUrl); order-lifecycle.service.ts; dto.ts.
- Order columns exist: status, lifecyclePhase, stateShipping, veeqoShipmentId, veeqo_order_id, veeqo_order_number, trackingNumber, trackingCarrier, trackingUrl, deliveredAt, outForDeliveryAt, shippingStatusLastCheckedAt, shippingStatusNextCheckAt.

## 4. CHANGES ALREADY MADE (Odin workspace only, NOT prod code)
1. Rewrote workspace/shared/tutorials/veeqo_fulfillment_api.md (backup .bak_catalog): catalog URL mandatory, order-status enum, tracking_events endpoint+enum, "label bought in Veeqo else carrier fallback", responsibility map.
2. Added durable VEEQO CATALOG RULE to rules[] in workspace/projects/fulfillment-vq-status-read-only-dc1e/index.json and workspace/projects/real-deployment-and-diagnosis-organics-07d7/index.json.
No prod code changed. No deploy run.

## 5. CLASSIFICATION (researched)
- Veeqo ~20-21 carrier entries (7 in /carriers, 16 in /shipping/carriers). Real orders USPS only.
- All carrier tracking APIs need auth (key or OAuth bearer). USPS/carriers/Amazon SP-API = free. Aggregators (EasyPost/AfterShip) free tier at this volume.
- Avenue A (vendor.myavenuea.com) = FULFILMENT PROVIDER (3PL), NOT a carrier. Same slot as Veeqo. No public API. Underlying parcels still carrier-tracked.
- Insight: an aggregator (EasyPost/AfterShip) is PROVIDER-AGNOSTIC — needs only tracking number+carrier, so one integration covers Veeqo/FBA/3PL without touching the switch. USPS-direct is the free option for current USPS orders.

## 6. FIX DESIGN (not built)
Add a carrier-tracking fallback in the sync path (NOT the shared interface): when Veeqo tracking_events empty but trackingNumber+carrier present, query chosen source (USPS API or aggregator) -> normalize to in_transit/out_for_delivery/delivered -> feed resolveLifecycleState via tracking_event_status. Existing code then stamps outForDeliveryAt/deliveredAt. No schema change, no rebase. Prefer provider-agnostic so 3PL covered. reviewed = app-owned post-delivery.
Also verify/normalize the 3 frontend surfaces (/home/mostafa/organics) so all read the SAME resolved status.

## 7. DECISION OPEN (needs user)
Tracking source: USPS API (free, OAuth2, USPS-only) | EasyPost/AfterShip aggregator (one key, provider-agnostic, webhook, free tier — recommended) | Amazon SP-API (FBA, heavy). User must self-register and paste key into AppSetting.RUNTIME_OPERATIONAL_SETTINGS (Claude never handles the secret). No USPS/aggregator key present yet.

## 8. BRIDGE OPERATION
- device_bash: user's local VM, Odin workspace mounted at /sessions/*/mnt/AiAgentWorkSpace/Odin-Orchestrator-v2 (host /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2). READ/WRITE workspace files + the CMD queue. No network.
- Mac terminal bridge (shells/agent_terminal_bridge.sh): runs on the Mac (has az, network). Write command to workspace/logs/agent_term/CMD; output in .run_out + OUT.log; STATUS = READY/RUNNING/IDLE/STOPPED. Drive by writing CMD via device_bash then poll STATUS/.run_out (device_bash timeout <=45000ms).
- Reach prod VM read-only (no port opened): az vm run-command invoke -g DJANGO-PROJECT -n django-vm --command-id RunShellScript --scripts "$VMSCRIPT" --query "value[0].message" -o tsv
  VM: RG=DJANGO-PROJECT, name=django-vm, IP 52.180.154.225, user mostafa. Backend /home/mostafa/bendcore, frontend /home/mostafa/organics.
  Read scoped key inside VM script (never print): DBURL from /home/mostafa/bendcore/.env DATABASE_URL; KEY = JSON veeqoApiKey from AppSetting RUNTIME_OPERATIONAL_SETTINGS. Do NOT use default VEEQO_API_KEY env.
  az output is CAPPED (~few KB, keeps TAIL) — read code in <=150-line chunks.
- KNOWN ISSUE: bridge stopped picking up new CMDs at end of session (stale .run_out). Ask user to restart shells/agent_terminal_bridge.sh (STATUS -> READY). Verify with a unique echo MARKER-$(date +%s) appearing in OUT.log.

## 9. NEXT STEPS
1. User picks tracking source (S7) + provides key. 2. Restart bridge, verify live. 3. Read frontend surfaces, normalize the 3 displays. 4. Build provider-agnostic carrier fallback (S6); keep interface intact; back up edited files. 5. STRONGLY TEST (simulator + real order #P-1959471694 must reach DELIVERED from carrier signal) before claiming anything. 6. Deploy only when authorized: deploy.sh with ODIN_MIG_OVERRIDE=none; backend runs live from repo (restart; no npm run dist). Firewall: az/ufw REPLACE current IP only, never open 22 to Any, never create ports, keep 80/443 up.

## 10. CONSTANTS
Order our id 6; veeqo_order_id 1959471694; #P-1959471694; shipment 1400784804; tracking 9361289736066469804724; USPS; dispatched 2026-07-21T14:00:19Z. Scoped key: AppSetting.RUNTIME_OPERATIONAL_SETTINGS.veeqoApiKey (len 36). No USPS/EasyPost/AfterShip key present yet. Tutorial: workspace/shared/tutorials/veeqo_fulfillment_api.md (re-read before any Veeqo work).
