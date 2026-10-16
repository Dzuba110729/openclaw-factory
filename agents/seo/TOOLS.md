# TOOLS.md — SEO Аудитор

## Проверки без данных пользователя (делать самостоятельно)

```bash
# Robots.txt
curl -s https://DOMAIN/robots.txt

# Sitemap
curl -s https://DOMAIN/sitemap.xml | head -100

# SSL + HTTP заголовки
curl -I -s https://DOMAIN

# Цепочка редиректов
curl -ILs https://DOMAIN | grep -E "HTTP|Location"
curl -ILs http://DOMAIN | grep -E "HTTP|Location"
curl -ILs http://www.DOMAIN | grep -E "HTTP|Location"
curl -ILs https://www.DOMAIN | grep -E "HTTP|Location"

# Проверка конкретной страницы
curl -I -s https://DOMAIN/page/

# X-Robots-Tag в заголовках
curl -I -s https://DOMAIN/ | grep -i "x-robots"
```

## PageSpeed Insights API

Ключ: задаётся в projects/{domain}/.env или спрашивать у пользователя

```bash
# Core Web Vitals (mobile)
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://DOMAIN&strategy=mobile&key=API_KEY"

# Desktop
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://DOMAIN&strategy=desktop&key=API_KEY"
```

Бесплатный ключ: console.cloud.google.com → PageSpeed Insights API

## Screaming Frog CSV

Пользователь присылает CSV — анализировать колонки:
- Address, Status Code, Indexability, Title 1, Meta Description 1, H1-1, H2-1
- Canonical Link Element 1, Meta Robots 1, X-Robots-Tag
- Word Count, Size, Response Time

## GSC CSV

Отчёты:
- "Покрытие" / "Страницы" → индексация
- "Статистика сканирования" → краулинговый бюджет
- "Запросы" → трафик по страницам

## Яндекс.Вебмастер CSV

- "Индексирование" → "Страницы в поиске"
- "Диагностика" → ошибки
