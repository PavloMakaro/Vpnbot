import json
import os
import threading
import time
import datetime
import uuid

# Configuration
data_dir = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(data_dir, 'users.json')
CONFIGS_FILE = os.path.join(data_dir, 'configs.json')
PAYMENTS_FILE = os.path.join(data_dir, 'payments.json')

class Database:
    def __init__(self):
        self.users_lock = threading.Lock()
        self.configs_lock = threading.Lock()
        self.payments_lock = threading.Lock()
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        for f in [USERS_FILE, CONFIGS_FILE, PAYMENTS_FILE]:
            if not os.path.exists(f):
                with open(f, 'w', encoding='utf-8') as file:
                    json.dump({}, file)

    def _load_json(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_json(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # --- USER METHODS ---
    def get_user(self, user_id):
        with self.users_lock:
            users = self._load_json(USERS_FILE)
            return users.get(str(user_id))

    def create_user(self, user_id, username, first_name, referred_by=None):
        with self.users_lock:
            users = self._load_json(USERS_FILE)
            uid = str(user_id)
            if uid not in users:
                users[uid] = {
                    'balance': 0,
                    'subscription_end': None,
                    'referred_by': referred_by,
                    'username': username,
                    'first_name': first_name,
                    'referrals_count': 0,
                    'used_configs': []
                }
                # Referral logic
                if referred_by and referred_by in users:
                    users[referred_by]['referrals_count'] = users[referred_by].get('referrals_count', 0) + 1
                    users[referred_by]['balance'] = users[referred_by].get('balance', 0) + 25

                # New User Bonus (REFERRAL_BONUS_NEW_USER = 50)
                users[uid]['balance'] = 50

                self._save_json(USERS_FILE, users)
                return users[uid]
            return users[uid]

    def update_user_balance(self, user_id, amount):
        with self.users_lock:
            users = self._load_json(USERS_FILE)
            uid = str(user_id)
            if uid in users:
                users[uid]['balance'] = users[uid].get('balance', 0) + amount
                self._save_json(USERS_FILE, users)
                return True
            return False

    def get_subscription_days_left(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return 0
        sub_end = user.get('subscription_end')
        if not sub_end:
            return 0
        try:
            end_date = datetime.datetime.strptime(sub_end, '%Y-%m-%d %H:%M:%S')
            now = datetime.datetime.now()
            if end_date <= now:
                return 0
            return (end_date - now).days
        except ValueError:
            return 0

    def add_subscription_days(self, user_id, days):
        with self.users_lock:
            users = self._load_json(USERS_FILE)
            uid = str(user_id)
            if uid in users:
                current_end = users[uid].get('subscription_end')
                if current_end:
                    try:
                        end_dt = datetime.datetime.strptime(current_end, '%Y-%m-%d %H:%M:%S')
                        if end_dt < datetime.datetime.now():
                            end_dt = datetime.datetime.now()
                    except ValueError:
                        end_dt = datetime.datetime.now()
                else:
                    end_dt = datetime.datetime.now()

                new_end = end_dt + datetime.timedelta(days=days)
                users[uid]['subscription_end'] = new_end.strftime('%Y-%m-%d %H:%M:%S')
                self._save_json(USERS_FILE, users)
                return new_end
            return None

    # --- CONFIG METHODS ---
    def get_available_config(self, period):
        with self.configs_lock:
            configs = self._load_json(CONFIGS_FILE)
            if period not in configs:
                return None
            for config in configs[period]:
                if not config.get('used', False):
                    return config
            return None

    def mark_config_used(self, period, config_link):
        with self.configs_lock:
            configs = self._load_json(CONFIGS_FILE)
            if period in configs:
                for config in configs[period]:
                    if config['link'] == config_link:
                        config['used'] = True
                        self._save_json(CONFIGS_FILE, configs)
                        return True
            return False

    def assign_config_to_user(self, user_id, config, period_key, period_days):
        with self.users_lock:
            users = self._load_json(USERS_FILE)
            uid = str(user_id)
            if uid in users:
                if 'used_configs' not in users[uid]:
                    users[uid]['used_configs'] = []

                used_config = {
                    'config_name': config['name'],
                    'config_link': config['link'],
                    'config_code': config.get('code', ''),
                    'period': period_key,
                    'days': period_days,
                    'issue_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                users[uid]['used_configs'].append(used_config)
                self._save_json(USERS_FILE, users)
                return used_config
            return None

    def get_user_configs(self, user_id):
        user = self.get_user(user_id)
        return user.get('used_configs', []) if user else []

    def add_config(self, period, link):
        with self.configs_lock:
            configs = self._load_json(CONFIGS_FILE)
            if period not in configs:
                configs[period] = []

            new_config = {
                'name': f"Config_{period}_{len(configs[period]) + 1}",
                'link': link,
                'used': False,
                'added_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            configs[period].append(new_config)
            self._save_json(CONFIGS_FILE, configs)
            return new_config

    def get_all_configs(self):
        with self.configs_lock:
            return self._load_json(CONFIGS_FILE)

    # --- PAYMENT METHODS ---
    def create_payment_record(self, payment_id, user_id, amount, method='yookassa'):
        with self.payments_lock:
            payments = self._load_json(PAYMENTS_FILE)
            payments[payment_id] = {
                'user_id': str(user_id),
                'amount': amount,
                'status': 'pending',
                'method': method,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'balance_topup'
            }
            self._save_json(PAYMENTS_FILE, payments)

    def get_pending_payments(self):
        with self.payments_lock:
            payments = self._load_json(PAYMENTS_FILE)
            return {pid: p for pid, p in payments.items() if p['status'] == 'pending'}

    def confirm_payment(self, payment_id):
        with self.payments_lock:
            payments = self._load_json(PAYMENTS_FILE)
            if payment_id in payments:
                payments[payment_id]['status'] = 'confirmed'
                self._save_json(PAYMENTS_FILE, payments)
                return payments[payment_id]
            return None

db = Database()
