-- Switch billing provider columns from Asaas to AbacatePay.
ALTER TABLE subscriptions
  RENAME COLUMN asaas_customer_id TO abacate_customer_id;

ALTER TABLE subscriptions
  RENAME COLUMN asaas_subscription_id TO abacate_subscription_id;
