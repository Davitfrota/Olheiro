package handlers

import (
	"github.com/gofiber/fiber/v2"

	"scouter-ia-api/internal/providers"
	"scouter-ia-api/internal/types"
)

func EvaluateValueGate(c *fiber.Ctx) error {
	var req types.ValueGateRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid payload",
		})
	}

	result := providers.EvaluateValueGate(req)
	return c.Status(fiber.StatusOK).JSON(result)
}
