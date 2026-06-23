from __future__ import annotations

import random
import json
from datetime import timedelta, datetime , time

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from core.models import ETSSite , ETSSiteBilling
from .models import OPCConnection, OPCNode, OPCNodeLive, OPCNodeHistory
from .opcua_client import OPCError, OPCErrorCodes, create_opcua_client
from django.db.models import Avg
from .alarm_utils import check_alarms
from opc.helpers import calculate_site_billing


def _set_sites_connected(connection_id: int, is_connected: bool) -> None:
    """
    Update `connected` flag on all ETSSites linked (via OPCAsset) to this connection.
    Silently does nothing if no sites are linked.
    """
    ETSSite.objects.filter(opc_assets__connection_id=connection_id).distinct().update(
        connected=is_connected , active=is_connected ,
    )



@shared_task(bind=True)
def poll_opc_connection(self, connection_id: int) -> dict:
    
    try:
        # First check if connection exists at all
        connection = OPCConnection.objects.get(pk=connection_id)
        print(f"Polling OPC connection {connection_id}")
    except OPCConnection.DoesNotExist:
        # nothing to update.
        return {"ok": False, "error": {"code": "OPC_CONNECTION_NOT_FOUND", "message": "Connection not found"}}

    if connection.is_deleted:
        # Connection exists but is soft-deleted — mark related sites as disconnected.
        _set_sites_connected(connection_id, False)
        return {"ok": False, "error": {"code": "OPC_CONNECTION_DELETED", "message": "Connection is soft-deleted"}}

    if not connection.enabled:
        # Connection exists but is disabled
        _set_sites_connected(connection_id, False)
        return {"ok": False, "error": {"code": "OPC_CONNECTION_DISABLED", "message": "Connection is disabled"}}

    now = timezone.now()
    nodes = (
        OPCNode.objects.filter(object__connection=connection)
        .select_related("object")
        .all()
    )

    results = []
    last_error_code = None
    last_error_message = None
    client = None
    
    # Normalize auth_type variants (e.g. 'username_password' → 'username')
    auth_type = connection.auth_type or 'anonymous'
    if 'username' in auth_type.lower():
        auth_type = 'username'

    try:
        client = create_opcua_client(
            endpoint_url=connection.endpoint_url,
            timeout_seconds=connection.timeout_seconds,
            security_policy=connection.security_policy,
            security_mode=connection.security_mode,
            auth_type=auth_type,                  # ← normalized
            username=connection.username,
            password=connection.password,
            client_cert_path=connection.client_cert_path,
            client_key_path=connection.client_key_path,
            server_cert_path=connection.server_cert_path,
        )

        # ── Connect attempt is the SOLE determinant of connected=True/False ──
        try:
            print(f"Trying endpoint: {connection.endpoint_url}", flush=True)
            client.connect()
            print(f"Successfully connected to OPC UA server for connection {connection_id}")
        except Exception:
            _set_sites_connected(connection_id, False)
            print(f"Failed to connect to OPC UA server for connection {connection_id}")
            raise   # let outer handlers process the error normally
        
        # Connection succeeded
        _set_sites_connected(connection.id, True)

        with transaction.atomic():
            for n in nodes:
                try:
                    node = client.get_node(n.opc_address)
                    dv = node.get_data_value()
                    val = dv.Value.Value if dv and dv.Value else None
                    status = str(dv.StatusCode) if dv and dv.StatusCode else None
                    source_ts = dv.SourceTimestamp if dv else None
                    server_ts = dv.ServerTimestamp if dv else None

                    # Parse JSON from VTS
                    actual_value = None
                    actual_timestamp = None
                    parsed_val = val
                    if val and isinstance(val, str):
                        try:
                            parsed_val = json.loads(val)
                        except json.JSONDecodeError:
                            pass

                    if isinstance(parsed_val, dict):
                        actual_value = parsed_val.get("value")
                        ts_str = parsed_val.get("ts")
                        if ts_str:
                            try:
                                dt_naive = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                                actual_timestamp = timezone.make_aware(dt_naive)
                            except ValueError:
                                pass

                    # ── Skip if actual_timestamp is missing/None ──
                    if actual_timestamp is None:
                        results.append({
                            "node_id":     n.id,
                            "node_name":   n.name,
                            "opc_address": n.opc_address,
                            "skipped":     "missing_actual_timestamp",
                            "raw_value":   parsed_val,
                        })
                        continue

                    live, _ = OPCNodeLive.objects.update_or_create(
                        node=n,
                        defaults={
                            "value": parsed_val,
                            "actual_value": actual_value,
                            "actual_timestamp": actual_timestamp,
                            "status": status,
                            "source_ts": source_ts,
                            "server_ts": server_ts,
                        },
                    )
                    # Ensure we have some timestamp to save
                    ts_to_save = source_ts or server_ts or actual_timestamp or now

                    OPCNodeHistory.objects.create(
                        node=n,
                        value=live.value,
                        actual_value=live.actual_value,
                        actual_timestamp=live.actual_timestamp,
                        status=live.status,
                        source_ts=source_ts or ts_to_save,
                        server_ts=server_ts or ts_to_save,
                    )

                    if actual_value is not None:
                        check_alarms(node=n, new_value=float(actual_value))

                    results.append(
                        {
                            "node_id": n.id,
                            "node_name": n.name,
                            "opc_address": n.opc_address,
                            "value": parsed_val,
                            "actual_value": actual_value,
                            "actual_timestamp": actual_timestamp,
                            "timestamp": source_ts or server_ts or now,
                        }
                    )
                except Exception as e:  # noqa: BLE001
                    import traceback
                    err_msg = traceback.format_exc()
                    print(f"ERROR processing node {n.name} ({n.opc_address}):")
                    print(err_msg)
                    results.append(
                        {
                            "node_id": n.id,
                            "node_name": n.name,
                            "opc_address": n.opc_address,
                            "error": {"code": OPCErrorCodes.READ_FAILED, "message": err_msg},
                        }
                    )

            connection.last_polled_at = now
            connection.last_error_code = None
            connection.last_error_message = None
            connection.save(update_fields=["last_polled_at", "last_error_code", "last_error_message"])

        return {"ok": True, "connection_id": connection.id, "results": results}

    except OPCError as e:
        last_error_code = e.code
        last_error_message = e.message
        return {"ok": False, "error": e.to_dict()}
    except Exception as e:  # noqa: BLE001
        last_error_code = OPCErrorCodes.CONNECT_FAILED
        last_error_message = str(e)
        return {"ok": False, "error": {"code": OPCErrorCodes.CONNECT_FAILED, "message": str(e)}}
    finally:
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass
        if last_error_code:
            OPCConnection.objects.filter(pk=connection_id).update(
                last_error_code=last_error_code,
                last_error_message=last_error_message,
            )
            print(f"Connection {connection_id} error: {last_error_code} - {last_error_message}")


