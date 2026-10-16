---
name: telegram-admin
description: Администрирование Telegram-каналов и групп через Bot API — закрепы, топики, модерация, права, приглашения. Активируется на: закрепи, создай топик, забань, права бота, пригласительная ссылка.
triggers:
  - закрепи
  - создай топик
  - модерация
  - права бота
  - пригласительная ссылка
---

# Telegram Admin — управление каналом и группой

Администрирование через Bot API. Все вызовы идут на `https://api.telegram.org/bot<TOKEN>/<метод>`.

## Перед работой

1. Бот должен быть админом в чате
2. У него должны быть нужные права — их выдают вручную в настройках чата
3. Проверить права: `getChatMember` с `user_id` бота

```bash
curl -s "https://api.telegram.org/bot$TOKEN/getChatMember?chat_id=$CHAT&user_id=$BOT_ID" | python3 -m json.tool
```

**Токены агентов** лежат в `~/.openclaw/openclaw.json` → `channels.telegram.accounts.<агент>.botToken`. Не печатать их в чат и не подставлять в сообщения.

## Закреп

```bash
# закрепить без уведомления
curl -s "https://api.telegram.org/bot$TOKEN/pinChatMessage" \
  -d chat_id=$CHAT -d message_id=$MSG -d disable_notification=true

# снять закреп
curl -s "https://api.telegram.org/bot$TOKEN/unpinChatMessage" -d chat_id=$CHAT -d message_id=$MSG

# снять все закрепы
curl -s "https://api.telegram.org/bot$TOKEN/unpinAllChatMessages" -d chat_id=$CHAT
```

Закреплять с уведомлением — только по-настоящему важное. Каждый закреп с уведомлением стоит части подписчиков.

## Топики (форумные группы)

Работают только в группах с включённым режимом «Темы».

```bash
# создать топик
curl -s "https://api.telegram.org/bot$TOKEN/createForumTopic" \
  -d chat_id=$CHAT -d name="Название" -d icon_color=7322096

# переименовать
curl -s "https://api.telegram.org/bot$TOKEN/editForumTopic" \
  -d chat_id=$CHAT -d message_thread_id=$TOPIC -d name="Новое"

# закрыть / открыть / удалить
curl -s "https://api.telegram.org/bot$TOKEN/closeForumTopic" -d chat_id=$CHAT -d message_thread_id=$TOPIC
curl -s "https://api.telegram.org/bot$TOKEN/reopenForumTopic" -d chat_id=$CHAT -d message_thread_id=$TOPIC
curl -s "https://api.telegram.org/bot$TOKEN/deleteForumTopic" -d chat_id=$CHAT -d message_thread_id=$TOPIC
```

Отправка в топик — параметр `message_thread_id` при `sendMessage`.

## Модерация

```bash
# ограничить (мут на час)
curl -s "https://api.telegram.org/bot$TOKEN/restrictChatMember" \
  -d chat_id=$CHAT -d user_id=$USER \
  -d until_date=$(($(date +%s)+3600)) \
  -d permissions='{"can_send_messages":false}'

# бан
curl -s "https://api.telegram.org/bot$TOKEN/banChatMember" -d chat_id=$CHAT -d user_id=$USER

# разбан
curl -s "https://api.telegram.org/bot$TOKEN/unbanChatMember" -d chat_id=$CHAT -d user_id=$USER -d only_if_banned=true

# удалить сообщение
curl -s "https://api.telegram.org/bot$TOKEN/deleteMessage" -d chat_id=$CHAT -d message_id=$MSG
```

**Правило:** бан и удаление сообщений — необратимые для пользователя действия. Спрашивать владельца перед применением к живым людям, кроме очевидного спама.

Сообщения старше 48 часов бот удалить не может.

## Пригласительные ссылки

```bash
# создать с лимитом и сроком
curl -s "https://api.telegram.org/bot$TOKEN/createChatInviteLink" \
  -d chat_id=$CHAT -d name="Кампания" \
  -d expire_date=$(($(date +%s)+604800)) -d member_limit=100

# отозвать
curl -s "https://api.telegram.org/bot$TOKEN/revokeChatInviteLink" -d chat_id=$CHAT -d invite_link="$LINK"
```

Именованные ссылки позволяют считать, откуда пришли подписчики.

## Оформление чата

```bash
curl -s "https://api.telegram.org/bot$TOKEN/setChatTitle" -d chat_id=$CHAT -d title="Название"
curl -s "https://api.telegram.org/bot$TOKEN/setChatDescription" -d chat_id=$CHAT -d description="Описание"
```

## Диагностика

| Ошибка | Причина |
|--------|---------|
| `Bad Request: not enough rights` | боту не выдали право в настройках чата |
| `Bad Request: chat not found` | неверный chat_id или бот не в чате |
| `Bad Request: message can't be deleted` | сообщение старше 48 часов |
| `Forbidden: bot was blocked by the user` | пользователь заблокировал бота |
| `Too Many Requests` | лимит; в ответе есть `retry_after` — подождать столько секунд |

Лимиты Bot API: до 30 сообщений в секунду суммарно, до 20 сообщений в минуту в одну группу.
