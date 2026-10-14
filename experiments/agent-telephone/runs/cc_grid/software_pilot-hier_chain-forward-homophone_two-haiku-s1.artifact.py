# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-u664ngqg/brennan_reminders/reminders.py
# NOTE: No file-writing or test tools were available to the implementer, so this code was not written to disk and the tests in this response were not run.
"""Appointment reminder planner for Brennan Opticians.

ASSUMED defaults to confirm with the client (question numbers from the architect design):
Q1  REMINDER_2_BEFORE = 2 hours.
Q2  Email text uses the same template and signature as SMS, with no length limit.
Q3  Quiet window is 21:00 (inclusive) to 08:00 (exclusive), Dublin wall-clock time.
    A quiet candidate moves to the 20:00 that opens its window. If that is before now,
    now is used when now is outside the window; when now is inside the window the
    reminder goes to the next 08:00, or is dropped if that is at or after starts_at.
Q4  If both reminder points have passed, exactly one reminder is sent, immediately.
    Consequence to confirm: if a clamp or immediate send collapses both slots onto now,
    two reminders with the same send_at and channel are returned for one appointment.
Q5  Appointments with starts_at <= now produce nothing.
Q6  Statuses other than cancelled (for example no_show) are still reminded.
Q7  No usable contact produces nothing and logs a WARNING with the id only.
Q8  Dates are DD/MM/YYYY and times are 24-hour HH:MM, in Europe/Dublin. The SMS length is
    len(text) against 160. Name forms, in order: full name, first name plus last initial
    with a dot, first name, no name.
Q9  Slots use absolute UTC elapsed time (48h and 2h before starts_at).
Q10 now and starts_at must be timezone-aware datetimes. Strings are not parsed.
Other: country comparison is case-insensitive, so 'pl' is treated as PL.
Other: if an SMS does not fit even without a name, it falls back to email when an email is
present, otherwise it is dropped with a WARNING.
Other: a blank customer name produces text with no greeting, in both SMS and email.
Open issue (not decided here): the signature contains non-GSM-7 characters, so SMS is UCS-2
with a 70-character segment limit. sms_length() is still len().
Scope cut: none.
"""
import logging
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger('brennan.reminders')

TZ = ZoneInfo('Europe/Dublin')
REMINDER_1_BEFORE = timedelta(hours=48)
REMINDER_2_BEFORE = timedelta(hours=2)
QUIET_START = time(21, 0)
QUIET_END = time(8, 0)
EVENING_SHIFT = time(20, 0)
SMS_MAX_CHARS = 160
SIGNATURE_DEFAULT = 'Siobhán Ní Dhuibhir'
SIGNATURE_PL = 'Grzegorz Szczepański'
REQUIRED_KEYS = ('id', 'customer_name', 'status', 'starts_at', 'optout_sms_v2', 'email', 'phone', 'country')
_UTC = timezone.utc


def _label(appt):
    ident = appt.get('id') if isinstance(appt, dict) else None
    if isinstance(ident, (str, int)) and not isinstance(ident, bool):
        return f'appointment {ident!r}'
    return 'appointment'


def validate_appointment(appt):
    if not isinstance(appt, dict):
        raise ValueError('each appointment must be a dict')
    for key in REQUIRED_KEYS:
        if key not in appt:
            raise ValueError(f'missing field {key!r} in {_label(appt)}')
    ident = appt['id']
    if isinstance(ident, bool) or not isinstance(ident, (str, int)):
        raise ValueError(f'id must be str or int in {_label(appt)}')
    starts = appt['starts_at']
    if not isinstance(starts, datetime) or starts.utcoffset() is None:
        raise ValueError(f'starts_at must be a timezone-aware datetime in {_label(appt)}')
    if appt['optout_sms_v2'] is not None and not isinstance(appt['optout_sms_v2'], bool):
        raise ValueError(f'optout_sms_v2 must be a bool or None in {_label(appt)}')
    for key in ('customer_name', 'status', 'email', 'phone', 'country'):
        if appt[key] is not None and not isinstance(appt[key], str):
            raise ValueError(f'{key} must be a string or None in {_label(appt)}')


def _present(value):
    return isinstance(value, str) and value.strip() != ''


def is_cancelled(appt):
    return (appt['status'] or '').strip().lower() == 'cancelled'


def choose_channel(appt):
    has_email = _present(appt['email'])
    if appt['optout_sms_v2'] is True:
        return 'email' if has_email else None
    if _present(appt['phone']):
        return 'sms'
    return 'email' if has_email else None