@shared_task(bind=True)
def poll_due_opc_connections(self) -> dict:
    now = timezone.now()
    due = []

    for c in OPCConnection.objects.filter(enabled=True, is_deleted=False).all():
        if not c.polling_rate_ms:
            continue
        if not c.last_polled_at:
            due.append(c.id)
            continue
        delta = now - c.last_polled_at
        if delta >= timedelta(milliseconds=c.polling_rate_ms):
            due.append(c.id)

    # Spread polling across the interval to avoid spikes
    # Use random countdown (0-30 seconds) to distribute tasks
    for cid in due:
        countdown = random.randint(0, 30)
        poll_opc_connection.apply_async(args=[cid], countdown=countdown)

    return {"ok": True, "scheduled": len(due), "connection_ids": due}


@shared_task
def calculate_monthly_billings():
    """
        Runs once a month, on the 1st at 00:01 (Celery Beat).

        Closes the billing cycle for every non-deleted site that has a
        billing_config. The cycle covers the entire previous month:
        from_date = 1st of previous month
        to_date   = last day of previous month

        For each site:
        consumption       = last(energy_mwh_4) - first(energy_mwh_4) over period
        average_delta_t   = mean(temp_diff_k_7 actual_value) over period
        delta_t_fees      = penalty if (contracted - avg) drop > tolerance,
                            else 0:  drop × 0.1 × delta_t_fee_rate
        consumption_fee   = consumption × consumption_fee_rate
        declared_load_fee = site.declared_load (flat monthly base fee)
        total             = sum of all three fees

        The billing_day field on ETSSiteBillingConfig is intentionally ignored
        here — all sites are billed on the same cadence.
        
    """
    today = timezone.localdate()

    # ── Period: entire previous calendar month ──
    first_of_this_month = today.replace(day=1)
    period_to   = first_of_this_month - timedelta(days=1)   # last day of prev month
    period_from = period_to.replace(day=1)                  # first day of prev month

    # ── Loop over ALL non-deleted sites ──
    sites = ETSSite.objects.filter(is_deleted=False).select_related("billing_config")

    for site in sites:

        # Skip if already billed for this period
        if ETSSiteBilling.objects.filter(
            ets_site=site, from_date=period_from, to_date=period_to
        ).exists():
            continue

        # Compute billing data via helper
        data = calculate_site_billing(site, period_from, period_to)
        if data is None:
            continue   # no billing_config → ski

        # ── Save ──
        ETSSiteBilling.objects.create(
            ets_site        = site,
            from_date       = period_from,
            to_date         = period_to,
            average_delta_t = data["average_delta_t"],
            delta_t_fees    = round(data["delta_t_fees"], 2),
            consumption     = round(data["consumption"], 4),
            consumption_fee = round(data["consumption_fee"], 2),
            declared_load_fee = round(data["declared_load_fee"], 2),  
            total             = round(data["total"], 2),               
        )


@shared_task
def check_site_connections_health() -> dict:
    """
    Heartbeat: sweeps every OPCConnection and updates the linked
    ETSSites' connected/active flags based on freshness of last_polled_at.

    Suggested Beat schedule: every 30s.

    Rule — a connection is "alive" when:
      - not soft-deleted
      - enabled
      - last_polled_at IS NOT NULL
      - now - last_polled_at <= max(3 × polling_rate_ms, 60s)
    """
    now = timezone.now()
    alive_conn_ids = []
    dead_conn_ids  = []

    for conn in OPCConnection.objects.all().only(
        "id", "is_deleted", "enabled", "last_polled_at", "polling_rate_ms"
    ):
        if conn.is_deleted or not conn.enabled or conn.last_polled_at is None:
            dead_conn_ids.append(conn.id)
            continue

        polling_ms  = conn.polling_rate_ms or 1000
        stale_after = timedelta(milliseconds=max(polling_ms * 3, 60_000))

        if (now - conn.last_polled_at) <= stale_after:
            alive_conn_ids.append(conn.id)
        else:
            dead_conn_ids.append(conn.id)

    if alive_conn_ids:
        ETSSite.objects.filter(
            opc_assets__connection_id__in=alive_conn_ids,
        ).distinct().update(connected=True, active=True)

    if dead_conn_ids:
        ETSSite.objects.filter(
            opc_assets__connection_id__in=dead_conn_ids,
        ).distinct().update(connected=False, active=False)

    return {
        "ok":                 True,
        "alive_connections":  len(alive_conn_ids),
        "dead_connections":   len(dead_conn_ids),
        "at":                 now.isoformat(),
    }