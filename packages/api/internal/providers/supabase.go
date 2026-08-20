package providers

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"scouter-ia-api/internal/types"
)

type SupabaseClient struct {
	BaseURL string
	APIKey  string
	HTTP    *http.Client
}

func NewSupabaseClient(baseURL, apiKey string) *SupabaseClient {
	return &SupabaseClient{
		BaseURL: baseURL,
		APIKey:  apiKey,
		HTTP:    &http.Client{Timeout: 20 * time.Second},
	}
}

func (c *SupabaseClient) ListPredictions(limit int, publishedOnly bool) ([]types.PredictionDTO, error) {
	if c.BaseURL == "" || c.APIKey == "" {
		return nil, fmt.Errorf("supabase url/key not configured")
	}
	if limit <= 0 {
		limit = 50
	}

	q := url.Values{}
	q.Set("select", "id,match_id,market,selection,model_probability,market_probability,edge,confidence_score,risk_label,value_decision,is_free_tier,published_at,created_at,prediction_results(actual_outcome,was_correct,settled_at)")
	q.Set("order", "created_at.desc")
	q.Set("limit", fmt.Sprintf("%d", limit))
	if publishedOnly {
		q.Set("published_at", "not.is.null")
	}

	endpoint := fmt.Sprintf("%s/rest/v1/predictions?%s", c.BaseURL, q.Encode())
	req, err := http.NewRequest(http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("apikey", c.APIKey)
	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Accept", "application/json")

	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("supabase error %d: %s", resp.StatusCode, string(body))
	}

	var raw []map[string]any
	if err := json.Unmarshal(body, &raw); err != nil {
		return nil, err
	}

	items := make([]types.PredictionDTO, 0, len(raw))
	for _, row := range raw {
		item := types.PredictionDTO{
			ID:            asString(row["id"]),
			MatchID:       asString(row["match_id"]),
			Market:        asString(row["market"]),
			Selection:     asString(row["selection"]),
			ValueDecision: asString(row["value_decision"]),
			IsFreeTier:    asBool(row["is_free_tier"]),
			CreatedAt:     asString(row["created_at"]),
		}
		item.ModelProbability = asFloatPtr(row["model_probability"])
		item.MarketProbability = asFloatPtr(row["market_probability"])
		item.Edge = asFloatPtr(row["edge"])
		item.ConfidenceScore = asFloatPtr(row["confidence_score"])
		item.RiskLabel = asStringPtr(row["risk_label"])
		item.PublishedAt = asStringPtr(row["published_at"])

		if pr, ok := row["prediction_results"].(map[string]any); ok {
			item.ActualOutcome = asStringPtr(pr["actual_outcome"])
			item.WasCorrect = asBoolPtr(pr["was_correct"])
			item.SettledAt = asStringPtr(pr["settled_at"])
		} else if arr, ok := row["prediction_results"].([]any); ok && len(arr) > 0 {
			if pr, ok := arr[0].(map[string]any); ok {
				item.ActualOutcome = asStringPtr(pr["actual_outcome"])
				item.WasCorrect = asBoolPtr(pr["was_correct"])
				item.SettledAt = asStringPtr(pr["settled_at"])
			}
		}
		items = append(items, item)
	}
	return items, nil
}

func (c *SupabaseClient) ListAccuracySnapshots() ([]types.AccuracyDTO, error) {
	if c.BaseURL == "" || c.APIKey == "" {
		return nil, fmt.Errorf("supabase url/key not configured")
	}

	q := url.Values{}
	q.Set("select", "id,period_start,period_end,market,risk_label,total_predictions,correct_predictions,accuracy_pct,methodology_version,computed_at")
	q.Set("order", "computed_at.desc")
	q.Set("limit", "50")

	endpoint := fmt.Sprintf("%s/rest/v1/accuracy_snapshots?%s", c.BaseURL, q.Encode())
	req, err := http.NewRequest(http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("apikey", c.APIKey)
	req.Header.Set("Authorization", "Bearer "+c.APIKey)
	req.Header.Set("Accept", "application/json")

	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("supabase error %d: %s", resp.StatusCode, string(body))
	}

	var items []types.AccuracyDTO
	if err := json.Unmarshal(body, &items); err != nil {
		return nil, err
	}
	return items, nil
}

func asString(v any) string {
	if v == nil {
		return ""
	}
	s, _ := v.(string)
	return s
}

func asStringPtr(v any) *string {
	if v == nil {
		return nil
	}
	s, ok := v.(string)
	if !ok {
		return nil
	}
	return &s
}

func asFloatPtr(v any) *float64 {
	if v == nil {
		return nil
	}
	switch n := v.(type) {
	case float64:
		return &n
	case json.Number:
		f, err := n.Float64()
		if err != nil {
			return nil
		}
		return &f
	default:
		return nil
	}
}

func asBool(v any) bool {
	b, _ := v.(bool)
	return b
}

func asBoolPtr(v any) *bool {
	if v == nil {
		return nil
	}
	b, ok := v.(bool)
	if !ok {
		return nil
	}
	return &b
}