def _is_quiet(local):
    t = local.time()
    return t >= QUIET_START or t < QUIET_END


def apply_quiet_window(candidate):
    """candidate is UTC-aware. Returns (utc_datetime, shifted_flag)."""
    local = candidate.astimezone(TZ)
    if not _is_quiet(local):
        return candidate, False
    if local.time() >= QUIET_START:
        day = local.date()
    else:
        day = local.date() - timedelta(days=1)
    evening = datetime.combine(day, EVENING_SHIFT, tzinfo=TZ)
    return evening.astimezone(_UTC), True


def _next_0800(now):
    local = now.astimezone(TZ)
    if local.time() >= QUIET_START:
        day = local.date() + timedelta(days=1)
    else:
        day = local.date()
    return datetime.combine(day, QUIET_END, tzinfo=TZ).astimezone(_UTC)


def clamp_past(candidate, now, starts, ident):
    """Returns the final UTC send time, or None to drop the reminder."""
    if candidate >= now:
        return candidate
    if not _is_quiet(now.astimezone(TZ)):
        logger.debug('clamped_to_now id=%s', ident)
        return now
    deferred = _next_0800(now)
    logger.debug('deferred_to_0800 id=%s', ident)
    if deferred >= starts:
        logger.debug('dropped_after_defer id=%s', ident)
        return None
    return deferred


def format_date_time(starts):
    local = starts.astimezone(TZ)
    return local.strftime('%d/%m/%Y'), local.strftime('%H:%M')


def _signature(country):
    code = (country or '').strip().upper()
    return SIGNATURE_PL if code == 'PL' else SIGNATURE_DEFAULT


def sms_length(text):
    return len(text)


def _render(name, date_s, time_s, sig):
    greet = f'Hi {name}, ' if name else ''
    return f'Brennan Opticians: {greet}your appointment is on {date_s} at {time_s}. {sig}'


def _name_forms(name):
    parts = name.split()
    if not parts:
        return ['']
    forms = [' '.join(parts)]
    if len(parts) > 1:
        forms.append(f'{parts[0]} {parts[-1][0]}.')
    forms.extend([parts[0], ''])
    return forms


def build_text(appt, channel, starts):
    """Returns (text, shortened_flag). For SMS, returns (None, False) if nothing fits."""
    date_s, time_s = format_date_time(starts)
    sig = _signature(appt['country'])
    forms = _name_forms((appt['customer_name'] or '').strip())
    if channel == 'email':
        return _render(forms[0], date_s, time_s, sig), False
    for index, name in enumerate(forms):
        text = _render(name, date_s, time_s, sig)
        if sms_length(text) <= SMS_MAX_CHARS:
            return text, index > 0
    return None, False


def _plan_one(appt, now):
    ident = appt['id']
    if is_cancelled(appt):
        logger.debug('skipped_cancelled id=%s', ident)
        return []
    starts = appt['starts_at'].astimezone(_UTC)
    if starts <= now:
        logger.debug('skipped_started id=%s', ident)
        return []
    channel = choose_channel(appt)
    if channel is None:
        logger.warning('no_contact id=%s', ident)
        return []
    logger.debug('channel_%s id=%s', channel, ident)

    t1 = starts - REMINDER_1_BEFORE
    t2 = starts - REMINDER_2_BEFORE
    if t2 <= now:
        slots = [now]
    elif t1 <= now:
        slots = [now, t2]
    else:
        slots = [t1, t2]

    out = []
    for candidate in slots:
        shifted, was_quiet = apply_quiet_window(candidate)
        if was_quiet:
            logger.debug('quiet_shift id=%s', ident)
        send_at = clamp_past(shifted, now, starts, ident)
        if send_at is None:
            continue
        text, shortened = build_text(appt, channel, starts)
        out_channel = channel
        if text is None:
            if not _present(appt['email']):
                logger.warning('sms_overflow_dropped id=%s', ident)
                continue
            logger.warning('sms_overflow_email_fallback id=%s', ident)
            out_channel = 'email'
            text, _ = build_text(appt, 'email', starts)
        elif shortened:
            logger.debug('sms_name_shortened id=%s', ident)
        out.append({'appointment_id': ident, 'channel': out_channel, 'send_at': send_at, 'text': text})
    return out


