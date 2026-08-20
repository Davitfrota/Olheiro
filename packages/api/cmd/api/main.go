package main

import (
	"log"

	"scouter-ia-api/internal/config"
	"scouter-ia-api/internal/handlers"
	"scouter-ia-api/internal/providers"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	sb := providers.NewSupabaseClient(cfg.SupabaseURL, cfg.SupabaseAnonKey)
	app := fiber.New()
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowMethods: "GET,POST,OPTIONS",
		AllowHeaders: "Origin, Content-Type, Accept",
	}))

	app.Get("/health", handlers.Health)
	app.Post("/v1/ingestion/fixtures", handlers.IngestFixtures)
	app.Post("/v1/analysis/value-gate", handlers.EvaluateValueGate)
	app.Get("/v1/predictions", handlers.ListPredictions(sb))
	app.Get("/v1/accuracy", handlers.ListAccuracy(sb))

	log.Printf("scouter-api listening on :%s", cfg.Port)
	if err := app.Listen(":" + cfg.Port); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
