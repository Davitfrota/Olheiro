package handlers

import (
	"strconv"

	"github.com/gofiber/fiber/v2"

	"scouter-ia-api/internal/providers"
	"scouter-ia-api/internal/types"
)

func ListPredictions(sb *providers.SupabaseClient) fiber.Handler {
	return func(c *fiber.Ctx) error {
		limit, _ := strconv.Atoi(c.Query("limit", "50"))
		publishedOnly := c.Query("published", "true") != "false"

		items, err := sb.ListPredictions(limit, publishedOnly)
		if err != nil {
			return c.Status(fiber.StatusBadGateway).JSON(fiber.Map{
				"error": err.Error(),
			})
		}
		return c.JSON(types.PredictionsResponse{
			Count: len(items),
			Items: items,
		})
	}
}
