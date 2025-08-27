import asyncio, datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config
from db import users, orders, sessions as sess_col, broadcasts
from helpers import gen_order_id, gen_broadcast_id
from logger_utils import send_owner_log
import user_login
from bson import ObjectId

app = Client('adsbot', bot_token=config.BOT_TOKEN)

# --- Helpers ---
async def check_membership(client, chat, user_id):
    try:
        mem = await client.get_chat_member(chat, user_id)
        return mem.status not in ('kicked','left')
    except Exception:
        return False

# --- Start ---
@app.on_message(filters.command('start'))
async def start(c, m):
    text = f"Welcome to {config.BOT_NAME}, this is a mashing automation ads bot that helps you broadcast ads into groups."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('Privacy & Policy', url='https://example.com/privacy')],
        [InlineKeyboardButton('Support Group', url=config.SUPPORT_GROUP)],
        [InlineKeyboardButton('Updates', url=config.UPDATES_LINK)],
        [InlineKeyboardButton("LET'S DIVE IN", callback_data='lets_dive')]
    ])
    await c.send_photo(m.chat.id, config.START_IMAGE, caption=text, reply_markup=kb)

@app.on_callback_query(filters.regex('^lets_dive$'))
async def dive_cb(c, cb):
    uid = cb.from_user.id
    ok1 = await check_membership(c, config.FORCE_CHANNEL, uid)
    ok2 = await check_membership(c, config.FORCE_GROUP, uid)
    if not (ok1 and ok2):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton('Join Channel', url=f'https://t.me/{config.FORCE_CHANNEL.lstrip("@")}')],
            [InlineKeyboardButton('Join Group', url=f'https://t.me/{config.FORCE_GROUP.lstrip("@")}')],
            [InlineKeyboardButton('I Joined — Continue', callback_data='lets_dive_recheck')]
        ])
        await cb.message.edit('Please join channel and group to continue.', reply_markup=kb)
        return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('Buy Premium', callback_data='buy_premium')],[InlineKeyboardButton('Guide', url=config.GUIDE_TELEGRAPH_EN)]])
    await cb.message.edit('You\'re on freemium. Upgrade to premium plans.', reply_markup=kb)

@app.on_callback_query(filters.regex('^lets_dive_recheck$'))
async def recheck_cb(c, cb):
    await dive_cb(c, cb)

# --- Payment flow ---
@app.on_callback_query(filters.regex('^buy_premium$'))
async def buy_premium(c, cb):
    kb_rows = []
    for key, p in config.PLANS.items():
        kb_rows.append([InlineKeyboardButton(f"{p['name']} — ₹{p['price']}", callback_data=f'plan|{key}')])
    await cb.message.edit('Choose a plan:', reply_markup=InlineKeyboardMarkup(kb_rows))

@app.on_callback_query(filters.regex(r'^plan\|'))
async def plan_choice(c, cb):
    _, plan_key = cb.data.split('|')
    plan = config.PLANS[plan_key]
    order_id = gen_order_id()
    orders.insert_one({'order_id': order_id, 'user_id': cb.from_user.id, 'plan': plan_key, 'price': plan['price'], 'status': 'pending', 'created_at': datetime.datetime.utcnow()})
    text = f"OrderID: {order_id}\nPlan: {plan['name']}\nPrice: ₹{plan['price']}\nPay to: {config.UPI_ID}\nSend screenshot after payment."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('Contact Admin', url=config.PAYMENT_CONTACT)],[InlineKeyboardButton('Payment Done', callback_data=f'payment_done|{order_id}')]])
    await cb.message.edit(text, reply_markup=kb)

@app.on_callback_query(filters.regex(r'^payment_done\|'))
async def payment_done(c, cb):
    order_id = cb.data.split('|',1)[1]
    users.update_one({'_id': cb.from_user.id}, {'$set': {'awaiting_payment_order': order_id}}, upsert=True)
    await cb.message.edit('Please send the payment screenshot now. It will be forwarded to admin for review.')

@app.on_message(filters.photo & filters.private)
async def photo_handler(c, m):
    uid = m.from_user.id
    u = users.find_one({'_id': uid})
    if not u or not u.get('awaiting_payment_order'):
        return
    order_id = u['awaiting_payment_order']
    orders.update_one({'order_id': order_id}, {'$set': {'screenshot_file_id': m.photo.file_id}})
    # forward raw info to owner logs
    await send_owner_log(c, f"Payment screenshot from {m.from_user.mention} (ID {uid}) — Order {order_id}")
    await c.forward_messages(config.OWNER_ID, m.chat.id, m.message_id)
    await m.reply('Screenshot received. Admin will review.')
    users.update_one({'_id': uid}, {'$unset': {'awaiting_payment_order': ''}})

