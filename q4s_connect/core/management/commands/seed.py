import calendar
import datetime
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# =============================================================================
# Configuration
# =============================================================================

SITES = [
    # (name, ets_code, ets_name, location, lat, lng, customer, contract_no, plot, declared_load, declared_load_fee)
    ("Burj Khalifa Tower",  "DXB-001", "BKT-01",  "Downtown Dubai",  25.1972, 55.2744, "Emaar Properties",   "CN-DXB-001", "PLT-001", 1200.0, 5000.0),
    ("Dubai Marina Walk",   "DXB-002", "DMW-01",  "Dubai Marina",    25.0820, 55.1394, "DAMAC Properties",   "CN-DXB-002", "PLT-002",  800.0, 3500.0),
    ("Business Bay Tower",  "DXB-003", "BBT-01",  "Business Bay",    25.1857, 55.2769, "Dubai Properties",   "CN-DXB-003", "PLT-003",  950.0, 4200.0),
    ("JBR Beach Residence", "DXB-004", "JBR-01",  "JBR",             25.0760, 55.1322, "Meraas Holding",     "CN-DXB-004", "PLT-004",  650.0, 2800.0),
    ("Palm Jumeirah Tower", "DXB-005", "PJT-01",  "Palm Jumeirah",   25.1124, 55.1390, "Nakheel",            "CN-DXB-005", "PLT-005", 1500.0, 6500.0),
    ("Dubai Hills Mall",    "DXB-006", "DHM-01",  "Dubai Hills",     25.1100, 55.2480, "Emaar Malls",        "CN-DXB-006", "PLT-006", 2000.0, 8500.0),
    ("Al Quoz Industrial",  "DXB-007", "AQI-01",  "Al Quoz",         25.1465, 55.2326, "Dubai Industrial",   "CN-DXB-007", "PLT-007",  500.0, 2000.0),
    ("Deira Souq Plaza",    "DXB-008", "DSP-01",  "Deira",           25.2697, 55.3094, "Dubai Municipality", "CN-DXB-008", "PLT-008",  400.0, 1800.0),
    ("Silicon Oasis HQ",    "DXB-009", "SOH-01",  "Silicon Oasis",   25.1245, 55.3870, "DSOA",               "CN-DXB-009", "PLT-009",  750.0, 3200.0),
    ("JLT Cluster F Tower", "DXB-010", "JLT-01",  "JLT",             25.0700, 55.1409, "DMCC",               "CN-DXB-010", "PLT-010",  850.0, 3800.0),
]

# Supply temperature varies 0.5°C site-to-site, range 4–6°C
SUPPLY_TEMPS = [4.0, 4.5, 5.0, 5.5, 6.0, 4.0, 4.5, 5.0, 5.5, 6.0]

# Sites 0,1,2 are "low delta-T" (return 8–9°C) — will be flagged on dashboard
# Sites 3-9 are "good" (return 11–14°C)
LOW_SITE_INDICES = {0, 1, 2}
RETURN_TEMPS_LOW  = [8.0, 8.5, 9.0]
RETURN_TEMPS_GOOD = [11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0]

# OPC metric object names — must match helpers.py billing/dashboard logic exactly
METRICS = [
    "flow_m3h_1",       # Flow (m³/h):   140–250
    "temp_supply_c_2",  # Supply Temp:   4–6°C
    "temp_return_c_3",  # Return Temp:   8–9 (low) or 11–14°C (good)
    "energy_mwh_4",     # Energy (MWh):  accumulated, +30–40 MWh/day
    "power_kw_5",       # Power (kW):    20–60
    "volume_m3_6",      # Volume (m³):   accumulated, +100–200 m³/day
    "temp_diff_k_7",    # Temp Diff (K): supply−return (negative)
    "serial_8",         # Serial:        fixed
    "address_9",        # Address:       fixed
]

HISTORY_MONTHS   = 10
READINGS_PER_DAY = 4   # every 6 hours

# Energy increases 30–40 MWh per day → 7.5–10 MWh per 6h reading
ENERGY_INC_MIN = 7.5
ENERGY_INC_MAX = 10.0

# Volume increases 100–200 m³ per day → 25–50 m³ per 6h reading
VOLUME_INC_MIN = 25.0
VOLUME_INC_MAX = 50.0

