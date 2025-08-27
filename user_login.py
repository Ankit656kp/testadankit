import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from bson import ObjectId
import config
from db import sessions

# temp storage
TEMP = {}

async def start_login_flow(user_id, phone, api_id, api_hash):
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        await client.send_code_request(phone)
    except Exception as e:
        await client.disconnect()
        return {'ok': False, 'error': str(e)}
    temp_id = f'tmp_{user_id}_{phone}_{api_id}'
    TEMP[temp_id] = {'client': client, 'phone': phone, 'api_id': api_id, 'api_hash': api_hash}
    return {'ok': True, 'temp_id': temp_id}

async def submit_login_code(temp_id, code, owner_user_id):
    obj = TEMP.get(temp_id)
    if not obj:
        return False, 'session expired or not found'
    client = obj['client']
    try:
        await client.sign_in(code=code, phone=obj['phone'])
    except PhoneCodeInvalidError:
        return False, 'invalid code'
    except SessionPasswordNeededError:
        await client.disconnect()
        TEMP.pop(temp_id, None)
        return False, '2FA required. Cannot continue.'
    # export string session
    string_sess = StringSession.save(client.session)
    sess_doc = {
        'owner_user_id': owner_user_id,
        'phone': obj['phone'],
        'api_id': obj['api_id'],
        'api_hash': obj['api_hash'],
        'string_session': string_sess,
    }
    res = sessions.insert_one(sess_doc)
    await client.disconnect()
    TEMP.pop(temp_id, None)
    return True, {'session_id': str(res.inserted_id)}

async def get_groups_for_session_by_id(session_id):
    from bson import ObjectId
    doc = sessions.find_one({'_id': ObjectId(session_id)})
    if not doc:
        return []
    client = TelegramClient(StringSession(doc['string_session']), doc['api_id'], doc['api_hash'])
    await client.connect()
    groups = []
    async for d in client.iter_dialogs():
        if d.is_group or d.is_channel:
            groups.append({'id': d.id, 'title': d.title})
    await client.disconnect()
    return groups

async def forward_message_with_session(session_id, from_chat_id, message_id, dest_ids, delay_seconds, randomize=False):
    from bson import ObjectId
    doc = sessions.find_one({'_id': ObjectId(session_id)})
    if not doc:
        return {'success':0,'failed':len(dest_ids),'details':[{'error':'session not found'}]}
    client = TelegramClient(StringSession(doc['string_session']), doc['api_id'], doc['api_hash'])
    await client.connect()
    success = 0; failed = 0; details = []
    import random, asyncio
    for dest in dest_ids:
        try:
            if from_chat_id:
                await client.forward_messages(entity=dest, messages=message_id, from_peer=from_chat_id)
            else:
                msg = await client.get_messages('me', ids=message_id)
                await client.send_message(dest, msg)
            success += 1
            details.append({'dest': dest, 'status': 'ok'})
        except Exception as e:
            failed += 1
            details.append({'dest': dest, 'status': str(e)})
        d = delay_seconds
        if randomize:
            d = delay_seconds + random.uniform(0, delay_seconds*0.6)
        await asyncio.sleep(d)
    await client.disconnect()
    return {'success': success, 'failed': failed, 'details': details}