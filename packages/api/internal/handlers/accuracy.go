package handlers

import (
	"github.com/gofiber/fiber/v2"

	"scouter-ia-api/internal/providers"
	"scouter-ia-api/internal/types"
)

func ListAccuracy(sb *providers.SupabaseClient) fiber.Handler {
	return func(c *fiber.Ctx) error {
		items, err := sb.ListAccuracySnapshots()
		if err != nil {
			return c.Status(fiber.StatusBadGateway).JSON(fiber.Map{
				"error": err.Error(),
			})
		}
		return c.JSON(types.AccuracyResponse{
			Count: len(items),
			Items: items,
		})
	}
}
