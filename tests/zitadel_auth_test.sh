# Команды для повторной проверки:

  # Перейти в каталог проекта
  cd "/home/maksim/FTP Project"

  # Извлечь значения из .env без вывода секрета
  ZITADEL_CLIENT_ID="$(sed -n 's/^ZITADEL_CLIENT_ID=//p' .env)"
  ZITADEL_CLIENT_SECRET="$(sed -n 's/^ZITADEL_CLIENT_SECRET=//p' .env)"
  ZITADEL_DOMAIN="$(sed -n 's/^ZITADEL_DOMAIN=//p' .env)"
  PROXY_PORT="$(sed -n 's/^PROXY_HTTP_PUBLISHED_PORT=//p' .env)"

  # Проверить состояние контейнеров production-стека
  docker compose --env-file .env -f docker-compose.prod.yml ps

# Найти API-приложение по Client ID в read-model базе Zitadel.
  # Выводит только метаданные, не сам секрет.
  docker compose --env-file .env -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres -d zitadel -v ON_ERROR_STOP=1 -c "
  SELECT
      a.instance_id,
      a.app_id,
      p.name AS app_name,
      p.project_id,
      p.state,
      a.auth_method,
      (a.client_secret IS NOT NULL) AS secret_present,
      length(a.client_secret) AS stored_secret_length
  FROM projections.apps7_api_configs a
  JOIN projections.apps7 p
    ON p.instance_id = a.instance_id
   AND p.id = a.app_id
  WHERE a.client_id = '${CLIENT_ID}';
  "

#   Ожидаемый результат — одна строка. Если строк нет, Client ID относится к другой инсталляции Zitadel
#   или другой базе.

#   Можно вывести все API-приложения без секретов:

  docker compose --env-file .env -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres -d zitadel -c "
  SELECT
      a.client_id,
      p.name AS app_name,
      p.state,
      a.auth_method,
      (a.client_secret IS NOT NULL) AS secret_present
  FROM projections.apps7_api_configs a
  JOIN projections.apps7 p
    ON p.instance_id = a.instance_id
   AND p.id = a.app_id
  ORDER BY p.name;
  "

  # Проверить OIDC discovery endpoint Zitadel
  curl -sS -o /tmp/zitadel-discovery.json \
    -w 'HTTP %{http_code}\n' \
    "http://${ZITADEL_DOMAIN}:${PROXY_PORT}/.well-known/openid-configuration"

  # Получить access token через client credentials.
  # Секрет используется только внутри curl и не печатается.
  curl -sS \
    -u "${ZITADEL_CLIENT_ID}:${ZITADEL_CLIENT_SECRET}" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data 'grant_type=client_credentials&scope=openid' \
    -w '\nHTTP %{http_code}\n' \
    "http://${ZITADEL_DOMAIN}:${PROXY_PORT}/oauth/v2/token"

#   Проверка через auth-сервис:

  # Передать тестовый Bearer-токен в auth.
  # Ожидаемый результат для невалидного токена — HTTP 401,
  # а HTTP 503 означает проблему соединения auth с Zitadel.
  curl -sS -X POST \
    "http://localhost:8001/v1/authorize" \
    -H 'Authorization: Bearer deliberately-invalid-token' \
    -H 'Content-Type: application/json' \
    -d '{"resource":"service:test","action":"read"}' \
    -w '\nHTTP %{http_code}\n'

