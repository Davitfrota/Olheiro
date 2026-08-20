package config

import (
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Port                   string
	SupabaseURL            string
	SupabaseAnonKey        string
	AbacatePayAPIKey       string
	AbacatePayAPIBase      string
	AbacatePayWebhookSecret string
	AbacatePayProductID    string
}

func Load() (Config, error) {
	_ = godotenv.Load("../../.env", "../../../.env", ".env")

	port := os.Getenv("SCOUTER_API_PORT")
	if port == "" {
		port = "8080"
	}
	apiBase := os.Getenv("ABACATEPAY_API_BASE")
	if apiBase == "" {
		apiBase = "https://api.abacatepay.com/v2"
	}

	return Config{
		Port:                    port,
		SupabaseURL:             os.Getenv("SUPABASE_URL"),
		SupabaseAnonKey:         os.Getenv("SUPABASE_ANON_KEY"),
		AbacatePayAPIKey:        os.Getenv("ABACATEPAY_API_KEY"),
		AbacatePayAPIBase:       apiBase,
		AbacatePayWebhookSecret: os.Getenv("ABACATEPAY_WEBHOOK_SECRET"),
		AbacatePayProductID:     os.Getenv("ABACATEPAY_PRODUCT_ID"),
	}, nil
}
