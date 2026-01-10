# Настройка AIMLAPI

## Шаг 1: Получение API ключа

1. Перейдите на [https://aimlapi.com/](https://aimlapi.com/)

2. Нажмите **"Get API Key"** или **"Sign Up"**

3. Создайте аккаунт (можно через Google/GitHub)

4. После входа перейдите в Dashboard

5. Скопируйте ваш **API Key**

## Шаг 2: Настройка проекта

### Вариант A: Локальный .env файл

1. Откройте файл `backend/.env`

2. Найдите строку:
   ```
   AIMLAPI_KEY=your-aimlapi-key-here
   ```

3. Замените `your-aimlapi-key-here` на ваш реальный ключ:
   ```
   AIMLAPI_KEY=sk_aiml_abcdef123456789...
   ```

4. Сохраните файл

### Вариант B: Переменные окружения

```bash
export AIMLAPI_KEY="sk_aiml_abcdef123456789..."
```

## Шаг 3: Проверка работоспособности

Запустите тест:

```bash
cd backend
python -c "
from app.core.config import settings
print(f'API Key: {settings.AIMLAPI_KEY[:20]}...')
print(f'Base URL: {settings.AIMLAPI_BASE_URL}')
print('✅ Configuration loaded successfully!')
"
```

Должно вывести:
```
API Key: sk_aiml_abcdef1234...
Base URL: https://api.aimlapi.com/v1
✅ Configuration loaded successfully!
```

## Шаг 4: Тарифные планы

### Free Tier (для начала)
- ✅ 10 requests/hour
- ✅ Доступ ко всем 400+ моделям
- ✅ Без кредитной карты

### Startup (рекомендуем)
- 💰 $99 prepaid
- ✅ 40M+ credits
- ✅ Pay-as-you-go
- ✅ Без лимитов на requests

### Production
- 💰 $50/месяц
- ✅ Выше лимиты
- ✅ Priority support

## Шаг 5: Примерные расходы

Для одного видео (все этапы):

| Этап | Модель | Примерная стоимость |
|------|--------|---------------------|
| Генерация сюжета | GPT-5.2 | ~$0.01 |
| Описание | GPT-5.2 | ~$0.015 |
| Промпт | GPT-5.2 | ~$0.005 |
| Изображение | DALL-E 3 | ~$0.04 |
| Сценарий | GPT-5.2 | ~$0.01 |
| Видео 5 сек | KLING v2.1 | ~$0.30 |
| Адаптация | GPT-5.2 | ~$0.01 |
| **ИТОГО** | | **~$0.38** |

10 сек видео будет ~$0.60

## Шаг 6: Мониторинг расходов

1. Зайдите в [Dashboard AIMLAPI](https://aimlapi.com/dashboard)

2. Вкладка **"Usage"** - смотрите статистику

3. Вкладка **"Billing"** - текущий баланс

4. Настройте **Alerts** при достижении лимита

## Безопасность

⚠️ **ВАЖНО:**
- Никогда не коммитьте `.env` файл в Git
- `.env` уже добавлен в `.gitignore`
- Не передавайте API ключ никому
- Используйте переменные окружения в production

## Troubleshooting

### Ошибка: "Invalid API Key"
```bash
# Проверьте что ключ скопирован полностью
echo $AIMLAPI_KEY

# Убедитесь что нет лишних пробелов
AIMLAPI_KEY=sk_aiml_xxx  # ✅ правильно
AIMLAPI_KEY= sk_aiml_xxx # ❌ лишний пробел
```

### Ошибка: "Rate limit exceeded"
- Вы на Free tier и превысили 10 requests/hour
- Решение: подождите час или апгрейдите план

### Ошибка: "Model not found"
```bash
# Проверьте название модели
GPT_MODEL=gpt-5.2        # ✅
GPT_MODEL=gpt5.2         # ❌
KLING_MODEL=v2.1-master  # ✅
KLING_MODEL=2.1-master   # ❌
```

## Полезные ссылки

- 📚 [AIMLAPI Документация](https://docs.aimlapi.com/)
- 💬 [AIMLAPI Discord](https://discord.gg/aimlapi)
- 📊 [Dashboard](https://aimlapi.com/dashboard)
- 💰 [Pricing](https://aimlapi.com/pricing)

## Следующие шаги

После настройки API ключа:

1. Запустите backend: `cd backend && uvicorn app.main:app --reload`
2. Запустите frontend: `cd frontend && npm run dev`
3. Создайте первый проект и протестируйте генерацию!

---

Если возникли проблемы - смотрите [QUICKSTART.md](./QUICKSTART.md)
