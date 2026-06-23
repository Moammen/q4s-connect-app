from __future__ import annotations

from django.utils import timezone

from .models import OPCAlarmRule, OPCAlarmLive, OPCAlarmEvent


def check_alarms(node, new_value: float) -> None:
    """
    Check all enabled alarm rules for a node and update OPCAlarmLive / OPCAlarmEvent accordingly.
    Called after every successful OPC node read inside the polling task.
    """
    rules = OPCAlarmRule.objects.filter(node=node, enabled=True, is_deleted=False).select_related("live_alarm")

    for rule in rules:
        live, _ = OPCAlarmLive.objects.get_or_create(rule=rule)

        # ── Determine if the value triggers the rule ──────────────────────
        triggered = False
        if rule.alarm_type in ("high", "high_high") and new_value > rule.limit_value:
            triggered = True
        elif rule.alarm_type in ("low", "low_low") and new_value < rule.limit_value:
            triggered = True

        # ── Determine if the value clears the rule (with deadband) ────────
        cleared = False
        if rule.alarm_type in ("high", "high_high") and new_value < (rule.limit_value - rule.deadband):
            cleared = True
        elif rule.alarm_type in ("low", "low_low") and new_value > (rule.limit_value + rule.deadband):
            cleared = True

        now = timezone.now()

        if triggered and not live.is_active:
            # ── New activation ─────────────────────────────────────────────
            live.is_active        = True
            live.value            = new_value
            live.activated_at     = now
            live.cleared_at       = None
            live.activation_count += 1
            live.save()

            OPCAlarmEvent.objects.create(
                rule=rule,
                started_at=now,
                start_value=new_value,
            )

        elif triggered and live.is_active:
            # ── Still active — just update the current value ───────────────
            live.value = new_value
            live.save(update_fields=["value", "updated_at"])

        elif cleared and live.is_active:
            # ── Alarm cleared ──────────────────────────────────────────────
            live.is_active  = False
            live.value      = new_value
            live.cleared_at = now
            live.save()

            OPCAlarmEvent.objects.filter(
                rule=rule,
                ended_at__isnull=True,
            ).update(ended_at=now, end_value=new_value)
