package main

import (
	"log"

	"scouter-ia-api/internal/config"
	"scouter-ia-api/internal/handlers"

	"github.com/gofiber/fiber/v2"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	app := fiber.New()

	app.Get("/health", handlers.Health)
	app.Post("/v1/ingestion/fixtures", handlers.IngestFixtures)
	app.Post("/v1/analysis/value-gate", handlers.EvaluateValueGate)

	log.Printf("scouter-api listening on :%s", cfg.Port)
	if err := app.Listen(":" + cfg.Port); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