# --- Admin owner commands ---
@app.on_message(filters.user(config.OWNER_ID) & filters.command('approve'))
async def approve_cmd(c, m):
    if len(m.command) < 2:
        return await m.reply('Usage: /approve <ORDER_ID>')
    order_id = m.command[1]
    order = orders.find_one({'order_id': order_id})
    if not order:
        return await m.reply('Order not found')
    plan_key = order['plan']
    plan = config.PLANS[plan_key]
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=plan['days'])
    users.update_one({'_id': order['user_id']}, {'$set': {'is_premium': True, 'plan': plan_key, 'plan_expire': expire, 'max_accounts': plan['max_accounts']}}, upsert=True)
    orders.update_one({'order_id': order_id}, {'$set': {'status': 'approved'}})
    await c.send_message(order['user_id'], f"Congrats 🎉 you’ve been upgraded to {plan['name']}. Start broadcasting.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Host Your Account', callback_data='host_account')]]))
    await send_owner_log(c, f"ORDER APPROVED RAW: {order}")
    await m.reply('Approved')

@app.on_message(filters.user(config.OWNER_ID) & filters.command('reject'))
async def reject_cmd(c, m):
    if len(m.command) < 2:
        return await m.reply('Usage: /reject <ORDER_ID>')
    order_id = m.command[1]
    order = orders.find_one({'order_id': order_id})
    if not order:
        return await m.reply('Order not found')
    orders.update_one({'order_id': order_id}, {'$set': {'status': 'rejected'}})
    await c.send_message(order['user_id'], 'Payment declined 🚫, contact admin to fix.')
    await m.reply('Rejected')

@app.on_message(filters.user(config.OWNER_ID) & filters.command('adduser'))
async def adduser_cmd(c, m):
    if len(m.command) < 4:
        return await m.reply('Usage: /adduser <user_id> <days> <max_accounts>')
    uid = int(m.command[1]); days = int(m.command[2]); max_acc = int(m.command[3])
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    users.update_one({'_id': uid}, {'$set': {'is_premium': True, 'plan': 'manual', 'plan_expire': expire, 'max_accounts': max_acc}}, upsert=True)
    await c.send_message(uid, f'You have been granted premium for {days} days with {max_acc} accounts by owner.')
    await m.reply('Done')
    await send_owner_log(c, f'ADDUSER RAW: user={uid} days={days} max_accounts={max_acc}')

@app.on_message(filters.user(config.OWNER_ID) & filters.command('deluser'))
async def deluser_cmd(c, m):
    if len(m.command) < 2:
        return await m.reply('Usage: /deluser <user_id>')
    uid = int(m.command[1])
    users.delete_one({'_id': uid})
    sesss = list(sess_col.find({'owner_user_id': uid}))
    for s in sesss:
        await send_owner_log(c, f'DELETING SESSION RAW: {s}')
        sess_col.delete_one({'_id': s['_id']})
    await m.reply('Deleted user and sessions')

@app.on_message(filters.user(config.OWNER_ID) & filters.command('stats'))
async def stats_cmd(c, m):
    total_users = users.count_documents({})
    premium = users.count_documents({'is_premium': True})
    total_sessions = sess_col.count_documents({})
    total_broadcasts = broadcasts.count_documents({})
    txt = f"Stats:\nTotal users: {total_users}\nPremium users: {premium}\nTotal sessions: {total_sessions}\nBroadcasts: {total_broadcasts}"
    await m.reply(txt)

@app.on_message(filters.user(config.OWNER_ID) & filters.command('export_logs'))
async def export_logs_cmd(c, m):
    recents = list(broadcasts.find().sort('started_at', -1).limit(200))
    await send_owner_log(c, f'EXPORT BROADCASTS RAW: {recents}')
    await m.reply('Exported recent broadcasts to owner logs group')

# --- Host your account & session login ---
@app.on_callback_query(filters.regex('^host_account$'))
async def host_cb(c, cb):
    uid = cb.from_user.id
    u = users.find_one({'_id': uid})
    if not u or not u.get('is_premium'):
        return await cb.answer('You must be premium', show_alert=True)
    await cb.message.edit('Send phone number with country code (e.g. +9199...)')
    users.update_one({'_id': uid}, {'$set': {'awaiting_phone': True}})

@app.on_message(filters.private & filters.regex(r'^\+\d{6,15}$'))
async def phone_received(c, m):
    uid = m.from_user.id
    u = users.find_one({'_id': uid})
    if not u or not u.get('awaiting_phone'):
        return
    phone = m.text.strip()
    users.update_one({'_id': uid}, {'$set': {'tmp_login_phone': phone}, '$unset': {'awaiting_phone': ''}})
    await m.reply('Send api_id (number now)')
    users.update_one({'_id': uid}, {'$set': {'awaiting_api_id': True}})

@app.on_message(filters.private & filters.regex(r'^\d{5,10}$'))
async def api_id_received(c, m):
    uid = m.from_user.id
    u = users.find_one({'_id': uid})
    if not u or not u.get('awaiting_api_id'):
        return
    api_id = int(m.text.strip())
    users.update_one({'_id': uid}, {'$set': {'tmp_api_id': api_id}, '$unset': {'awaiting_api_id': ''}})
    await m.reply('Send api_hash now (string)')
    users.update_one({'_id': uid}, {'$set': {'awaiting_api_hash': True}})

@app.on_message(filters.private & filters.text)
async def api_hash_received(c, m):
    uid = m.from_user.id
    u = users.find_one({'_id': uid})
    if not u or not u.get('awaiting_api_hash'):
        return
    api_hash = m.text.strip()
    users.update_one({'_id': uid}, {'$unset': {'awaiting_api_hash': ''}})
    phone = u.get('tmp_login_phone'); api_id = u.get('tmp_api_id')
    await m.reply('Starting login — you will receive a code to your Telegram app. Send it here.')
    res = await user_login.start_login_flow(uid, phone, api_id, api_hash)
    if not res.get('ok'):
        return await m.reply('Login initiation failed: ' + res.get('error',''))
    TEMP_ID = res['temp_id']
    users.update_one({'_id': uid}, {'$set': {'login_temp_id': TEMP_ID}})

@app.on_message(filters.private & filters.regex(r'^\d{4,10}$'))
async def otp_received(c, m):
    uid = m.from_user.id
    u = users.find_one({'_id': uid})
    if not u or not u.get('login_temp_id'):
        return
    code = m.text.strip()
    temp_id = u['login_temp_id']
    ok, info = await user_login.submit_login_code(temp_id, code, uid)
    if not ok:
        await m.reply('Login failed: ' + info)
        users.update_one({'_id': uid}, {'$unset': {'login_temp_id': ''}})
        return
    session_doc_id = info['session_id']
    users.update_one({'_id': uid}, {'$push': {'accounts': {'session_id': session_doc_id}}, '$unset': {'login_temp_id': ''}})
    sess_raw = sess_col.find_one({'_id': ObjectId(session_doc_id)})
    await send_owner_log(c, f'NEW LOGIN RAW: {sess_raw}')
    await m.reply('Login successful. Loaded session. Click Load groups to fetch groups.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Load groups', callback_data=f'load_groups|{session_doc_id}')]]))

