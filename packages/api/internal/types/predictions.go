package types

type PredictionDTO struct {
	ID                string   `json:"id"`
	MatchID           string   `json:"match_id"`
	Market            string   `json:"market"`
	Selection         string   `json:"selection"`
	ModelProbability  *float64 `json:"model_probability"`
	MarketProbability *float64 `json:"market_probability"`
	Edge              *float64 `json:"edge"`
	ConfidenceScore   *float64 `json:"confidence_score"`
	RiskLabel         *string  `json:"risk_label"`
	ValueDecision     string   `json:"value_decision"`
	IsFreeTier        bool     `json:"is_free_tier"`
	PublishedAt       *string  `json:"published_at"`
	CreatedAt         string   `json:"created_at"`
}

type PredictionsResponse struct {
	Count int             `json:"count"`
	Items []PredictionDTO `json:"items"`
}