def plan_reminders(appointments, now):
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError('now must be a timezone-aware datetime')
    now = now.astimezone(_UTC)
    try:
        items = list(appointments)
    except TypeError:
        raise ValueError('appointments must be an iterable of dicts') from None
    reminders = []
    for appt in items:
        validate_appointment(appt)
        reminders.extend(_plan_one(appt, now))
    reminders.sort(key=lambda r: (r['send_at'], str(r['appointment_id']), r['channel']))
    sms_count = sum(1 for r in reminders if r['channel'] == 'sms')
    logger.info('planned %d reminders (sms=%d, email=%d) for %d appointments',
                len(reminders), sms_count, len(reminders) - sms_count, len(items))
    return reminders


# FILE: /private/var/folders/0q/mn9bnkzs1z3g69vnt_vj5qd80000gp/T/agent-telephone-cc-u664ngqg/tests/test_reminders.py
# NOTE: Not executed. Run from the project root with: python -m pytest tests/test_reminders.py
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from brennan_reminders import reminders as R

DUB = ZoneInfo('Europe/Dublin')
UTC = timezone.utc
EMAIL = 'test.customer@example.invalid'
PHONE = '+353000000001'
NAME = 'Test Customer'
NOW = datetime(2026, 10, 13, 9, 0, tzinfo=UTC)
STARTS = datetime(2026, 11, 5, 10, 0, tzinfo=DUB)
KEYS = {'appointment_id', 'channel', 'send_at', 'text'}


def appt(**kw):
    base = {
        'id': 'A1', 'customer_name': NAME, 'email': EMAIL, 'phone': PHONE,
        'country': 'IE', 'status': 'booked', 'starts_at': STARTS, 'optout_sms_v2': False,
    }
    base.update(kw)
    return base


def utc(*args):
    return datetime(*args, tzinfo=UTC)


def local_to_utc(*args):
    return datetime(*args, tzinfo=DUB).astimezone(UTC)


def _render_len(name):
    return len(R._render(name, '05/11/2026', '10:00', R.SIGNATURE_DEFAULT))


def test_basic_two_reminders_sorted_with_date_time_and_signature():
    res = R.plan_reminders([appt()], NOW)
    assert [r['send_at'] for r in res] == [utc(2026, 11, 3, 10), utc(2026, 11, 5, 8)]
    for r in res:
        assert r['channel'] == 'sms'
        assert '05/11/2026' in r['text'] and '10:00' in r['text']
        assert r['text'].endswith(R.SIGNATURE_DEFAULT)


def test_between_points_first_is_immediate_second_at_t2():
    now = utc(2026, 11, 3, 11)
    res = R.plan_reminders([appt()], now)
    assert [r['send_at'] for r in res] == [now, utc(2026, 11, 5, 8)]


def test_both_points_passed_sends_one_immediate():
    now = utc(2026, 11, 5, 9)
    res = R.plan_reminders([appt()], now)
    assert len(res) == 1 and res[0]['send_at'] == now


@pytest.mark.parametrize('now', [STARTS, STARTS + timedelta(hours=1)])
def test_started_appointment_gets_nothing(now):
    assert R.plan_reminders([appt()], now) == []


@pytest.mark.parametrize('status', ['cancelled', 'CANCELLED ', ' Cancelled\t'])
def test_cancelled_gets_nothing(status):
    assert R.plan_reminders([appt(status=status)], NOW) == []


def test_no_show_is_still_reminded():
    assert len(R.plan_reminders([appt(status='no_show')], NOW)) == 2


def test_phone_not_opted_out_gives_sms_only():
    res = R.plan_reminders([appt()], NOW)
    assert res and all(r['channel'] == 'sms' for r in res)


def test_opted_out_with_email_gives_email_only():
    res = R.plan_reminders([appt(optout_sms_v2=True)], NOW)
    assert res and all(r['channel'] == 'email' for r in res)


def test_opted_out_without_email_gives_nothing():
    assert R.plan_reminders([appt(optout_sms_v2=True, email=None)], NOW) == []


@pytest.mark.parametrize('phone', [None, ''])
def test_missing_phone_uses_email(phone):
    res = R.plan_reminders([appt(phone=phone)], NOW)
    assert res and all(r['channel'] == 'email' for r in res)


def test_no_phone_and_no_email_gives_nothing():
    assert R.plan_reminders([appt(phone='', email='')], NOW) == []


def test_old_opt_out_field_is_ignored():
    res = R.plan_reminders([appt(opt_out=True)], NOW)
    assert res and all(r['channel'] == 'sms' for r in res)


