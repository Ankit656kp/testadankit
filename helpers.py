import random, string

def gen_order_id():
    return 'ORD_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def gen_broadcast_id():
    return 'BRC_' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))