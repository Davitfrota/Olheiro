package handlers

import (
	"encoding/json"

	"github.com/gofiber/fiber/v2"

	"scouter-ia-api/internal/providers"
)

type createCheckoutBody struct {
	CustomerID    string            `json:"customerId"`
	ExternalID    string            `json:"externalId"`
	ReturnURL     string            `json:"returnUrl"`
	CompletionURL string            `json:"completionUrl"`
	Metadata      map[string]string `json:"metadata"`
}

func CreateBillingCheckout(ap *providers.AbacatePayClient) fiber.Handler {
	return func(c *fiber.Ctx) error {
		if ap == nil || ap.APIKey == "" {
			return c.Status(fiber.StatusServiceUnavailable).JSON(fiber.Map{
				"error": "abacatepay not configured",
			})
		}

		var body createCheckoutBody
		if len(c.Body()) > 0 {
			if err := c.BodyParser(&body); err != nil {
				return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid json"})
			}
		}

		checkout, err := ap.CreateSubscriptionCheckout(providers.AbacateCheckoutRequest{
			CustomerID:    body.CustomerID,
			ExternalID:    body.ExternalID,
			ReturnURL:     body.ReturnURL,
			CompletionURL: body.CompletionURL,
			Metadata:      body.Metadata,
			Methods:       []string{"CARD", "PIX"},
		})
		if err != nil {
			return c.Status(fiber.StatusBadGateway).JSON(fiber.Map{"error": err.Error()})
		}

		return c.JSON(fiber.Map{
			"id":  checkout.ID,
			"url": checkout.URL,
		})
	}
}

func AbacatePayWebhook(webhookSecret string) fiber.Handler {
	return func(c *fiber.Ctx) error {
		if webhookSecret != "" {
			got := c.Query("webhookSecret")
			if got == "" || got != webhookSecret {
				return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{"error": "invalid webhook secret"})
			}
		}

		var payload map[string]any
		if err := json.Unmarshal(c.Body(), &payload); err != nil {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{"error": "invalid json"})
		}

		event, _ := payload["event"].(string)
		if event == "" {
			event, _ = payload["type"].(string)
		}

		// Scaffold: acknowledge events; profile/subscription sync lands with auth.
		switch event {
		case "subscription.completed", "subscription.renewed", "subscription.cancelled",
			"checkout.completed", "checkout.refunded":
			return c.JSON(fiber.Map{"ok": true, "handled": event})
		default:
			return c.JSON(fiber.Map{"ok": true, "ignored": event})
		}
	}
}
