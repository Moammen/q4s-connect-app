from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
import datetime, random

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with dummy data for testing."

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...")

        self._seed_users()
        self._seed_sites()
        self._seed_opc()
        self._seed_alarms()

        self.stdout.write(self.style.SUCCESS("Done! Database seeded successfully."))

    # ── Users ─────────────────────────────────────────────────────────────────
    def _seed_users(self):
        from accounts.models import User
        users = [
            dict(username="admin1",    email="admin1@ets.com",    role="admin",    password="Admin@1234",  is_superuser=False),
            dict(username="engineer1", email="eng1@ets.com",      role="engineer", password="Eng@1234",    is_superuser=False),
            dict(username="operator1", email="op1@ets.com",       role="operator", password="Op@1234",     is_superuser=False),
            dict(username="superadmin",email="super@ets.com",     role="admin",    password="Super@1234",  is_superuser=True),
        ]
        for u in users:
            if not User.objects.filter(username=u["username"]).exists():
                User.objects.create_superuser(**u) if u["is_superuser"] else User.objects.create_user(**u)
                self.stdout.write(f"  Created user: {u['username']}")

    # ── ETS Sites ─────────────────────────────────────────────────────────────
    def _seed_sites(self):
        from core.models import ETSSite, ETSSiteBillingConfig, ETSSiteBilling
        sites_data = [
            dict(name="Dubai Central Station",   ets_code="ETS-001", cts_name="CTS-Dubai-01",   region="dubai",          country="UAE", connected=True,  active=True,  alarm_status="inactive", declared_load=500.0, contracted_delta_t=10.0, customer_name="DEWA",   contract_number="CN-001", plot_number="P-101", location="Dubai, UAE",       latitude=25.2048,  longitude=55.2708),
            dict(name="Abu Dhabi North Station", ets_code="ETS-002", cts_name="CTS-AbuDhabi-01", region="abu_dhabi",      country="UAE", connected=True,  active=True,  alarm_status="active",   declared_load=750.0, contracted_delta_t=12.0, customer_name="ADDC",   contract_number="CN-002", plot_number="P-202", location="Abu Dhabi, UAE",   latitude=24.4539,  longitude=54.3773),
            dict(name="Sharjah East Station",    ets_code="ETS-003", cts_name="CTS-Sharjah-01",  region="northern_region",country="UAE", connected=False, active=True,  alarm_status="inactive", declared_load=300.0, contracted_delta_t=8.0,  customer_name="SEWA",   contract_number="CN-003", plot_number="P-303", location="Sharjah, UAE",     latitude=25.3463,  longitude=55.4209),
            dict(name="Dubai South Station",     ets_code="ETS-004", cts_name="CTS-Dubai-02",    region="dubai",          country="UAE", connected=True,  active=False, alarm_status="inactive", declared_load=450.0, contracted_delta_t=9.0,  customer_name="Empower",contract_number="CN-004", plot_number="P-404", location="Dubai South, UAE", latitude=24.8976,  longitude=55.1624),
        ]
        for s in sites_data:
            site, created = ETSSite.objects.get_or_create(ets_code=s["ets_code"], defaults=s)
            if created:
                self.stdout.write(f"  Created site: {site.name}")

                ETSSiteBillingConfig.objects.create(
                    ets_site=site,
                    delta_t_tolerance=0.5,
                    delta_t_fee_rate=5.0,
                    consumption_fee_rate=0.35,
                )

                ETSSiteBilling.objects.create(
                    ets_site=site,
                    from_date=datetime.date(2026, 1, 1),
                    to_date=datetime.date(2026, 1, 31),
                    average_delta_t=9.8,
                    delta_t_fees=1200.0,
                    consumption=12000.0,
                    consumption_fee=4200.0,
                )

    # ── OPC ───────────────────────────────────────────────────────────────────
    def _seed_opc(self):
        from core.models import ETSSite
        from opc.models import OPCConnection, OPCObject, OPCNode, OPCNodeLive, OPCNodeHistory

        sites = list(ETSSite.objects.all())

        for site in sites:
            conn, created = OPCConnection.objects.get_or_create(
                name=f"{site.name} PLC",
                defaults=dict(ets_site=site, endpoint_url=f"opc.tcp://192.168.{random.randint(1,254)}.1:4840"),
            )
            if not created:
                continue
            self.stdout.write(f"  Created connection: {conn.name}")

            for obj_name, opc_obj_name in [("Supply Unit", "Supply_Unit"), ("Return Unit", "Return_Unit")]:
                obj = OPCObject.objects.create(
                    connection=conn,
                    name=obj_name,
                    opc_name=opc_obj_name,
                    parent_path=f"Root.{opc_obj_name}",
                )

                nodes_data = [
                    ("Supply Temp",    "Supply_Temp",    "Float", "°C"),
                    ("Return Temp",    "Return_Temp",    "Float", "°C"),
                    ("Flow Rate",      "Flow_Rate",      "Float", "m³/h"),
                    ("Pressure",       "Pressure",       "Float", "bar"),
                    ("Power",          "Power",          "Float", "kW"),
                ]
                for node_name, opc_node_name, dtype, unit in nodes_data:
                    node = OPCNode.objects.create(
                        object=obj,
                        name=node_name,
                        opc_name=opc_node_name,
                        opc_address=f"ns=2;s={opc_obj_name}.{opc_node_name}",
                        data_type=dtype,
                        unit=unit,
                    )

                    OPCNodeLive.objects.create(
                        node=node,
                        value=round(random.uniform(10, 100), 2),
                        status="Good",
                        source_ts=timezone.now(),
                        server_ts=timezone.now(),
                    )

                    for i in range(5):
                        OPCNodeHistory.objects.create(
                            node=node,
                            value=round(random.uniform(10, 100), 2),
                            status="Good",
                            source_ts=timezone.now() - datetime.timedelta(hours=i+1),
                            server_ts=timezone.now() - datetime.timedelta(hours=i+1),
                        )

    # ── Alarms ────────────────────────────────────────────────────────────────
    def _seed_alarms(self):
        from opc.models import OPCNode, OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent

        nodes = list(OPCNode.objects.filter(name__icontains="Temp"))

        for node in nodes:
            rule_high, created = OPCAlarmRule.objects.get_or_create(
                node=node,
                name=f"High {node.name}",
                defaults=dict(alarm_type="high", limit_value=90.0, deadband=2.0, severity="high", enabled=True),
            )
            rule_low, _ = OPCAlarmRule.objects.get_or_create(
                node=node,
                name=f"Low {node.name}",
                defaults=dict(alarm_type="low", limit_value=5.0, deadband=1.0, severity="medium", enabled=True),
            )

            if created:
                self.stdout.write(f"  Created alarm rules for node: {node.name}")

                OPCAlarmLive.objects.get_or_create(
                    rule=rule_high,
                    defaults=dict(is_active=True,  value=92.5, status="Good", message="High temperature exceeded 90°C", activation_count=3, activated_at=timezone.now() - datetime.timedelta(minutes=30)),
                )
                OPCAlarmLive.objects.get_or_create(
                    rule=rule_low,
                    defaults=dict(is_active=False, value=6.1,  status="Good", message="", activation_count=1, activated_at=timezone.now() - datetime.timedelta(days=2), cleared_at=timezone.now() - datetime.timedelta(days=1)),
                )

                for day in range(5):
                    started = timezone.now() - datetime.timedelta(days=day, hours=random.randint(1, 8))
                    OPCAlarmEvent.objects.create(
                        rule=rule_high,
                        started_at=started,
                        ended_at=started + datetime.timedelta(minutes=random.randint(10, 120)),
                        start_value=round(random.uniform(90, 100), 2),
                        end_value=round(random.uniform(80, 90), 2),
                        start_status="Good",
                        end_status="Good",
                        message="Temperature exceeded high limit.",
                        acknowledged=random.choice([True, False]),
                    )
