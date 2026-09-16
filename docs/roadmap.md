# Domain Model and Architecture Roadmap

`STATE.md` показывает, что базовый фундамент уже реализован: Master, Auth/ZITADEL, PostgreSQL, `ServiceAssignment`, Desired/Actual State и основные hosting resources. Следующие шаги должны закрывать оставшиеся domain boundaries вертикальными срезами без расширения архитектуры сверх текущих требований.

## 1. CLI read command

Это текущий официальный `Next Step` из `STATE.md`.

Рекомендуемый сценарий:

```text
ftpctl service-plan get <id>
```

Критерии:

- используется сохранённая пользовательская сессия;
- Bearer token передаётся в Master;
- обрабатываются `404`, authorization error и transport error;
- выводится JSON или компактное текстовое представление;
- Auth и token validation не расширяются.

## 2. Identity и ownership

Зафиксировать в Master связь:

```text
User → IdentityReference(zitadel, subject_id)
```

Определить:

- `Administrator`;
- `Reseller`;
- `Customer/User`;
- область видимости ресурсов;
- проверку, что reseller работает только со своими пользователями и подписками.

Сначала достаточно persistence/application boundary, без полноценной
универсальной RBAC-системы.

## 3. Administrator и Reseller

Реализовать минимальный vertical slice:

```text
Administrator
  └── Reseller
      └── User
          └── Subscription
```

Порядок:

1. модели и репозитории;
2. lifecycle services;
3. authorization scope;
4. API create/read;
5. один CLI read/create command.

Не добавлять универсальную иерархию ролей, пока она не требуется текущими
сценариями.

## 4. Typed resource entitlements

`ServicePlan` уже содержит resource limits, но полноценное наследование должно
быть оформлено явно:

```text
Administrator capacity
  → Reseller quota
    → ServicePlan defaults
      → Subscription entitlement
        → usage/reservation
```

Минимальная модель должна поддерживать:

- тип ресурса;
- лимит;
- текущее использование;
- reservation;
- источник значения;
- расчёт effective limit;
- запрет превышения родительской квоты.

Расчёт quota находится в Master. Agents получают ограничения и сообщают usage,
но не выдают quota и не разрешают ownership.

## 5. Domain service model

Следующий заметный пробел — полноценные DNS business entities:

```text
Domain
└── DnsZone
    └── DnsRecord
```

После создания DNS entities необходимо:

- формировать DNS desired state;
- передавать его DNS Agent;
- принимать actual state;
- обеспечить idempotency по desired-state version.

Mail aliases, subdomains и database-server entities пока не добавлять без
отдельного бизнес-требования.

## 6. Первый Agent end-to-end

Рекомендуется начать с Web Agent:

```text
Master API
 → Service lifecycle
 → ServiceAssignment
 → DesiredState
 → Agent Client
 → Web Agent
 → ActualState report
```

Минимальные гарантии:

- Agent принимает только принадлежащий ему service type;
- версия desired state используется как idempotency key;
- повторная доставка безопасна;
- Agent не обращается к другим Agents;
- Master не выполняет автоматический failover.

После Web Agent тем же контрактом подключаются DNS, Mail и DB Agents.

## 7. Lifecycle и reconciliation

Явно разделить:

```text
Business lifecycle:
Subscription / Domain / Service

Provisioning state:
DesiredState / ActualState / reconciliation result
```

Необходимые проверки:

- нельзя provision service для suspended subscription;
- нельзя отправлять stale desired version;
- actual state не меняет ownership;
- замена assignment атомарно обновляет assignment и desired state;
- ошибка Agent не создаёт новый assignment автоматически.

## 8. Дополнительные infrastructure slices

После основных service domains можно добавлять отдельными slices:

- `IPAddress` / `IPAllocation`;
- certificates;
- subdomains;
- aliases;
- backups;
- metrics/reporting.

Эти возможности не являются частью текущего core domain model и не должны
добавляться заранее.

## Priority order

```text
CLI read
  → IdentityReference
  → Administrator/Reseller scopes
  → ResourceEntitlement
  → DNS Zone/Record
  → Web Agent reconciliation
  → DNS/Mail/DB Agents
  → IP allocation and optional Plesk features
```

Structurizr C4 model менять не нужно: она уже содержит Master management
components, Reseller Management, Resource Management, Scheduler и отдельные
Agents.


## Additional roadmap items to bear in mind if they do not break points above

1. Introduce Master domain types and repositories for `Account` roles,
   `ResourceLimitSet`, effective subscription limits and quota reservations.
2. Extend the existing business API from User semantics to explicit
   Administrator/Reseller/Customer ownership checks.
3. Add plan revision and subscription plan-change rules without rewriting
   historical usage.
4. Add domain/service-family creation rules and quota validation before
   placement.
5. Keep placement, desired/actual versioning and Agent reconciliation on the
   existing `ServiceAssignment` boundary; implement one vertical Agent flow
   before adding the remaining service families.