"""Terminal demo for Nova Brain V3. Nothing is actually sent or booked."""
import copy
import json
import shlex
from brain import (BUSINESS, SEED_LEADS, decide_next_action, apply_extraction,
                   new_session, load_sessions, save_sessions)

HELP = '''
/users                  list customers
/switch rachel          switch customer (sarah / rachel / james)
/show                   show current lead and review state
/inquiry                use that customer's stored initial enquiry
/start                  generate a new outreach DRAFT (never sent)
/approve                simulate approval of pending draft only
/reject                 discard pending draft
/new alex "Alex Lee"     create a new blank customer
/restart                reset ONLY the active customer
/quit                   exit (all customer sessions are saved)
Anything else is a customer message for the selected customer.
'''


def show_users(db):
    for key, session in db['sessions'].items():
        lead = session['lead']
        pointer = '*' if db['active'] == key else ' '
        print(f"{pointer} {key:12} {lead.get('name', ''):24} "
              f"{lead.get('lead_status', 'new'):22} "
              f"{len(session['conversation'])} messages")


def handle_turn(db, message=None, outreach=False):
    session = db['sessions'][db['active']]
    if message is not None:
        session['conversation'].append({'role': 'customer', 'content': message})
    try:
        decision = decide_next_action(
            BUSINESS, session['lead'], [] if outreach else session['conversation']
        )
    except Exception as exc:
        if message is not None:
            session['conversation'].pop()
        print(f'Nova could not decide: {exc}')
        return
    session['lead'] = apply_extraction(session['lead'], decision)
    # Preserve an existing unanswered human-review request across later turns.
    if decision['review_status'] == 'pending':
        session['review_status'] = 'pending'
        session['escalation'] = decision['escalation']
    elif session.get('review_status') != 'pending':
        session['review_status'] = 'not_required'
        session['escalation'] = None
    print(json.dumps(decision, indent=2, ensure_ascii=False))

    if decision['requires_human_approval'] and decision['next_action'] in (
        'draft_outreach', 'recommend_consultation'
    ):
        session['pending_draft'] = decision['message']
        print('\nDRAFT PENDING: use /approve to simulate approval. No real send or booking.')
    elif decision['next_action'] == 'escalate_to_human':
        print('\nESCALATION NOT ROUTED: JSON request only; team must create review task.')
    elif decision['message']:
        session['conversation'].append({
            'role': 'agent', 'content': decision['message'], 'delivery': 'simulated'
        })
    save_sessions(db)


def main():
    db = load_sessions()
    save_sessions(db)
    print('Nova Brain V3 — multi-customer demo')
    print('Type /help for commands. NO messages or bookings are sent.')
    show_users(db)
    while True:
        active = db['active']
        first = db['sessions'][active]['lead'].get('name', active).split()[0]
        try:
            text = input(f'\n{first}> ').strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not text:
            continue
        if text == '/help':
            print(HELP)
        elif text == '/users':
            show_users(db)
        elif text.startswith('/switch '):
            key = text.split(maxsplit=1)[1].lower()
            if key in db['sessions']:
                db['active'] = key
                print('Switched to', db['sessions'][key]['lead'].get('name'))
            else:
                print('Unknown customer; type /users')
        elif text == '/show':
            print(json.dumps(db['sessions'][db['active']], indent=2, ensure_ascii=False))
        elif text == '/inquiry':
            initial = db['sessions'][db['active']]['lead'].get('initial_message')
            if initial:
                print('Customer:', initial)
                handle_turn(db, message=initial)
            else:
                print('No saved initial enquiry. Type a customer message instead.')
        elif text == '/start':
            handle_turn(db, outreach=True)
        elif text == '/approve':
            s = db['sessions'][db['active']]
            if not s['pending_draft']:
                print('No draft is waiting for approval.')
            else:
                s['conversation'].append({
                    'role': 'agent', 'content': s['pending_draft'],
                    'delivery': 'approved_simulation_only'
                })
                s['pending_draft'] = None
                print('Approved in the demo. No real message or booking was sent.')
        elif text == '/reject':
            db['sessions'][db['active']]['pending_draft'] = None
            print('Pending draft discarded.')
        elif text == '/restart':
            seed = SEED_LEADS.get(active)
            if seed:
                db['sessions'][active] = new_session(seed)
            else:
                old = db['sessions'][active]['lead']
                db['sessions'][active] = new_session({
                    'id': active, 'name': old.get('name', active),
                    'subject': None, 'lead_status': 'new', 'intent_confirmed': False
                })
            print(f'Reset {active} only. Other customers were preserved.')
        elif text.startswith('/new '):
            try:
                _, key, name = shlex.split(text)
                key = key.lower()
                if key in db['sessions']:
                    print('That customer ID already exists.')
                elif not key.replace('_', '').isalnum():
                    print('Use a simple ID with letters, digits or underscores.')
                else:
                    db['sessions'][key] = new_session({
                        'id': key, 'name': name, 'subject': None,
                        'lead_status': 'new', 'intent_confirmed': False
                    })
                    db['active'] = key
                    print('Created:', name)
            except ValueError:
                print('Use: /new alex "Alex Lee"')
        elif text == '/quit':
            break
        elif text.startswith('/'):
            print('Unknown command. Type /help.')
        else:
            handle_turn(db, message=text)
        save_sessions(db)
    save_sessions(db)
    print('All local sessions saved.')


if __name__ == '__main__':
    main()
