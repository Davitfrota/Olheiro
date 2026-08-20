package handlers

import (
	"time"

	"github.com/gofiber/fiber/v2"
)

func Health(c *fiber.Ctx) error {
	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":    "ok",
		"service":   "scouter-api",
		"timestamp": time.Now().UTC().Format(time.RFC3339),
	})
}