# Alarm rules: (metric, rule_name, alarm_type, limit_value, deadband, severity)
ALARM_DEFS = [
    ("temp_supply_c_2", "Supply Temp High Notice",   "high",      7.0,  0.3, "low"),
    ("temp_supply_c_2", "Supply Temp High Warning",  "high",      8.0,  0.5, "medium"),
    ("temp_supply_c_2", "Supply Temp Critical",      "high_high", 10.0, 0.5, "critical"),
    ("temp_return_c_3", "Return Temp High Notice",   "high",      15.0, 0.3, "low"),
    ("temp_return_c_3", "Return Temp High Warning",  "high",      16.0, 0.5, "medium"),
    ("temp_diff_k_7",   "Marginal Delta-T",          "low",       -5.0, 0.5, "medium"),
    ("temp_diff_k_7",   "Low Delta-T",               "low",       -4.0, 0.5, "high"),
    ("temp_diff_k_7",   "Critically Low Delta-T",    "low_low",   -3.0, 0.5, "critical"),
    ("flow_m3h_1",      "Low Flow Warning",          "low",      100.0, 2.0, "high"),
    ("power_kw_5",      "Power High Warning",        "high",      58.0, 1.0, "medium"),
]

# Days-ago offsets for historical alarm events (10 events per rule)
ALARM_EVENT_DAYS = [3, 7, 14, 21, 30, 45, 60, 90, 150, 200]


# =============================================================================
# Management Command
# =============================================================================

