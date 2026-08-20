# Billing — AbacatePay

Único provedor de pagamento do Scouter IA.

## Fluxo MVP

1. Criar produto mensal na loja AbacatePay (`cycle: MONTHLY`) e guardar o `id` em `ABACATEPAY_PRODUCT_ID`.
2. `POST /v1/billing/checkout` → cria checkout de assinatura e devolve `url`.
3. Usuário paga (CARD/PIX) no checkout hospedado.
4. Webhook `POST /v1/billing/webhooks/abacatepay?webhookSecret=...` recebe `subscription.completed` / `renewed` / `cancelled`.
5. (próximo passo) sync → `profiles.plan` + `subscriptions`.

## Env

```
ABACATEPAY_API_KEY=
ABACATEPAY_WEBHOOK_SECRET=
ABACATEPAY_PRODUCT_ID=
ABACATEPAY_API_BASE=https://api.abacatepay.com/v2
```

Docs: https://docs.abacatepay.com
