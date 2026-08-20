package types

type FixtureIngestionRequest struct {
	Source string `json:"source"`
	League string `json:"league"`
	Season int    `json:"season"`
	Status string `json:"status"`
}

type ValueGateRequest struct {
	PAdj                    float64 `json:"p_adj"`
	SeAdj                   float64 `json:"se_adj"`
	PFair                   float64 `json:"p_fair"`
	InformationCompleteness float64 `json:"information_completeness"`
	ThinData                bool    `json:"thin_data"`
	KMultiplier             float64 `json:"k_multiplier"`
	CompletenessThreshold   float64 `json:"completeness_threshold"`
}

type ValueGateResponse struct {
	Edge     float64 `json:"edge"`
	Decision string  `json:"decision"`
	Reason   string  `json:"reason"`
}
