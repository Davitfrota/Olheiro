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
	HomeTeam          *string  `json:"home_team,omitempty"`
	AwayTeam          *string  `json:"away_team,omitempty"`
	KickoffAt         *string  `json:"kickoff_at,omitempty"`
	MatchStatus       *string  `json:"match_status,omitempty"`
	HomeScore         *int     `json:"home_score,omitempty"`
	AwayScore         *int     `json:"away_score,omitempty"`
	ActualOutcome     *string  `json:"actual_outcome,omitempty"`
	WasCorrect        *bool    `json:"was_correct,omitempty"`
	SettledAt         *string  `json:"settled_at,omitempty"`
}

type PredictionsResponse struct {
	Count int             `json:"count"`
	Items []PredictionDTO `json:"items"`
}

type AccuracyDTO struct {
	ID                 string  `json:"id"`
	PeriodStart        string  `json:"period_start"`
	PeriodEnd          string  `json:"period_end"`
	Market             string  `json:"market"`
	RiskLabel          *string `json:"risk_label"`
	TotalPredictions   int     `json:"total_predictions"`
	CorrectPredictions int     `json:"correct_predictions"`
	AccuracyPct        float64 `json:"accuracy_pct"`
	MethodologyVersion string  `json:"methodology_version"`
	ComputedAt         string  `json:"computed_at"`
}

type AccuracyResponse struct {
	Count int           `json:"count"`
	Items []AccuracyDTO `json:"items"`
}