class Command(BaseCommand):
    help = "Clear existing seed data and reseed with 10 Dubai sites + 10 months of history."

    def handle(self, *args, **kwargs):
        from accounts.models import User
        from core.models import ETSSite, ETSSiteBillingConfig, ETSSiteBilling
        from opc.models import (
            OPCConnection, OPCAsset, OPCObject, OPCNode,
            OPCNodeLive, OPCNodeHistory,
            OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent,
            OPCGeneratedSiteLink,
        )

        self.stdout.write(self.style.WARNING("=== Step 1: Clearing existing data ==="))
        self._clear(User, ETSSite, OPCConnection, OPCGeneratedSiteLink)

        self.stdout.write(self.style.WARNING("=== Step 2: Seeding users ==="))
        self._seed_users(User)

        self.stdout.write(self.style.WARNING("=== Step 3: Seeding sites, OPC tree, history, alarms ==="))
        self._seed_all(
            ETSSite, ETSSiteBillingConfig, ETSSiteBilling,
            OPCConnection, OPCAsset, OPCObject, OPCNode,
            OPCNodeLive, OPCNodeHistory,
            OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent,
        )

        self.stdout.write(self.style.SUCCESS("=== Done! Database seeded successfully. ==="))

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1 – Clear
    # ─────────────────────────────────────────────────────────────────────────

    def _clear(self, User, ETSSite, OPCConnection, OPCGeneratedSiteLink):
        with transaction.atomic():
            cnt, _ = OPCGeneratedSiteLink.objects.all().delete()
            self.stdout.write(f"  Deleted {cnt} OPCGeneratedSiteLinks")

            # OPCConnection CASCADE: OPCAsset → OPCObject → OPCNode → Live/History/AlarmRule/Live/Event
            cnt, _ = OPCConnection.objects.all().delete()
            self.stdout.write(f"  Deleted {cnt} OPCConnections (and all child OPC records)")

            # ETSSite CASCADE: ETSSiteBilling, ETSSiteBillingConfig
            cnt, _ = ETSSite.objects.all().delete()
            self.stdout.write(f"  Deleted {cnt} ETSSites (and billing records)")

            cnt, _ = User.objects.filter(is_superuser=False).delete()
            self.stdout.write(f"  Deleted {cnt} non-superuser users")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2 – Users
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_users(self, User):
        users = [
            dict(username="admin_dxb",   email="admin@ets-dxb.ae",     role="admin",    password="Admin@2026",    is_superuser=True,  all_sites=True),
            dict(username="manager_dxb", email="manager@ets-dxb.ae",   role="admin",    password="Manager@2026",  is_superuser=True,  all_sites=True),
            dict(username="engineer1",   email="engineer1@ets-dxb.ae", role="engineer", password="Engineer@2026", is_superuser=False, all_sites=False),
            dict(username="operator1",   email="operator1@ets-dxb.ae", role="operator", password="Operator@2026", is_superuser=False, all_sites=False),
        ]
        for u in users:
            if User.objects.filter(username=u["username"]).exists():
                continue
            if u["is_superuser"]:
                User.objects.create_superuser(
                    username=u["username"], email=u["email"],
                    password=u["password"], role=u["role"], all_sites=u["all_sites"]
                )
            else:
                User.objects.create_user(
                    username=u["username"], email=u["email"],
                    password=u["password"], role=u["role"], all_sites=u["all_sites"]
                )
            self.stdout.write(f"  Created user: {u['username']}")

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3 – Sites, OPC tree, history, alarms
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_all(
        self,
        ETSSite, ETSSiteBillingConfig, ETSSiteBilling,
        OPCConnection, OPCAsset, OPCObject, OPCNode,
        OPCNodeLive, OPCNodeHistory,
        OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent,
    ):
        now = timezone.now()

        # Build timestamp series (every 6h for HISTORY_MONTHS months)
        interval = datetime.timedelta(hours=24 // READINGS_PER_DAY)
        history_start = now - datetime.timedelta(days=HISTORY_MONTHS * 31)
        timestamps = []
        ts = history_start
        while ts <= now:
            timestamps.append(ts)
            ts += interval

        self.stdout.write(f"  History series: {len(timestamps)} timestamps per node")

        low_ret_idx  = 0
        good_ret_idx = 0

        for i, site_def in enumerate(SITES):
            (name, ets_code, ets_name, location, lat, lng,
             customer, contract_no, plot, declared_load, declared_load_fee) = site_def

            is_low = i in LOW_SITE_INDICES
            supply_temp = SUPPLY_TEMPS[i]

            if is_low:
                return_temp = RETURN_TEMPS_LOW[low_ret_idx % len(RETURN_TEMPS_LOW)]
                low_ret_idx += 1
                contracted_delta_t = 10.0   # Low sites exceed tolerance → flagged
            else:
                return_temp = RETURN_TEMPS_GOOD[good_ret_idx % len(RETURN_TEMPS_GOOD)]
                good_ret_idx += 1
                contracted_delta_t = 6.0    # Good sites: abs(delta-T)≈7 > 6+0.5 → NOT flagged

            # temp_diff = supply − return (negative; billing helpers call abs())
            delta_t_base = supply_temp - return_temp

            connected = (ets_code != "DXB-007")  # Al Quoz is disconnected

            # ── ETSSite ──────────────────────────────────────────────────────
            site = ETSSite.objects.create(
                name=name,
                ets_code=ets_code,
                ets_name=ets_name,
                location=location,
                latitude=lat,
                longitude=lng,
                region="dubai",
                country="UAE",
                customer_name=customer,
                contract_number=contract_no,
                plot_number=plot,
                declared_load=declared_load,
                declared_load_fee=declared_load_fee,
                contracted_delta_t=contracted_delta_t,
                connected=connected,
                active=True,
                alarm_status="active" if is_low else "inactive",
            )

            # ── Billing Config ────────────────────────────────────────────────
            ETSSiteBillingConfig.objects.create(
                ets_site=site,
                delta_t_tolerance=0.5,
                delta_t_fee_rate=0.15 if is_low else 0.10,
                consumption_fee_rate=0.4,
                billing_day=1,
            )

            # ── Billing History (10 months) ──────────────────────────────────
            self._create_billing(
                ETSSiteBilling, site, contracted_delta_t,
                supply_temp, return_temp, declared_load_fee,
            )

            # ── OPCConnection ─────────────────────────────────────────────────
            conn = OPCConnection.objects.create(
                name=f"{ets_code}-PLC",
                endpoint_url=f"opc.tcp://10.20.1.{i + 2}:4840/flxinOPC",
                enabled=True,
                auth_type="anonymous",
                timeout_seconds=10,
                polling_rate_ms=1000,
                last_polled_at=now - datetime.timedelta(minutes=5) if connected else None,
                last_error_code=None if connected else "OPC_CONNECT_FAILED",
                last_error_message=None if connected else "Connection timed out",
            )

            # ── OPCAsset ──────────────────────────────────────────────────────
            asset = OPCAsset.objects.create(
                connection=conn,
                ets_site=site,
                name=name,
                opc_name=f"Device_{ets_code}",
                opc_address="ns=2;i=2",
            )

            # ── OPC Objects → Nodes → Live + History ─────────────────────────
            history_batch = []
            node_by_metric = {}

            for j, metric in enumerate(METRICS):
                obj = OPCObject.objects.create(
                    connection=conn,
                    asset=asset,
                    name=metric,
                    opc_name=metric,
                    opc_address=f"ns=2;i={3 + j * 4}",
                    parent_path=f"Device_{ets_code}",
                )

                # Node name/opc_name MUST be "VTS" for billing helper filters
                node = OPCNode.objects.create(
                    object=obj,
                    name="VTS",
                    opc_name="VTS",
                    opc_address=f"ns=2;s={metric}.VTS",
                    data_type="json",
                    unit=None,
                )
                node_by_metric[metric] = node

                # Generate full value series for this metric
                values = _gen_series(
                    metric, len(timestamps),
                    supply_temp, return_temp, delta_t_base,
                )

                # OPCNodeLive — latest reading
                latest_val = values[-1]
                latest_ts  = timestamps[-1]
                OPCNodeLive.objects.create(
                    node=node,
                    value={"value": latest_val, "ts": latest_ts.strftime("%Y-%m-%d %H:%M:%S")},
                    actual_value=latest_val,
                    actual_timestamp=latest_ts,
                    status="StatusCode(Good)",
                    source_ts=latest_ts,
                    server_ts=latest_ts,
                )

                # Collect history rows for bulk insert
                for ts_val, val in zip(timestamps, values):
                    history_batch.append(OPCNodeHistory(
                        node=node,
                        value={"value": val, "ts": ts_val.strftime("%Y-%m-%d %H:%M:%S")},
                        actual_value=val,
                        actual_timestamp=ts_val,
                        status="StatusCode(Good)",
                        source_ts=ts_val,
                        server_ts=ts_val,
                    ))

            # Bulk insert all history for this site in one shot
            OPCNodeHistory.objects.bulk_create(history_batch, batch_size=2000)
            self.stdout.write(
                f"  [{i+1}/10] {name}: {len(history_batch):,} history rows | "
                f"supply={supply_temp}°C return={return_temp}°C "
                f"({'LOW Δt' if is_low else 'good Δt'})"
            )

            # ── Alarms ────────────────────────────────────────────────────────
            self._create_alarms(
                node_by_metric, OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent, now
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Billing helper
    # ─────────────────────────────────────────────────────────────────────────

    def _create_billing(
        self, ETSSiteBilling, site, contracted_delta_t,
        supply_temp, return_temp, declared_load_fee,
    ):
        today = timezone.localdate()
        delta_t_magnitude = abs(return_temp - supply_temp)
        consumption_fee_rate = 0.4
        delta_t_fee_rate     = 0.15 if contracted_delta_t > 7 else 0.10
        tolerance            = 0.5

        for offset in range(1, HISTORY_MONTHS + 1):
            year  = today.year
            month = today.month - offset
            while month <= 0:
                month += 12
                year  -= 1

            last_day  = calendar.monthrange(year, month)[1]
            from_date = datetime.date(year, month, 1)
            to_date   = datetime.date(year, month, last_day)

            # avg_delta_t with slight random noise
            avg_delta_t = round(delta_t_magnitude + random.uniform(-0.3, 0.3), 2)

            # Consumption: 30–40 MWh/day × days in month
            consumption     = round(random.uniform(30, 40) * last_day, 2)
            consumption_fee = round(consumption * consumption_fee_rate, 2)

            # Delta-T penalty
            drop = contracted_delta_t - avg_delta_t - tolerance
            delta_t_fees = (
                round(drop * 0.1 * float(declared_load_fee) * 2, 2)
                if drop > 0 else 0.0
            )

            total = round(float(declared_load_fee) + delta_t_fees + consumption_fee, 2)

            ETSSiteBilling.objects.create(
                ets_site=site,
                from_date=from_date,
                to_date=to_date,
                average_delta_t=avg_delta_t,
                delta_t_fees=delta_t_fees,
                consumption=consumption,
                consumption_fee=consumption_fee,
                declared_load_fee=declared_load_fee,
                total=total,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Alarm helper
    # ─────────────────────────────────────────────────────────────────────────

    def _create_alarms(
        self, node_by_metric, OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent, now
    ):
        active_prob = {"low": 0.30, "medium": 0.40, "high": 0.35, "critical": 0.25}

        for metric, rule_name, alarm_type, limit_value, deadband, severity in ALARM_DEFS:
            node = node_by_metric.get(metric)
            if not node:
                continue

            try:
                rule = OPCAlarmRule.objects.create(
                    node=node,
                    name=rule_name,
                    alarm_type=alarm_type,
                    limit_value=limit_value,
                    deadband=deadband,
                    severity=severity,
                    enabled=True,
                )
            except Exception:
                continue  # skip duplicate names (safe on re-run with same nodes)

            is_active = random.random() < active_prob.get(severity, 0.3)
            if is_active:
                activated_at = now - datetime.timedelta(hours=random.randint(1, 48))
                cleared_at   = None
            else:
                activated_at = now - datetime.timedelta(days=random.randint(5, 30))
                cleared_at   = activated_at + datetime.timedelta(hours=random.randint(1, 5))

            # live value: slightly past the threshold
            sign  = -1 if alarm_type in ("low", "low_low") else 1
            live_val = round(limit_value + sign * random.uniform(0.5, 2.0), 2)

            OPCAlarmLive.objects.create(
                rule=rule,
                is_active=is_active,
                value=live_val,
                status="StatusCode(Good)",
                message=f"{rule_name} triggered" if is_active else "",
                activation_count=random.randint(1, 5),
                activated_at=activated_at,
                cleared_at=cleared_at,
            )

            # Historical alarm events (one per ALARM_EVENT_DAYS entry)
            events = []
            for days_ago in ALARM_EVENT_DAYS:
                started = now - datetime.timedelta(days=days_ago, hours=random.randint(0, 8))
                ended   = started + datetime.timedelta(minutes=random.randint(10, 180))
                events.append(OPCAlarmEvent(
                    rule=rule,
                    started_at=started,
                    ended_at=ended,
                    start_value=round(limit_value + sign * random.uniform(1.0, 3.0), 2),
                    end_value=round(limit_value + sign * -0.5, 2),
                    start_status="StatusCode(Good)",
                    end_status="StatusCode(Good)",
                    message=f"{rule_name} triggered {days_ago} days ago",
                    acknowledged=(days_ago > 2),
                    acknowledged_at=(
                        started + datetime.timedelta(minutes=45) if days_ago > 2 else None
                    ),
                ))
            OPCAlarmEvent.objects.bulk_create(events)


# =============================================================================
# Value series generators (module-level for clarity)
# =============================================================================

def _gen_series(metric, count, supply_temp, return_temp, delta_t_base):
    """
    Return a list of `count` float values for the given metric.

    Accumulated metrics (energy, volume) grow monotonically.
    All other metrics are random within spec ranges.
    """
    values = []

    if metric == "energy_mwh_4":
        # Accumulated: +30–40 MWh/day → +7.5–10 MWh per 6h reading
        val = round(1000.0 + random.uniform(0, 200), 4)
        for _ in range(count):
            values.append(round(val, 4))
            val += random.uniform(ENERGY_INC_MIN, ENERGY_INC_MAX)

    elif metric == "volume_m3_6":
        # Accumulated: +100–200 m³/day → +25–50 m³ per 6h reading
        val = round(50000.0 + random.uniform(0, 1000), 2)
        for _ in range(count):
            values.append(round(val, 2))
            val += random.uniform(VOLUME_INC_MIN, VOLUME_INC_MAX)

    elif metric == "temp_supply_c_2":
        for _ in range(count):
            values.append(round(supply_temp + random.uniform(-0.15, 0.15), 2))

    elif metric == "temp_return_c_3":
        for _ in range(count):
            values.append(round(return_temp + random.uniform(-0.25, 0.25), 2))

    elif metric == "temp_diff_k_7":
        # supply − return (negative; billing helpers call abs())
        for _ in range(count):
            values.append(round(delta_t_base + random.uniform(-0.15, 0.15), 2))

    elif metric == "flow_m3h_1":
        for _ in range(count):
            values.append(round(random.uniform(140, 250), 2))

    elif metric == "power_kw_5":
        for _ in range(count):
            values.append(round(random.uniform(20, 60), 2))

    elif metric in ("serial_8", "address_9"):
        for _ in range(count):
            values.append(12345.0)

    else:
        for _ in range(count):
            values.append(0.0)

    return values
