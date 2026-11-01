"""Default reference and learner-specific FSRS state curves, without invented observations."""
from datetime import datetime, timedelta, timezone
from fsrs import Card, Rating
from sqlalchemy import text
from scheduler import FSRS


def build(c, stamp, answers):
    stamp = stamp.astimezone(timezone.utc)
    reference, _ = FSRS.review_card(Card(card_id=1), Rating.Good, review_datetime=stamp)
    cards = []
    # Exclude test skips and reset/orphan states from the personal prediction.
    for row in c.execute(text('''SELECT m.card_json FROM memory_states m JOIN answers a
        ON a.id=m.last_answer AND a.knowledge_id=m.knowledge_id
        ''' )).scalars():
        card = Card.from_json(row)
        if card.last_review and card.last_review <= stamp:
            cards.append(card)
    points = []
    for step in range(121):
        day = step / 4
        default = FSRS.get_card_retrievability(reference, current_datetime=stamp + timedelta(days=day))
        personal = sum(FSRS.get_card_retrievability(card, current_datetime=card.last_review + timedelta(days=day)) for card in cards) / len(cards) if cards else default
        points.append(dict(day=day, default=default, personal=personal))
    # Genuine delayed tests, grouped by elapsed time; same-day repetition is excluded.
    bins = [dict(start=a, end=b, count=0, successes=0, elapsed=0) for a,b in [(1,3),(3,7),(7,14),(14,31),(31,100000)]]
    previous = {}
    for a in answers:
        at = datetime.fromisoformat(a['created_at']).astimezone(timezone.utc)
        if at > stamp:
            continue
        old = previous.get(a['knowledge_id'])
        previous[a['knowledge_id']] = at
        if old is None:
            continue
        gap = (at-old).total_seconds()/86400
        for bucket in bins:
            if bucket['start'] <= gap < bucket['end']:
                bucket['count'] += 1
                bucket['successes'] += bool(a['correct'] and not a['revealed'] and not a['failed'] and a['rating']=='clear')
                bucket['elapsed'] += gap
                break
    observations = [dict(day=b['elapsed']/b['count'], rate=b['successes']/b['count'], count=b['count']) for b in bins if b['count']]
    return dict(algorithm='FSRS-6', target_retention=FSRS.desired_retention,
                parameter_source='default', mode='personal_prediction' if cards else 'default_prediction',
                items=len(cards), delayed_samples=sum(b['count'] for b in bins),
                points=points, observations=observations, updated_at=stamp.isoformat())
