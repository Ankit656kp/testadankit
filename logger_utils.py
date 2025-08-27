import config

async def send_owner_log(client, text):
    try:
        if config.OWNER_LOGS_GROUP:
            await client.send_message(config.OWNER_LOGS_GROUP, text, disable_web_page_preview=True)
        await client.send_message(config.OWNER_ID, text, disable_web_page_preview=True)
    except Exception as e:
        print('Failed to send owner log:', e)