package providers

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type AbacatePayClient struct {
	BaseURL    string
	APIKey     string
	ProductID  string
	HTTP       *http.Client
}

func NewAbacatePayClient(baseURL, apiKey, productID string) *AbacatePayClient {
	return &AbacatePayClient{
		BaseURL:   baseURL,
		APIKey:    apiKey,
		ProductID: productID,
		HTTP:      &http.Client{Timeout: 25 * time.Second},
	}
}

type AbacateCheckoutRequest struct {
	Items         []AbacateItem      `json:"items"`
	CustomerID    string             `json:"customerId,omitempty"`
	ExternalID    string             `json:"externalId,omitempty"`
	ReturnURL     string             `json:"returnUrl,omitempty"`
	CompletionURL string             `json:"completionUrl,omitempty"`
	Methods       []string           `json:"methods,omitempty"`
	Metadata      map[string]string  `json:"metadata,omitempty"`
}

type AbacateItem struct {
	ID       string `json:"id"`
	Quantity int    `json:"quantity"`
}

type AbacateCheckoutData struct {
	ID  string `json:"id"`
	URL string `json:"url"`
}

type AbacateEnvelope struct {
	Data    json.RawMessage `json:"data"`
	Success bool            `json:"success"`
	Error   any             `json:"error"`
}

func (c *AbacatePayClient) CreateSubscriptionCheckout(req AbacateCheckoutRequest) (*AbacateCheckoutData, error) {
	if c.APIKey == "" {
		return nil, fmt.Errorf("ABACATEPAY_API_KEY not configured")
	}
	if len(req.Items) == 0 {
		if c.ProductID == "" {
			return nil, fmt.Errorf("ABACATEPAY_PRODUCT_ID not configured")
		}
		req.Items = []AbacateItem{{ID: c.ProductID, Quantity: 1}}
	}
	if len(req.Methods) == 0 {
		req.Methods = []string{"CARD", "PIX"}
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	endpoint := fmt.Sprintf("%s/subscriptions/create", c.BaseURL)
	httpReq, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Authorization", "Bearer "+c.APIKey)
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "application/json")

	resp, err := c.HTTP.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("abacatepay error %d: %s", resp.StatusCode, string(raw))
	}

	var env AbacateEnvelope
	if err := json.Unmarshal(raw, &env); err != nil {
		return nil, err
	}
	if !env.Success {
		return nil, fmt.Errorf("abacatepay unsuccessful: %s", string(raw))
	}

	var data AbacateCheckoutData
	if err := json.Unmarshal(env.Data, &data); err != nil {
		return nil, err
	}
	return &data, nil
}
