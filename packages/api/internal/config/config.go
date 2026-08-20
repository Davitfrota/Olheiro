package config

import (
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Port            string
	SupabaseURL     string
	SupabaseAnonKey string
}

func Load() (Config, error) {
	_ = godotenv.Load("../../.env", "../../../.env", ".env")

	port := os.Getenv("SCOUTER_API_PORT")
	if port == "" {
		port = "8080"
	}

	return Config{
		Port:            port,
		SupabaseURL:     os.Getenv("SUPABASE_URL"),
		SupabaseAnonKey: os.Getenv("SUPABASE_ANON_KEY"),
	}, nil
}