def test_never_both_channels_for_same_appointment():
    apps = [appt(id='A1'), appt(id='A2', optout_sms_v2=True), appt(id='A3', phone=None)]
    res = R.plan_reminders(apps, NOW)
    channels = {}
    for r in res:
        channels.setdefault(r['appointment_id'], set()).add(r['channel'])
    assert set(channels) == {'A1', 'A2', 'A3'}
    assert all(len(c) == 1 for c in channels.values())


@pytest.mark.parametrize('candidate, expected', [
    ((2026, 11, 5, 20, 59, 59), (2026, 11, 5, 20, 59, 59)),
    ((2026, 11, 5, 21, 0, 0), (2026, 11, 5, 20, 0, 0)),
    ((2026, 11, 5, 7, 59, 59), (2026, 11, 4, 20, 0, 0)),
    ((2026, 11, 5, 8, 0, 0), (2026, 11, 5, 8, 0, 0)),
])
def test_quiet_boundaries(candidate, expected):
    cand = local_to_utc(*candidate)
    res = R.plan_reminders([appt(starts_at=cand + timedelta(hours=2))], NOW)
    assert res[-1]['send_at'] == local_to_utc(*expected)


def test_immediate_inside_quiet_window_defers_to_next_0800():
    now = local_to_utc(2026, 11, 4, 22, 0)
    res = R.plan_reminders([appt(starts_at=utc(2026, 11, 6, 10))], now)
    assert len(res) == 2
    assert res[0]['send_at'] == utc(2026, 11, 5, 8)
    assert res[1]['send_at'] == utc(2026, 11, 6, 8)


def test_inside_quiet_window_drops_when_start_before_0800():
    now = local_to_utc(2026, 11, 4, 22, 0)
    assert R.plan_reminders([appt(starts_at=utc(2026, 11, 5, 7))], now) == []


def test_shifted_slot_before_now_is_clamped_to_now():
    cand = local_to_utc(2026, 11, 5, 21, 30)
    now = local_to_utc(2026, 11, 5, 20, 10)
    res = R.plan_reminders([appt(starts_at=cand + timedelta(hours=2))], now)
    assert res and res[-1]['send_at'] == now
    assert all(r['send_at'] >= now for r in res)


def test_dst_slot_0030_local_maps_to_previous_evening_2000():
    cand = datetime(2026, 10, 25, 0, 30, tzinfo=DUB).astimezone(UTC)
    assert cand == utc(2026, 10, 24, 23, 30)
    res = R.plan_reminders([appt(starts_at=cand + timedelta(hours=2))], NOW)
    assert res[-1]['send_at'] == utc(2026, 10, 24, 19)


def test_dst_ambiguous_0130_uses_first_occurrence_bst():
    first = datetime(2026, 10, 25, 1, 30, tzinfo=DUB)
    assert first.fold == 0
    assert first.astimezone(UTC) == utc(2026, 10, 25, 0, 30)
    cand = utc(2026, 10, 25, 0, 30)
    res = R.plan_reminders([appt(starts_at=cand + timedelta(hours=2))], NOW)
    assert res[-1]['send_at'] == utc(2026, 10, 24, 19)


def test_48h_across_dst_end_uses_absolute_elapsed_time():
    starts = datetime(2026, 10, 27, 10, 0, tzinfo=DUB)
    res = R.plan_reminders([appt(starts_at=starts)], NOW)
    assert res[0]['send_at'] == utc(2026, 10, 25, 10)


def test_48h_on_26_oct_displays_shifted_but_text_keeps_10_00():
    starts = datetime(2026, 10, 26, 10, 0, tzinfo=DUB)
    res = R.plan_reminders([appt(starts_at=starts)], NOW)
    assert res[0]['send_at'] == utc(2026, 10, 24, 10)
    assert res[0]['send_at'].astimezone(DUB).hour == 11
    assert '26/10/2026' in res[0]['text'] and 'at 10:00.' in res[0]['text']


def test_short_name_kept_in_full():
    res = R.plan_reminders([appt()], NOW)
    assert f'Hi {NAME}, ' in res[0]['text']


def test_long_name_uses_first_name_and_last_initial():
    n = next(n for n in range(1, 300) if _render_len('Aoife ' + 'X' * n) > 160)
    res = R.plan_reminders([appt(customer_name='Aoife ' + 'X' * n)], NOW)
    text = res[0]['text']
    assert 'Hi Aoife X., ' in text
    assert '05/11/2026' in text and '10:00' in text and len(text) <= 160