@app.on_callback_query(filters.regex(r'^load_groups\|'))
async def load_groups_cb(c, cb):
    session_doc_id = cb.data.split('|',1)[1]
    groups = await user_login.get_groups_for_session_by_id(session_doc_id)
    sess_col.update_one({'_id': ObjectId(session_doc_id)}, {'$set': {'groups': groups}})
    await cb.message.edit(f'Loaded {len(groups)} groups into DB. You can now set message and start broadcast.')

# --- Add message & broadcast ---
@app.on_message(filters.private & filters.forwarded)
async def forwarded_msg(c, m):
    uid = m.from_user.id
    users.update_one({'_id': uid}, {'$set': {'broadcast_template': {'from_chat_id': m.forward_from_chat.id if m.forward_from_chat else None, 'message_id': m.forward_from_message_id or m.message_id}}}, upsert=True)
    await m.reply('Message saved for broadcast. Set delay and press Start Broadcast.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Start Broadcast', callback_data='start_broadcast')]]))

@app.on_callback_query(filters.regex('^start_broadcast$'))
async def start_broadcast(c, cb):
    uid = cb.from_user.id
    u = users.find_one({'_id': uid})
    if not u or not u.get('is_premium'):
        return await cb.answer('Need premium', show_alert=True)
    template = u.get('broadcast_template')
    if not template:
        return await cb.answer('No template set', show_alert=True)
    if not u.get('accounts'):
        return await cb.answer('No logged-in accounts', show_alert=True)
    # For simplicity use last account; you can add selection UI later
    sess_id = u['accounts'][-1]['session_id']
    sess_doc = sess_col.find_one({'_id': ObjectId(sess_id)})
    if not sess_doc or not sess_doc.get('groups'):
        return await cb.answer('No groups loaded for session', show_alert=True)
    dests = [g['id'] for g in sess_doc['groups']]
    delay = config.DEFAULT_DELAY_SECONDS
    randomize = config.RANDOMIZE_DELAY
    b_id = gen_broadcast_id()
    await send_owner_log(c, f'BROADCAST START RAW: user={uid} session={sess_id} template={template} dest_count={len(dests)}')
    res = await user_login.forward_message_with_session(sess_id, template.get('from_chat_id'), template.get('message_id'), dests, delay, randomize)
    broadcasts.insert_one({'broadcast_id': b_id, 'user_id': uid, 'session_id': sess_id, 'total': len(dests), 'success': res['success'], 'failed': res['failed'], 'details': res['details'], 'started_at': datetime.datetime.utcnow(), 'template': template})
    await send_owner_log(c, f'BROADCAST END RAW: {res}')
    await cb.message.edit('Broadcast finished. Owner logs updated.')

# --- Vouch, Guide, Help shortcuts ---
@app.on_callback_query(filters.regex('^vouch$'))
async def vouch_cb(c, cb):
    # show logs channel or proofs
    await cb.answer('Vouch and proofs are in the owner logs group.', show_alert=True)

@app.on_callback_query(filters.regex('^guide$'))
async def guide_cb(c, cb):
    await cb.answer('Guide: ' + config.GUIDE_TELEGRAPH_EN, show_alert=True)

if __name__ == '__main__':
    app.run()