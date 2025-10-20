def send_config_to_user(user_id, period, username, first_name):
    user_info = users_db.get(str(user_id), {})
    
    # 1. Сначала ищем, был ли уже выдан конфиг для этого периода
    existing_config_data = get_user_config_for_period(user_id, period)

    if existing_config_data:
        # Конфиг уже был выдан, отправляем его повторно
        config_to_send = existing_config_data
        is_new_config = False
    else:
        # Конфиг не был выдан, ищем новый доступный
        new_config = get_available_config(period)
        if not new_config:
            return False, "Нет доступных конфигов для этого периода"
        
        mark_config_used(period, new_config['link']) # Отмечаем новый конфиг как использованный
        
        config_to_send = {
            'config_name': new_config.get('name', f"Config for {first_name}"),
            'config_link': new_config['link'],
            'config_code': new_config.get('code', new_config['link']), 
            'period': period,
            'issue_date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': f"{first_name} (@{username})"
        }
        
        if 'used_configs' not in user_info:
            user_info['used_configs'] = []
        user_info['used_configs'].append(config_to_send)
        users_db[str(user_id)] = user_info # Обновляем users_db
        save_data('users.json', users_db)
        is_new_config = True
    
    config_name_display = config_to_send.get('config_name', f"VPN {SUBSCRIPTION_PERIODS[period]['days']} дней")
    
    try:
        message_text = (f"🔐 **Ваш VPN конфиг** " + ("(НОВЫЙ)" if is_new_config else "(повторно выдан)") + "\n\n"
                        f"👤 **Имя:** {config_name_display}\n"
                        f"📅 **Период:** {SUBSCRIPTION_PERIODS[period]['days']} дней\n"
                        f"🔗 **Ссылка на конфиг:** `{config_to_send['config_link']}`\n\n"
                        f"💾 _Сохраните этот конфиг для использования_")
        
        bot.send_message(user_id, message_text, parse_mode='Markdown')
        return True, config_to_send
    except Exception as e:
        print(f"Error sending config to user {user_id}: {e}")
        return False, f"Ошибка отправки конфига: {e}"