def test_name_steps_to_first_name_only():
    kb = next(k for k in range(1, 300) if _render_len('A' * k + ' Q.') > 160)
    res = R.plan_reminders([appt(customer_name='A' * kb + ' ' + 'Q' * 30)], NOW)
    text = res[0]['text']
    assert f'Hi {"A" * kb}, ' in text
    assert 'Q' * 30 not in text
    assert '05/11/2026' in text and '10:00' in text and len(text) <= 160


def test_name_drops_to_no_name_form():
    kc = next(k for k in range(1, 300) if _render_len('A' * k) > 160)
    res = R.plan_reminders([appt(customer_name='A' * kc)], NOW)
    text = res[0]['text']
    assert 'Hi ' not in text
    assert text.startswith('Brennan Opticians: your appointment is on 05/11/2026 at 10:00. ')
    assert len(text) <= 160


def test_exactly_160_kept_and_161_shortened():
    k = next(k for k in range(1, 300) if _render_len('N' * k) == 160)
    res = R.plan_reminders([appt(customer_name='N' * k)], NOW)
    assert len(res[-1]['text']) == 160
    assert f'Hi {"N" * k}, ' in res[-1]['text']
    res = R.plan_reminders([appt(customer_name='N' * (k + 1))], NOW)
    assert len(res[-1]['text']) <= 160
    assert 'N' * (k + 1) not in res[-1]['text']


@pytest.mark.parametrize('country', ['PL', 'pl', ' PL '])
def test_pl_gets_pl_signature(country):
    res = R.plan_reminders([appt(country=country)], NOW)
    assert res and all(r['text'].endswith(R.SIGNATURE_PL) for r in res)


def test_email_text_never_shortened():
    long_name = 'Q' * 200
    res = R.plan_reminders([appt(customer_name=long_name, optout_sms_v2=True)], NOW)
    assert res and all(r['channel'] == 'email' and long_name in r['text'] for r in res)


@pytest.mark.parametrize('country', ['IE', 'PL'])
def test_non_gsm_signature_stays_within_limit(country):
    name = 'Siobhán Ní Dhuibhir ' + 'Ó' * 30
    res = R.plan_reminders([appt(customer_name=name, country=country)], NOW)
    assert res
    for r in res:
        assert len(r['text']) <= 160
        assert '05/11/2026' in r['text'] and '10:00' in r['text']


def test_naive_now_raises():
    with pytest.raises(ValueError):
        R.plan_reminders([appt()], datetime(2026, 10, 13, 9, 0))


def test_naive_starts_at_raises():
    with pytest.raises(ValueError):
        R.plan_reminders([appt(starts_at=datetime(2026, 11, 5, 10, 0))], NOW)


def test_missing_phone_key_raises_without_email_value():
    a = appt()
    del a['phone']
    with pytest.raises(ValueError) as exc:
        R.plan_reminders([a], NOW)
    assert EMAIL not in str(exc.value)


def test_bad_optout_raises_without_email_value():
    with pytest.raises(ValueError) as exc:
        R.plan_reminders([appt(optout_sms_v2='yes')], NOW)
    assert EMAIL not in str(exc.value)


def test_ties_ordered_by_id_and_output_sorted():
    res = R.plan_reminders([appt(id='B2', customer_name='Test Two'), appt(id='A1')], NOW)
    keys = [r['send_at'] for r in res]
    assert keys == sorted(keys)
    tie = [r['appointment_id'] for r in res if r['send_at'] == utc(2026, 11, 5, 8)]
    assert tie == ['A1', 'B2']


def test_invariants_and_no_pii_in_logs(caplog):
    caplog.set_level(logging.DEBUG, logger='brennan.reminders')
    cases = [
        ([appt(), appt(id='C3', optout_sms_v2=True), appt(id='D4', status='cancelled'),
          appt(id='E5', phone=None, email='')], NOW),
        ([appt(id='F6', customer_name='Q' * 200)], local_to_utc(2026, 11, 4, 22, 0)),
    ]
    for apps, now in cases:
        res = R.plan_reminders(apps, now)
        for r in res:
            assert set(r) == KEYS
            assert r['send_at'].utcoffset() == timedelta(0)
            assert r['send_at'] >= now
    for rec in caplog.records:
        msg = rec.getMessage()
        assert EMAIL not in msg
        assert NAME not in msg
    assert EMAIL not in caplog.text
</br>