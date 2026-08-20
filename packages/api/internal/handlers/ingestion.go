package handlers

import (
	"github.com/gofiber/fiber/v2"

	"scouter-ia-api/internal/types"
)

func IngestFixtures(c *fiber.Ctx) error {
	var req types.FixtureIngestionRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "invalid payload",
		})
	}

	if req.Source == "" || req.League == "" || req.Season == 0 {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "source, league and season are required",
		})
	}

	// Scaffold: real ingestion worker (API-Football/The Odds API + Supabase)
	// will be implemented in the next phase-0 iteration.
	return c.Status(fiber.StatusAccepted).JSON(fiber.Map{
		"status":  "queued",
		"payload": req,
	})
}
