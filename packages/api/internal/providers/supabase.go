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
	q.Set("select", "id,match_id,market,selection,model_probability,market_probability,edge,confidence_score,risk_label,value_decision,is_free_tier,published_at,created_at")
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

	var items []types.PredictionDTO
	if err := json.Unmarshal(body, &items); err != nil {
		return nil, err
	}
	return items, nil
}
